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
Phase 1 is complete: the user reviewed the assets and exported the clauses.
There are 946 records across the two JSONL collections, with unique IDs and
nonempty text. Phase 2 now has a keyword retriever. Start with:

```bash
python scripts/retrieve.py "What are the clearances for fastener holes?"
```

It prints matching terms, ranked passages and source pages, preserving table and
image display references. No new dependencies are needed. See
`RETRIEVAL_CHECKPOINT.md` for the theory and five review questions. The user asked
for larger checkpoints, so review is now combined with the comparison below.

Semantic and hybrid search are now available as a larger comparison checkpoint:

```bash
python -m pip install -r requirements-search.txt
python scripts/search.py --examples
```

This compares all three methods across six questions. The first semantic run
downloads a local model and builds a cached index; later runs reuse it. Read
`SEARCH_CHECKPOINT.md` for the theory. The interactive interface remains a later
step.

Recorded results and tradeoffs are in `reports/search_comparison.md`. Semantic
search fixes the vehicle-collision paraphrase; hybrid search is not best for
every question. Both retain the same source, table and diagram metadata.

Grounded answers now use a pluggable `LLMProvider` abstract class with Gemini as
the first adapter. Preview the exact evidence and model input without a key:

```bash
python scripts/answer.py "What are accidental loads?" --method keyword --preview
```

For live generation install `requirements-llm.txt`, export `GEMINI_API_KEY`, and
run the same command without `--preview`. `LLM_PROVIDER` and `LLM_MODEL` select
the implementation and model. See `ANSWER_CHECKPOINT.md` for theory, configuration,
provider extension and verification status.

Gemini generation automatically tries `gemini-3.8-flash`, `gemini-3.6-flash`,
`gemini-3.5-flash-lite`, then `gemini-3.1-flash-lite` when models are unavailable,
rate-limited, or time out. `LLM_MODEL` selects the primary and
`LLM_FALLBACK_MODELS` supplies a comma-separated fallback order. Each model is
attempted once. Use `--fallback-models` to override the list or `--no-fallback`
to use only the primary. JSON output records the attempt history and actual
answering model; citation validation remains the same for every model.

## Web Application & UI Prototype

The interactive web application is located in `prototype/`: a React + TypeScript + Vite frontend featuring Source Serif 4 typography, solid yellowish paper palette, KaTeX math typesetting, interactive source inspection, and clarification flows.

### Prerequisites

* Node.js 18+ and npm
* Python 3.10+
* (Optional) `GEMINI_API_KEY` or `GOOGLE_API_KEY` set in `.env` or exported in your shell for live answers.

### 1. Python Environment Setup

Create and activate a virtual environment, then install the required backend packages:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# Upgrade pip and install requirements
python -m pip install --upgrade pip
python -m pip install -r requirements-api.txt -r requirements-search.txt -r requirements-llm.txt
```

### Option 1: Development Mode (Vite + FastAPI with live reload)

Run the backend and frontend in separate terminals for instant hot reloading:

1. **Start the Python API Backend** (ensure `.venv` is activated; default port is 8000):
   ```bash
   uvicorn rag_demo.api:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start the Frontend Vite Dev Server**:
   ```bash
   cd prototype
   npm ci
   npm run dev
   ```
   Open `http://127.0.0.1:5173/` in your browser. Vite automatically proxies `/api` requests to the backend at `http://127.0.0.1:8000`.

### Option 2: Unified Production Mode (FastAPI serving built UI)

Build the static assets and serve everything from a single port:

```bash
# 1. Build the React frontend
cd prototype
npm ci
npm run build
cd ..

# 2. Run the unified FastAPI server on port 8000 (ensure .venv is activated)
uvicorn rag_demo.api:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/` in your browser. The app serves the built UI and all `/api/*` endpoints directly.


