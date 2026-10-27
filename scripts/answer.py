"""Retrieve evidence, then generate a cited answer through a configurable LLM.

--preview shows model input without making an API call. Add --method keyword to
run the preview using only Python's standard library.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag_demo.grounding import GroundedAnswerer, prepare_request
from rag_demo.providers import create_provider
from retrieve import KeywordRetriever, load_chunks, tokenize
from search import SemanticRetriever, rank_question


def print_answer(answer):
    print(f"\nStatus: {answer['status']}")
    for claim in answer["claims"]:
        refs = ", ".join(dict.fromkeys(c["source_id"] for c in claim["citations"]))
        print(f"\n{claim['text']} [{refs}]")
    for note in answer["limitations"]:
        print(f"\nLimitation: {note}")
    for source in answer["sources"]:
        chunk = source["chunk"]
        print(f"\n[{source['source_id']}] {chunk['chunk_id']} | "
              f"PDF pages {', '.join(map(str, chunk['pdf_pages']))} | {chunk.get('renderer', 'text')}")
        print(f"  Source: {', '.join(chunk['source_links'])}")
        print(f"  Review: {chunk.get('review_status', 'unspecified')}")
        if chunk.get("content_type") == "table":
            ref = chunk["structured_data_ref"]
            print(f"  Table: {ref['file']} (record_id={ref['record_id']})")
        elif chunk.get("content_type") == "diagram":
            print(f"  Image: {chunk['image_path']}")
    if answer["generation"]:
        print(f"\nModel: {answer['generation']['provider']} / {answer['generation']['model']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--method", choices=("keyword", "semantic", "hybrid"), default="hybrid")
    parser.add_argument("--provider", help="Provider name or module:ClassName (default: LLM_PROVIDER or gemini)")
    parser.add_argument("--model", help="Model override (default: LLM_MODEL or provider default)")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--preview", action="store_true", help="Inspect evidence and prompt without an API call")
    parser.add_argument("--json", action="store_true", help="Print complete result, citations and display data")
    args = parser.parse_args()
    if args.top_k < 1 or not tokenize(args.question):
        parser.error("Supply content search terms and a positive --top-k.")
    try:
        provider = None if args.preview else create_provider(args.provider, args.model)
        chunks = load_chunks()
        keyword = KeywordRetriever(chunks)
        semantic = None if args.method == "keyword" else SemanticRetriever(chunks)
        results = rank_question(args.question, keyword, semantic, args.method, args.top_k)[args.method]
        if args.preview:
            request, sources = prepare_request(args.question, results)
            preview = {"preview_only": True, "api_call_made": False, "question": args.question,
                       "retrieval_method": args.method, "sources": list(sources.values()),
                       "request": {"system_instruction": request.system_instruction,
                                   "prompt": json.loads(request.prompt),
                                   "response_schema": request.response_schema}}
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            return
        answer = GroundedAnswerer(provider).answer(args.question, results)
        if args.json:
            print(json.dumps(answer, ensure_ascii=False, indent=2))
        else:
            print_answer(answer)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
