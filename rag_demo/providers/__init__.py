"""Model-provider contract and configurable adapter factory."""
from .base import GenerationRequest, GenerationResult, LLMProvider, ProviderError
from .factory import create_provider

__all__ = ["GenerationRequest", "GenerationResult", "LLMProvider", "ProviderError", "create_provider"]
