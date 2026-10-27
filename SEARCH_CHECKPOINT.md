# Compare retrieval methods

This larger checkpoint combines semantic retrieval and hybrid retrieval while
keeping the original keyword baseline available. All methods search the same
946 records and preserve their source, table, and image metadata. No answers
are generated yet.

## Run

From the active `rag-is-code` repository, install the optional search dependency
in your Python environment once:

```bash
python -m pip install -r requirements-search.txt
```

Then run one comparison of six questions:

```bash
python scripts/search.py --examples
```

The sixth question, "What loads arise from vehicle collisions?", paraphrases
the accidental-load definition. The first semantic run downloads model files
and builds the index. Later runs reuse the model files and cached passage vectors.
This needs no API key or separate vector database service. Search is performed
locally; model files are downloaded during setup, and source text is not sent to
an embedding API.

For your own question:

```bash
python scripts/search.py "What loads arise from vehicle collisions?"
python scripts/search.py "What are the clearances for fastener holes?" --method hybrid
```

Choose `keyword`, `semantic`, `hybrid`, or the default `compare` with `--method`.
The keyword mode also works without the optional dependencies. `--top-k` controls
the result count. `--json` prints complete records and metadata as machine-readable
JSON, with progress messages on stderr.

## Theory in three parts

- **Keyword search:** count distinct shared search words. It is transparent but
  misses synonyms and may rank a short, partly relevant passage highly.
- **Semantic search:** encode text and the complete question as numerical vectors
  (embeddings). Similarity between those vectors can retrieve related meaning
  despite different wording. This implementation uses normalized vectors and
  their dot product, equivalent to cosine similarity.
- **Hybrid search:** combine the two ranked lists using reciprocal rank fusion:
  each appearance adds `1 / (60 + rank)`. We fuse the best 20 candidates from each
  method (or more if `top-k` is larger), favoring results that rank well in both.
  Their raw scores have different scales, so they are not added together.

The model is `BAAI/bge-small-en-v1.5` through FastEmbed, producing 384-dimensional
text embeddings. Model implementation and supported-model details are in the
[FastEmbed documentation](https://qdrant.github.io/fastembed/).

Long records use overlapping 384-token windows with 48 tokens of overlap, safely
below this model's 512-token input limit. Windows are sliced using tokenizer
offsets from the original text. Each window is embedded, and a record's semantic
score is its best matching window. Results are deduplicated back to the original
record, so the corpus remains 946 chunks. Source text and existing JSONL files
are unchanged. The diagram is searched through its caption, not its pixels.

## Inspect together

Look at which method puts useful evidence first. A method can improve one question
and worsen another. Neither embedding similarity nor fused rank is an answer
confidence. Nearest neighbors can still appear for unsupported questions; answer
grounding and insufficient-evidence handling belong to the next checkpoint.

Model files and the local vector index live under `.cache/` and are ignored by
Git. The index signature includes record IDs, searchable text, model version,
and window settings. Changed text or ordering triggers a rebuild. `--rebuild`
explicitly rebuilds vectors when needed.

After reviewing the comparison, continue to source-grounded answer generation.
The remaining broader milestones are grounded answers, the interactive interface
with clarification options, and final demo checks. Routine mechanical checks are
handled by the agent; keep user checkpoints to working features and short theory.
