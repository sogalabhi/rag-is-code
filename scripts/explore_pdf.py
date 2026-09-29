from pathlib import Path
import json
import pymupdf

PDF_PATH = Path(__file__).resolve().parent.parent / "data" / "is.800.2007.pdf"

doc = pymupdf.open(PDF_PATH)

import re

clause_pattern = re.compile(r"^(\d+(?:[.,]\d+)+)\s+")

def extract_page(page, top_cutoff=30, bottom_cutoff=720):

    blocks = page.get_text("blocks")

    # Filter text blocks
    content_blocks = [
        block for block in blocks
        if (
            block[6] == 0
            and block[4].strip()
            and top_cutoff <= block[1] < bottom_cutoff
        )
    ]

    # Separate columns
    midpoint = page.rect.width * 0.4

    left = sorted(
        [b for b in content_blocks if b[0] < midpoint],
        key=lambda b: b[1]
    )

    right = sorted(
        [b for b in content_blocks if b[0] >= midpoint],
        key=lambda b: b[1]
    )

    # Reconstruct text
    ordered_blocks = left + right

    return "\n".join(
        " ".join(block[4].split())
        for block in ordered_blocks
    )



# PDF page index and its top cutoff

page_specs = [
    (14, 160),  # Page 15
    (15, 30),   # Page 16
    (16, 30),   # Page 17
    (17, 30),   # Page 18
    (18, 30),   # Page 19
]


all_lines = []

for page_index, top_cutoff in page_specs:

    page = doc[page_index]

    page_text = extract_page(
        page,
        top_cutoff=top_cutoff
    )

    pdf_page = page_index + 1

    for line in page_text.splitlines():
        if line.startswith("1.4 Symbols"):
            break

        if line.startswith("I.3.105 "):
            line = "1" + line[1:]

        all_lines.append((pdf_page, line))

print("\n--- PAGE 19 RECONSTRUCTED TEXT ---\n")
page19_text = extract_page(doc[18], top_cutoff=30)
for line in page19_text.splitlines():
    print(repr(line[:90]))

print("\n--- PAGE 19 PARSER INPUT ---\n")
for page_number, line in all_lines:
    if page_number != 19:
        continue
    match = clause_pattern.match(line)
    if line.startswith(("1.3", "I.3")):
        print(
            repr(line[:65]),
            "=>",
            match.group(1) if match else "NO MATCH"
        )

clauses = []
current_clause = None

for page_number, line in all_lines:
    line = line.strip()
    match = clause_pattern.match(line)

    if match:
        if current_clause:
            clauses.append(current_clause)

        current_clause = {
            "clause_id": match.group(1).replace(",", "."),
            "content": line[match.end():].strip(),
            "start_page": page_number,
            "end_page": page_number
        }
    elif current_clause:
        current_clause["content"] += " " + line
        current_clause["end_page"] = page_number

if current_clause:
    clauses.append(current_clause)
print("Total extracted clauses:", len(clauses))

# Check cross-page and cross-column clauses
for clause in clauses:
    if clause["clause_id"] in ["1.3.67", "1.3.81"]:
        print(clause)
        print("-" * 50)

# Validate all terminology clauses
expected = {f"1.3.{i}" for i in range(1, 120)}
detected = {clause["clause_id"] for clause in clauses}

print("Missing clauses:", expected - detected)

for clause in clauses:
    if clause["clause_id"] == "1.3.105":
        print(clause)

OUTPUT_PATH = PDF_PATH.parent / "section1_terminology.json"

with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
    json.dump(
        clauses,
        file,
        ensure_ascii=False,
        indent=2
    )

print(f"Saved {len(clauses)} clauses to {OUTPUT_PATH}")
print(json.dumps(clauses[-1], indent=2, ensure_ascii=False))

print("\n--- PAGE 19 SYMBOL CANDIDATES ---\n")

symbols = []
page = doc[18]  # PDF page 19

