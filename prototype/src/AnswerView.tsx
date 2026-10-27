import type { Answer, Clarification, Claim, Source, TableData } from './types';
import { referenceImage, sourceLabel } from './types';
import { Icon, Math, MathText } from './ui';

const columnLabels: Record<string, string> = {
  serial: 'No.', definition: 'Resistance', symbol_latex: 'Symbol', general: 'General',
  shop_fabrication: 'Shop', field_fabrication: 'Field', nominal_fastener_diameter_mm: 'Fastener Ø (mm)',
  standard_clearance_mm: 'Standard (mm)', oversize_clearance_mm: 'Oversize (mm)',
  short_slot_length_clearance_mm: 'Short slot (mm)', long_slot_length_clearance: 'Long slot',
};

function TableView({ table }: { table: TableData }) {
  return <div className="table-wrap">
    <table><caption>{table.title}</caption>
      <thead><tr>{table.columns.map((column) => <th key={column} scope="col">{columnLabels[column] || column.replaceAll('_', ' ')}</th>)}</tr></thead>
      <tbody>{table.rows.map((row, index) => <tr key={index}>{row.map((value, column) => {
        const content = value === null ? <span aria-label="Not applicable">—</span>
          : table.columns[column].endsWith('_latex') ? <Math tex={value} />
          : table.columns[column] === 'long_slot_length_clearance' && value === '2.5 d' ? <Math tex="2.5d" />
          : <MathText>{value}</MathText>;
        return column === 0 ? <th key={column} scope="row">{content}</th> : <td key={column}>{content}</td>;
      })}</tr>)}</tbody>
    </table>
    {[...(table.header_notes || []), ...(table.notes || []), ...(table.structure_note ? [table.structure_note] : [])].map((note, index) => <p key={index} className="table-footnote"><MathText>{note}</MathText></p>)}
  </div>;
}

function Citation({ source, quote, open }: { source: Source; quote: string; open: (id: string) => void }) {
  return <button className="citation" title={quote} onClick={() => open(source.source_id)}>
    <Icon name="source" />{sourceLabel(source)}<span>p. {source.chunk.pdf_pages.join(', ')}</span>
  </button>;
}

function CitedClaim({ claim, sources, open }: { claim: Claim; sources: Source[]; open: (id: string) => void }) {
  const unique = [...new Set(claim.citations.map((citation) => citation.source_id))];
  return <div className="cited-claim"><div className="claim-text"><MathText>{claim.text}</MathText></div>
    <div className="citations">{unique.map((id) => {
      const source = sources.find((source) => source.source_id === id);
      return source ? <Citation key={id} source={source} quote={claim.citations.find((citation) => citation.source_id === id)!.quote} open={open} /> : null;
    })}</div>
  </div>;
}

export function AnswerView({ answer, openSource, clarify, disabled }: {
  answer: Answer; openSource: (id: string) => void;
  clarify: (clarification: Clarification, value?: string) => void; disabled: boolean;
}) {
  if (answer.status === 'needs_clarification' && answer.clarification) {
    const clarification = answer.clarification;
    return <><h2>First, a little context.</h2><p>{clarification.prompt}</p>
      <div className="clarification-options">{clarification.options.map((option) => <button key={option.value} disabled={disabled} onClick={() => clarify(clarification, option.value)}>{option.label}<Icon name="chevron" /></button>)}
        {clarification.allow_custom && <button disabled={disabled} onClick={() => clarify(clarification)}>Something else<Icon name="plus" /></button>}
      </div>
    </>;
  }
  const hasOCR = answer.sources.some((source) => source.chunk.review_flags?.some((flag) => /ocr|formula_review/.test(flag)));
  return <>
    <h2>{answer.status === 'insufficient_evidence' ? 'The evidence stops here.' : 'From the codebook.'}</h2>
    {answer.claims.map((claim, index) => <CitedClaim key={index} claim={claim} sources={answer.sources} open={openSource} />)}
    {answer.sources.filter((source) => source.table_data).map((source) => <TableView key={source.source_id} table={source.table_data!} />)}
    {answer.sources.filter((source) => source.chunk.content_type === 'diagram').map((source) => {
      const image = referenceImage(source);
      return image ? <figure key={source.source_id} className="answer-figure"><a href={image} target="_blank" rel="noreferrer"><img src={image} alt={source.chunk.title || 'Original diagram from the codebook'} /></a><figcaption>{sourceLabel(source)} · PDF page {source.chunk.pdf_pages.join(', ')}</figcaption></figure> : null;
    })}
    {answer.limitations.map((note, index) => <div className="answer-note" key={index}><Icon name="info" /><p><MathText>{note}</MathText></p></div>)}
    {hasOCR && <p className="small-note">Some cited text has unverified OCR. Check the original pages, especially where formulas are involved.</p>}
    {answer.generation && <details className="pipeline-details"><summary>How this answer was built</summary>
      <dl><div><dt>Retrieval</dt><dd>{answer.retrieval.method}</dd></div><div><dt>Answering model</dt><dd>{answer.generation.model}</dd></div>
        {answer.generation.usage.total_tokens != null && <div><dt>Total tokens</dt><dd>{answer.generation.usage.total_tokens}</dd></div>}
      </dl>
      {answer.generation.attempts.length > 0 && <><p>Model attempts</p><ol>{answer.generation.attempts.map((attempt, index) => <li key={index}>{attempt.model} — {attempt.status}{attempt.status_code ? ` (${attempt.status_code})` : ''}</li>)}</ol></>}
      <p className="small-note">Citations and supporting quotes passed validation. Retrieval scores are not answer confidence.</p>
    </details>}
  </>;
}

