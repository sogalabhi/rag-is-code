"""Compare keyword, semantic and hybrid retrieval over the same saved chunks.

Embeddings run locally. The first semantic run downloads a small model and builds
a cached index. No API key, vector server, or answer generation is involved.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import textwrap

if __package__:
    from .retrieve import EXAMPLE_QUESTIONS, KeywordRetriever, load_chunks, tokenize
else:
    from retrieve import EXAMPLE_QUESTIONS, KeywordRetriever, load_chunks, tokenize

ROOT = Path(__file__).resolve().parent.parent
MODEL = "BAAI/bge-small-en-v1.5"
INDEX = ROOT / ".cache" / "search" / "index.npz"
WINDOW_TOKENS = 384
OVERLAP_TOKENS = 48
EXAMPLES = EXAMPLE_QUESTIONS + ("What loads arise from vehicle collisions?",)


def log(message):
    print(message, file=sys.stderr, flush=True)


def dependencies():
    try:
        import numpy as np
        from fastembed import TextEmbedding
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise ValueError("Install search dependencies: python -m pip install -r requirements-search.txt") from exc
    return np, TextEmbedding, Tokenizer


def fuse_rankings(keyword, semantic, top_k=3):
    """Reciprocal rank fusion combines ranks, not incomparable raw scores."""
    combined = {}
    for name, results in (("keyword", keyword), ("semantic", semantic)):
        for rank, result in enumerate(results, 1):
            key = result["chunk"]["chunk_id"]
            item = combined.setdefault(key, {"chunk": result["chunk"], "score": 0.0,
                                              "keyword_rank": None, "semantic_rank": None})
            item["score"] += 1 / (60 + rank)
            item[f"{name}_rank"] = rank
    return sorted(combined.values(), key=lambda r: (-r["score"], r["chunk"]["chunk_id"]))[:top_k]


class SemanticRetriever:
    def __init__(self, chunks, rebuild=False):
        self.chunks = chunks
        self.np, TextEmbedding, Tokenizer = dependencies()
        self.texts = [f"{chunk['content_type']}\n{chunk['text']}" for chunk in chunks]
        signature = hashlib.sha256(json.dumps(
            [(chunk["chunk_id"], text) for chunk, text in zip(chunks, self.texts)],
            ensure_ascii=False, separators=(",", ":")
        ).encode()).hexdigest()
        self.manifest = {"schema": 1, "model": MODEL, "corpus_sha256": signature,
                         "window_tokens": WINDOW_TOKENS, "overlap_tokens": OVERLAP_TOKENS,
                         "fastembed_version": importlib.metadata.version("fastembed")}
        log("Loading local embedding model (the first run downloads its files)...")
        self.model = TextEmbedding(model_name=MODEL, cache_dir=str(ROOT / ".cache" / "models"),
                                   threads=2, providers=["CPUExecutionProvider"])
        if not rebuild and self._load_index():
            log(f"Reusing semantic index: {len(chunks)} records, {len(self.owners)} windows.")
            return
        # Clone the tokenizer: windowing must not change query/model tokenization.
        tokenizer = Tokenizer.from_str(self.model.model.tokenizer.to_str())
        tokenizer.no_padding()
        tokenizer.enable_truncation(max_length=WINDOW_TOKENS, stride=OVERLAP_TOKENS)
        windows, owners = [], []
        for owner, text in enumerate(self.texts):
            encoded = tokenizer.encode(text, add_special_tokens=False)
            for part in [encoded, *encoded.overflowing]:
                start, end = part.offsets[0][0], part.offsets[-1][1]
                windows.append(text[start:end])
                owners.append(owner)
        log(f"Embedding {len(windows)} windows from {len(chunks)} records...")
        vectors = list(self.model.passage_embed(windows, batch_size=32))
        self.vectors = self._normalize(self.np.asarray(vectors, dtype=self.np.float32))
        self.owners = self.np.asarray(owners, dtype=self.np.int32)
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        # Replace the finished cache atomically; partial files cannot look valid.
        temporary = INDEX.with_suffix(".tmp")
        with temporary.open("wb") as stream:
            self.np.savez_compressed(stream, manifest=json.dumps(self.manifest),
                                     vectors=self.vectors, owners=self.owners)
        temporary.replace(INDEX)
        log(f"Saved semantic index: {INDEX}")

    def _normalize(self, vectors):
        norms = self.np.linalg.norm(vectors, axis=-1, keepdims=True)
        return vectors / self.np.maximum(norms, 1e-12)

    def _load_index(self):
        if not INDEX.is_file():
            return False
        try:
            with self.np.load(INDEX, allow_pickle=False) as saved:
                if json.loads(saved["manifest"].item()) != self.manifest:
                    return False
                vectors, owners = saved["vectors"], saved["owners"]
            if (vectors.ndim != 2 or vectors.shape[1] != 384 or owners.ndim != 1
                    or len(vectors) != len(owners) or not len(owners)
                    or not self.np.issubdtype(owners.dtype, self.np.integer)
                    or owners.min() < 0 or owners.max() >= len(self.chunks)
                    or len(self.np.unique(owners)) != len(self.chunks)
                    or not self.np.isfinite(vectors).all()):
                return False
            self.vectors, self.owners = vectors, owners
            return True
        except (ValueError, OSError, KeyError):
            return False

    def search(self, question, top_k=3):
        if top_k < 1 or not question.strip():
            raise ValueError("Supply a nonempty question and positive top_k.")
        query = self.np.asarray(next(iter(self.model.query_embed(question))), dtype=self.np.float32)
        query = self._normalize(query)
        window_scores = self.vectors @ query
        # A long clause can have several windows; return the original clause once.
        scores = self.np.full(len(self.chunks), -self.np.inf, dtype=self.np.float32)
        self.np.maximum.at(scores, self.owners, window_scores)
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), self.chunks[i]["chunk_id"]))
        return [{"score": float(scores[i]), "chunk": self.chunks[i]} for i in order[:top_k]]


def rank_question(question, keyword, semantic, method="compare", top_k=3):
    if not tokenize(question):
        raise ValueError("The question has no content search terms.")
    pool = max(20, top_k)
    lexical = keyword.search(question, pool) if method in ("keyword", "hybrid", "compare") else []
    dense = semantic.search(question, pool) if method in ("semantic", "hybrid", "compare") else []
    results = {}
    if method in ("keyword", "compare"):
        results["keyword"] = lexical[:top_k]
    if method in ("semantic", "compare"):
        results["semantic"] = dense[:top_k]
    if method in ("hybrid", "compare"):
        results["hybrid"] = fuse_rankings(lexical, dense, top_k)
    return results


def print_rankings(question, rankings, compact=False):
    print(f"\nQuestion: {question}")
    for method, results in rankings.items():
        print(f"  {method.upper()}")
        if not results:
            print("    No matching chunks.")
        for rank, result in enumerate(results, 1):
            chunk = result["chunk"]
            score = f"{result['score']:.4f}" if method != "keyword" else str(result["score"])
            print(f"    {rank}. {chunk['chunk_id']} | score={score} | "
                  f"PDF {','.join(map(str, chunk['pdf_pages']))} | {chunk['renderer']}")
            if not compact:
                print(f"       Source: {', '.join(chunk['source_links'])}")
                if method == "hybrid":
                    print(f"       Ranks: keyword={result['keyword_rank']}, semantic={result['semantic_rank']}")
                print("       " + textwrap.shorten(" ".join(chunk["text"].split()), width=180, placeholder=" …"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?")
    parser.add_argument("--examples", action="store_true", help="Compare six example questions, including a paraphrase")
    parser.add_argument("--method", choices=("keyword", "semantic", "hybrid", "compare"), default="compare")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--rebuild", action="store_true", help="Rebuild cached embeddings")
    parser.add_argument("--json", action="store_true", help="Print complete results and metadata as JSON")
    args = parser.parse_args()
    if bool(args.question) == args.examples:
        parser.error("Supply either one question or --examples.")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1.")
    questions = EXAMPLES if args.examples else (args.question,)
    if any(not tokenize(question) for question in questions):
        parser.error("The question has no content search terms.")
    try:
        chunks = load_chunks()
        keyword = KeywordRetriever(chunks)
        semantic = None if args.method == "keyword" else SemanticRetriever(chunks, rebuild=args.rebuild)
        log(f"Loaded {len(chunks)} records. Scores use different scales across methods.")
        output = []
        for question in questions:
            rankings = rank_question(question, keyword, semantic, args.method, args.top_k)
            if args.json:
                output.append({"question": question, "rankings": rankings})
            else:
                print_rankings(question, rankings, compact=args.examples)
        if args.json:
            print(json.dumps({"model": MODEL if semantic else None, "results": output}, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