for block in page.get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        for span in line["spans"]:
            x0, y0, x1, y1 = span["bbox"]
            raw_text = span["text"].strip()

            if raw_text and 270 <= x0 < 305 and 285 <= y0 < 705:
                symbols.append({
                    "raw_text": raw_text,
                    "bbox": [x0, y0, x1, y1],
                    "page": 19,
                    "meaning": None,
                    "latex": None,
                })

symbols.sort(key=lambda symbol: symbol["bbox"][1])

for symbol in symbols:
    print(symbol)

print("Symbol candidates:", len(symbols))

print("\n--- PAGE 19 DEFINITION FRAGMENTS ---\n")
fragments = []

for block in doc[18].get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        x0, y0, x1, y1 = line["bbox"]

        if x0 >= 310 and 285 <= y0 < 705:
            text = "".join(
                span["text"] for span in line["spans"]
            ).strip()

            # Remove the leading symbol–definition separator.
            text = text.removeprefix("—").strip()

            if text:
                fragments.append({
                    "text": text,
                    "bbox": [x0, y0, x1, y1],
                })

fragments.sort(
    key=lambda fragment: (
        fragment["bbox"][1],
        fragment["bbox"][0],
    )
)

for fragment in fragments:
    x0, y0, _, _ = fragment["bbox"]
    print(f"y={y0:.2f}  x={x0:.2f}  {fragment['text']!r}")

    rows = []

for fragment in fragments:
    y0 = fragment["bbox"][1]

    if not rows or abs(y0 - rows[-1]["y"]) > 2:
        rows.append({
            "y": y0,
            "fragments": [fragment],
        })
    else:
        rows[-1]["fragments"].append(fragment)

for row in rows:
    row["fragments"].sort(key=lambda item: item["bbox"][0])

    row["text"] = " ".join(
        item["text"] for item in row["fragments"]
    )

    print(f"y={row['y']:.2f}  {row['text']}")


print("\n--- FIRST 8 SYMBOL–MEANING PAIRS ---\n")

tolerance = 3

# Our inspected region contains all definitions for these 8 symbols.
for index, symbol in enumerate(symbols[:8]):
    start_y = symbol["bbox"][1] - tolerance
    end_y = symbols[index + 1]["bbox"][1] - tolerance

    matching_rows = [
        row for row in rows
        if start_y <= row["y"] < end_y
    ]

    symbol["meaning"] = (
        " ".join(row["text"] for row in matching_rows)
        if matching_rows else None
    )

    print(
        f"{symbol['raw_text']!r} "
        f"(y={symbol['bbox'][1]:.2f}) "
        f"=> {symbol['meaning']}"
    )

print("\n--- ALL PAGE 19 SYMBOL–MEANING PAIRS ---\n")

tolerance = 3

for index, symbol in enumerate(symbols):
    start_y = symbol["bbox"][1] - tolerance

    if index + 1 < len(symbols):
        end_y = symbols[index + 1]["bbox"][1] - tolerance
    else:
        end_y = 705

    matching_rows = [
        row for row in rows
        if start_y <= row["y"] < end_y
    ]

    symbol["meaning"] = (
        " ".join(row["text"] for row in matching_rows)
        if matching_rows else None
    )

    print(
        f"{index + 1}. {symbol['raw_text']!r} "
        f"(y={symbol['bbox'][1]:.2f}) "
        f"=> {symbol['meaning']}"
    )
    

    # Keep a reference to the original PDF.
for symbol in symbols:
    symbol["source_pdf"] = PDF_PATH.name

SYMBOLS_PATH = PDF_PATH.parent / "section1_symbols_page19.json"

with open(SYMBOLS_PATH, "w", encoding="utf-8") as file:
    json.dump(symbols, file, ensure_ascii=False, indent=2)

# Confirm the saved file can be read back.
with open(SYMBOLS_PATH, encoding="utf-8") as file:
    saved_symbols = json.load(file)