export function SourcePanel({ answer, selectedId, select, close }: {
  answer?: Answer; selectedId?: string; select: (id: string) => void; close: () => void;
}) {
  const cited = answer?.sources || [];
  const sources = cited.length ? cited : answer?.retrieved_sources || [];
  const selected = sources.find((source) => source.source_id === selectedId) || sources[0];
  const quotes = [...new Set(answer?.claims.flatMap((claim) => claim.citations.filter((citation) => citation.source_id === selected?.source_id).map((citation) => citation.quote)) || [])];
  const image = selected && referenceImage(selected);
  return <div className="source-panel-content">
    <div className="sources-heading"><div><span className="eyebrow">The reference desk</span><h2>From the codebook<span>.</span></h2></div><button className="icon-button" onClick={close} aria-label="Close sources"><Icon name="close" /></button></div>
    <p className="source-intro">{sources.length && !cited.length ? 'Retrieved passages — none were cited as supporting an answer.' : 'Read the passage behind the answer.'}</p>
    {selected ? <>
      <div className="source-tabs" aria-label="Available sources">{sources.map((source, index) => <button key={source.source_id} className={selected.source_id === source.source_id ? 'selected' : ''} onClick={() => select(source.source_id)} aria-pressed={selected.source_id === source.source_id}><span>{String(index + 1).padStart(2, '0')}</span>{sourceLabel(source)}</button>)}</div>
      <article className="document-preview" key={selected.chunk.chunk_id}>
        <div className="document-running-head"><span>IS 800 : 2007</span><Icon name="book" /></div>
        <span className="document-section">{sourceLabel(selected)}</span>
        {selected.chunk.title && <h3>{selected.chunk.title}</h3>}
        {image && <a href={image} target="_blank" rel="noreferrer"><img className="source-figure" src={image} alt={`Original ${sourceLabel(selected)} crop`} /></a>}
        {quotes.length > 0 && <div className="supporting-quotes"><span className="eyebrow">Supporting quotation{quotes.length > 1 ? 's' : ''}</span>{quotes.map((quote, index) => <blockquote key={index}>{quote}</blockquote>)}</div>}
        <details className="source-text-details" open={quotes.length === 0 && !image}><summary>Full retrieved text</summary><div className="source-raw-text">{selected.chunk.text}</div></details>
        <div className="document-page">PDF page{selected.chunk.pdf_pages.length > 1 ? 's' : ''} {selected.chunk.pdf_pages.join(', ')}</div>
      </article>
      <div className="source-location"><span><Icon name="source" />Original PDF</span><div className="pdf-page-links">{selected.chunk.pdf_pages.map((page) => <a key={page} href={`/api/reference/codebook.pdf#page=${page}`} target="_blank" rel="noreferrer">Page {page}<Icon name="external" /></a>)}</div></div>
      <div className="source-note"><Icon name="info" /><div><p>Review: {selected.chunk.review_status?.replaceAll('_', ' ') || 'Unspecified'}.</p>{selected.chunk.review_flags?.map((flag) => <p key={flag}>{flag.replaceAll('_', ' ')}</p>)}</div></div>
    </> : <div className="empty-sources"><Icon name="book" /><p>Your references will appear here after an answer is retrieved.</p></div>}
    <div className="edition-note"><span className="tiny-dot" />Original 2007 edition · amendments not applied</div>
  </div>;
}
