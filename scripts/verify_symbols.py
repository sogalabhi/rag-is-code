"""Batch notation review for this IS 800:2007 PDF, pages 19-25.

Save beside combine_symbols.py and run: python scripts/verify_symbols.py
Reads data/section1_symbols_raw.json and data/is.800.2007.pdf.
Writes three NEW derived files; the raw dataset and existing corrections stay intact:
  symbol_corrections_batch.json
  section1_symbols_reviewed.json
  symbol_verification_audit.json
Also writes symbol_review.html with original-PDF crops for unresolved cases.

Learning points:
  1. Stable IDs connect reviewed corrections to extraction evidence.
  2. A correction overlay preserves raw text and makes the result reproducible.
  3. Multi-symbol definitions keep one record and an explicit latex_symbols list.
  4. Notation verification and definition verification have separate statuses.

The notation below was visually transcribed from the uploaded PDF, not inferred
from OCR. A leading '?' marks an unresolved candidate; it is NEVER applied as
verified LaTeX. Some source glyphs are damaged. Definition corrections are limited
to the explicit entries below; all other meanings remain raw and need review.
"""
from pathlib import Path
from collections import Counter
import base64
import copy
import hashlib
import html
import json
import pymupdf

EXPECTED_SIGNATURE = '39a78441ba2bb0ff4206d69b65db50b5f595939f152781f23b9ae5dcd706e601'

