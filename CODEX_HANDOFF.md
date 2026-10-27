# Continue the IS 800:2007 RAG learning demo

## Active repository

Work in `/home/abhijith/coding/rag-is-code/rag-is-code`. The user explicitly chose
this older folder because it has existing Git history. The sibling
`rag-is-code-new` is a reference copy, not the active project. No new commit was
made during the switch. Its preparation pipeline was not copied or rerun.
Existing tracked parser, symbol scripts and datasets were preserved unchanged.

## Working style and scope

Explain one learning checkpoint, implement it, let the user run it, inspect the
output, then continue. Do not rebuild the PDF parser or exhaustively review
equations and tables. Keep PDF page links and OCR uncertainty. Never invent
numerical values or diagram meaning.

The reduced demo should show clause answers with citations, two source-checked
tables rendered as rows and columns, one original PDF diagram crop, and one
clarification flow with member-type options and custom input. Add keyword
retrieval first; embeddings, hybrid retrieval, grounded answers and an interface
come later. Comprehensive codebook coverage is outside this demo.

## Files available here

- Original PDF: `data/is.800.2007.pdf`, 158 pages. It is identical to the sibling's
  PDF. The original terminology dataset is also identical and is reused.
- `data/section1_terminology.json`: 126 original records.
- `data/clause_candidates.json`: 817 additional candidates, imported for the demo.
- `scripts/export_chunks.py`: builds 943 clause chunks with stable IDs, text,
  one-based PDF pages, source links and OCR flags. The user already ran and shared
  five preview records, then ran the export in this active repository.
  `data/chunks.jsonl` now contains 943 saved clause chunks.
- Clause size check: 0 empty records. Longest five, in whitespace-separated words:
  5.1.2 (621), 8.4.2.2 (459), 10.7 (457), E-1.2 (429), 14.2.3 (378). Keep boundaries
  for the first baseline, then evaluate whether splitting helps retrieval.
- `data/tables_structured.json`: only the two selected table records copied here,
  Table 5 (7 rows, PDF page 44) and Table 19 (4 rows, PDF page 87). Their existing
  assistant review status is retained; independent review has not been performed.
  Other table data remains in the sibling reference folder.
- `scripts/prepare_demo_assets.py`: prepares two table chunks referencing those
  rows and one diagram chunk; `--preview` writes no files.
- `data/demo_asset_chunks.jsonl`: 3 generated asset records. Table searchable text
  includes original row values; `structured_data_ref` points to the existing rows.
  `renderer` is `table` or `image`.
- `data/review_assets/table-05.png`, `table-19.png`: existing table source crops.
- `data/review_assets/figure-05.png`: visually inspected crop of Figure 5,
  "Plates with Bolts Holes in Tension," PDF page 47 (printed page 33), referenced
  by clause 6.3.1. Description uses only the caption and explicit clause reference.
- `reports/demo_assets_preview.html`: static preview of two tables and the image,
  with source links and expandable complete chunk records. It has no retrieval.
- `requirements.txt`: existing PyMuPDF dependency, used only to regenerate a crop.
- `scripts/retrieve.py`: standard-library keyword retriever over both JSONL
  collections. Lowercases, tokenizes and removes common stop words; matches
  distinct query words against chunk text and content type. Score is the number
  of matching terms, with shorter tokenized passages preferred on ties. Original
  metadata is preserved; clause records get `content_type=clause` and
  `renderer=text` defaults in memory. No stemming, embeddings or generation.
  Run one quoted question or `--examples`; `--top-k` defaults to 3. It writes no
  files. See `RETRIEVAL_CHECKPOINT.md` for explanations and known limitations.
- `scripts/search.py`: compares keyword, local semantic and hybrid retrieval.
  Optional dependencies are in `requirements-search.txt` (FastEmbed 0.9.1 and
  NumPy). Uses `BAAI/bge-small-en-v1.5` with 384-dimensional normalized embeddings
  and cosine similarity. 384-token windows overlap by 48 tokens; the 946 original
  records become 959 embedding windows, collapsed back to source records at search
  time. Hybrid search uses reciprocal rank fusion with constant 60 over the best
  20 candidates per method. All source/renderer metadata is retained. `--examples`
  compares six questions; `--method` selects a method; `--json` keeps full metadata.
  Models and signature-checked vectors are cached under ignored `.cache/`. This
  agent has built and verified the cache locally; users can recreate it on first
  run. No embedding API or vector database server is required.
- `SEARCH_CHECKPOINT.md`: theory and the combined comparison command.
- `reports/search_comparison.md`: actual top results and observed failures for
  six example questions. Semantic search improves vehicle collisions and minimum
  connection action, but ranks general material safety factors poorly. Hybrid
  retains clause 5.4.1/Table 5 among the first three for that question but misses
  the accidental-load definition among the first three for vehicle collisions.
  Do not claim hybrid is universally better or treat similarities as confidence.

The larger table/symbol/equation preparation datasets and old audit reports in
the sibling folder are reference material. They are not prerequisites for this
demo. The clause and table data represent original-edition text; amendment
instructions have not been applied.

## Next checkpoint

Phase 1 is complete. The user previewed all three asset records, opened the static
HTML preview and confirmed that everything displayed correctly, then exported
the 943 clause chunks and shared the output. Read-only validation confirmed 946
unique IDs across both JSONL files, zero empty text fields, valid PDF page links,
and resolvable table/image references. All 943 exported clause texts match the
existing source records exactly. These structural checks do not establish full
PDF coverage or OCR accuracy.

Phase 2 has begun. The user identified `clearances`, `fastener`, and `holes` as
useful terms and learned about stop words. They then authorized continuing.
The retriever is implemented and developer-checked: expected evidence appears
among the top 3 for all five documented example questions, and table/image
references survive. Table 19 ranks first for the initial fastener-hole question.
No-match and stop-word-only inputs are handled, and source files remain unchanged.
These five examples are a learning sanity check, not a comprehensive evaluation.

The user then said progress was too slow. Change the pace: handle routine checks
autonomously, group related implementation into working features, keep theory
short, and request one meaningful review per feature. Do not require pasting
each result or answering a quiz for every small step.

The combined Phase 2/3 search comparison is now implemented and checked with real
local embeddings: six questions, normalized vectors, cached reload, stale-corpus
detection, rank fusion, unique results and preserved metadata. The sources are
unchanged. User review of the combined comparison is still pending. Let them run
`python -m pip install -r requirements-search.txt` in their environment once,
then `python scripts/search.py --examples`. Present a short explanation of keyword,
semantic and hybrid retrieval together. They can also read the recorded report.
Then continue to grounded answers, the interactive demo with clarification options,
and final demo checks. Do not build the entire app without teaching checkpoints.
