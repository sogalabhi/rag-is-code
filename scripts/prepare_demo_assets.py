"""Prepare two table chunks, one diagram chunk, and a static rendering preview.

--preview prints the three records without writing files. This script never
changes chunks.jsonl or the existing table datasets and implements no retrieval.
"""
import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TABLE_FILE = "data/tables_structured.json"
FIGURE_PATH = "data/review_assets/figure-05.png"
FIGURE_BBOX = [42, 262, 266, 419]
CAPTION_BBOX = [60, 400, 255, 417]
CAPTION_RAW = "FIG. 5 PLATESWITHBOLTSHOLESINTENSION"
CAPTION = "Plates with Bolts Holes in Tension"
HEADERS = {
    5: ["Serial", "Definition", "Symbol", "General", "Shop fabrication", "Field fabrication"],
    19: ["Serial", "Nominal fastener diameter (mm)", "Standard clearance (mm)",
         "Oversize clearance (mm)", "Short slot length clearance (mm)",
         "Long slot length clearance"],
}


def source_fields(pages):
    return {
        "pdf_pages": pages,
        "source_pdf": "data/is.800.2007.pdf",
        "source_links": [f"data/is.800.2007.pdf#page={page}" for page in pages],
        "edition_scope": "original_2007_text",
    }


def build_records():
    tables = json.loads((ROOT / TABLE_FILE).read_text(encoding="utf-8"))
    selected = {r["table_number"]: r for r in tables if r["table_number"] in (5, 19)}
    records = []
    for number in (5, 19):
        table = selected[number]
        if table.get("status") != "assistant_visually_reviewed":
            raise ValueError(f"Table {number} lacks the expected recorded review")
        if not (DATA / table["source_crop"]).is_file():
            raise ValueError(f"Table {number} source crop is missing")
        description = (
            "Material resistance and connection partial safety factors, with general, "
            "shop fabrication and field fabrication columns."
            if number == 5 else
            "Fastener hole clearances by nominal diameter, including standard holes, "
            "oversize holes, short slots and long slots."
        )
        lines = [f"Table {number}: {table['title']}", description,
                 f"Related clauses: {', '.join(table['clause_references'])}"]
        for row in table["rows"]:
            if len(row) != len(HEADERS[number]):
                raise ValueError(f"Table {number} has inconsistent row widths")
            # Search text includes original values; display still uses source rows.
            lines.append("; ".join(f"{label}: {value}" for label, value
                                   in zip(HEADERS[number], row) if value is not None))
        lines.extend(table.get("header_notes", []))
        lines.extend(table.get("notes", []))
        lines.append(table["structure_note"])
        records.append({
            "chunk_id": f"is800-2007:table:{number:02d}",
            "content_type": "table",
            "renderer": "table",
            "table_number": number,
            "title": table["title"],
            "description": description,
            "text": "\n".join(lines),
            "clause_ids": table["clause_references"],
            **source_fields([table["pdf_page"]]),
            "printed_page": table["printed_page"],
            "structured_data_ref": {"file": TABLE_FILE, "record_id": table["record_id"],
                                    "columns_field": "columns", "rows_field": "rows"},
            "source_crop": f"data/{table['source_crop']}",
            "source_bbox": table["source_bbox"],
            "review_status": table["status"],
            "review_flags": ["independent_review_not_performed"],
        })
    records.append({
        "chunk_id": "is800-2007:figure:05",
        "content_type": "diagram",
        "renderer": "image",
        "figure_number": 5,
        "title": CAPTION,
        "caption": CAPTION,
        "source_caption_raw": CAPTION_RAW,
        "description": "Figure 5, referenced by clause 6.3.1 (Plates).",
        "text": f"Figure 5: {CAPTION}. Referenced by clause 6.3.1 (Plates).",
        "description_basis": "Printed caption and explicit clause reference only",
        "clause_ids": ["6.3.1"],
        **source_fields([47]),
        "printed_page": 33,
        "image_path": FIGURE_PATH,
        "source_bbox": FIGURE_BBOX,
        "review_status": "caption_and_crop_visually_reviewed",
        "review_flags": ["diagram_not_interpreted", "independent_review_not_performed"],
    })
    return records, selected


def escape(value):
    return html.escape(str(value), quote=True)


def display_cell(value):
    if value is None:
        return '<span class="muted" aria-label="Not applicable">—</span>'
    if value.startswith("\\gamma_{") and value.endswith("}"):
        return f"γ<sub>{escape(value[8:-1])}</sub>"
    return escape(value)


