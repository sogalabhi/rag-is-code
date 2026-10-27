"""Model-provider contract and configurable adapter factory."""
from .base import GenerationRequest, GenerationResult, LLMProvider, ProviderError
from .factory import create_provider
from .fallback import FallbackProvider

__all__ = ["GenerationRequest", "GenerationResult", "LLMProvider", "ProviderError", "FallbackProvider", "create_provider"]