print(f"Saved {len(saved_symbols)} symbols to {SYMBOLS_PATH}")
print("Missing meanings:", sum(
    symbol["meaning"] is None for symbol in saved_symbols
))

print("\n--- PAGE 20 TEXT BLOCKS ---\n")

page = doc[19]  # PDF page 20
print("Page dimensions:", page.rect)

for block in page.get_text("blocks"):
    if block[6] != 0:
        continue

    x0, y0, x1, y1 = block[:4]
    text = " ".join(block[4].split())

    if text:
        print(
            f"x={x0:.1f}–{x1:.1f}  "
            f"y={y0:.1f}–{y1:.1f}  "
            f"{text[:100]!r}"
        )

print("\n--- PAGE 20 RIGHT-COLUMN SYMBOL SPANS ---\n")

sample = []

for block in doc[19].get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        for span in line["spans"]:
            x0, y0, x1, y1 = span["bbox"]

            if 270 <= x0 < 310 and 30 <= y0 < 715:
                sample.append(span)

sample.sort(key=lambda span: (
    span["bbox"][1],
    span["bbox"][0],
))

grouped_symbols = []

for span in sample:
    x0, y0, x1, y1 = span["bbox"]

    if (
        not grouped_symbols
        or y0 >= grouped_symbols[-1]["bbox"][3]
    ):
        grouped_symbols.append({
            "bbox": [x0, y0, x1, y1],
            "spans": [span],
        })
    else:
        group = grouped_symbols[-1]
        group["spans"].append(span)
        bx0, by0, bx1, by1 = group["bbox"]
        group["bbox"] = [
            min(bx0, x0),
            min(by0, y0),
            max(bx1, x1),
            max(by1, y1),
        ]

for group in grouped_symbols:
    group["spans"].sort(key=lambda span: span["bbox"][0])
    group["text"] = "".join(span["text"] for span in group["spans"])

print("\n--- PAGE 20 RIGHT-COLUMN SYMBOL GROUPS ---\n")
for index, group in enumerate(grouped_symbols, start=1):
    print(
        f"{index}. {group['text']!r}  "
        f"y={group['bbox'][1]:.2f}–{group['bbox'][3]:.2f}  "
        f"spans={len(group['spans'])}"
    )
print("Total groups:", len(grouped_symbols))

print("\n--- PAGE 20 RIGHT-COLUMN DEFINITION ROWS ---\n")
definition_sample = []

for block in doc[19].get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        x0, y0, x1, y1 = line["bbox"]

        if x0 >= 310 and 30 <= y0 < 715:
            text = "".join(
                span["text"] for span in line["spans"]
            ).strip()

            # Some separators are extracted as "-—".
            text = text.lstrip("—- ").strip()

            if text:
                definition_sample.append({
                    "text": text,
                    "bbox": [x0, y0, x1, y1],
                })

definition_sample.sort(key=lambda item: (
    item["bbox"][1],
    item["bbox"][0],
))

right_rows = []

for fragment in definition_sample:
    y0 = fragment["bbox"][1]

    if not right_rows or abs(y0 - right_rows[-1]["y"]) > 2:
        right_rows.append({"y": y0, "fragments": []})

    right_rows[-1]["fragments"].append(fragment)

for row in right_rows:
    row["fragments"].sort(key=lambda item: item["bbox"][0])
    row["text"] = " ".join(
        item["text"] for item in row["fragments"]
    )

# Preserve the top-right continuation for later.
tolerance = 4
first_start = grouped_symbols[0]["bbox"][1] - tolerance
continuation_rows = [
    row for row in right_rows
    if row["y"] < first_start
]

print("\n--- PAGE 20 RIGHT-COLUMN SYMBOL MEANINGS ---\n")

for index, symbol in enumerate(grouped_symbols):
    start_y = symbol["bbox"][1] - tolerance

    if index + 1 < len(grouped_symbols):
        end_y = grouped_symbols[index + 1]["bbox"][1] - tolerance
    else:
        end_y = 715

    matching_rows = [
        row for row in right_rows
        if start_y <= row["y"] < end_y
    ]

    symbol["meaning"] = " ".join(
        row["text"] for row in matching_rows
    ) or None

    print(f"{index + 1}. {symbol['text']!r} => {symbol['meaning']!r}")

