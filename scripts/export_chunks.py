"""Export existing clause records; no PDF parsing or retrieval.

Run with --preview to inspect five examples without writing any files.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SAMPLE_IDS = ("1.1", "1.1.1", "1.3.1", "1.5", "1.6")


def build_chunks():
    chunks = []
    seen = set()
    for filename in ("section1_terminology.json", "clause_candidates.json"):
        records = json.loads((DATA / filename).read_text(encoding="utf-8"))
        for index, record in enumerate(records):
            clause_id = record["clause_id"]
            chunk_id = f"is800-2007:clause:{clause_id}"
            if chunk_id in seen:
                raise ValueError(f"Duplicate clause ID: {clause_id}")
            seen.add(chunk_id)
            # Preserve extracted content, including uncertain OCR and line breaks.
            text = record["content"]
            pages = sorted(set(record.get("source_pages") or range(
                record["start_page"], record["end_page"] + 1)))
            if not text.strip() or not pages or any(
                not isinstance(page, int) or page < 1 for page in pages
            ):
                raise ValueError(f"Empty text or invalid pages: {clause_id}")
            chunks.append({
                "chunk_id": chunk_id,
                "clause_id": clause_id,
                "text": text,
                "pdf_pages": pages,
                "source_pdf": "data/is.800.2007.pdf",
                "source_links": [f"data/is.800.2007.pdf#page={page}" for page in pages],
                "source_record": {"file": f"data/{filename}", "index": index},
                "edition_scope": record.get("edition_scope", "original_2007_text"),
                "review_status": record.get("review_status", "extracted_not_verified"),
                "review_flags": sorted(set(record.get("review_flags", [])) | {"ocr_not_fully_verified"}),
                "amendment_ids": record.get("amendment_ids", []),
            })
    return chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Show samples without writing chunks.jsonl")
    args = parser.parse_args()
    chunks = build_chunks()
    if not args.preview:
        output = DATA / "chunks.jsonl"
        output.write_text("".join(json.dumps(chunk, ensure_ascii=False) + "\n"
                                  for chunk in chunks), encoding="utf-8")
        print(f"Wrote {len(chunks)} chunks to {output}")
    else:
        print(f"Preview: {len(chunks)} chunks; no files written.")
    print("Five samples (complete records):")
    by_clause = {chunk["clause_id"]: chunk for chunk in chunks}
    for clause_id in SAMPLE_IDS:
        print(json.dumps(by_clause[clause_id], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
