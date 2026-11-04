import { useEffect, useState } from 'react';
import {
  Activity, Archive, BookOpen, BrainCircuit, CheckCircle2, ChevronRight,
  CircleAlert, Copy, FileText, FolderOpen, Gauge, MessageSquare, RefreshCw,
  Search, ShieldCheck, Sparkles, Upload, Workflow,
} from 'lucide-react';

type Conversation = {
  id: string; provider: string; title: string; imported_at: string; message_count: number;
};
type Knowledge = {
  id: string; kind: string; scope: string; canonical_text: string; description: string;
  status: string; interpretation_class: string; support_level: string; evidence_count: number;
};
type Health = { status: string; version: string; local_model_configured: boolean };
type ProviderPolicy = {
  provider: string; policy_status: string; policy_url: string | null;
  policy_version: string | null; reviewed_at: string | null; notes: string;
};
type Tab = 'overview' | 'imports' | 'conversations' | 'knowledge' | 'settings';
const API = 'http://127.0.0.1:8765/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body as T;
}

export default function App() {
  const [tab, setTab] = useState<Tab>('overview');
  const [health, setHealth] = useState<Health | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [knowledge, setKnowledge] = useState<Knowledge[]>([]);
  const [providerPolicies, setProviderPolicies] = useState<ProviderPolicy[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [confirmStore, setConfirmStore] = useState(false);
  const [allowIndex, setAllowIndex] = useState(false);
  const [allowAnalysis, setAllowAnalysis] = useState(false);
  const [allowStrategies, setAllowStrategies] = useState(false);
  const [allowTransfer, setAllowTransfer] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [analysisPacket, setAnalysisPacket] = useState('');
  const [analysisHandoffId, setAnalysisHandoffId] = useState('');
  const [analysisJsonText, setAnalysisJsonText] = useState('');
  const [analysisStorageConfirmed, setAnalysisStorageConfirmed] = useState(false);
  const [analysisManualConfirmed, setAnalysisManualConfirmed] = useState(false);
  const [destination, setDestination] = useState('chatgpt');
  const [policyProvider, setPolicyProvider] = useState('chatgpt');
  const [policyUrl, setPolicyUrl] = useState('');
  const [policyVersion, setPolicyVersion] = useState('');
  const [policyStatus, setPolicyStatus] = useState('allowed_with_conditions');
  const [policyNotes, setPolicyNotes] = useState('');
  const [policyAcknowledged, setPolicyAcknowledged] = useState(false);

  const refresh = async () => {
    const [h, c, k, p] = await Promise.all([
      request<Health>('/health'), request<Conversation[]>('/conversations'),
      request<Knowledge[]>('/knowledge'), request<ProviderPolicy[]>('/settings/providers'),
    ]);
    setHealth(h); setConversations(c); setKnowledge(k); setProviderPolicies(p);
  };
  useEffect(() => { refresh().catch((e) => setError(e.message)); }, []);

  const reviewProviderPolicy = async () => {
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await request<ProviderPolicy>(`/settings/providers/${encodeURIComponent(policyProvider)}/policy-review`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          policy_url: policyUrl, policy_version: policyVersion, policy_status: policyStatus,
          notes: policyNotes, user_acknowledged: policyAcknowledged,
        }),
      });
      setNotice(`Recorded your ${result.policy_status} policy review for ${result.provider}. This is your attestation, not a Mosaic legal determination.`);
      setPolicyAcknowledged(false);
      await refresh();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const openConversation = async (id: string) => {
    setSelected(id); setAnalysisPacket(''); setAnalysisHandoffId(''); setAnalysisJsonText(''); setAnalysisStorageConfirmed(false); setAnalysisManualConfirmed(false); setError('');
    try { setDetail(await request(`/conversations/${id}`)); }
    catch (e) { setError((e as Error).message); }
  };

  const upload = async () => {
    if (!file) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('confirm_local_storage', String(confirmStore));
      form.append('enable_local_indexing', String(allowIndex));
      form.append('enable_semantic_analysis', String(allowAnalysis));
      form.append('enable_strategy_analysis', String(allowStrategies));
      form.append('enable_cross_provider_transfer', String(allowTransfer));
      const result = await request<any>('/imports', { method: 'POST', body: form });
      setNotice(result.duplicate ? 'This archive was already imported.' :
        `Imported ${result.conversation_count} conversations and ${result.message_count} messages.`);
      setFile(null);
      await refresh(); setTab('conversations');
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const search = async () => {
    if (!query.trim()) { setSearchResults([]); return; }
    setError('');
    try { setSearchResults(await request<any[]>(`/search?q=${encodeURIComponent(query)}`)); }
    catch (e) { setError((e as Error).message); }
  };

  const prepareAnalysis = async () => {
    if (!selected) return;
    setBusy(true); setError('');
    try {
      const result = await request<any>(`/conversations/${selected}/analysis-packet`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destination_provider: destination, include_strategies: allowStrategies }),
      });
      setAnalysisPacket(result.prompt); setAnalysisHandoffId(result.handoff_id); setAnalysisJsonText(''); setAnalysisStorageConfirmed(false); setAnalysisManualConfirmed(false);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const copyPacket = async () => {
    try { await navigator.clipboard.writeText(analysisPacket); setNotice('Analysis prompt copied. Review it before pasting into the selected AI.'); }
    catch { setError('Clipboard access is unavailable. Select and copy the prompt manually.'); }
  };

  const analyseLocal = async () => {
    if (!selected) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await request<any>(`/conversations/${selected}/analyse-local`, { method: 'POST' });
      setNotice(`${result.created.length} local analysis candidates created. Review them in Knowledge.`);
      await refresh();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const importAnalysis = async () => {
    if (!selected || !analysisJsonText.trim() || !analysisHandoffId) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const parsed = JSON.parse(analysisJsonText);
      const result = await request<any>(`/conversations/${selected}/analysis`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handoff_id: analysisHandoffId, confirm_local_storage: analysisStorageConfirmed, confirm_manual_authorship: analysisManualConfirmed, analysis: parsed }),
      });
      setNotice(`${result.created.length} knowledge candidates saved. Review them in the Knowledge workspace.`);
      setAnalysisJsonText(''); setAnalysisPacket(''); setAnalysisHandoffId(''); setAnalysisStorageConfirmed(false); setAnalysisManualConfirmed(false); await refresh();
    } catch (e) { setError(/JSON|Unexpected token|position/i.test((e as Error).message) ? `Analysis response could not be parsed: ${(e as Error).message}` : (e as Error).message); }
    finally { setBusy(false); }
  };

  const reviewItem = async (id: string, decision: 'confirm' | 'reject') => {
    setError(''); setNotice('');
    try {
      const result = await request<any>(`/knowledge/${id}/review`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, rationale: '' }),
      });
      setNotice(`Knowledge ${decision === 'confirm' ? 'confirmed by you' : 'rejected'}; status: ${result.status}.`);
      await refresh();
    } catch (e) { setError((e as Error).message); }
  };

  const tabs: { id: Tab; label: string; icon: typeof Activity }[] = [
    { id: 'overview', label: 'Overview', icon: Gauge }, { id: 'imports', label: 'Import', icon: Archive },
    { id: 'conversations', label: 'Conversations', icon: MessageSquare },
    { id: 'knowledge', label: 'Knowledge', icon: BookOpen },
    { id: 'settings', label: 'Settings', icon: ShieldCheck },
  ];

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><BrainCircuit size={22}/></div><div><strong>MOSAIC</strong><span>Conversation intelligence</span></div></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{tabs.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}><Icon size={17}/>{label}{id === 'conversations' && <span className="nav-count">{conversations.length}</span>}</button>)}</nav>
      <div className="sidebar-bottom">
        <div className="status-card"><div className="status-head"><span className={`status-dot ${health?.status === 'ok' ? 'online' : ''}`}/><b>{health?.status === 'ok' ? 'Local engine online' : 'Connecting'}</b></div><p>Data stays on this device. Provider pages are never read automatically.</p><span className="version">Mosaic {health?.version || '—'}</span></div>
      </div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div><span className="breadcrumb">Personal workspace</span><ChevronRight size={14}/><strong>{tabs.find((t) => t.id === tab)?.label}</strong></div><div className="top-actions"><span className="local-pill"><ShieldCheck size={14}/> Local-first</span><button className="icon-button" title="Refresh" onClick={() => refresh().catch((e) => setError(e.message))}><RefreshCw size={16}/></button></div></header>
      <div className="page-content">
        {error && <div className="alert error"><CircleAlert size={17}/><span>{error}</span><button onClick={() => setError('')}>Dismiss</button></div>}
        {notice && <div className="alert success"><CheckCircle2 size={17}/><span>{notice}</span><button onClick={() => setNotice('')}>Dismiss</button></div>}
        {tab === 'overview' && <>
          <div className="welcome-row"><div><div className="eyebrow">YOUR INDEPENDENT KNOWLEDGE LAYER</div><h1>Good to see you.</h1><p>Bring your AI conversations together. Keep the knowledge, decisions and methods that matter.</p></div><button className="primary" onClick={() => setTab('imports')}><Upload size={16}/> Import conversations</button></div>
          <section className="stats-grid"><Stat icon={Archive} label="Imported conversations" value={conversations.length}/><Stat icon={MessageSquare} label="Messages indexed" value={conversations.reduce((n, c) => n + c.message_count, 0)}/><Stat icon={BookOpen} label="Knowledge candidates" value={knowledge.length}/><Stat icon={Sparkles} label="Local model" value={health?.local_model_configured ? 'Configured' : 'Optional'}/></section>
          <div className="section-heading"><div><h2>Recent conversations</h2><p>Your source history, preserved and searchable.</p></div><button className="text-button" onClick={() => setTab('conversations')}>View all <ChevronRight size={15}/></button></div>
          <ConversationList conversations={conversations.slice(0, 5)} onSelect={openConversation}/>
          <div className="callout"><div className="callout-icon"><Workflow size={20}/></div><div><b>From conversation to reusable knowledge</b><p>Import a transcript, review its source-linked insights, and prepare a context handoff for another AI. Nothing is promoted automatically.</p></div></div>
        </>}
        {tab === 'imports' && <>
          <div className="page-title"><div className="eyebrow">SOURCE INTAKE</div><h1>Import conversations</h1><p>Start with an official export archive or a pasted transcript.</p></div>
          <div className="import-layout"><section className="panel upload-panel"><div className="panel-title"><div className="panel-icon"><FolderOpen size={19}/></div><div><h2>Choose a source file</h2><p>ChatGPT ZIP / JSON, TXT or Markdown</p></div></div>
            <label className="dropzone"><input type="file" accept=".zip,.json,.txt,.md" onChange={(e) => setFile(e.target.files?.[0] || null)}/><Upload size={26}/><b>{file ? file.name : 'Choose a file to import'}</b><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'or drag it here · maximum 100 MB'}</span></label>
            <div className="permission-title">Local data permissions</div>
            <Check checked={confirmStore} onChange={setConfirmStore} title="Store the original archive locally" desc="Mosaic will retain the original source file and parsed messages on this device."/>
            <Check checked={allowIndex} onChange={setAllowIndex} title="Index messages for local search" desc="Message text will be added to the local SQLite full-text index."/>
            <Check checked={allowAnalysis} onChange={setAllowAnalysis} title="Allow semantic analysis of this source" desc="Enables user-mediated or local-model extraction into candidate knowledge items."/>
            <Check checked={allowStrategies} onChange={setAllowStrategies} title="Allow observable strategy analysis" desc="Permits analysis of visible problem-solving behaviours, not hidden chain-of-thought."/>
            <Check checked={allowTransfer} onChange={setAllowTransfer} title="Allow cross-provider context transfer" desc="Permits selected source-derived material to be included in a handoff to another provider."/>
            <div className="policy-note"><ShieldCheck size={16}/><span>Indexing is optional. Cross-provider handoffs additionally require a recorded review of both providers in Settings. Mosaic records your attestation; it does not provide legal advice.</span></div>
            <button className="primary full" disabled={!file || !confirmStore || busy} onClick={upload}>{busy ? 'Importing…' : 'Import and index source'} <ChevronRight size={16}/></button>
          </section><aside className="panel info-panel"><h3>Supported in this build</h3><div className="provider-row"><span className="provider-logo openai">C</span><div><b>ChatGPT</b><small>Official ZIP / conversations.json</small></div><span className="supported">Available</span></div><div className="provider-row"><span className="provider-logo manual">TXT</span><div><b>Manual transcript</b><small>TXT / Markdown with speaker labels</small></div><span className="supported">Available</span></div><div className="provider-row muted"><span className="provider-logo">Cl</span><div><b>Claude</b><small>Fixture-verified adapter pending</small></div><span className="pending">Planned</span></div><div className="provider-row muted"><span className="provider-logo">G</span><div><b>Gemini</b><small>Takeout adapter pending</small></div><span className="pending">Planned</span></div><div className="divider"/><h3>Import safety</h3><ul className="safety-list"><li>Archives are inspected without extracting files.</li><li>Path traversal, symbolic links and decompression bombs are rejected.</li><li>Original sources are content-addressed and deduplicated.</li><li>Unsupported structures fail visibly; no silent data loss.</li></ul></aside></div>
        </>}
        {tab === 'conversations' && <>
          <div className="page-title"><div className="eyebrow">SOURCE LIBRARY</div><h1>Conversations</h1><p>Search original messages and open their source context.</p></div>
          <div className="searchbar"><Search size={17}/><input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} placeholder="Search concepts, questions or exact phrases…"/><button onClick={search}>Search</button></div>
          {searchResults.length > 0 && <div className="search-results"><div className="subheading">Search results</div>{searchResults.map((result) => <button className="search-result" key={result.message_id} onClick={() => openConversation(result.conversation_id)}><span className="result-role">{result.role}</span><span><b>{result.title}</b><small>{result.excerpt}</small></span></button>)}</div>}
          <div className="library-layout"><div><ConversationList conversations={conversations} onSelect={openConversation} selected={selected}/></div>{detail ? <section className="panel detail-panel"><div className="detail-heading"><div><div className="eyebrow">{detail.provider}</div><h2>{detail.title}</h2><p>{detail.messages.length} messages · source preserved</p></div><button className="icon-button" onClick={() => {setDetail(null);setSelected(null);setAnalysisPacket('');setAnalysisHandoffId('');setAnalysisJsonText('');setAnalysisManualConfirmed(false);setAnalysisStorageConfirmed(false);}}>×</button></div><div className="message-list">{detail.messages.map((message: any) => <div className={`message message-${message.role}`} key={message.id}><div className="message-meta"><span>{message.role}</span><code>#{message.sequence_no}</code></div><p>{message.content_text || `[${message.modality} content not decoded]`}</p><code className="message-id">{message.id}</code></div>)}</div><div className="handoff-tools">{health?.local_model_configured && <button className="secondary" disabled={busy} onClick={analyseLocal}><BrainCircuit size={15}/> Analyse with local model</button>}<label>Analysis destination<select value={destination} onChange={(e) => {setDestination(e.target.value); setAnalysisPacket(''); setAnalysisHandoffId(''); setAnalysisJsonText(''); setAnalysisStorageConfirmed(false); setAnalysisManualConfirmed(false);}}><option value="manual">Manual analysis</option><option value="chatgpt">ChatGPT</option><option value="claude">Claude</option><option value="gemini">Gemini</option></select></label><button className="secondary" disabled={busy} onClick={prepareAnalysis}><Sparkles size={15}/> Prepare analysis prompt</button>{analysisPacket && <div className="packet-box"><div className="packet-head"><b>Source-grounded analysis prompt</b><button className="text-button" onClick={copyPacket}><Copy size={14}/> Copy</button></div><textarea readOnly value={analysisPacket}/><small>Handoff expires after 24 hours and can be used once. Review the prompt before transferring it. Cross-provider use requires source and destination policy review.</small><div className="packet-head response-heading"><b>Paste the model's JSON response</b></div><textarea className="response-input" value={analysisJsonText} onChange={(e) => setAnalysisJsonText(e.target.value)} placeholder={`{
  "summary": "...",
  "items": []
}`}/>{destination === 'manual' ? <label className="response-consent"><input type="checkbox" checked={analysisManualConfirmed} onChange={(e) => setAnalysisManualConfirmed(e.target.checked)}/> I confirm that I authored this analysis myself; it was not generated by another AI service.</label> : <label className="response-consent"><input type="checkbox" checked={analysisStorageConfirmed} onChange={(e) => setAnalysisStorageConfirmed(e.target.checked)}/> I confirm that Mosaic may store this returned analysis locally.</label>}<button className="secondary" disabled={busy || !analysisJsonText.trim() || !analysisHandoffId || (destination === 'manual' ? !analysisManualConfirmed : !analysisStorageConfirmed)} onClick={importAnalysis}>Import as candidate knowledge</button></div>}</div></section> : <div className="empty-detail"><FileText size={28}/><b>Select a conversation</b><span>Open a source to inspect messages and prepare its analysis prompt.</span></div>}</div>
        </>}
        {tab === 'knowledge' && <>
          <div className="page-title"><div className="eyebrow">SEMANTIC KNOWLEDGE</div><h1>Knowledge library</h1><p>Extracted items remain candidates until you review and promote them.</p></div>
          <div className="knowledge-notice"><ShieldCheck size={17}/><span>Evidence-backed does not mean universally true. Every item retains its source messages and current review status.</span></div>
          {knowledge.length ? <div className="knowledge-grid">{knowledge.map((item) => <article className="panel knowledge-card" key={item.id}><div className="knowledge-top"><span className="kind-tag">{item.kind.replace('_', ' ')}</span><span className="candidate-tag">{item.status}</span></div><h3>{item.canonical_text}</h3><p>{item.description || 'No additional description.'}</p><div className="knowledge-meta"><span>{item.scope} scope</span><span>{item.interpretation_class}</span><span>{item.evidence_count} sources</span><span>v{item.version}</span></div>{item.status === 'candidate' && <div className="review-actions"><button className="review-confirm" onClick={() => reviewItem(item.id, 'confirm')}>Confirm</button><button className="review-reject" onClick={() => reviewItem(item.id, 'reject')}>Reject</button></div>}</article>)}</div> : <div className="empty-state"><BookOpen size={30}/><h3>No knowledge items yet</h3><p>Import a conversation, enable semantic analysis, and submit a source-grounded analysis result.</p></div>}
        </>}
        {tab === 'settings' && <>
          <div className="page-title"><div className="eyebrow">PRIVACY & GOVERNANCE</div><h1>Provider policy reviews</h1><p>Record your review of the provider terms relevant to the operations you intend to perform.</p></div>
          <div className="knowledge-notice"><ShieldCheck size={17}/><span>Mosaic records your attestation and the policy reference. It does not interpret provider terms or provide legal advice. Unreviewed, restricted, and prohibited providers cannot participate in cross-provider handoffs.</span></div>
          <div className="import-layout">
            <section className="panel upload-panel">
              <div className="panel-title"><div className="panel-icon"><ShieldCheck size={19}/></div><div><h2>Record a policy review</h2><p>Review the provider's current terms independently before enabling transfers.</p></div></div>
              <label className="form-label">Provider<select value={policyProvider} onChange={(e) => setPolicyProvider(e.target.value)}><option value="chatgpt">ChatGPT / OpenAI</option><option value="claude">Claude / Anthropic</option><option value="gemini">Gemini / Google</option><option value="other">Other provider</option></select></label>
              <label className="form-label">Official policy URL<input type="url" value={policyUrl} onChange={(e) => setPolicyUrl(e.target.value)} placeholder="https://provider.example/terms"/></label>
              <label className="form-label">Policy version or review date<input value={policyVersion} onChange={(e) => setPolicyVersion(e.target.value)} placeholder="Terms version or YYYY-MM-DD"/></label>
              <label className="form-label">Your assessment<select value={policyStatus} onChange={(e) => setPolicyStatus(e.target.value)}><option value="allowed_with_conditions">Allowed with conditions</option><option value="restricted">Restricted</option><option value="prohibited">Prohibited</option></select></label>
              <label className="form-label">Conditions, restrictions, or rationale<textarea value={policyNotes} onChange={(e) => setPolicyNotes(e.target.value)} rows={4} placeholder="Record which operations you reviewed and any conditions or limitations."/></label>
              <Check checked={policyAcknowledged} onChange={setPolicyAcknowledged} title="I have reviewed the linked policy for my intended use" desc="I understand Mosaic records my assessment; it does not verify that the assessment is legally correct."/>
              <button className="primary full" disabled={busy || !policyUrl.trim() || !policyVersion.trim() || !policyNotes.trim() || !policyAcknowledged} onClick={reviewProviderPolicy}>{busy ? 'Saving review…' : 'Record policy review'}</button>
            </section>
            <aside className="panel info-panel"><h3>Recorded provider reviews</h3>{providerPolicies.length ? providerPolicies.map((item) => <div className="policy-record" key={item.provider}><div className="knowledge-top"><b>{item.provider}</b><span className={`candidate-tag ${item.policy_status === 'allowed_with_conditions' ? 'candidate-approved' : ''}`}>{item.policy_status.replaceAll('_', ' ')}</span></div><small>{item.policy_version || 'No version recorded'} · {item.reviewed_at ? new Date(item.reviewed_at).toLocaleString() : 'Not reviewed'}</small>{item.policy_url && <a href={item.policy_url} target="_blank" rel="noreferrer">Open recorded policy reference</a>}<p>{item.notes}</p></div>) : <div className="empty-state"><ShieldCheck size={25}/><p>No provider reviews recorded. Cross-provider handoffs remain blocked for external providers.</p></div>}</aside>
          </div>
        </>}
      </div>
    </main>
  </div>;
}

function Stat({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: string | number }) {
  return <div className="stat-card"><div className="stat-icon"><Icon size={18}/></div><span>{label}</span><strong>{value}</strong></div>;
}
function Check({ checked, onChange, title, desc }: { checked: boolean; onChange: (v: boolean) => void; title: string; desc: string }) {
  return <label className="permission-row"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)}/><span><b>{title}</b><small>{desc}</small></span></label>;
}
function ConversationList({ conversations, onSelect, selected }: { conversations: Conversation[]; onSelect: (id: string) => void; selected?: string | null }) {
  if (!conversations.length) return <div className="empty-state"><Archive size={28}/><h3>No conversations imported</h3><p>Import an official archive or paste a transcript to begin.</p></div>;
  return <div className="conversation-list">{conversations.map((item) => <button key={item.id} className={`conversation-row ${selected === item.id ? 'selected' : ''}`} onClick={() => onSelect(item.id)}><span className="conversation-icon"><MessageSquare size={17}/></span><span className="conversation-main"><b>{item.title}</b><small>{item.provider} · {item.message_count} messages</small></span><span className="conversation-date">{new Date(item.imported_at).toLocaleDateString()}</span><ChevronRight size={15}/></button>)}</div>;
}