# One line per record, in reading order. " | " separates shared symbols.
NOTATION_ROWS = {
    (19, 'right'): r"""A
A_c
A_e
A_{ef}
A_f
A_g
A_{gf}
A_{go}
A_n
A_{nb}
A_{nc}
A_{nf}
A_{no}
A_{pb}
A_q
A_s
A_{sb}
A_{tg}""",
    (20, 'left'): r"""A_{tn}
A_v
A_{vg}
A_{vn}
a | b
a_o
a_1
B
b
b_1
b_e
b_f
b_i
b_o
b_p
b_s
b_t
b_w
C
C_m
C_{my} | C_{mz}
c
c_b
c_m
c_s
D
d
d_2""",
    (20, 'right'): r"""d_h
d_o
d_p
E
E(T)
E(20)
E_p
F_{cdw}
F_d
F_n
F_o
F_{psd}
F_q
F_{qd}
F_{\mathrm{test}}
F_{\mathrm{test},a}
F_{\mathrm{test},\mathrm{Min}}
F_{\mathrm{test},R}
F_{\mathrm{test},S}
F_w
F_x
F_{xd}
f
f_1
f_2
f_a
f_{abc}
f_{ac}
f_{abt}
f_{apb}
f_{asb}""",
    (21, 'left'): r"""f_{at}
f_{atb}
f_{aw}
f_b
f_{bc}
f_{bd}
f_{br}
f_{bt}
f_{bs}
f_c
f_{cc}
f_{cd}
f_{cr,b}
f_e
f_f
f_{feq}
f_{fd}
f_{f,\mathrm{Max}}
f_{fn}
f_{nw}
f_o
f_p
f_{pb}
f_{psd}
f_r
f_{sb}
f_t
f_{tb}
f_u
f_{ub}
f_{um}
f_{up}""",
    (21, 'right'): r"""f_v
f_w
f_{wd}
f_{wn}
f_x
f_y
f_y(T)
f_y(20)
f_{yb}
f_{yf}
f_{ym}
f_{yp}
f_{yq}
f_{yw}
G
g
h
h_b
h_c
h_e
h_f
h_i
h_L
h_s
h_y
I
I_{fc}
I_{ft}
I_q
I_s
I_{so}""",
    (22, 'left'): r"""I_T
I_t
I_w
I_y
I_z
K_b
K_h
KL
KL/r
KL/r_y
KL/r_z
\left(\frac{KL}{r}\right)_o
\left(\frac{KL}{r}\right)_e
K_v
K_w
k
k_{sm}
L
L_c
L_{LT}
L_m
L_o""",
    (22, 'right'): r"""l
l_e
l_g
l_j
l_s
l_v
l_w
M
M_a
M_{cr}
M_d
M_{dv}
M_{dy}
M_{dz}
M_{eff}
M_{fr}
M_{fd}
M_{nd}
M_{ndy} | M_{ndz}
M_p
M_{pb}
M_{pc}
M_{pd}
M_{pdf}
M_q
M_s
M_{tf}
M_y""",
    (23, 'left'): r"""M_{yq}
M_z
N
N_d
N_f
N_{SC}
n
n_e
n_n
n_s
P
P_{cc}
P_d
P_{dy} | P_{dz}
P_e
P_{\mathrm{Min}}
P_r
P_s
P_y
p
p_s
Q
Q_a
Q_c
Q_d
Q_p
Q_v
q
R
R_d""",
    (23, 'right'): r"""R_i
R_r
R_{tf}
R_u
r
r_1
r_f
r_{vv}
r_y
r_z
S
S_c
S_d
S_o
S_p
S_u
s_c
s_t
s_a
T
T_b
T_{cf}
T_d
T_{dg}
T_{dn}
T_{db}
T_e
T_f
T_l
T_{nb}
T_{nd}""",
    (24, 'left'): r"""T_{ndf}
T_{nf}
T_s
t
t_f
t_p
t_{pk}
t_q
t_s
t_t
t_w
V
V_b
V_{bf}
V_{cr}
V_d
V_{db}
V_{nb}
V_{nbf}
V_p
V_n
V_{npb}
V_{nsb}
V_{nsf}
V_s
V_{sb}
V_{sd}
V_{sdf}
V_{sf}
V_t
V_{tf}
W
w
w_{tf}
x_t
Z_e
Z_{ec}""",
    (24, 'right'): r"""Z_{et}
Z_p
Z_v
y_g
y_s
\alpha
\alpha_t
\beta_M
\beta_{My} | \beta_{Mz}
\beta_{MLT}
\chi
\chi_m
\chi_{LT}
\delta
\delta_L
\delta_p
\delta_U
\phi
\gamma
\gamma_f
\gamma_m
\gamma_{m0}
\gamma_{m1}
\gamma_{mb}
\gamma_{mf}""",
    (25, 'left'): r"""\gamma_{fft}
\gamma_{mft}
\gamma_{mv}
\gamma_{mw}
\varepsilon
\lambda
\lambda_{cr}
\lambda_e
\lambda_{LT}
\lambda_{scr}
\mu
\mu_c
\mu_f
\mu_r
\theta
\rho
\tau
\tau_b
\tau_{ab}
\tau_{cr,e}
\tau_f
\tau_{f,\mathrm{Max}}
\tau_{fd}
\tau_{fn}
\tau_v
\psi
\Gamma""",
}

# These are candidates, not authoritative interpretations of damaged glyphs.
AMBIGUITIES = {
    "symbols-p23-left-18": {
        "note": "Visually verified as P_s.",
        "alternatives": ["P_s"], "region": [22, 426, 61, 444],
    },
    "symbols-p23-right-29": {
        "note": "Visually verified as T_l.",
        "alternatives": ["T_l", "T_1"], "region": [255, 663, 294, 682],
    },
    "symbols-p24-left-14": {
        "note": "Visually verified as V_{bf}.",
        "alternatives": ["V_{bf}", "V_{hf}"], "region": [43, 250, 80, 270],
    },
    "symbols-p24-left-36": {
        "note": "Visually verified as Z_e.",
        "alternatives": ["Z_e", "Z'_e"], "region": [43, 680, 80, 698],
    },
}

