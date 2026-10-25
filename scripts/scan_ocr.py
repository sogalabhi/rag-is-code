from pathlib import Path
import json
import re

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_PATH = DATA_DIR / "section1_symbols_reviewed.json"
OUTPUT_PATH = DATA_DIR / "meaning_review_queue.json"

PATTERNS = [
    ("broken_word", re.compile(r"\b[A-Za-z]+[~|][A-Za-z]+\b")),
    ("split_word", re.compile(r"\b[A-Za-z]+-\s+[A-Za-z]+\b")),
    ("spacing_after_slash", re.compile(r"\w/\s+\w")),
    ("spacing_before_punctuation", re.compile(r"\s+[,.);:]")),
    ("duplicate_space", re.compile(r" {2,}")),
    ("suspicious_character", re.compile(r"[~|`]")),
    ("likely_ocr_word", re.compile(
        r"\b(?:Cenre|Stwdard|atong|refrence|Limir|Bui/t|se:)\b",
        re.IGNORECASE,
    )),
]


def classify(record):
    meaning = record.get("meaning", "")
    matches = []
    for name, pattern in PATTERNS:
        matches.extend(
            {"category": name, "text": match.group(0)}
            for match in pattern.finditer(meaning)
        )

    if not matches:
        return None

    categories = sorted({match["category"] for match in matches})
    if "likely_ocr_word" in categories or "suspicious_character" in categories:
        priority = "high"
    elif "broken_word" in categories or "split_word" in categories:
        priority = "medium"
    else:
        priority = "low"

    return {
        "record_id": record["record_id"],
        "page": record["page"],
        "column": record["column"],
        "meaning": meaning,
        "priority": priority,
        "matches": matches,
        "source_regions": record.get("meaning_fragments", []),
    }


records = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
queue = [item for record in records if (item := classify(record))]

OUTPUT_PATH.write_text(
    json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

counts = {priority: sum(item["priority"] == priority for item in queue)
          for priority in ("high", "medium", "low")}

print(f"Records scanned: {len(records)}")
print(f"Review candidates: {len(queue)}")
print(f"High priority: {counts['high']}")
print(f"Medium priority: {counts['medium']}")
print(f"Low priority: {counts['low']}")
print(f"Saved: {OUTPUT_PATH}")
