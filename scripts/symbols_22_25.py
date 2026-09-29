from pathlib import Path
import json
import pymupdf

COLUMNS = [
    (22, "left",  (40, 79),   (94, 250),  (38, 722), 22),
    (22, "right", (275, 331), (330, 490), (38, 722), 28),
    (23, "left",  (22, 61),   (76, 232),  (40, 722), 30),
    (23, "right", (255, 294), (311, 470), (40, 722), 31),
    (24, "left",  (43, 80),   (96, 250),  (30, 717), 37),
    (24, "right", (278, 316), (331, 490), (30, 717), 25),
    (25, "left",  (40, 77),   (92, 250),  (42, 629), 27),
]


def union_bbox(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def join_symbol_spans(spans):
    groups = []
    for span in sorted(spans, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        if not groups or span["bbox"][1] >= groups[-1]["bbox"][3]:
            groups.append({"bbox": list(span["bbox"]), "spans": [span]})
        else:
            group = groups[-1]
            group["spans"].append(span)
            group["bbox"] = union_bbox([group["bbox"], span["bbox"]])

    return "\n".join(
        "".join(item["text"] for item in sorted(
            group["spans"], key=lambda item: item["bbox"][0]
        ))
        for group in groups
    ).strip() or None


def extract_column(page, spec, source_pdf):
    number, column, symbol_x, definition_x, (top, bottom), expected = spec
    definition_clip = pymupdf.Rect(definition_x[0], top, definition_x[1], bottom)
    definitions = sorted([
        {"raw_text": " ".join(block[4].split()), "bbox": list(block[:4])}
        for block in page.get_text("blocks", clip=definition_clip)
        if block[6] == 0 and block[4].strip()
    ], key=lambda item: item["bbox"][1])

    continuation = None
    if (number, column) == (24, "right"):
        continuation = definitions.pop(0)
        if not continuation["raw_text"].startswith("member with respect to"):
            raise ValueError("Page 24 continuation differs from the reviewed PDF.")

    if len(definitions) != expected:
        raise ValueError(
            f"Page {number} {column}: expected {expected} definition "
            f"blocks, found {len(definitions)}. Inspect before exporting."
        )

    symbol_clip = pymupdf.Rect(symbol_x[0], top, symbol_x[1], bottom)
    spans = [
        span
        for block in page.get_text("dict", clip=symbol_clip)["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        if span["text"].strip()
    ]

    if (number, column) == (22, "right"):
        spans = [
            span for span in spans
            if span["text"].strip() not in {"—", "–", "-", "."}
        ]

    starts = [max(top, definition["bbox"][1] - 4) for definition in definitions]
    if (number, column) == (22, "left"):
        starts[11], starts[12], starts[13] = 351, 394, 435

    records, assigned = [], set()
    for index, definition in enumerate(definitions):
        lower = starts[index]
        upper = starts[index + 1] if index + 1 < len(starts) else bottom
        selected = [
            (position, span)
            for position, span in enumerate(spans)
            if lower <= span["bbox"][1] < upper
        ]
        assigned.update(position for position, _ in selected)
        pieces = [span for _, span in selected]
        raw_text = join_symbol_spans(pieces)
        bbox = union_bbox([span["bbox"] for span in pieces]) if pieces else None
        region = [symbol_x[0], lower, symbol_x[1], upper]
        if bbox:
            region = union_bbox([region, bbox])

        flags = []
        if not raw_text:
            flags.append("missing_symbol_text")
        elif not any(character.isalnum() for character in raw_text):
            flags.append("symbol_text_only_punctuation")
        if raw_text and raw_text.endswith(("—", "–")):
            flags.append("separator_attached_to_raw_symbol")
        if (number, column) == (22, "left") and index in (11, 12):
            flags.append("stacked_fraction_symbol")
        if (number, column) == (25, "left") and index in (4, 5):
            flags.append("equation_in_definition")

        records.append({
            "record_id": f"symbols-p{number}-{column}-{index + 1:02d}",
            "raw_text": raw_text,
            "bbox": bbox,
            "spans": pieces,
            "symbol_region": region,
            "region_status": "provisional",
            "page": number,
            "column": column,
            "meaning": definition["raw_text"].lstrip("—– "),
            "meaning_fragments": [{"page": number, "column": column, **definition}],
            "latex": None,
            "source_pdf": source_pdf,
            "symbol_status": (
                "needs_visual_verification" if raw_text
                else "needs_visual_transcription"
            ),
            "meaning_status": "raw_extraction_needs_review",
            "review_flags": flags,
        })

    unassigned = [
        span for position, span in enumerate(spans)
        if position not in assigned
    ]
    return records, continuation, unassigned


def extract_remaining_symbols(doc, pdf_path, output_dir=None):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir) if output_dir else pdf_path.parent

    if len(doc) != 158:
        raise ValueError("This configuration was reviewed for the 158-page PDF.")

    page25_text = " ".join(doc[24].get_text().split())
    if "1.5 Units" not in page25_text:
        raise ValueError("Cannot confirm the Section 1.4 endpoint on PDF page 25.")

    all_records, summary, unassigned = [], [], []
    for spec in COLUMNS:
        number, column = spec[:2]
        records, continuation, unused = extract_column(
            doc[number - 1], spec, pdf_path.name
        )

        if continuation:
            previous = all_records[-1]
            if (previous["page"], previous["column"]) != (24, "left"):
                raise ValueError("Unexpected record before the page 24 continuation.")
            previous["meaning"] += " " + continuation["raw_text"]
            previous["meaning_fragments"].append(
                {"page": 24, "column": "right", **continuation}
            )
            previous["review_flags"].append("cross_column_definition")

        all_records.extend(records)
        summary.append({
            "page": number,
            "column": column,
            "records": len(records),
            "missing_symbols": sum(record["raw_text"] is None for record in records),
            "missing_meanings": sum(not record["meaning"] for record in records),
        })
        unassigned.extend(
            {"page": number, "column": column, "span": span}
            for span in unused
        )

    note_clip = pymupdf.Rect(29, 629, 250, 674)
    note_text = " ".join(doc[24].get_text("text", clip=note_clip).split())
    if not note_text.startswith("NOTE"):
        raise ValueError("The Section 1.4 closing note was not captured.")

    review = {
        "source_pdf": pdf_path.name,
        "scope": "Section 1.4, PDF pages 22-25 only",
        "all_notation_requires_verification": True,
        "summary": summary,
        "unassigned_symbol_spans": unassigned,
        "flagged_records": [
            {
                "record_id": record["record_id"],
                "raw_text": record["raw_text"],
                "meaning": record["meaning"],
                "flags": record["review_flags"],
            }
            for record in all_records
            if record["review_flags"]
        ],
        "section_notes": [{
            "section": "1.4",
            "page": 25,
            "column": "left",
            "raw_text": note_text,
            "region": list(note_clip),
        }],
    }

    if unassigned:
        raise ValueError(
            f"{len(unassigned)} symbol spans are outside the entry bands; "
            "inspect before exporting."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in [
        ("section1_symbols_pages22_25.json", all_records),
        ("section1_symbols_pages22_25_review.json", review),
    ]:
        path = output_dir / filename
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with path.open(encoding="utf-8") as file:
            if json.load(file) != json.loads(json.dumps(data)):
                raise ValueError(f"JSON round-trip failed: {path}")

    print("\n--- SYMBOL BATCH: PDF PAGES 22-25 ---")
    for row in summary:
        print(
            f"Page {row['page']} {row['column']:5}: {row['records']:2} records; "
            f"missing symbols={row['missing_symbols']}; "
            f"missing meanings={row['missing_meanings']}"
        )
    print(f"Total records: {len(all_records)}")
    print(f"Records with review flags: {len(review['flagged_records'])}")
    print("Unassigned symbol spans:", len(unassigned))
    print("Section notes preserved:", len(review["section_notes"]))
    print("All notation remains unverified; latex is null.")
    print("Saved:", output_dir / "section1_symbols_pages22_25.json")
    print("Saved:", output_dir / "section1_symbols_pages22_25_review.json")
    return all_records, review


if __name__ == "__main__":
    path = Path(__file__).resolve().parent.parent / "data" / "is.800.2007.pdf"
    with pymupdf.open(path) as document:
        extract_remaining_symbols(document, path)
