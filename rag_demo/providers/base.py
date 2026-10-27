"""The RAG pipeline depends on this contract, never on a vendor SDK."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """Provider setup, transport, or response-format failure."""


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


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Return structured data matching the request's response schema.

        Adapters translate SDK calls and failures into this shared contract.
        The caller validates citations independently of the provider.
        """
        raise NotImplementedError
