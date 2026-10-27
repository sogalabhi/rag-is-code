import { useEffect, useRef, useState } from 'react';
import { APIError, askQuestion } from './api';
import { AnswerView, SourcePanel } from './AnswerView';
import { Icon, MathText, Modal } from './ui';
import type { Answer, Clarification, ClarificationContext, Conversation, HistoryTurn, Message, QuestionRequest, RetrievalMethod } from './types';

const examples = [
  { title: 'Tension member design', description: 'Yielding of the gross section', question: 'How do I check a tension member for yielding?' },
  { title: 'Fastener hole clearances', description: 'Standard, oversize & slotted', question: 'What are the clearances for fastener holes?' },
  { title: 'Material safety factors', description: 'Reading Table 5', question: 'What partial safety factors apply to materials?' },
  { title: 'Connection safety factors', description: 'A question with a little context', question: 'Which safety factor should I use for a connection?' },
  { title: 'Plates with bolt holes', description: 'A closer look at Figure 5', question: 'Show me the diagram of plates with bolt holes in tension.' },
];

function historyFor(messages: Message[]): HistoryTurn[] {
  return messages.flatMap((message): HistoryTurn[] => {
    if (message.role === 'user' && message.text) return [{ role: 'user', text: message.text.slice(0, 4000) }];
    if (message.answer) {
      const text = [message.answer.clarification?.prompt, ...message.answer.claims.map((claim) => claim.text), ...message.answer.limitations].filter(Boolean).join('\n');
      return text ? [{ role: 'assistant', text: text.slice(0, 4000) }] : [];
    }
    return [];
  }).slice(-12);
}

type Pending = { threadId: string; controller: AbortController; request: QuestionRequest; timeout: ReturnType<typeof setTimeout> };
type Selection = { messageId: string; sourceId?: string };

