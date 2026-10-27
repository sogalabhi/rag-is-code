"""Reuse the CLI's retrieval and grounding pipeline for complete HTTP answers."""
from contextlib import suppress
import re
from threading import Lock

from scripts.retrieve import KeywordRetriever, load_chunks, tokenize
from scripts.search import SemanticRetriever, rank_question

from .grounding import GroundedAnswerer, prepare_request
from .providers import create_provider


def clarification_for(question, context):
    text = question.lower()
    if re.search(r"\b(all|compare|comparison|different|table|list)\b", text):
        return None
    if ("connection" in text and re.search(r"\b(factor|strength|resistance|design)\b", text)
            and not re.search(r"\b(bolt\w*|weld\w*|rivet\w*)\b", text)
            and not context.get("connection_type")):
        return {"kind": "connection_type", "prompt": "Which type of connection are you asking about?",
                "options": [{"label": label, "value": value} for label, value in (
                    ("Bolted connection", "bolted"), ("Welded connection", "welded"),
                    ("Riveted connection", "riveted"))], "allow_custom": True}
    if ("member" in text and re.search(r"\b(strength|design|slenderness|resistance)\b", text)
            and not re.search(r"\b(tension|compression|beam|bending|flexur\w*)\b", text)
            and not context.get("member_type")):
        return {"kind": "member_type", "prompt": "Which type of member do you mean?",
                "options": [{"label": label, "value": value} for label, value in (
                    ("Tension member", "tension"), ("Compression member", "compression"),
                    ("Beam", "beam"))], "allow_custom": True}
    return None


def retrieval_question(question, history, context):
    query = question
    if re.search(r"^(and\b|also\b|what about\b|how about\b)|\b(it|this|that|these|those|above|same|symbols|notation)\b",
                 question.lower()):
        previous = next((turn["text"] for turn in reversed(history) if turn["role"] == "user"), None)
        if previous:
            query = f"{previous}\nFollow-up: {question}"
    if context:
        query += "\nUser context: " + "; ".join(f"{key}: {value}" for key, value in context.items())
    return query


def current_context(question, context):
    """A new explicit member/connection type takes precedence over earlier context."""
    context = dict(context)
    text = question.lower()
    for kind, pattern in (
        ("connection_type", r"\b(bolt\w*|weld\w*|rivet\w*)\b"),
        ("member_type", r"\b(tension|compression|beam|bending)\b"),
    ):
        if kind in context and re.search(pattern, text):
            del context[kind]
    return context


class RAGService:
    def __init__(self, chunks=None, provider_factory=create_provider, semantic_factory=SemanticRetriever):
        self.chunks = load_chunks() if chunks is None else chunks
        self.keyword = KeywordRetriever(self.chunks)
        self.provider_factory = provider_factory
        self.semantic_factory = semantic_factory
        self.semantic = None
        self.search_lock = Lock()

    def answer(self, question, method="hybrid", top_k=3, history=(), context=None):
        if not tokenize(question):
            raise ValueError("Supply a question with content search terms.")
        context = current_context(question, context or {})
        clarification = clarification_for(question, context)
        if clarification:
            return {"question": question, "status": "needs_clarification", "claims": [],
                    "limitations": [], "sources": [], "retrieved_sources": [], "generation": None,
                    "clarification": clarification, "context": context,
                    "retrieval": {"method": method, "query": question, "results": []}}
        query = retrieval_question(question, history, context)
        with self.search_lock:
            if method != "keyword" and self.semantic is None:
                self.semantic = self.semantic_factory(self.chunks)
            results = rank_question(query, self.keyword, self.semantic, method, top_k)[method]
        _, evidence = prepare_request(question, results)
        if not results:
            answer = {"question": question, "status": "insufficient_evidence", "claims": [],
                      "limitations": ["No matching evidence was retrieved."], "sources": [], "generation": None}
        else:
            model_question = question
            if context:
                model_question += "\nAdditional context from the user: " + "; ".join(
                    f"{key}: {value}" for key, value in context.items())
            provider = self.provider_factory()
            try:
                answer = GroundedAnswerer(provider).answer(model_question, results, conversation=list(history))
            finally:
                with suppress(Exception):
                    provider.close()
            answer["question"] = question
        return {**answer, "retrieved_sources": list(evidence.values()), "clarification": None,
                "context": context, "retrieval": {"method": method, "query": query,
                    "results": [{"chunk_id": item["chunk"]["chunk_id"], "score": item["score"]}
                                for item in results]}}