# These replacement meanings were visually checked. Source typos are not
# automatically corrected: for example, the printed 'Cenre-to-centre' stays raw.
MEANING_CORRECTIONS = {
    "symbols-p20-left-04": "Net cross-sectional area in shear along the line of transmitted force (see 6.4)",
    "symbols-p20-left-05": "Larger and smaller projection of the slab base beyond the rectangle circumscribing the column, respectively (see 7.4)",
    "symbols-p20-left-26": "Overall depth/diameter of the cross-section",
    "symbols-p20-right-05": "Modulus of elasticity of steel at T °C",
    "symbols-p20-right-06": "Modulus of elasticity of steel at 20°C",
    "symbols-p20-right-01": "Diameter of a bolt/rivet hole",
    "symbols-p20-right-24": "Frequency for a simply supported one-way system",
    "symbols-p21-left-01": "Permissible tensile stress at service load",
    "symbols-p21-left-02": "Permissible tensile stress of the bolt at service load",
    "symbols-p21-left-15": "Fatigue stress range corresponding to 5 × 10⁶ cycles of loading",
    "symbols-p21-right-07": "Yield stress of steel at T °C",
    "symbols-p22-right-17": "Design plastic resistance of the flange alone",
    "symbols-p23-left-06": "Number of stress cycles",
    "symbols-p24-right-01": "Elastic section modulus of the member with respect to extreme tension fibre",
    "symbols-p24-right-12": "Strength reduction factor, χ, at f_ym",
    "symbols-p25-left-24": "Fatigue shear stress range at N_SC cycle for the detail category",
}

# Keep source regions for mathematical definitions that still need an explicit
# equation transcription. The left-hand symbol can be verified independently.
PENDING_EQUATIONS = {
    "symbols-p25-left-05": [90, 136, 249, 154],
    "symbols-p25-left-06": [90, 151, 249, 214],
}


def input_signature(records):
    payload = sorted([
        [r["record_id"], r["page"], r["column"], " ".join(r["meaning"].split())]
        for r in records
    ])
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()


def build_corrections(records):
    by_id = {r["record_id"]: r for r in records}
    corrections = {}
    for (page, column), text in NOTATION_ROWS.items():
        for index, row in enumerate(text.splitlines(), 1):
            record_id = f"symbols-p{page}-{column}-{index:02d}"
            if record_id not in by_id:
                raise ValueError(f"Missing expected record: {record_id}")
            unresolved = row.startswith("?")
            symbols = row.lstrip("?").split(" | ")
            correction = {
                "latex": None if unresolved else r",\; ".join(symbols),
                "latex_symbols": [] if unresolved else symbols,
                "status": "needs_review" if unresolved else "verified",
                "verification_method": "visual_pdf",
                "reviewer": "assistant_visual_review",
                "source_page": page,
                "source_column": column,
                "definition_at_review": by_id[record_id]["meaning"],
            }
            if unresolved:
                correction.update(AMBIGUITIES[record_id])
                correction["candidate_latex"] = symbols[0]
            if record_id in MEANING_CORRECTIONS:
                correction["meaning_corrected"] = MEANING_CORRECTIONS[record_id]
            corrections[record_id] = correction
    if set(corrections) != set(by_id):
        raise ValueError("The correction IDs do not exactly cover the dataset.")
    return corrections


