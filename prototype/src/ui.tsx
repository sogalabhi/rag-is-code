import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import katex from 'katex';

const icons: Record<string, ReactNode> = {
  book: <><path d="M4 4h11a5 5 0 0 1 5 5v12H9a5 5 0 0 1-5-5Z" /><path d="M4 17h16M9 4v13" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  arrow: <path d="M12 19V5m-6 6 6-6 6 6" />,
  external: <><path d="M14 4h6v6m0-6-10 10" /><path d="M10 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5" /></>,
  source: <><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M13 3v18M7 8h3m-3 4h3m-3 4h3" /></>,
  copy: <><rect x="8" y="8" width="12" height="13" rx="2" /><path d="M15 8V3H3v13h5" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  chat: <path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2Z" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v1" /></>,
  leaf: <><path d="M19 4c-7-1-14 2-14 8a6 6 0 0 0 6 6c6 0 9-7 8-14Z" /><path d="M4 21 15 10" /></>,
};

export function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <svg className={`icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[name]}</svg>;
}

export function Math({ tex, block = false }: { tex: string; block?: boolean }) {
  try {
    const html = katex.renderToString(tex, { displayMode: block, throwOnError: true, trust: false, maxExpand: 500, maxSize: 10 });
    return <span className={block ? 'math-block' : 'math-inline'} dangerouslySetInnerHTML={{ __html: html }} />;
  } catch {
    return <code className="math-error" title="This expression could not be typeset">{tex}</code>;
  }
}

export function MathText({ children }: { children: string }) {
  const pieces = children.split(/(\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]+\$)/g);
  return <>{pieces.map((piece, index) => {
    if (piece.startsWith('\\[') || piece.startsWith('$$')) return <DisplayEquation key={index} tex={piece.slice(2, -2)} />;
    if (piece.startsWith('\\(')) return <Math key={index} tex={piece.slice(2, -2)} />;
    if (piece.startsWith('$') && piece.endsWith('$')) return <Math key={index} tex={piece.slice(1, -1)} />;
    return piece;
  })}</>;
}

function DisplayEquation({ tex }: { tex: string }) {
  const [feedback, setFeedback] = useState('TeX');
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  async function copy() {
    try { await navigator.clipboard.writeText(tex); setFeedback('Copied'); }
    catch { setFeedback('Select to copy'); }
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setFeedback('TeX'), 2000);
  }
  return <span className="equation"><span className="equation-label">The expression</span><button className="equation-copy" aria-label="Copy LaTeX formula" onClick={copy}>{feedback}<Icon name="copy" /></button><Math tex={tex} block /></span>;
}

export function Modal({ title, children, close }: { title: string; children: ReactNode; close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  return <dialog className="modal" ref={ref} onCancel={close} onClick={(event) => { if (event.target === event.currentTarget) close(); }}><div className="modal-heading"><h2>{title}</h2><button className="icon-button" aria-label="Close dialog" onClick={close}><Icon name="close" /></button></div>{children}</dialog>;
}

