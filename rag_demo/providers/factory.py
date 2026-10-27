"""Select a provider by configuration; import its SDK only when needed."""
import importlib
import inspect
import os

from .base import LLMProvider, ProviderError
from .fallback import FallbackProvider

BUILTINS = {"gemini": "rag_demo.providers.gemini:GeminiProvider"}


def create_provider(name=None, model=None, fallback_models=None) -> LLMProvider:
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
    primary = provider_class(model=model)
    if fallback_models is None:
        fallback_models = os.environ.get("LLM_FALLBACK_MODELS")
    if fallback_models is None:
        fallback_models = getattr(provider_class, "default_fallback_models", ())
    if isinstance(fallback_models, str):
        fallback_models = fallback_models.split(",")
    providers = [primary]
    seen = {getattr(primary, "model", model)}
    for fallback_model in fallback_models:
        fallback_model = fallback_model.strip().removeprefix("models/")
        if not fallback_model or fallback_model in seen:
            continue
        seen.add(fallback_model)
        providers.append(provider_class(model=fallback_model))
    return FallbackProvider(providers) if len(providers) > 1 else primary
