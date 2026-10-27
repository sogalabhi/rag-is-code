"""The RAG pipeline depends on this contract, never on a vendor SDK."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """Provider setup, transport, or response-format failure."""

    def __init__(self, message, *, retryable=False, status_code=None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


@dataclass(frozen=True)
class GenerationRequest:
    system_instruction: str
    prompt: str
    response_schema: dict[str, Any]


@dataclass(frozen=True)
class GenerationResult:
    data: dict[str, Any]
    provider: str
    model: str
    usage: dict[str, int | None] = field(default_factory=dict)
    attempts: list[dict[str, Any]] = field(default_factory=list)


class LLMProvider(ABC):
    def close(self):
        """Release optional resources after a request; adapters may override."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Return structured data matching the request's response schema.

        Adapters translate SDK calls and failures into this shared contract.
        The caller validates citations independently of the provider.
        """
        raise NotImplementedError
