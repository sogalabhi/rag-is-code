import type { Answer, QuestionRequest } from './types';

export class APIError extends Error {
  constructor(message: string, public code: string) { super(message); }
}

export async function askQuestion(request: QuestionRequest, signal: AbortSignal): Promise<Answer> {
  let response: Response;
  try {
    response = await fetch('/api/answer', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request), signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new APIError('The answer service is not reachable. Check that the local backend is running, then retry.', 'unreachable');
  }
  let body;
  try { body = await response.json(); }
  catch { throw new APIError('The answer service returned an unreadable response. Please retry.', 'invalid_response'); }
  if (!response.ok) {
    const detail = body.detail;
    throw new APIError(typeof detail?.message === 'string' ? detail.message : 'The request could not be completed. Please check the question and retry.', detail?.code || 'request_failed');
  }
  if (!['answered', 'insufficient_evidence', 'needs_clarification'].includes(body.status) || !Array.isArray(body.claims) || !Array.isArray(body.sources)) {
    throw new APIError('The answer service returned an unexpected response. Please retry.', 'invalid_response');
  }
  return body as Answer;
}
