"""Model failover behavior, configuration, and actual SDK request serialization."""
import json
import os
from types import ModuleType, SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

from rag_demo.providers import (
    FallbackProvider, GenerationRequest, GenerationResult, LLMProvider, ProviderError, create_provider,
)
from rag_demo.providers.gemini import DEFAULT_FALLBACK_MODELS, DEFAULT_MODEL, GeminiProvider

try:
    import httpx
    from google import genai
except ImportError:
    httpx = genai = None


class StubProvider(LLMProvider):
    def __init__(self, model=None):
        self.model = model or "primary"
        self.generate = Mock(return_value=GenerationResult(
            data={"status": "answered"}, provider="stub", model=self.model,
            usage={"total_tokens": 42}))

    def generate(self, request):
        raise NotImplementedError


class ModelFallbackTests(unittest.TestCase):
    def setUp(self):
        self.request = GenerationRequest("Use evidence.", "Question", {"type": "object"})

    def test_unavailable_and_rate_limited_models_fall_through_in_order(self):
        primary, second, third, unused = [StubProvider(name) for name in ("primary", "second", "third", "unused")]
        primary.generate.side_effect = ProviderError("Unavailable", retryable=True, status_code=503)
        second.generate.side_effect = ProviderError("Rate limited", retryable=True, status_code=429)
        with self.assertLogs("rag_demo.providers.fallback", level="WARNING"):
            result = FallbackProvider([primary, second, third, unused]).generate(self.request)
        self.assertEqual(result.model, "third")
        self.assertEqual(result.usage, {"total_tokens": 42})
        self.assertEqual(result.attempts, [
            {"model": "primary", "status": "failed", "status_code": 503},
            {"model": "second", "status": "failed", "status_code": 429},
            {"model": "third", "status": "succeeded"},
        ])
        for provider in (primary, second, third):
            provider.generate.assert_called_once_with(self.request)
        unused.generate.assert_not_called()

    def test_successful_primary_skips_other_models(self):
        primary, fallback = StubProvider("primary"), StubProvider("fallback")
        result = FallbackProvider([primary, fallback]).generate(self.request)
        self.assertEqual(result.model, "primary")
        fallback.generate.assert_not_called()

    def test_authentication_and_invalid_request_errors_stop_immediately(self):
        for code in (400, 401, 402, 403):
            with self.subTest(code=code):
                primary, fallback = StubProvider("primary"), StubProvider("fallback")
                failure = ProviderError("Fix configuration", status_code=code)
                primary.generate.side_effect = failure
                with self.assertRaises(ProviderError) as caught:
                    FallbackProvider([primary, fallback]).generate(self.request)
                self.assertIs(caught.exception, failure)
                fallback.generate.assert_not_called()

    def test_exhausted_chain_reports_all_attempts_without_raw_errors(self):
        providers = [StubProvider("first"), StubProvider("second")]
        for provider in providers:
            provider.generate.side_effect = ProviderError(
                "request contains secret-key-value", retryable=True, status_code=503)
        with self.assertLogs("rag_demo.providers.fallback", level="WARNING") as logs:
            with self.assertRaises(ProviderError) as caught:
                FallbackProvider(providers).generate(self.request)
        self.assertIn("first (503), second (503)", str(caught.exception))
        self.assertNotIn("secret-key-value", str(caught.exception) + str(logs.output))
        for provider in providers:
            provider.generate.assert_called_once()

    def test_factory_uses_gemini_defaults_without_importing_vendor_sdk(self):
        def initialize(provider, model=None):
            provider.model = model or DEFAULT_MODEL

        with patch.dict(os.environ, {}, clear=True), patch.object(GeminiProvider, "__init__", initialize):
            provider = create_provider()
        self.assertIsInstance(provider, FallbackProvider)
        self.assertEqual([item.model for item in provider.providers], [DEFAULT_MODEL, *DEFAULT_FALLBACK_MODELS])

    def test_factory_configuration_deduplicates_models_and_respects_overrides(self):
        plugin = ModuleType("fallback_fixture")
        plugin.Provider = StubProvider
        with patch.dict(sys.modules, {"fallback_fixture": plugin}), patch.dict(os.environ, {
            "LLM_PROVIDER": "fallback_fixture:Provider", "LLM_MODEL": "primary",
            "LLM_FALLBACK_MODELS": "primary, second,models/second, third, ,second",
        }, clear=True):
            provider = create_provider()
            explicit = create_provider(model="override", fallback_models="fourth,fourth")
            disabled = create_provider(fallback_models=[])
            os.environ["LLM_FALLBACK_MODELS"] = ""
            empty = create_provider()
        self.assertEqual([item.model for item in provider.providers], ["primary", "second", "third"])
        self.assertEqual([item.model for item in explicit.providers], ["override", "fourth"])
        self.assertIsInstance(disabled, StubProvider)
        self.assertEqual(disabled.model, "primary")
        self.assertIsInstance(empty, StubProvider)

    def test_gemini_marks_only_recoverable_api_errors_for_fallback(self):
        for code in (400, 401, 402, 403, 404, 408, 429, 500, 502, 503, 504):
            with self.subTest(code=code):
                failure = RuntimeError("request with secret-key-value failed")
                failure.code = code
                provider = GeminiProvider(model="test", client=SimpleNamespace(
                    models=SimpleNamespace(generate_content=Mock(side_effect=failure))))
                with self.assertRaises(ProviderError) as caught:
                    provider.generate(self.request)
                self.assertEqual(caught.exception.status_code, code)
                self.assertEqual(caught.exception.retryable, code not in (400, 401, 402, 403))
                self.assertNotIn("secret-key-value", str(caught.exception))

    def test_transport_timeout_can_fall_back_but_unknown_failure_cannot(self):
        failures = [(TimeoutError("timed out"), True), (ConnectionError("connection lost"), True),
                    (RuntimeError("unexpected bug"), False)]
        if httpx is not None:
            failures.append((httpx.ReadTimeout("timed out"), True))
        for failure, retryable in failures:
            with self.subTest(failure=type(failure).__name__):
                provider = GeminiProvider(client=SimpleNamespace(
                    models=SimpleNamespace(generate_content=Mock(side_effect=failure))))
                with self.assertRaises(ProviderError) as caught:
                    provider.generate(self.request)
                self.assertEqual(caught.exception.retryable, retryable)

    def test_invalid_or_blocked_output_stops_without_trying_other_models(self):
        for text in (None, "not JSON", "[]"):
            with self.subTest(text=text):
                primary = GeminiProvider(model="primary", client=SimpleNamespace(models=SimpleNamespace(
                    generate_content=Mock(return_value=SimpleNamespace(text=text)))))
                fallback = StubProvider("fallback")
                with self.assertRaises(ProviderError):
                    FallbackProvider([primary, fallback]).generate(self.request)
                fallback.generate.assert_not_called()

    @unittest.skipIf(genai is None, "Optional Gemini SDK is not installed")
    def test_sdk_transport_switches_models_without_hidden_same_model_retries(self):
        requests = []

        def handle(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(503, json={"error": {
                    "code": 503, "status": "UNAVAILABLE", "message": "Model busy"}})
            return httpx.Response(200, json={"candidates": [{
                "content": {"role": "model", "parts": [{"text": '{"status":"answered"}'}]},
                "finishReason": "STOP",
            }], "usageMetadata": {"totalTokenCount": 42}})

        real_client = genai.Client
        clients = []

        def make_client(**kwargs):
            kwargs["http_options"]["client_args"] = {"transport": httpx.MockTransport(handle)}
            client = real_client(**kwargs)
            clients.append(client)
            return client

        try:
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True), patch.object(
                genai, "Client", side_effect=make_client,
            ):
                provider = create_provider(model="primary", fallback_models=["fallback"])
                with self.assertLogs("rag_demo.providers.fallback", level="WARNING"):
                    result = provider.generate(self.request)
        finally:
            for client in clients:
                client.close()
        self.assertEqual(result.model, "fallback")
        self.assertEqual(len(requests), 2)
        self.assertIn("/models/primary:generateContent", requests[0].url.path)
        self.assertIn("/models/fallback:generateContent", requests[1].url.path)
        for request in requests:
            body = json.loads(request.content)
            self.assertEqual(body["generationConfig"]["responseJsonSchema"], self.request.response_schema)
        self.assertEqual(result.usage["total_tokens"], 42)


if __name__ == "__main__":
    unittest.main()
