"""FastAPI application and local API routes."""

from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager, closing
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field

from mosaic import __version__
from mosaic.config import Settings
from mosaic.db.database import Database
from mosaic.repositories import (
    create_analysis_candidates,
    create_analysis_handoff,
    get_analysis_handoff,
    ensure_default_workspace,
    get_conversation,
    get_policy_flags,
    list_conversations,
    list_imports,
    list_knowledge,
    record_provider_policy_review,
    record_user_permissions,
    require_provider_transfer_review,
    search_messages,
)
from mosaic.schemas import (
    AnalysisSubmission,
    ContextPacketRequest,
    ImportResponse,
    KnowledgeReviewRequest,
    ObjectiveCreate,
    ProviderPolicyReviewRequest,
)
from mosaic.semantic.assisted import build_analysis_prompt
from mosaic.semantic.ollama import LocalModelUnavailable, analyse_with_ollama
from mosaic.semantic.segmentation import segment_messages
from mosaic.services.coordination import (
    CoordinationRejected,
    build_context_packet,
    create_objective,
    save_model_response,
)
from mosaic.services.imports import ImportRejected, execute_import

logger = logging.getLogger("mosaic")


class ProviderPermissions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_store: bool = False
    allow_index: bool = False
    allow_derive: bool = False
    allow_strategy_analysis: bool = False
    allow_cross_provider_transfer: bool = False


class AnalysisPacketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_provider: str = Field(
        min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$"
    )
    include_strategies: bool = False


class AnalysisIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_id: str = Field(min_length=36, max_length=36)
    confirm_local_storage: bool = False
    confirm_manual_authorship: bool = False
    analysis: AnalysisSubmission


class ModelResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    model_label: str = Field(default="unknown", max_length=120)
    response_text: str = Field(min_length=1, max_length=200_000)
    confirm_local_storage: bool = False
    confirm_manual_authorship: bool = False


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = database or Database(settings.data_dir / "mosaic.sqlite3")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        database.migrate()
        app.state.workspace_id = ensure_default_workspace(database)
        yield

    app = FastAPI(
        title="Mosaic Local API",
        version=__version__,
        description="Local-first, source-grounded conversation intelligence.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "[::1]"],
    )
    @app.middleware("http")
    async def reject_untrusted_browser_origins(request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origins:
            return JSONResponse(status_code=403, content={"detail": "Untrusted browser origin"})
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    def workspace_id() -> str:
        value = getattr(app.state, "workspace_id", None)
        if not value:
            raise HTTPException(status_code=503, detail="Workspace has not been initialised")
        return str(value)

    @app.get("/api/v1/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "application": "Mosaic",
            "version": __version__,
            "database": "sqlite",
            "local_model_configured": bool(settings.ollama_model),
            "workspace_ready": bool(getattr(app.state, "workspace_id", None)),
        }

    @app.get("/api/v1/settings/providers")
    def provider_settings() -> list[dict[str, Any]]:
        with closing(database.connect()) as connection:
            rows = connection.execute(
                """SELECT provider,product,policy_status,allow_store,allow_index,allow_derive,
                          allow_strategy_analysis,allow_cross_provider_transfer,allow_model_training,
                          reviewed_at,notes
                   FROM provider_policies WHERE workspace_id=? ORDER BY provider""",
                (workspace_id(),),
            ).fetchall()
            return [dict(row) for row in rows]

    @app.put("/api/v1/settings/providers/{provider}/permissions")
    def update_provider_permissions(provider: str, permissions: ProviderPermissions) -> dict[str, Any]:
        provider_key = provider.strip().lower()
        if not provider_key or len(provider_key) > 80:
            raise HTTPException(status_code=400, detail="Invalid provider identifier")
        record_user_permissions(
            database,
            workspace_id(),
            provider_key,
            allow_store=permissions.allow_store,
            allow_index=permissions.allow_index,
            allow_derive=permissions.allow_derive,
            allow_strategy_analysis=permissions.allow_strategy_analysis,
            allow_cross_provider_transfer=permissions.allow_cross_provider_transfer,
        )
        return {
            "provider": provider_key,
            **permissions.model_dump(),
            "policy_status": "unreviewed",
            "notice": "User permissions are recorded separately from provider policy review.",
        }

    @app.put("/api/v1/settings/providers/{provider}/policy-review")
    def review_provider_policy(
        provider: str, request: ProviderPolicyReviewRequest
    ) -> dict[str, Any]:
        provider_key = provider.strip().lower()
        if not provider_key or len(provider_key) > 80 or provider_key in {"manual", "local"}:
            raise HTTPException(status_code=400, detail="Invalid external provider identifier")
        return record_provider_policy_review(
            database,
            workspace_id(),
            provider_key,
            policy_url=request.policy_url,
            policy_version=request.policy_version,
            policy_status=request.policy_status,
            notes=request.notes,
        )

    @app.post("/api/v1/imports", response_model=ImportResponse)
    async def create_import(
        file: Annotated[UploadFile, File()],
        confirm_local_storage: Annotated[bool, Form()],
        enable_local_indexing: Annotated[bool, Form()] = False,
        enable_semantic_analysis: Annotated[bool, Form()] = False,
        enable_strategy_analysis: Annotated[bool, Form()] = False,
        enable_cross_provider_transfer: Annotated[bool, Form()] = False,
    ) -> ImportResponse:
        data = await file.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Upload exceeds configured size limit")
        try:
            outcome = execute_import(
                database, settings, workspace_id=workspace_id(), filename=file.filename, data=data,
                confirm_local_storage=confirm_local_storage,
                enable_local_indexing=enable_local_indexing,
                enable_semantic_analysis=enable_semantic_analysis,
                enable_strategy_analysis=enable_strategy_analysis,
                enable_cross_provider_transfer=enable_cross_provider_transfer,
            )
        except ImportRejected as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception:
            logger.exception("Import failed")
            raise HTTPException(status_code=500, detail="Import failed; see local application log")
        finally:
            await file.close()
        return ImportResponse(
            source_artifact_id=outcome.source_artifact_id,
            provider=outcome.provider,
            conversation_count=outcome.conversation_count,
            message_count=outcome.message_count,
            duplicate=outcome.duplicate,
            warnings=outcome.warnings,
        )

    @app.get("/api/v1/imports")
    def imports() -> list[dict[str, Any]]:
        return list_imports(database, workspace_id())

    @app.get("/api/v1/conversations")
    def conversations(limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
        return list_conversations(database, workspace_id(), limit)

    @app.get("/api/v1/conversations/{conversation_id}")
    def conversation_detail(conversation_id: str) -> dict[str, Any]:
        result = get_conversation(database, conversation_id)
        if not result or result["workspace_id"] != workspace_id():
            raise HTTPException(status_code=404, detail="Conversation not found")
        return result

    @app.get("/api/v1/conversations/{conversation_id}/report")
    def conversation_report(conversation_id: str) -> dict[str, Any]:
        result = get_conversation(database, conversation_id)
        if not result or result["workspace_id"] != workspace_id():
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {
            "conversation_id": conversation_id,
            "title": result["title"],
            "provider": result["provider"],
            "message_count": len(result["messages"]),
            "episodes": segment_messages(result["messages"]),
            "semantic_analysis": "not_run",
            "note": "Episode boundaries are deterministic. No LLM-generated summary is implied.",
        }

    @app.get("/api/v1/search")
    def search(q: str, limit: int = 30) -> list[dict[str, Any]]:
        if len(q) > 300:
            raise HTTPException(status_code=400, detail="Search query is too long")
        if not 1 <= limit <= 100:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        return search_messages(database, workspace_id(), q, limit)

    @app.get("/api/v1/search/knowledge")
    def search_knowledge_route(q: str, limit: int = 30) -> list[dict[str, Any]]:
        if len(q) > 300 or not 1 <= limit <= 100:
            raise HTTPException(status_code=400, detail="Invalid query or result limit")
        from mosaic.repositories import search_knowledge
        return search_knowledge(database, workspace_id(), q, limit)

    @app.post("/api/v1/conversations/{conversation_id}/analysis-packet")
    def analysis_packet(conversation_id: str, request: AnalysisPacketRequest) -> dict[str, Any]:
        conversation = get_conversation(database, conversation_id)
        if not conversation or conversation["workspace_id"] != workspace_id():
            raise HTTPException(status_code=404, detail="Conversation not found")
        flags = get_policy_flags(database, workspace_id(), conversation["provider"])
        if not flags["allow_derive"]:
            raise HTTPException(status_code=403, detail="Semantic analysis is disabled for this source provider")
        if request.include_strategies and not flags["allow_strategy_analysis"]:
            raise HTTPException(status_code=403, detail="Strategy analysis is disabled for this source provider")
        destination = request.destination_provider.strip().lower()
        if destination not in {"manual", "local"}:
            if destination != conversation["provider"] and not flags["allow_cross_provider_transfer"]:
                raise HTTPException(status_code=403, detail="Cross-provider transfer is disabled for this source")
            try:
                require_provider_transfer_review(
                    database, workspace_id(), conversation["provider"], destination
                )
            except PermissionError as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
        try:
            prompt, redaction_report = build_analysis_prompt(
                conversation, include_strategies=request.include_strategies
            )
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        if not destination or len(destination) > 80:
            raise HTTPException(status_code=400, detail="Invalid destination provider")
        if destination == "local":
            raise HTTPException(status_code=400, detail="Use the local analysis endpoint for local inference")
        handoff_id = create_analysis_handoff(
            database, workspace_id=workspace_id(), conversation_id=conversation_id,
            source_provider=conversation["provider"], destination_provider=destination,
            content_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            redaction_report=redaction_report,
        )
        return {
            "conversation_id": conversation_id,
            "destination_provider": destination,
            "handoff_id": handoff_id,
            "expires_in_seconds": 24 * 60 * 60,
            "prompt": prompt,
            "message_count": len(conversation["messages"]),
            "redaction_report": redaction_report,
            "transfer_warning": "Review the packet before pasting it into another provider. This handoff can be used once and expires after 24 hours.",
        }

    @app.post("/api/v1/conversations/{conversation_id}/analysis")
    def ingest_analysis(conversation_id: str, request: AnalysisIngestRequest) -> dict[str, Any]:
        conversation = get_conversation(database, conversation_id)
        if not conversation or conversation["workspace_id"] != workspace_id():
            raise HTTPException(status_code=404, detail="Conversation not found")
        handoff = get_analysis_handoff(
            database, workspace_id=workspace_id(), conversation_id=conversation_id,
            handoff_id=request.handoff_id,
        )
        if not handoff:
            raise HTTPException(status_code=404, detail="Analysis handoff not found")
        if handoff["status"] != "prepared":
            raise HTTPException(status_code=409, detail="Analysis handoff has already been used or revoked")
        if handoff["destination_provider"] not in {"manual", "local"} and not request.confirm_local_storage:
            raise HTTPException(status_code=400, detail="Confirm local storage of the external analysis response")
        if handoff["destination_provider"] == "manual" and not request.confirm_manual_authorship:
            raise HTTPException(status_code=400, detail="Confirm that this is your own manually authored analysis")
        if any(item.interpretation_class == "user_confirmed" for item in request.analysis.items):
            raise HTTPException(status_code=422, detail="Only the user review action can mark knowledge as user_confirmed")
        try:
            created = create_analysis_candidates(
                database,
                workspace_id=workspace_id(),
                conversation_id=conversation_id,
                summary=request.analysis.summary,
                items=[item.model_dump() for item in request.analysis.items],
                handoff_id=request.handoff_id,
                confirm_local_storage=request.confirm_local_storage,
                confirm_manual_authorship=request.confirm_manual_authorship,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            message = str(exc)
            status = 409 if "handoff" in message.lower() else 422
            raise HTTPException(status_code=status, detail=message) from exc
        return {"conversation_id": conversation_id, "created": created,
                "analysis_provider": handoff["destination_provider"],
                "notice": "All extracted items remain candidates until reviewed by the user."}

    @app.post("/api/v1/conversations/{conversation_id}/analyse-local")
    async def analyse_local(conversation_id: str) -> dict[str, Any]:
        conversation = get_conversation(database, conversation_id)
        if not conversation or conversation["workspace_id"] != workspace_id():
            raise HTTPException(status_code=404, detail="Conversation not found")
        flags = get_policy_flags(database, workspace_id(), conversation["provider"])
        if not flags["allow_derive"]:
            raise HTTPException(status_code=403, detail="Local semantic analysis is disabled for this source")
        if not flags["allow_strategy_analysis"]:
            include_strategies = False
        else:
            include_strategies = True
        try:
            prompt, redaction_report = build_analysis_prompt(conversation, include_strategies=include_strategies)
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        try:
            analysis = await analyse_with_ollama(settings, prompt)
            if any(item.interpretation_class == "user_confirmed" for item in analysis.items):
                raise ValueError("Only the user review action can mark knowledge as user_confirmed")
            if (
                any(item.kind == "strategy_observation" for item in analysis.items)
                and not flags["allow_strategy_analysis"]
            ):
                raise ValueError("Local model returned strategy observations when strategy analysis is disabled")
            created = create_analysis_candidates(
                database, workspace_id=workspace_id(), conversation_id=conversation_id,
                summary=analysis.summary, items=[item.model_dump() for item in analysis.items],
                analysis_provider="local",
            )
        except LocalModelUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"conversation_id": conversation_id, "created": created,
                "analysis_provider": "local",
                "redaction_report": redaction_report,
                "notice": "All items remain candidates pending user review.",
            }

    @app.get("/api/v1/knowledge")
    def knowledge(limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
        return list_knowledge(database, workspace_id(), limit)

    @app.post("/api/v1/knowledge/{knowledge_id}/review")
    def review_knowledge(knowledge_id: str, request: KnowledgeReviewRequest) -> dict[str, Any]:
        from mosaic.repositories import review_knowledge_item
        try:
            return review_knowledge_item(
                database, workspace_id=workspace_id(), knowledge_id=knowledge_id,
                decision=request.decision, rationale=request.rationale,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


    @app.get("/api/v1/knowledge/{knowledge_id}/sources")
    def knowledge_sources(knowledge_id: str) -> list[dict[str, Any]]:
        from mosaic.repositories import get_knowledge_sources

        with closing(database.connect()) as connection:
            found = connection.execute(
                "SELECT 1 FROM knowledge_items WHERE id=? AND workspace_id=?",
                (knowledge_id, workspace_id()),
            ).fetchone()
        if not found:
            raise HTTPException(status_code=404, detail="Knowledge item not found")
        return get_knowledge_sources(database, knowledge_id)

    @app.post("/api/v1/objectives")
    def objective_create(payload: ObjectiveCreate) -> dict[str, Any]:
        objective_id = create_objective(database, workspace_id(), payload.model_dump())
        return {"objective_id": objective_id, "status": "active"}

    @app.post("/api/v1/objectives/{objective_id}/packets")
    def objective_packet(objective_id: str, request: ContextPacketRequest) -> dict[str, Any]:
        try:
            return build_context_packet(
                database, workspace_id=workspace_id(), objective_id=objective_id,
                destination_provider=request.destination_provider.strip().lower(),
                requested_role=request.requested_role,
                knowledge_item_ids=request.knowledge_item_ids,
                include_open_questions=request.include_open_questions,
                max_chars=request.max_chars,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CoordinationRejected as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/api/v1/objectives/{objective_id}/responses")
    def objective_response(objective_id: str, request: ModelResponseRequest) -> dict[str, Any]:
        try:
            response_id = save_model_response(
                database, workspace_id=workspace_id(), objective_id=objective_id,
                session_id=request.session_id,
                model_label=request.model_label, response_text=request.response_text,
                confirm_local_storage=request.confirm_local_storage,
                confirm_manual_authorship=request.confirm_manual_authorship,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CoordinationRejected as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"response_id": response_id, "status": "response_received"}

    return app