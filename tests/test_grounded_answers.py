"""Offline behavior checks: provider swapping and citation integrity."""
import copy
import json
import os
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from rag_demo.grounding import GroundedAnswerer, GroundingError, prepare_request, validate_answer
from rag_demo.providers import GenerationResult, LLMProvider, ProviderError, create_provider
from rag_demo.providers.gemini import GeminiProvider


class FixtureProvider(LLMProvider):
    """Test fixture only; never presented as a generated Gemini answer."""
    def __init__(self, model=None):
        self.model = model or "fixture-model"
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        source = json.loads(request.prompt)["evidence"][0]
        return GenerationResult({
            "status": "answered", "claims": [{"text": "This passage defines accidental loads.",
                "citations": [{"source_id": source["source_id"], "quote": source["text"]}]}],
            "limitations": [],
        }, provider="fixture", model=self.model)


class GroundedAnswerTests(unittest.TestCase):
    def setUp(self):
        self.chunk = {
            "chunk_id": "is800-2007:clause:1.3.1", "clause_id": "1.3.1",
            "content_type": "clause", "renderer": "text",
            "text": "Accidental Loads — Loads due to explosion, impact of vehicles, or other rare loads.",
            "pdf_pages": [15], "source_pdf": "data/is.800.2007.pdf",
            "source_links": ["data/is.800.2007.pdf#page=15"],
            "review_flags": ["ocr_not_fully_verified"],
        }
        self.results = [{"score": 2, "chunk": self.chunk}]
        self.request, self.sources = prepare_request("What are accidental loads?", self.results)
        self.valid = {"status": "answered", "claims": [{
            "text": "Accidental loads include vehicle impacts.",
            "citations": [{"source_id": "S1", "quote": "impact of vehicles"}],
        }], "limitations": []}

    def test_abstract_contract_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            LLMProvider()

    def test_another_provider_can_be_loaded_by_configuration(self):
        plugin = ModuleType("fixture_plugin")
        plugin.OtherProvider = FixtureProvider
        with patch.dict(sys.modules, {"fixture_plugin": plugin}), patch.dict(os.environ, {
            "LLM_PROVIDER": "fixture_plugin:OtherProvider", "LLM_MODEL": "alternate-model",
        }):
            provider = create_provider()
            answer = GroundedAnswerer(provider).answer("What are accidental loads?", self.results)
        self.assertEqual(answer["generation"]["provider"], "fixture")
        self.assertEqual(answer["generation"]["model"], "alternate-model")
        self.assertEqual(answer["sources"][0]["chunk"], self.chunk)

    def test_valid_citations_resolve_to_original_pages_and_flags(self):
        answer = validate_answer(self.valid, self.sources)
        self.assertEqual(answer["sources"][0]["chunk"]["pdf_pages"], [15])
        self.assertIn("ocr_not_fully_verified", answer["sources"][0]["chunk"]["review_flags"])

    def test_fabricated_source_is_rejected(self):
        data = copy.deepcopy(self.valid)
        data["claims"][0]["citations"][0]["source_id"] = "S99"
        with self.assertRaises(GroundingError):
            validate_answer(data, self.sources)

    def test_fabricated_quote_is_rejected(self):
        data = copy.deepcopy(self.valid)
        data["claims"][0]["citations"][0]["quote"] = "The safety factor is 999."
        with self.assertRaises(GroundingError):
            validate_answer(data, self.sources)

    def test_uncited_claim_is_rejected(self):
        data = copy.deepcopy(self.valid)
        data["claims"][0]["citations"] = []
        with self.assertRaises(GroundingError):
            validate_answer(data, self.sources)

    def test_whitespace_normalization_allows_line_wrapped_quotes(self):
        data = copy.deepcopy(self.valid)
        data["claims"][0]["citations"][0]["quote"] = "impact of\nvehicles"
        self.assertEqual(validate_answer(data, self.sources)["status"], "answered")

    def test_no_evidence_does_not_call_model(self):
        provider = FixtureProvider()
        answer = GroundedAnswerer(provider).answer("Unrelated question", [])
        self.assertEqual(provider.calls, 0)
        self.assertEqual(answer["status"], "insufficient_evidence")
        self.assertIsNone(answer["generation"])

    def test_insufficient_evidence_cannot_contain_claims(self):
        valid = {"status": "insufficient_evidence", "claims": [],
                 "limitations": ["The sources do not cover this question."]}
        self.assertEqual(validate_answer(valid, self.sources)["sources"], [])
        valid["claims"] = self.valid["claims"]
        with self.assertRaises(GroundingError):
            validate_answer(valid, self.sources)

    def test_gemini_adapter_translates_the_shared_contract(self):
        captured = {}

        def generate_content(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text=json.dumps(self.valid), usage_metadata=SimpleNamespace(
                prompt_token_count=100, candidates_token_count=40, total_token_count=140))

        provider = GeminiProvider(model="selected-model", client=SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)))
        result = provider.generate(self.request)
        self.assertEqual(captured["model"], "selected-model")
        self.assertEqual(captured["config"]["response_json_schema"], self.request.response_schema)
        self.assertEqual(result.data, self.valid)
        self.assertEqual(result.usage["total_tokens"], 140)

    def test_provider_failure_does_not_expose_credentials(self):
        def fail(**kwargs):
            raise RuntimeError("request with secret-key-value failed")

        provider = GeminiProvider(client=SimpleNamespace(models=SimpleNamespace(generate_content=fail)))
        with self.assertRaises(ProviderError) as caught:
            provider.generate(self.request)
        self.assertNotIn("secret-key-value", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
