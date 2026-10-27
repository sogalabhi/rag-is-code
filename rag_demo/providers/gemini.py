"""Google Gemini adapter; vendor imports and API details stay in this file."""
import json
import os

from .base import GenerationRequest, GenerationResult, LLMProvider, ProviderError

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_FALLBACK_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite")


class GeminiProvider(LLMProvider):
    default_fallback_models = DEFAULT_FALLBACK_MODELS

    def __init__(self, model=None, api_key=None, client=None):
        self.model = (model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL).strip().removeprefix("models/")
        if client is not None:
            self.client = client
            return
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ProviderError("Set GEMINI_API_KEY in your terminal environment, or use --preview without a key.")
        try:
            from google import genai
        except ImportError as exc:
            raise ProviderError("Install Gemini support: python -m pip install -r requirements-llm.txt") from exc
        # One request per model; avoid multiplying the fallback chain by SDK retries.
        self.client = genai.Client(api_key=key, http_options={
            "timeout": 30000, "retry_options": {"attempts": 1}})

    def generate(self, request: GenerationRequest) -> GenerationResult:
        config = {"system_instruction": request.system_instruction,
                  "response_mime_type": "application/json",
                  "response_json_schema": request.response_schema,
                  "max_output_tokens": 4096}
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=request.prompt, config=config)
        except Exception as exc:
            # Avoid exposing URLs, request headers, or credentials in CLI output.
            code = getattr(exc, "code", None)
            code = code if isinstance(code, int) else None
            retryable = code in (404, 408, 429, 500, 502, 503, 504) or isinstance(
                exc, (TimeoutError, ConnectionError))
            if code is None:
                try:
                    from httpx import TransportError
                except ImportError:
                    pass
                else:
                    retryable = retryable or isinstance(exc, TransportError)
            detail = f"status {code}" if isinstance(code, int) else type(exc).__name__
            raise ProviderError(
                f"Gemini request failed ({detail}). Check connectivity, key, model and quota.",
                retryable=retryable, status_code=code,
            ) from exc
        if not response.text:
            raise ProviderError("Gemini returned no text. The response may have been blocked or incomplete.")
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise ProviderError("Gemini returned incomplete or invalid JSON; no answer was accepted.") from exc
        if not isinstance(data, dict):
            raise ProviderError("Gemini must return a JSON object.")
        usage = getattr(response, "usage_metadata", None)
        return GenerationResult(data=data, provider="gemini", model=self.model, usage={
            "input_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
        })