def render_preview(records, tables):
    cards = []
    for record in records:
        title = (f"Table {record['table_number']}: {record['title']}"
                 if record["content_type"] == "table" else f"Figure 5: {record['title']}")
        if record["content_type"] == "table":
            table = tables[record["table_number"]]
            header = "".join(f'<th scope="col">{escape(label)}</th>'
                             for label in HEADERS[record["table_number"]])
            rows = "".join("<tr>" + "".join(f"<td>{display_cell(v)}</td>" for v in row)
                           + "</tr>" for row in table["rows"])
            display_notes = table.get("header_notes", []) + table.get("notes", [])
            display_notes += (["A dash means not applicable to that column group."]
                              if record["table_number"] == 5 else
                              ["The source expression 2.5 d is retained as printed."])
            notes = "".join(f"<p>{escape(note)}</p>" for note in display_notes)
            body = (f'<div class="table-scroll"><table><caption>{escape(title)}</caption>'
                    f"<thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>"
                    f'<div class="notes">{notes}</div>'
                    f'<p><a href="../{escape(record["source_crop"])}">View original table crop</a></p>')
        else:
            body = (f'<figure><img src="../{escape(record["image_path"])}" '
                    f'alt="Figure 5: {escape(record["caption"])}">'
                    f'<figcaption>{escape(record["description"])}</figcaption></figure>')
        page = record["pdf_pages"][0]
        source = (f'<a href="../data/is.800.2007.pdf#page={page}" target="_blank" '
                  f'rel="noopener">PDF page {page}</a> · Printed page {record["printed_page"]}'
                  f' · Clause {escape(", ".join(record["clause_ids"]))}')
        metadata = escape(json.dumps(record, ensure_ascii=False, indent=2))
        cards.append(f'<article><h2>{escape(title)}</h2><p class="source">{source}</p>'
                     f'{body}<details><summary>Inspect chunk record</summary>'
                     f'<pre>{metadata}</pre></details></article>')
    return """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>IS 800 demo assets review</title>
<style>
body{font:16px/1.55 system-ui,sans-serif;background:#f3f5f7;color:#192a35;margin:0}
main{max-width:1100px;margin:40px auto;padding:0 20px}h1{line-height:1.2}h2{font-size:22px}
article{background:white;border:1px solid #ccd6df;border-radius:12px;padding:24px;margin:24px 0}
a{color:#005b93} .source,.notes,.muted{color:#51616c}.source{font-size:14px}
.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}
caption{text-align:left;font-weight:600;margin:12px 0}th,td{text-align:left;border:1px solid #cbd5df;padding:10px}
th{background:#eaf0f5}tbody tr:nth-child(even){background:#f8fafc}.notes{font-size:14px}
figure{margin:20px 0}img{display:block;width:min(100%,540px);height:auto;border:1px solid #d8e0e7}
figcaption{margin-top:12px}details{border-top:1px solid #d8e0e7;padding-top:15px;margin-top:20px}
summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}
</style>
<main><h1>IS 800:2007 — tables and diagram preview</h1>
<p>Two tables and one diagram from the supplied PDF. Open the source links to inspect the original pages.</p>
""" + "\n".join(cards) + "</main></html>\n"


def export_assets(records, tables):
    try:
        import pymupdf
    except ImportError as exc:
        raise SystemExit("Install the existing requirements first: python -m pip install -r requirements.txt") from exc
    with pymupdf.open(DATA / "is.800.2007.pdf") as pdf:
        page = pdf[46]
        caption = " ".join(page.get_text(clip=pymupdf.Rect(CAPTION_BBOX)).split())
        if caption != CAPTION_RAW:
            raise ValueError(f"Unexpected Figure 5 caption on PDF page 47: {caption!r}")
        crop = page.get_pixmap(matrix=pymupdf.Matrix(3, 3),
                               clip=pymupdf.Rect(FIGURE_BBOX), alpha=False)
    image_path = ROOT / FIGURE_PATH
    image_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(image_path)
    output = DATA / "demo_asset_chunks.jsonl"
    output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    report = ROOT / "reports" / "demo_assets_preview.html"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_preview(records, tables), encoding="utf-8")
    print(f"Wrote {len(records)} asset chunks to {output}")
    print(f"Rendering preview: {report}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Print records without writing files")
    args = parser.parse_args()
    records, tables = build_records()
    if args.preview:
        print("Preview: 2 table chunks and 1 diagram chunk; no files written.")
    else:
        export_assets(records, tables)
    for record in records:
        print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
