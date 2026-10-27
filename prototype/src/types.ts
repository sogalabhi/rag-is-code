export type RetrievalMethod = 'keyword' | 'semantic' | 'hybrid';
export type ClarificationContext = Partial<Record<'member_type' | 'connection_type', string>>;
export type HistoryTurn = { role: 'user' | 'assistant'; text: string };
export type QuestionRequest = { question: string; method: RetrievalMethod; top_k: number; history: HistoryTurn[]; context: ClarificationContext };
export type TableData = {
  record_id: string; title: string; columns: string[]; rows: (string | null)[][];
  header_notes?: string[]; notes?: string[]; structure_note?: string;
};
export type SourceChunk = {
  chunk_id: string; text: string; pdf_pages: number[]; source_links: string[];
  content_type?: string; renderer?: string; clause_id?: string; clause_ids?: string[];
  title?: string; table_number?: number; figure_number?: number; image_path?: string;
  source_crop?: string; review_status?: string; review_flags?: string[];
};
export type Source = { source_id: string; chunk: SourceChunk; table_data?: TableData };
export type Claim = { text: string; citations: { source_id: string; quote: string }[] };
export type Clarification = {
  kind: 'member_type' | 'connection_type'; prompt: string;
  options: { label: string; value: string }[]; allow_custom: boolean;
};
export type Answer = {
  question: string; status: 'answered' | 'insufficient_evidence' | 'needs_clarification';
  claims: Claim[]; limitations: string[]; sources: Source[]; retrieved_sources: Source[];
  clarification: Clarification | null; context: ClarificationContext;
  generation: null | { provider: string; model: string; usage: Record<string, number | null>; attempts: { model: string; status: string; status_code?: number }[] };
  retrieval: { method: RetrievalMethod; query: string; results: { chunk_id: string; score: number }[] };
};
export type Message = {
  id: string; role: 'user' | 'assistant'; text?: string; answer?: Answer;
  error?: { message: string; code: string; request: QuestionRequest };
};
export type Conversation = { id: string; title: string; messages: Message[]; context: ClarificationContext };

export function sourceLabel(source: Source) {
  const chunk = source.chunk;
  if (chunk.table_number) return `Table ${chunk.table_number}`;
  if (chunk.figure_number) return `Figure ${chunk.figure_number}`;
  const clause = chunk.clause_id || chunk.clause_ids?.[0];
  return clause ? `Clause ${clause}` : chunk.title || chunk.chunk_id;
}

export function referenceImage(source: Source) {
  const filename = (source.chunk.image_path || source.chunk.source_crop)?.split('/').pop();
  return filename && ['table-05.png', 'table-19.png', 'figure-05.png'].includes(filename)
    ? `/api/reference/${filename}` : undefined;
}
