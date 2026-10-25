# Tables and diagram checkpoint

The working project is this `rag-is-code` repository, with its existing Git
history. The sibling `rag-is-code-new` is a reference copy. This checkpoint adds a separate collection without changing the 943
clause records, the clause exporter, or any existing table data.

## Three records

| Chunk ID | Content | PDF page | Display |
|---|---|---|---|
| `is800-2007:table:05` | Table 5: Partial Safety Factor for Materials | 44 | 7 source rows, with general and fabrication columns |
| `is800-2007:table:19` | Table 19: Clearances for Fastener Holes | 87 | 4 source rows, with clearance notes |
| `is800-2007:figure:05` | Figure 5: Plates with Bolts Holes in Tension | 47 | Original PDF crop and caption; related clause 6.3.1 |

The caption's wording is retained from the PDF. Descriptions use the caption and
explicit clause reference; no automatic interpretation of the diagram is added.
PDF page numbers differ from printed page numbers; both are recorded.

## Run and inspect

From this `rag-is-code` repository, using your Python environment:

```bash
python scripts/prepare_demo_assets.py --preview
```

This prints all three records without writing files, using only the standard
library. The `text` field is intended for future search. `structured_data_ref`
points to a table's existing columns and rows; `image_path` points to the diagram.
The `renderer` field identifies which display to use.

To regenerate the assets and static HTML preview:

```bash
python -m pip install -r requirements.txt
python scripts/prepare_demo_assets.py
```

This uses the project's existing PyMuPDF dependency to crop one known rectangle.
It does not rerun document preparation. It creates or replaces only:

- `data/demo_asset_chunks.jsonl` — three complete records.
- `data/review_assets/figure-05.png` — the selected PDF crop.
- `reports/demo_assets_preview.html` — both tables, the diagram, source links,
  and expandable metadata.

Those three outputs have already been generated for review. Open
`reports/demo_assets_preview.html` in your browser. If your editor requires an
HTTP URL, run this from this `rag-is-code` repository:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8000/reports/demo_assets_preview.html`.
Stop the server with Ctrl+C. This is a static preview, with no search or model.

The two table records retain their existing assistant review status; independent
review has not been performed. The remaining tables, equations, symbols, and
amendment records are outside this checkpoint.

Phase 1 is complete: the user reviewed the three asset records, confirmed the
tables and diagram display correctly, and exported `data/chunks.jsonl` with 943
clause chunks. Validation confirmed 946 unique nonempty records across the two
collections, preserved clause text, and resolvable source/display references.
A later retriever can read both JSONL files. No retrieval has been implemented.