def write_review_html(path, doc, reviewed, corrections, audit):
    by_id = {r["record_id"]: r for r in reviewed}
    cards = []
    for record_id in list(AMBIGUITIES) + list(PENDING_EQUATIONS):
        record = by_id[record_id]
        is_symbol = record_id in AMBIGUITIES
        region = (AMBIGUITIES[record_id]["region"] if is_symbol
                  else PENDING_EQUATIONS[record_id])
        clip = pymupdf.Rect(region) & doc[record["page"] - 1].rect
        png = doc[record["page"] - 1].get_pixmap(
            matrix=pymupdf.Matrix(5, 5), clip=clip, alpha=False
        ).tobytes("png")
        uri = "data:image/png;base64," + base64.b64encode(png).decode()
        label = "Unresolved notation" if is_symbol else "Equation transcription pending"
        details = (AMBIGUITIES[record_id]["note"] if is_symbol
                   else "The symbol is reviewed; the mathematical definition remains raw.")
        candidates = (" / ".join(AMBIGUITIES[record_id]["alternatives"]) if is_symbol else "")
        cards.append(
            f'<article><h2>{html.escape(record_id)}</h2><p class="tag">{label}</p>'
            f'<p>{html.escape(record["meaning"])}</p>'
            f'<img src="{uri}" alt="Original PDF crop for {record_id}">'
            f'<p>{html.escape(details)}</p><code>{html.escape(candidates)}</code></article>'
        )
    rows = "".join(
        f'<tr><td>{html.escape(r["record_id"])}</td>'
        f'<td>{html.escape(r["raw_text"] or "[missing]")}</td>'
        f'<td><code>{html.escape(r["latex"] or "[needs review]")}</code></td>'
        f'<td>{html.escape(r["meaning"])}</td></tr>' for r in reviewed
    )
    document = '''<!doctype html><html lang="en"><meta charset="utf-8">
<title>IS 800 symbol verification</title><style>
body{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#182433}
h1{margin-bottom:8px}.summary{background:#eaf3f5;padding:20px;border-radius:10px}
article{border:1px solid #ccd7df;border-radius:10px;padding:20px;margin:20px 0;break-inside:avoid}
img{display:block;max-width:100%;margin:18px 0}.tag{font-weight:600;color:#895318}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #ccd7df;padding:8px;text-align:left;vertical-align:top}
code{overflow-wrap:anywhere}summary{cursor:pointer;font-weight:600;padding:16px 0}
</style><h1>IS 800:2007 — symbol review</h1>'''
    document += (
        f'<p class="summary">{audit["records"]} records; '
        f'{audit["verified_notation_records"]} notation records visually reviewed; '
        f'{audit["pending_notation_records"]} unresolved notation records. '
        'This is not a declaration that all definitions or equations are verified.</p>'
        + "".join(cards)
        + '<details><summary>All records: raw text, reviewed LaTeX, and definitions</summary>'
        '<table><thead><tr><th>ID</th><th>Raw symbol</th><th>LaTeX source</th><th>Definition</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table></details></html>'
    )
    path.write_text(document, encoding="utf-8")


