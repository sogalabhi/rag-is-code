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

Begin Phase 2 with the theory of keyword retrieval and a small interactive
exercise. Then build one keyword retriever reading both JSONL collections
(943 clauses + 3 assets = 946 records), preserving renderer metadata and returning
source pages. Let the user run it and inspect results for five example questions.
Do not jump to embeddings, generated answers or the interface. The user wants
theory alongside implementation, one checkpoint at a time.