print("\nPending continuation rows:")
for row in continuation_rows:
    print(f"y={row['y']:.2f}  {row['text']!r}")

left_spans = []

for block in doc[19].get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        for span in line["spans"]:
            x0, y0, x1, y1 = span["bbox"]

            if 35 <= x0 < 75 and 30 <= y0 < 715:
                left_spans.append(span)

left_spans.sort(key=lambda span: (
    span["bbox"][1],
    span["bbox"][0],
))

left_symbols = []

for span in left_spans:
    x0, y0, x1, y1 = span["bbox"]

    if (
        not left_symbols
        or y0 >= left_symbols[-1]["bbox"][3]
    ):
        left_symbols.append({
            "bbox": [x0, y0, x1, y1],
            "spans": [span],
        })
    else:
        group = left_symbols[-1]
        group["spans"].append(span)
        bx0, by0, bx1, by1 = group["bbox"]
        group["bbox"] = [
            min(bx0, x0),
            min(by0, y0),
            max(bx1, x1),
            max(by1, y1),
        ]

for group in left_symbols:
    group["spans"].sort(key=lambda span: span["bbox"][0])
    group["text"] = "".join(span["text"] for span in group["spans"])

print("\n--- PAGE 20 LEFT-COLUMN SYMBOL GROUPS ---\n")
for index, group in enumerate(left_symbols, start=1):
    print(
        f"{index}. {group['text']!r}  "
        f"y={group['bbox'][1]:.2f}–{group['bbox'][3]:.2f}  "
        f"spans={len(group['spans'])}"
    )
print("Total groups:", len(left_symbols))

left_fragments = []

for block in doc[19].get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        x0, y0, x1, y1 = line["bbox"]

        if 75 <= x0 < 250 and 30 <= y0 < 715:
            text = "".join(
                span["text"] for span in line["spans"]
            ).strip()

            # Some separators are extracted as "-—".
            text = text.lstrip("—- ").strip()

            if text:
                left_fragments.append({
                    "text": text,
                    "bbox": [x0, y0, x1, y1],
                })

left_fragments.sort(key=lambda item: (
    item["bbox"][1],
    item["bbox"][0],
))

left_rows = []

for fragment in left_fragments:
    y0 = fragment["bbox"][1]

    if not left_rows or abs(y0 - left_rows[-1]["y"]) > 2:
        left_rows.append({"y": y0, "fragments": []})

    left_rows[-1]["fragments"].append(fragment)

for row in left_rows:
    row["fragments"].sort(key=lambda item: item["bbox"][0])
    row["text"] = " ".join(
        item["text"] for item in row["fragments"]
    )

for index, group in enumerate(left_symbols):
    start_y = group["bbox"][1] - 6
    end_y = (
        left_symbols[index + 1]["bbox"][1] - 6
        if index + 1 < len(left_symbols)
        else 715
    )

    matching_rows = [
        row for row in left_rows
        if start_y <= row["y"] < end_y
    ]

    group["meaning"] = (
        " ".join(row["text"] for row in matching_rows)
        if matching_rows else None
    )

continuation_text = " ".join(
    row["text"] for row in continuation_rows
)

if left_symbols[-1]["meaning"] and continuation_text:
    left_symbols[-1]["meaning"] += " " + continuation_text

print("\n--- PAGE 20 LEFT-COLUMN MEANINGS ---\n")
for index, group in enumerate(left_symbols, start=1):
    print(f"{index}. {group['text']!r} => {group['meaning']!r}")

page20_symbols = []