def main(data_dir=None):
    data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent / "data"
    raw_path = data_dir / "section1_symbols_raw.json"
    if not raw_path.exists():
        raw_path = data_dir / "section1_symbols_combined.json"
    pdf_path = data_dir / "is.800.2007.pdf"
    raw_bytes = raw_path.read_bytes()
    raw = json.loads(raw_bytes)
    if len(raw) != 340 or len({r["record_id"] for r in raw}) != 340:
        raise ValueError("Expected exactly 340 records with unique IDs.")
    if input_signature(raw) != EXPECTED_SIGNATURE:
        raise ValueError("IDs or definitions differ from the reviewed dataset. "
                         "No corrections applied. Inspect the changed records first.")
    if any(not r.get("meaning") for r in raw):
        raise ValueError("A source definition is empty.")
    corrections = build_corrections(raw)

    # Check existing user corrections for conflicts; never overwrite that file.
    existing_path = data_dir / "symbol_corrections.json"
    if existing_path.exists():
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
        for record_id, value in existing.items():
            if record_id not in corrections:
                raise ValueError(f"Unknown existing correction ID: {record_id}")
            if value.get("latex") and value["latex"] != corrections[record_id]["latex"]:
                raise ValueError(f"Existing correction conflicts with this batch: {record_id}")

    reviewed = copy.deepcopy(raw)
    for record in reviewed:
        correction = corrections[record["record_id"]]
        record["meaning_raw"] = record["meaning"]
        record["meaning"] = correction.get("meaning_corrected", record["meaning"])
        record["meaning_status"] = ("visually_corrected" if "meaning_corrected" in correction
                                    else "raw_extraction_needs_review")
        record["latex"] = correction["latex"]
        record["latex_symbols"] = correction["latex_symbols"]
        record["symbol_status"] = ("visually_verified" if correction["status"] == "verified"
                                   else "needs_review")
        record["notation_review"] = {
            "method": "visual_pdf", "reviewer": "assistant_visual_review",
            "status": correction["status"],
        }
        if correction["status"] != "verified":
            record["notation_review"]["note"] = correction["note"]
            record["notation_review"]["candidates"] = correction["alternatives"]
        if record["record_id"] in PENDING_EQUATIONS:
            record["meaning_status"] = "equation_transcription_pending"
            record["equation_region"] = PENDING_EQUATIONS[record["record_id"]]

    page_counts = Counter(r["page"] for r in reviewed)
    missing_raw = [r for r in reviewed if not r["raw_text"]]
    verified = [r for r in reviewed if r["symbol_status"] == "visually_verified"]
    audit = {
        "records": len(reviewed), "unique_ids": len({r["record_id"] for r in reviewed}),
        "records_per_page": dict(sorted(page_counts.items())),
        "missing_raw_symbol_texts": len(missing_raw),
        "recovered_missing_symbol_texts": sum(r["latex"] is not None for r in missing_raw),
        "verified_notation_records": len(verified),
        "pending_notation_records": len(reviewed) - len(verified),
        "verified_individual_symbols": sum(len(r["latex_symbols"]) for r in verified),
        "multi_symbol_records": sum(len(r["latex_symbols"]) > 1 for r in reviewed),
        "missing_meanings": sum(not r["meaning"] for r in reviewed),
        "visually_corrected_meanings": len(MEANING_CORRECTIONS),
        "other_meanings_require_review": len(reviewed) - len(MEANING_CORRECTIONS),
        "pending_notation": AMBIGUITIES,
        "pending_equations": PENDING_EQUATIONS,
        "raw_dataset_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "raw_dataset_preserved": True,
        "review_scope": "Symbol notation; only explicit meaning corrections are verified.",
    }
    # Check preservation and associations before writing any results.
    for before, after in zip(raw, reviewed):
        assert before["record_id"] == after["record_id"]
        assert before["raw_text"] == after["raw_text"]
        assert before["meaning"] == after["meaning_raw"]
        assert before.get("bbox") == after.get("bbox")
        assert before.get("spans") == after.get("spans")
    with pymupdf.open(pdf_path) as doc:
        if len(doc) != 158:
            raise ValueError("Expected the original 158-page PDF.")
        write_review_html(data_dir / "symbol_review.html", doc, reviewed, corrections, audit)
    for filename, content in [
        ("symbol_corrections_batch.json", corrections),
        ("section1_symbols_reviewed.json", reviewed),
        ("symbol_verification_audit.json", audit),
    ]:
        path = data_dir / filename
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        assert json.loads(path.read_text(encoding="utf-8")) == json.loads(json.dumps(content))
    assert raw_path.read_bytes() == raw_bytes
    print("\n--- SYMBOL VERIFICATION BATCH ---")
    print("Records / unique IDs:", audit["records"], "/", audit["unique_ids"])
    print("Visually verified notation records:", audit["verified_notation_records"])
    print("Notation records needing review:", audit["pending_notation_records"])
    print("Missing raw symbols recovered:", audit["recovered_missing_symbol_texts"], "/", len(missing_raw))
    print("Records with multiple symbols:", audit["multi_symbol_records"])
    print("Visually corrected meanings:", audit["visually_corrected_meanings"])
    print("Other meanings still requiring review:", audit["other_meanings_require_review"])
    print("Mathematical definitions pending transcription:", len(PENDING_EQUATIONS))
    print("Raw dataset: unchanged")
    print("Open for the unresolved cases:", data_dir / "symbol_review.html")
    return reviewed, audit


if __name__ == "__main__":
    main()
