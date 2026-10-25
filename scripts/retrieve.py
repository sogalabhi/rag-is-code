"""Keyword retrieval learning checkpoint: no embeddings or answer generation.

Score = number of distinct query terms matched. Ties favor shorter passages.
Run with a question, or --examples for the five review questions.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parent.parent
FILES = ("chunks.jsonl", "demo_asset_chunks.jsonl")
STOP_WORDS = frozenset("""
a an and are as at be been being by can could did do does for from has have how
i in into is it its of on or our should that the their them there these they
this those to was we were what when where which who why will with would you your
""".split())
EXAMPLE_QUESTIONS = (
    "What are accidental loads?",
    "What are the clearances for fastener holes?",
    "What partial safety factors apply to materials?",
    "Diagram of plates with bolts holes in tension",
    "What is the minimum design action on a connection?",
)


def tokenize(text):
    """Lowercase, split punctuation, preserve numbers, remove common stop words.

    No stemming or synonyms yet: 'hole' and 'holes' are different tokens.
    'not', 'no', and 'without' are kept, though matching does not understand logic.
    """
    return [word for word in re.findall(r"[a-z0-9]+(?:\.[0-9]+)*", text.lower())
            if word not in STOP_WORDS]


def load_chunks():
    chunks = []
    seen = set()
    for name in FILES:
        path = ROOT / "data" / name
        if not path.is_file():
            command = "export_chunks.py" if name == "chunks.jsonl" else "prepare_demo_assets.py"
            raise ValueError(f"Missing {path}. Run: python scripts/{command}")
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {name}:{line_number}") from exc
                if not isinstance(chunk, dict) or not all(
                    chunk.get(key) for key in ("chunk_id", "text", "pdf_pages", "source_links")
                ) or not chunk["text"].strip():
                    raise ValueError(f"Missing text or source metadata in {name}:{line_number}")
                if chunk["chunk_id"] in seen:
                    raise ValueError(f"Duplicate chunk ID: {chunk['chunk_id']}")
                seen.add(chunk["chunk_id"])
                # Add defaults in memory; all original display/source fields survive.
                chunk.setdefault("content_type", "clause")
                chunk.setdefault("renderer", "text")
                chunks.append(chunk)
    return chunks


class KeywordRetriever:
    def __init__(self, chunks):
        self.passages = []
        for chunk in chunks:
            text_tokens = tokenize(chunk["text"])
            # Index type labels too, so 'diagram' can find the image record.
            terms = set(text_tokens) | set(tokenize(chunk["content_type"]))
            self.passages.append((chunk, terms, len(text_tokens)))

    def search(self, question, top_k=3):
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        query_terms = set(tokenize(question))
        if not query_terms:
            raise ValueError("The question has no search terms after removing stop words.")
        scored = []
        for chunk, terms, length in self.passages:
            matched = sorted(query_terms & terms)
            if matched:
                scored.append({"score": len(matched), "matched_terms": matched,
                               "query_term_count": len(query_terms), "chunk": chunk,
                               "passage_length": length})
        scored.sort(key=lambda result: (-result["score"], result["passage_length"],
                                        result["chunk"]["chunk_id"]))
        return scored[:top_k]


def print_results(question, results):
    print(f"\nQuestion: {question}")
    print(f"Search terms: {', '.join(sorted(set(tokenize(question))))}")
    if not results:
        print("No matching chunks found.")
        return
    for rank, result in enumerate(results, 1):
        chunk = result["chunk"]
        print(f"\n{rank}. {chunk['chunk_id']} [{chunk['content_type']}]")
        print(f"   Matched {result['score']}/{result['query_term_count']} terms: "
              f"{', '.join(result['matched_terms'])}")
        print(f"   PDF pages: {', '.join(map(str, chunk['pdf_pages']))}; "
              f"renderer: {chunk['renderer']}")
        print(f"   Source: {', '.join(chunk['source_links'])}")
        if chunk["content_type"] == "table":
            ref = chunk["structured_data_ref"]
            print(f"   Rows: {ref['file']} (record_id={ref['record_id']})")
        elif chunk["content_type"] == "diagram":
            print(f"   Image: {chunk['image_path']}")
        print(f"   Review: {chunk.get('review_status', 'unspecified')}")
        snippet = textwrap.shorten(" ".join(chunk["text"].split()), width=350, placeholder=" …")
        print(f"   Text: {snippet}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Question enclosed in quotes")
    parser.add_argument("--examples", action="store_true", help="Run the five review questions")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results (default: 3)")
    args = parser.parse_args()
    if bool(args.question) == args.examples:
        parser.error("Supply either one question or --examples.")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1.")
    try:
        chunks = load_chunks()
        retriever = KeywordRetriever(chunks)
        counts = Counter(chunk["content_type"] for chunk in chunks)
        print(f"Loaded {len(chunks)} chunks: {counts['clause']} clauses, "
              f"{counts['table']} tables, {counts['diagram']} diagram.")
        questions = EXAMPLE_QUESTIONS if args.examples else (args.question,)
        for question in questions:
            print_results(question, retriever.search(question, args.top_k))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