for column, groups in [
    ("left", left_symbols),
    ("right", grouped_symbols),
]:
    for group in groups:
        page20_symbols.append({
            "raw_text": group["text"],
            "bbox": group["bbox"],
            "spans": group["spans"],
            "page": 20,
            "column": column,
            "meaning": group["meaning"],
            "latex": None,
            "source_pdf": PDF_PATH.name,
        })

SYMBOLS20_PATH = PDF_PATH.parent / "section1_symbols_page20.json"

with open(SYMBOLS20_PATH, "w", encoding="utf-8") as file:
    json.dump(page20_symbols, file, ensure_ascii=False, indent=2)

with open(SYMBOLS20_PATH, encoding="utf-8") as file:
    saved = json.load(file)

print(f"Saved {len(saved)} records to {SYMBOLS20_PATH}")
print("Missing meanings:", sum(
    record["meaning"] is None for record in saved
))

print("\n--- PAGE 21 TEXT BLOCKS ---\n")

page = doc[20]  # PDF page 21
print("Page dimensions:", page.rect)

for block in page.get_text("blocks"):
    if block[6] != 0:
        continue

    x0, y0, x1, y1 = block[:4]
    text = " ".join(block[4].split())

    if text:
        print(
            f"x={x0:.1f}–{x1:.1f}  "
            f"y={y0:.1f}–{y1:.1f}  "
            f"{text[:100]!r}"
        )

        page = doc[20]

left_symbol_spans = [
    span
    for block in page.get_text("dict")["blocks"]
    for line in block.get("lines", [])
    for span in line["spans"]
    if span["bbox"][0] < 70
]

print("Left symbol text spans:", len(left_symbol_spans))

for image in page.get_image_info():
    print(
        "Image dimensions:",
        image["width"],
        image["height"],
    )
    print("Image bbox:", image["bbox"])

    page21_left = []

for block in doc[20].get_text("blocks"):
    if block[6] != 0:
        continue

    x0, y0, x1, y1 = block[:4]

    # Definition blocks only; excludes the separate "1" artifacts.
    if 87 <= x0 < 240 and 45 <= y0 < 730:
        meaning = " ".join(block[4].split())

        if meaning:
            page21_left.append({
                "raw_text": None,
                "bbox": None,
                "symbol_region": [25, y0 - 4, 70, y1],
                "meaning": meaning,
                "meaning_bbox": list(block[:4]),
                "page": 21,
                "column": "left",
                "latex": None,
                "source_pdf": PDF_PATH.name,
            })

page21_left.sort(key=lambda item: item["meaning_bbox"][1])

for index, item in enumerate(page21_left, start=1):
    print(f"{index}. {item['meaning']}")

print("Definition candidates:", len(page21_left))

PREVIEW_DIR = PDF_PATH.parent / "page21_previews"
PREVIEW_DIR.mkdir(exist_ok=True)

for index in [0, 9, 31]:
    item = page21_left[index]
    pixmap = doc[20].get_pixmap(
        matrix=pymupdf.Matrix(4, 4),
        clip=pymupdf.Rect(item["symbol_region"]),
        alpha=False,
    )
    output_path = PREVIEW_DIR / f"symbol_{index + 1:02d}.png"
    pixmap.save(output_path)
    print(f"{output_path.name}: {item['meaning']}")

for item in page21_left:
    item["symbol_status"] = "needs_visual_transcription"
    item["region_status"] = "provisional"

OUTPUT21_LEFT = PDF_PATH.parent / "section1_symbols_page21_left.json"

with open(OUTPUT21_LEFT, "w", encoding="utf-8") as file:
    json.dump(page21_left, file, ensure_ascii=False, indent=2)

with open(OUTPUT21_LEFT, encoding="utf-8") as file:
    saved = json.load(file)

print("Saved records:", len(saved))
print("Missing meanings:", sum(not item["meaning"] for item in saved))
print("Missing symbol text:", sum(
    item["raw_text"] is None for item in saved
))

page21_right_spans = []

for block in doc[20].get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        for span in line["spans"]:
            x0, y0, x1, y1 = span["bbox"]

            if 265 <= x0 < 300 and 45 <= y0 < 730:
                page21_right_spans.append(span)

