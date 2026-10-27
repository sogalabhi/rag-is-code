"""Select a provider by configuration; import its SDK only when needed."""
import importlib
import inspect
import os

from .base import LLMProvider, ProviderError

BUILTINS = {"gemini": "rag_demo.providers.gemini:GeminiProvider"}


def create_provider(name=None, model=None) -> LLMProvider:
    name = name or os.environ.get("LLM_PROVIDER") or "gemini"
    model = model or os.environ.get("LLM_MODEL") or None
    target = BUILTINS.get(name, name)
    if ":" not in target:
        raise ProviderError(f"Unknown provider {name!r}. Use 'gemini' or a module:ClassName adapter.")
    module_name, class_name = target.split(":", 1)
    try:
        provider_class = getattr(importlib.import_module(module_name), class_name)
    except (ImportError, AttributeError) as exc:
        raise ProviderError(f"Cannot load provider adapter {target!r}.") from exc
    if (not inspect.isclass(provider_class) or not issubclass(provider_class, LLMProvider)
            or inspect.isabstract(provider_class)):
        raise ProviderError("A provider adapter must be a concrete LLMProvider subclass.")
    return provider_class(model=model)
