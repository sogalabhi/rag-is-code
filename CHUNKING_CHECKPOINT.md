# Clause export checkpoint

The active project is this `rag-is-code` repository, which retains the original
Git history. Use the existing JSON without rerunning PDF preparation.

1. Load 126 terminology records and 817 clause candidates.
2. Map each existing record to one chunk, preserving text and clause boundaries.
3. Attach a stable clause ID, PDF pages and links, source pointer and OCR flags.
4. Write one complete JSON object per line to `data/chunks.jsonl`.

From the active repository:

```bash
cd /home/abhijith/coding/rag-is-code/rag-is-code
python scripts/export_chunks.py --preview
```

Preview writes no files and displays five complete records. The user already
inspected the same samples in the sibling folder. To save the export, run:

```bash
python scripts/export_chunks.py
```

The script uses only Python's standard library and creates or replaces only
`data/chunks.jsonl`. It should report 943 chunks. Duplicate IDs and empty text
cause an error. IDs remain stable while clause IDs remain the same.

All records retain uncertainty flags and their exact extracted text. Heading-only
clauses remain separate; long clauses are not split yet. The longest has 621
whitespace-separated words, and there are zero empty records. These checks do not
prove PDF completeness. Clause 1.5 visibly retains damaged unit notation.

PDF links are relative to this repository root; viewer pages are one-based.
The source record pointer lets you revisit original fragments and bounding boxes
where available. Amendments are not applied. Tables and the diagram live in the
separate three-record `data/demo_asset_chunks.jsonl` collection.

Phase 1 is complete: the user reviewed the asset preview and ran the export here.
Validation found 943 clause chunks and 3 asset chunks, 946 unique IDs, zero empty
text fields, and intact source references. Clause texts match their source
records exactly. Phase 2 begins with keyword retrieval theory before coding.