page21_right_spans.sort(key=lambda span: (
    span["bbox"][1],
    span["bbox"][0],
))

page21_right_symbols = []

for span in page21_right_spans:
    x0, y0, x1, y1 = span["bbox"]

    if (
        not page21_right_symbols
        or y0 >= page21_right_symbols[-1]["bbox"][3]
    ):
        page21_right_symbols.append({
            "bbox": [x0, y0, x1, y1],
            "spans": [span],
        })
    else:
        group = page21_right_symbols[-1]
        group["spans"].append(span)
        bx0, by0, bx1, by1 = group["bbox"]
        group["bbox"] = [
            min(bx0, x0),
            min(by0, y0),
            max(bx1, x1),
            max(by1, y1),
        ]

for group in page21_right_symbols:
    group["spans"].sort(key=lambda span: span["bbox"][0])
    group["text"] = "".join(span["text"] for span in group["spans"])

print("\n--- PAGE 21 RIGHT-COLUMN SYMBOL GROUPS ---\n")
for index, group in enumerate(page21_right_symbols, start=1):
    print(
        f"{index}. {group['text']!r}  "
        f"y={group['bbox'][1]:.2f}–{group['bbox'][3]:.2f}  "
        f"spans={len(group['spans'])}"
    )
print("Total groups:", len(page21_right_symbols))

page21_right_fragments = []

for block in doc[20].get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        x0, y0, x1, y1 = line["bbox"]

        if 320 <= x0 < 480 and 45 <= y0 < 730:
            text = "".join(
                span["text"] for span in line["spans"]
            ).strip()

            if text:
                page21_right_fragments.append({
                    "text": text,
                    "bbox": [x0, y0, x1, y1],
                })

page21_right_fragments.sort(key=lambda item: (
    item["bbox"][1],
    item["bbox"][0],
))

page21_right_rows = []

for fragment in page21_right_fragments:
    y0 = fragment["bbox"][1]

    if (
        not page21_right_rows
        or abs(y0 - page21_right_rows[-1]["y"]) > 2
    ):
        page21_right_rows.append({"y": y0, "fragments": []})

    page21_right_rows[-1]["fragments"].append(fragment)

for row in page21_right_rows:
    row["fragments"].sort(key=lambda item: item["bbox"][0])
    row["text"] = " ".join(
        item["text"] for item in row["fragments"]
    )

print("\n--- PAGE 21 RIGHT-COLUMN MEANINGS ---\n")

for index, group in enumerate(page21_right_symbols):
    start_y = group["bbox"][1] - 4
    end_y = (
        page21_right_symbols[index + 1]["bbox"][1] - 4
        if index + 1 < len(page21_right_symbols)
        else 730
    )

    matching_rows = [
        row for row in page21_right_rows
        if start_y <= row["y"] < end_y
    ]

    group["meaning"] = (
        " ".join(row["text"] for row in matching_rows)
        if matching_rows else None
    )

    print(f"{index + 1}. {group['text']!r} => {group['meaning']}")

page21_right = [
    {
        "raw_text": group["text"],
        "bbox": group["bbox"],
        "spans": group["spans"],
        "page": 21,
        "column": "right",
        "meaning": group["meaning"],
        "latex": None,
        "source_pdf": PDF_PATH.name,
        "symbol_status": "needs_visual_verification",
    }
    for group in page21_right_symbols
]

OUTPUT21_RIGHT = PDF_PATH.parent / "section1_symbols_page21_right.json"

with open(OUTPUT21_RIGHT, "w", encoding="utf-8") as file:
    json.dump(page21_right, file, ensure_ascii=False, indent=2)

with open(OUTPUT21_RIGHT, encoding="utf-8") as file:
    saved = json.load(file)

print("Saved records:", len(saved))
print("Missing meanings:", sum(not item["meaning"] for item in saved))

doc.close()