export default function App() {
  const [threads, setThreads] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [method, setMethod] = useState<RetrievalMethod>('hybrid');
  const [pendingThread, setPendingThread] = useState<string | null>(null);
  const [sourcesOpen, setSourcesOpen] = useState(true);
  const [mobileSources, setMobileSources] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [modal, setModal] = useState<'library' | 'about' | null>(null);
  const [toast, setToast] = useState('');
  const [custom, setCustom] = useState<{ kind: Clarification['kind']; question: string } | null>(null);
  const [health, setHealth] = useState<'connecting' | 'ready' | 'unconfigured' | 'offline'>('connecting');
  const [healthVersion, setHealthVersion] = useState(0);
  const input = useRef<HTMLTextAreaElement>(null);
  const transcript = useRef<HTMLDivElement>(null);
  const running = useRef<Pending | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const followScroll = useRef(false);

  const thread = threads.find((item) => item.id === activeId);
  const messages = thread?.messages || [];
  const busy = pendingThread !== null;
  const selectedMessage = messages.find((message) => message.id === selection?.messageId && message.answer)
    || [...messages].reverse().find((message) => message.answer);
  const currentAnswer = selectedMessage?.answer;
  const sourceCount = currentAnswer?.sources.length || currentAnswer?.retrieved_sources.length || 0;

  useEffect(() => {
    const controller = new AbortController();
    setHealth('connecting');
    fetch('/api/health', { signal: controller.signal }).then(async (response) => {
      if (!response.ok) throw new Error('Unavailable');
      const body = await response.json();
      setHealth(body.status === 'ok' ? body.generation_configured ? 'ready' : 'unconfigured' : 'offline');
    }).catch(() => { if (!controller.signal.aborted) setHealth('offline'); });
    return () => controller.abort();
  }, [healthVersion]);

  useEffect(() => () => {
    if (running.current) { clearTimeout(running.current.timeout); running.current.controller.abort(); }
    clearTimeout(toastTimer.current);
  }, []);

  useEffect(() => {
    if (followScroll.current) transcript.current?.scrollTo({ top: transcript.current.scrollHeight, behavior: 'smooth' });
  }, [messages, busy]);

  function updateThread(id: string, update: (thread: Conversation) => Conversation) {
    setThreads((previous) => previous.map((item) => item.id === id ? update(item) : item));
  }

  function notify(text: string) {
    clearTimeout(toastTimer.current); setToast(text);
    toastTimer.current = setTimeout(() => setToast(''), 2600);
  }

  async function copyAnswer(message: Message) {
    const answer = message.answer;
    if (!answer) return;
    const text = [...answer.claims.map((claim) => claim.text), ...answer.limitations,
      ...answer.sources.map((source) => `${source.source_id}: ${source.chunk.chunk_id} — ${source.chunk.pdf_pages.map((page) => `${location.origin}/api/reference/codebook.pdf#page=${page}`).join(', ')}`)].join('\n\n');
    try { await navigator.clipboard.writeText(text); notify('Answer and citations copied'); }
    catch { notify('Clipboard unavailable. You can select and copy the answer.'); }
  }

  function cancelPending() {
    const pending = running.current;
    if (!pending) return;
    running.current = null;
    clearTimeout(pending.timeout); pending.controller.abort(); setPendingThread(null);
    updateThread(pending.threadId, (item) => ({ ...item, messages: [...item.messages, {
      id: crypto.randomUUID(), role: 'assistant', error: { message: 'You stopped waiting for this answer.', code: 'canceled', request: pending.request },
    }] }));
  }

  function newConversation() {
    cancelPending(); setActiveId(null); setDraft(''); setCustom(null); setSelection(null); setMobileNav(false);
    followScroll.current = false;
    transcript.current?.scrollTo({ top: 0 }); input.current?.focus();
  }

  function selectConversation(id: string) {
    if (id !== activeId) cancelPending();
    setActiveId(id); setDraft(''); setCustom(null); setSelection(null); setMobileNav(false);
    followScroll.current = false; transcript.current?.scrollTo({ top: 0 });
  }

  async function runRequest(target: Conversation, request: QuestionRequest, displayText?: string, retryId?: string) {
    if (running.current) return;
    const existing = threads.some((item) => item.id === target.id);
    const user: Message | null = displayText ? { id: crypto.randomUUID(), role: 'user', text: displayText } : null;
    const next = { ...target, context: request.context, messages: [...target.messages.filter((message) => message.id !== retryId), ...(user ? [user] : [])] };
    setThreads((previous) => existing ? previous.map((item) => item.id === target.id ? next : item) : [...previous, next]);
    setActiveId(target.id); setDraft(''); setCustom(null); setMobileNav(false); setPendingThread(target.id);
    followScroll.current = true;
    const controller = new AbortController();
    const pending: Pending = { threadId: target.id, controller, request, timeout: setTimeout(() => controller.abort('timeout'), 150_000) };
    running.current = pending;
    try {
      const answer: Answer = await askQuestion(request, controller.signal);
      if (running.current !== pending) return;
      const message: Message = { id: crypto.randomUUID(), role: 'assistant', answer };
      updateThread(target.id, (item) => ({ ...item, context: answer.context, messages: [...item.messages, message] }));
      setSelection({ messageId: message.id, sourceId: answer.sources[0]?.source_id || answer.retrieved_sources[0]?.source_id });
      if (answer.generation) setHealth('ready');
    } catch (error) {
      if (running.current !== pending) return;
      const failure = controller.signal.aborted ? new APIError('This request took too long. Please retry.', 'timeout')
        : error instanceof APIError ? error : new APIError('The answer could not be loaded. Please retry.', 'request_failed');
      updateThread(target.id, (item) => ({ ...item, messages: [...item.messages, {
        id: crypto.randomUUID(), role: 'assistant', error: { message: failure.message, code: failure.code, request },
      }] }));
      if (failure.code === 'unreachable') setHealth('offline');
    } finally {
      clearTimeout(pending.timeout);
      if (running.current === pending) { running.current = null; setPendingThread(null); }
    }
  }

  function send(text = draft) {
    const value = text.trim().slice(0, 2000);
    if (!value || running.current) return;
    const target = thread || { id: crypto.randomUUID(), title: value.slice(0, 58), messages: [], context: {} };
    const context: ClarificationContext = custom ? { ...target.context, [custom.kind]: value.slice(0, 500) } : target.context;
    const request: QuestionRequest = { question: custom?.question || value, method, top_k: 3, history: historyFor(target.messages), context };
    void runRequest(target, request, value);
  }

  function askExample(example: typeof examples[number]) {
    cancelPending(); setSelection(null);
    const target: Conversation = { id: crypto.randomUUID(), title: example.title, messages: [], context: {} };
    void runRequest(target, { question: example.question, method, top_k: 3, history: [], context: {} }, example.question);
  }

  function clarify(message: Message, clarification: Clarification, value?: string) {
    if (!thread || !message.answer || running.current) return;
    if (value === undefined) {
      setCustom({ kind: clarification.kind, question: message.answer.question });
      setDraft(''); input.current?.focus(); return;
    }
    const context = { ...thread.context, [clarification.kind]: value };
    const request: QuestionRequest = { question: message.answer.question, method, top_k: 3, history: historyFor(thread.messages), context };
    const label = clarification.options.find((option) => option.value === value)?.label || value;
    void runRequest(thread, request, label);
  }

  function openSource(messageId: string, sourceId?: string) {
    setSelection({ messageId, sourceId });
    if (window.matchMedia('(max-width: 1150px)').matches) setMobileSources(true);
    else setSourcesOpen(true);
  }

  function Navigation() {
    return <>
      <button className="brand" onClick={newConversation} aria-label="The Codebook home"><span className="brand-mark"><Icon name="book" /></span><span>The Codebook<span className="brand-caption">A reference, within reach.</span></span></button>
      <button className="new-conversation" onClick={newConversation}><Icon name="plus" />New conversation<span className="new-shortcut">↵</span></button>
      <nav className="conversation-nav" aria-label="Conversations">
        <div className="conversation-group"><h2>Your conversations</h2>{threads.length ? [...threads].reverse().map((item) => <button key={item.id} className={`conversation-link ${activeId === item.id ? 'active' : ''}`} onClick={() => selectConversation(item.id)} aria-current={activeId === item.id ? 'page' : undefined}><Icon name="chat" /><span>{item.title}<small>{item.messages.filter((message) => message.role === 'user').length} question{item.messages.filter((message) => message.role === 'user').length === 1 ? '' : 's'}</small></span>{activeId === item.id && <span className="active-dot" />}</button>) : <p className="empty-history">A fresh notebook. Start with a question below.</p>}</div>
        <div className="conversation-group"><h2>Explore the code</h2>{examples.map((example) => <button key={example.title} className="conversation-link" onClick={() => askExample(example)}><Icon name="source" /><span>{example.title}<small>{example.description}</small></span></button>)}</div>
      </nav>
      <div className="sidebar-bottom"><button className="reference-book" onClick={() => { setModal('library'); setMobileNav(false); }}><span className="book-spine"><Icon name="book" /></span><span><strong>IS 800 : 2007</strong><small>General construction<br />in steel — Code of practice</small></span><Icon name="external" /></button><button className="about-link" onClick={() => { setModal('about'); setMobileNav(false); }}><Icon name="info" />About this workspace<Icon name="chevron" /></button><div className="sidebar-signoff"><Icon name="leaf" /><span>Built for a closer reading.</span></div></div>
    </>;
  }

  const sourcePanel = <SourcePanel answer={currentAnswer} selectedId={selection?.sourceId} select={(sourceId) => selectedMessage && setSelection({ messageId: selectedMessage.id, sourceId })} close={() => { setSourcesOpen(false); setMobileSources(false); }} />;
  return <div className={`workspace ${!sourcesOpen ? 'sources-collapsed' : ''}`}>
    <aside className="sidebar"><Navigation /></aside>
    <main className="main-panel">
      <header className="workspace-header"><div className="header-title"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open conversations"><Icon name="menu" /></button><span className="breadcrumb">Workspace<span>/</span></span><h1>{thread?.title || 'A fresh page'}</h1></div><div className="header-actions"><span className={`preview-badge health-${health}`}><span className="tiny-dot" />{health === 'ready' ? 'Live answers' : health === 'connecting' ? 'Connecting' : health === 'unconfigured' ? 'Setup needed' : 'Backend offline'}</span><button className={`source-toggle ${sourcesOpen ? 'enabled' : ''}`} aria-label="Toggle sources" aria-expanded={sourcesOpen} onClick={() => { if (window.matchMedia('(max-width: 1150px)').matches) setMobileSources(true); else setSourcesOpen(!sourcesOpen); }}><Icon name="source" /><span>Sources</span><span className="source-count">{sourceCount}</span></button></div></header>
      {(health === 'offline' || health === 'unconfigured') && <div className="connection-banner" role="status"><Icon name="info" /><span>{health === 'offline' ? 'The local answer service is not reachable.' : 'The backend is running, but model credentials are not configured.'}</span><button onClick={() => setHealthVersion((value) => value + 1)}>Check again</button></div>}
      <div className="transcript" ref={transcript}><div className="reading-column">
        {messages.length ? <><div className="conversation-date"><span />A page from your notebook<span /></div>{messages.map((message) => message.role === 'user' ? <article className="user-message" key={message.id}><div className="message-label">You<span className="user-avatar">Y</span></div><p><MathText>{message.text!}</MathText></p></article> : <article className="assistant-message" key={message.id}>
          <div className="message-label"><span className="assistant-avatar"><Icon name="book" /></span>The Codebook<span className="message-label-detail">From IS 800:2007</span></div>
          <div className="answer-content">{message.answer ? <AnswerView answer={message.answer} openSource={(sourceId) => openSource(message.id, sourceId)} clarify={(clarification, value) => clarify(message, clarification, value)} disabled={busy} /> : <div className="request-error" role="alert"><h2>{message.error?.code === 'canceled' ? 'Request stopped.' : 'The answer could not be completed.'}</h2><p>{message.error?.message}</p><button className="text-action" disabled={busy} onClick={() => { if (thread && message.error) void runRequest(thread, message.error.request, undefined, message.id); }}>Try again<Icon name="chevron" /></button></div>}</div>
          {message.answer && message.answer.status !== 'needs_clarification' && <div className="answer-actions"><button onClick={() => copyAnswer(message)} aria-label="Copy answer"><Icon name="copy" />Copy answer</button><button onClick={() => openSource(message.id)}><Icon name="source" />Inspect sources</button><span>{message.answer.generation?.model || 'No generation needed'}</span></div>}
        </article>)}{busy && <div className="sample-loading" role="status"><span className="loading-dot" /><span>Retrieving evidence and preparing a cited answer…</span><button onClick={cancelPending}>Cancel</button></div>}</> : <div className="welcome"><span className="welcome-mark"><Icon name="book" /></span><span className="eyebrow">Your reference desk, open.</span><h2>A little clarity.<br /><em>Straight from the code.</em></h2><p>Explore IS 800:2007 through a conversation.<br />Follow the reasoning. Keep the source close.</p><div className="welcome-examples">{examples.slice(0, 3).map((example, index) => <button key={example.title} onClick={() => askExample(example)}><span>0{index + 1}</span>{example.question}<Icon name="chevron" /></button>)}</div></div>}
      </div></div>
      <div className="composer-area"><div className="composer-inner">{custom && <div className="context-indicator">{custom.kind === 'member_type' ? 'Tell us about your member.' : 'Tell us about your connection.'}<button aria-label="Cancel custom context" onClick={() => setCustom(null)}><Icon name="close" /></button></div>}
        <form className="composer" onSubmit={(event) => { event.preventDefault(); send(); }}><label className="sr-only" htmlFor="question">Ask a question about IS 800:2007</label><textarea id="question" ref={input} value={draft} rows={2} maxLength={custom ? 500 : 2000} placeholder={custom ? 'Describe what you have in mind…' : 'What would you like to understand?'} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send(); } }} />
          <div className="composer-toolbar"><div className="composer-tools"><button type="button" className="composer-reference" onClick={() => setModal('library')}><Icon name="book" />IS 800 : 2007<Icon name="chevron" /></button><label className="method-selector"><span className="sr-only">Retrieval method</span><select value={method} onChange={(event) => setMethod(event.target.value as RetrievalMethod)}><option value="hybrid">Hybrid</option><option value="semantic">Semantic</option><option value="keyword">Keyword</option></select></label></div><div className="composer-send-group"><span>Enter to send</span><button className="send-button" type="submit" disabled={!draft.trim() || busy} aria-label="Send question"><Icon name={busy ? 'book' : 'arrow'} /></button></div></div>
        </form><div className="composer-note"><span className="tiny-dot" />Answers use retrieved evidence. Check the original pages and source review notes.</div>
      </div></div>
    </main>
    {sourcesOpen && <aside className="sources-panel" aria-label="Source references">{sourcePanel}</aside>}
    {mobileSources && <Modal title="Source references" close={() => setMobileSources(false)}>{sourcePanel}</Modal>}
    {mobileNav && <Modal title="Your workspace" close={() => setMobileNav(false)}><div className="mobile-navigation"><Navigation /></div></Modal>}
    {modal === 'library' && <Modal title="The reference library" close={() => setModal(null)}><div className="library-entry"><div className="library-cover"><Icon name="book" /><strong>IS 800</strong><span>2007</span></div><div><span className="eyebrow">Bureau of Indian Standards</span><h3>General Construction in Steel</h3><p>Code of practice · Original 2007 edition</p><a className="primary-link" href="/api/reference/codebook.pdf" target="_blank" rel="noreferrer">Open the codebook<Icon name="external" /></a></div></div><p className="modal-note">The collection contains 943 clause records, Tables 5 and 19, and Figure 5. Amendment instructions have not been applied.</p></Modal>}
    {modal === 'about' && <Modal title="A desk for a closer reading." close={() => setModal(null)}><p>This workspace retrieves IS 800:2007 source passages and generates complete answers through the local Python backend. Questions and selected evidence are sent to the configured model provider.</p><p>Each answer is checked for valid source IDs and supporting quotations before it appears. These checks establish reference integrity; you should still inspect whether the source supports the full claim.</p><p>Model fallback is automatic for recoverable service errors. Conversation history stays in this browser tab's memory and resets on reload. Answer streaming is a later step.</p><div className="palette-swatches" aria-label="Paper, ink and forest palette"><span /><span /><span /><span /></div><p className="modal-note">Source Serif 4 · Paper, ink & forest · React + TypeScript + Python</p></Modal>}
    {toast && <div className="toast" role="status"><Icon name="check" />{toast}</div>}
  </div>;
}
