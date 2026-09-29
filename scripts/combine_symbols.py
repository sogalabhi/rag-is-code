from collections import defaultdict
from pathlib import Path
import json

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

filenames = [
    "section1_symbols_page19.json",
    "section1_symbols_page20.json",
    "section1_symbols_page21_left.json",
    "section1_symbols_page21_right.json",
    "section1_symbols_pages22_25.json",
]

combined = []
counts = defaultdict(int)

for filename in filenames:
    records = json.loads(
        (DATA_DIR / filename).read_text(encoding="utf-8")
    )

    for record in records:
        record = dict(record)
        page = record["page"]

        # Page 19's symbol list occupies the right column.
        if page == 19:
            record.setdefault("column", "right")

        column = record.get("column", "unknown")
        counts[(page, column)] += 1
        record["record_id"] = (
            f"symbols-p{page}-{column}-{counts[(page, column)]:02d}"
        )
        combined.append(record)

output_path = DATA_DIR / "section1_symbols_combined.json"
output_path.write_text(
    json.dumps(combined, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

missing_symbol_text = sum(
    record.get("raw_text") is None
    for record in combined
)

print(f"Total records: {len(combined)}")
print(f"Missing symbol texts: {missing_symbol_text}")
print(f"Saved: {output_path}")

corrections = json.loads(
    (DATA_DIR / "symbol_corrections.json").read_text(encoding="utf-8")
)
records_by_id = {record["record_id"]: record for record in combined}

# Read visually from PDF page 19, in top-to-bottom order.
page19_latex = [
    "A",
    "A_c",
    "A_e",
    "A_{ef}",
    "A_f",
    "A_g",
    "A_{gf}",
    "A_{go}",
    "A_n",
    "A_{nb}",
    "A_{nc}",
    "A_{nf}",
    "A_{no}",
    "A_{pb}",
    "A_q",
    "A_s",
    "A_{sb}",
    "A_{tg}",
]

for index, latex in enumerate(page19_latex, start=1):
    record_id = f"symbols-p19-right-{index:02d}"
    assert record_id in records_by_id
    corrections[record_id] = {
        "latex": latex,
        "verification_method": "visual_pdf",
        "status": "verified",
    }

(DATA_DIR / "symbol_corrections.json").write_text(
    json.dumps(corrections, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("Verified notation records:", len(corrections))

for record_id, correction in corrections.items():
    assert record_id in records_by_id, f"Unknown ID: {record_id}"
    print(
        record_id,
        repr(records_by_id[record_id]["raw_text"]),
        "=>",
        correction["latex"],
    )
