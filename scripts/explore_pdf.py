from pathlib import Path
import pymupdf

PDF_PATH = Path(__file__).resolve().parent.parent / "data" / "is.800.2007.pdf"

doc = pymupdf.open(PDF_PATH)

page = doc[14]

print("Page dimensions:", page.rect)

blocks = page.get_text("blocks")

text_blocks = [block for block in blocks if block[6] == 0]

print("Total text blocks:", len(text_blocks))



content_blocks = []

for block in text_blocks:
    x0, y0, x1, y1, text, block_no, block_type = block

    if not text.strip():
        continue

    if y0 < 160 or y0 > 720:
        continue

    content_blocks.append(block)


midpoint = page.rect.width / 2

left_blocks = []
right_blocks = []

for block in content_blocks:
    x0 = block[0]

    if x0 < midpoint:
        left_blocks.append(block)
    else:
        right_blocks.append(block)

print("Left column:", len(left_blocks))
print("Right column:", len(right_blocks))


left_blocks.sort(key=lambda block: block[1])
right_blocks.sort(key=lambda block: block[1])

# Combine in reading order
ordered_blocks = left_blocks + right_blocks

for block in ordered_blocks:
    block_no = block[5]
    text = " ".join(block[4].split())

    print(f"Block {block_no:02} | {text[:75]}")



page_text = "\n".join(
    " ".join(block[4].split())
    for block in ordered_blocks
)

print("\n--- RECONSTRUCTED PAGE ---\n")
print(page_text)


import re

# Pattern for numbered clauses
clause_pattern = re.compile(r"^(\d+(?:\.\d+)+)\s+")

print("\n--- DETECTED CLAUSES ---\n")

for line in page_text.splitlines():

    match = clause_pattern.match(line)

    if match:
        clause_number = match.group(1)
        print(clause_number)


print("Content blocks:", len(content_blocks))
clauses = []

for line in page_text.splitlines():
    match = clause_pattern.match(line)

    if match:
        clauses.append(match.group(1))

print("Total clauses:", len(clauses))
print(clauses)


clause_pattern = re.compile(r"^(\d+(?:\.\d+)+)\s+")

clauses = []
current_clause = None

for line in page_text.splitlines():

    line = line.strip()
    match = clause_pattern.match(line)

    if match:

        # Save the previous clause
        if current_clause:
            clauses.append(current_clause)

        # Start a new clause
        current_clause = {
            "clause_id": match.group(1),
            "content": line[match.end():].strip()
        }

    elif current_clause:

        # Continue the current clause
        current_clause["content"] += " " + line

# Save the final clause
if current_clause:
    clauses.append(current_clause)

print("Total extracted clauses:", len(clauses))

for clause in clauses[:3]:
    print(clause)
    print("-" * 50)


# Inspect the second actual code page
next_page = doc[15]

print("\n--- PAGE 16 BLOCKS ---\n")

for block in next_page.get_text("blocks"):

    x0, y0, x1, y1, text, block_no, block_type = block

    if block_type != 0 or not text.strip():
        continue

    preview = " ".join(text.split())[:85]

    print(
        f"Block {block_no:02} | "
        f"x0={x0:6.1f} | "
        f"y0={y0:6.1f} | "
        f"{preview}"
    )


# Second code page
page16 = doc[15]

blocks16 = [
    block for block in page16.get_text("blocks")
    if (
        block[6] == 0
        and block[4].strip()
        and 30 <= block[1] < 720
    )
]

midpoint = page16.rect.width / 2

left16 = sorted(
    [b for b in blocks16 if b[0] < midpoint],
    key=lambda b: b[1]
)

right16 = sorted(
    [b for b in blocks16 if b[0] >= midpoint],
    key=lambda b: b[1]
)

ordered16 = left16 + right16

page16_text = "\n".join(
    " ".join(block[4].split())
    for block in ordered16
)

print("Page 16 content blocks:", len(ordered16))


all_lines = (
    [(15, line) for line in page_text.splitlines()]
    +
    [(16, line) for line in page16_text.splitlines()]
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
            "clause_id": match.group(1),
            "content": line[match.end():].strip(),
            "start_page": page_number,
            "end_page": page_number
        }

    elif current_clause:

        current_clause["content"] += " " + line
        current_clause["end_page"] = page_number

if current_clause:
    clauses.append(current_clause)


for clause in clauses:
    if clause["clause_id"] == "1.3.13":
        print(clause)
        break

print("Total extracted clauses:", len(clauses))

doc.close()
