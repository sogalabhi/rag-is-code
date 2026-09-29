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

doc.close()
