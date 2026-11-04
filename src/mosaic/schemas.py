"""Canonical, provider-neutral data contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["system", "developer", "user", "assistant", "tool", "unknown"]
KnowledgeKind = Literal[
    "concept",
    "claim",
    "constraint",
    "decision",
    "procedure",
    "strategy_observation",
    "finding",
    "preference",
    "outcome",
    "open_question",
]
KnowledgeScope = Literal["personal", "general"]
InterpretationClass = Literal["explicit", "inferred", "user_confirmed"]


class CanonicalMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_message_id: str | None = None
    parent_provider_message_id: str | None = None
    sequence_no: int = Field(ge=0)
    role: Role = "unknown"
    author_label: str | None = None
    model_label: str | None = None
    created_at: datetime | None = None
    content_text: str = ""
    modality: str = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_conversation_id: str | None = None
    title: str = "Untitled conversation"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    messages: list[CanonicalMessage]

    @field_validator("messages")
    @classmethod
    def require_messages(cls, value: list[CanonicalMessage]) -> list[CanonicalMessage]:
        if not value:
            raise ValueError("A conversation must contain at least one message")
        if len(value) > 100_000:
            raise ValueError("Conversation exceeds the 100,000-message safety limit")
        return value


class ImportResponse(BaseModel):
    source_artifact_id: str
    provider: str
    conversation_count: int
    message_count: int
    duplicate: bool = False
    warnings: list[str] = Field(default_factory=list)


class KnowledgeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: KnowledgeKind
    scope: KnowledgeScope = "personal"
    canonical_text: str = Field(min_length=3, max_length=2_000)
    description: str = Field(default="", max_length=8_000)
    interpretation_class: InterpretationClass = "inferred"
    source_message_ids: list[str] = Field(min_length=1, max_length=50)
    exact_span: str | None = Field(default=None, max_length=4_000)
    strategy_labels: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("source_message_ids")
    @classmethod
    def unique_source_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("source_message_ids must be unique")
        return value


class KnowledgeReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["confirm", "reject", "withdraw"]
    rationale: str = Field(default="", max_length=4_000)


class AnalysisSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(default="", max_length=12_000)
    items: list[KnowledgeCandidate] = Field(default_factory=list, max_length=200)


class ObjectiveCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    objective_text: str = Field(min_length=1, max_length=8_000)
    expected_output: str = Field(default="", max_length=4_000)
    constraints: list[str] = Field(default_factory=list, max_length=50)
    non_goals: list[str] = Field(default_factory=list, max_length=50)


class ContextPacketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_provider: str = Field(
        min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$"
    )
    requested_role: str = Field(min_length=1, max_length=500)
    knowledge_item_ids: list[str] = Field(default_factory=list, max_length=100)
    include_open_questions: bool = True
    max_chars: int = Field(default=18_000, ge=1_000, le=40_000)


class ProviderPolicyReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_url: str = Field(min_length=12, max_length=2_000)
    policy_version: str = Field(min_length=1, max_length=120)
    policy_status: Literal["allowed_with_conditions", "restricted", "prohibited"]
    notes: str = Field(min_length=1, max_length=8_000)
    user_acknowledged: bool = Field(default=False, validate_default=True)

    @field_validator("policy_url")
    @classmethod
    def require_https_policy_url(cls, value: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(value.strip())
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("policy_url must be an HTTPS URL")
        return value.strip()

    @field_validator("user_acknowledged")
    @classmethod
    def require_user_acknowledgement(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Explicitly acknowledge that you reviewed the provider policy")
        return value