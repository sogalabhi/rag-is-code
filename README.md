# IS 800:2007 RAG learning demo

This is the active project, preserving its existing Git history. The sibling
`rag-is-code-new` is a reference copy. Read `CODEX_HANDOFF.md` for current scope.

The demo uses 943 existing clause records, two selected tables (5 and 19), and
one diagram (Figure 5). Comprehensive extraction is outside the demo scope.

From this repository:

```bash
python scripts/export_chunks.py --preview
python scripts/prepare_demo_assets.py --preview
```

Both previews print records without writing files. To save clause chunks:

```bash
python scripts/export_chunks.py
```

The table and diagram collection and its HTML preview are already prepared.
Open `reports/demo_assets_preview.html` in your browser to review them.
To regenerate these assets, use Python 3.10+ with the existing dependency:

```bash
python -m pip install -r requirements.txt
python scripts/prepare_demo_assets.py
```

See `CHUNKING_CHECKPOINT.md` and `DEMO_ASSETS_CHECKPOINT.md` for explanations.
Retrieval is not implemented; review the assets before continuing.
