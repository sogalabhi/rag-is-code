"""Try configured models in order when an adapter reports a recoverable error."""
from dataclasses import replace
import logging

from .base import GenerationRequest, GenerationResult, LLMProvider, ProviderError

logger = logging.getLogger(__name__)


class FallbackProvider(LLMProvider):
    def __init__(self, providers):
        self.providers = tuple(providers)
        if not self.providers:
            raise ValueError("At least one model provider is required.")

    def generate(self, request: GenerationRequest) -> GenerationResult:
        attempts = []
        for index, provider in enumerate(self.providers):
            model = provider.model
            try:
                result = provider.generate(request)
            except ProviderError as exc:
                if not exc.retryable:
                    raise
                attempts.append({"model": model, "status": "failed", "status_code": exc.status_code})
                if index + 1 == len(self.providers):
                    summary = ", ".join(
                        f"{item['model']} ({item['status_code'] or 'transport error'})" for item in attempts)
                    raise ProviderError(
                        f"All configured models failed: {summary}. Check availability, quota and model access.",
                        retryable=True, status_code=exc.status_code,
                    ) from exc
                logger.warning("Model %s failed (%s); trying %s.", model,
                               exc.status_code or "transport error", self.providers[index + 1].model)
                continue
            attempts.append({"model": result.model, "status": "succeeded"})
            return replace(result, attempts=attempts)
