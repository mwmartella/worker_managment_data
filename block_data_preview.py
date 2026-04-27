"""
block_data_preview.py
─────────────────────
Reads BLOCK DATA.xlsx, calls the Farm Master API to get live blocks/varieties/
rootstocks/clones, fuzzy-matches everything automatically, determines whether
multi-entry rows are SIDES or PORTIONS, and writes two reviewable CSV files:

  block_rows_preview.csv    – one row per proposed block_row record
  row_portions_preview.csv  – one row per proposed row_portion record

SIDE rows all default to side="N" — edit them in the CSV to set the real
orientation before running the bulk-import script.
"""

import csv
import re
import statistics
from collections import defaultdict
from difflib import SequenceMatcher

import openpyxl
import requests

BASE_URL = "http://192.168.1.7:8000"

# ─────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────

def api_get(path):
    resp = requests.get(f"{BASE_URL}{path}")
    resp.raise_for_status()
    return resp.json()

def load_api_lookups():
    blocks     = [(r["name"], r["id"]) for r in api_get("/blocks/")]
    varieties  = [(r["name"], r["id"]) for r in api_get("/varieties/")]
    rootstocks = [(r["name"], r["id"]) for r in api_get("/rootstocks/")]
    clones     = [(r["name"], r["id"]) for r in api_get("/variety-clones/")]
    return blocks, varieties, rootstocks, clones

# ─────────────────────────────────────────────
# Fuzzy matching
# ─────────────────────────────────────────────

def similarity(a, b):
    return SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio()

def best_match(value, candidates, threshold=0.35):
    """Return (best_name, best_id, score) or (None, None, score) if below threshold."""
    if not value or not candidates:
        return None, None, 0.0
    scored = [(similarity(value, name), name, id_) for name, id_ in candidates]
    scored.sort(reverse=True)
    score, name, id_ = scored[0]
    if score >= threshold:
        return name, str(id_), round(score, 2)
    return None, None, round(score, 2)

def best_match_block(block_raw, variety_raw, db_blocks, threshold=0.35):
    """
    Block-matching with variety-aware disambiguation:

    1. BRAVO + number  → search for just "Bravo" (Robbies field block)
    2. WB-G-GS         → build "Wisharts {variety}" as the search term so the
                         correct Wishart block is chosen per variety
    3. General         → if top-2 scores are within 0.1 of each other, boost
                         whichever candidate name contains a word from the
                         variety (e.g. "Spray Shed Pink Lady" vs "Spray Shed GS")
    """
    if not block_raw or not db_blocks:
        return None, None, 0.0

    # ── Rule 1: BRAVO 13 / BRAVO 14 / BRAVO 15 → "Bravo" block ──
    if re.match(r"^BRAVO\s*\d+$", block_raw.strip(), re.IGNORECASE):
        return best_match("Bravo", db_blocks, threshold)

    # ── Rule 2: WB-G-GS → Wisharts {variety} ──
    if block_raw.strip().upper() == "WB-G-GS":
        variety_hint = variety_raw or ""
        # Map common short codes to likely block name words
        variety_word = variety_hint.lower().strip()
        if variety_word in ("g/s", "granny smith", "granny"):
            search = "Wisharts Granny Smith"
        elif variety_word in ("gala", "galaval"):
            search = "Wisharts Gala"
        elif variety_word in ("bravo",):
            search = "Wisharts Bravo"
        else:
            # Fall back to generic Wisharts + whatever the variety says
            search = f"Wisharts {variety_hint}"
        return best_match(search, db_blocks, threshold)

    # ── General: score all candidates ──
    scored = [(similarity(block_raw, name), name, id_) for name, id_ in db_blocks]
    scored.sort(reverse=True)

    if not scored:
        return None, None, 0.0

    top_score, top_name, top_id = scored[0]

    # If there's a close second, use variety to break the tie
    if len(scored) > 1:
        second_score = scored[1][0]
        if top_score - second_score < 0.10 and variety_raw:
            v_lower = variety_raw.lower()
            # Boost any candidate whose name contains a variety-related word
            boosted = []
            for sc, nm, id_ in scored[:5]:   # check top 5 only
                boost = 0.15 if v_lower in nm.lower() else 0.0
                boosted.append((sc + boost, nm, id_))
            boosted.sort(reverse=True)
            top_score, top_name, top_id = boosted[0]

    if top_score >= threshold:
        return top_name, str(top_id), round(top_score, 2)
    return None, None, round(top_score, 2)

# ─────────────────────────────────────────────
# Year cleaning
# ─────────────────────────────────────────────

def clean_year(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s == ' ':
        return None
    try:
        val = int(float(s))
    except ValueError:
        return None
    if val >= 1900:
        return val
    return 2000 + val if val <= 30 else 1900 + val

# ─────────────────────────────────────────────
# Side vs Portion detection
# ─────────────────────────────────────────────

def detect_structure(group_lengths, block_row_lengths):
    if len(group_lengths) < 2:
        return "PORTION"
    if not block_row_lengths:
        return "AMBIGUOUS"
    med        = statistics.median(block_row_lengths)
    total      = sum(l for l in group_lengths if l)
    avg_indiv  = statistics.mean(abs((l or 0) - med) for l in group_lengths)
    total_diff = abs(total - med)
    if total_diff < avg_indiv:
        return "PORTION"
    elif avg_indiv < total_diff:
        return "SIDE"
    return "AMBIGUOUS"

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    print("Loading lookups from API…")
    db_blocks, db_varieties, db_rootstocks, db_clones = load_api_lookups()
    print(f"  {len(db_blocks)} blocks, {len(db_varieties)} varieties, "
          f"{len(db_rootstocks)} rootstocks, {len(db_clones)} clones")

    wb = openpyxl.load_workbook("BLOCK DATA.xlsx", data_only=True)
    ws = wb["Sheet1"]

    raw_rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        block, row_no, variety, rs, year, row_width, tree_width, tree_no, row_len, _, area, _ = row
        if not block or str(block).strip() == "" or row_no is None:
            continue
        raw_rows.append({
            "block_raw":   str(block).strip(),
            "row_number":  int(row_no),
            "variety_raw": str(variety).strip() if variety else None,
            "rs_raw":      str(rs).strip() if rs is not None else None,
            "year_raw":    year,
            "row_width":   row_width,
            "tree_count":  int(tree_no) if tree_no else None,
            "row_length":  float(row_len) if row_len else None,
            "area_m2":     float(area) if area else None,
        })

    # Group by (block, row_number)
    groups = defaultdict(list)
    for r in raw_rows:
        groups[(r["block_raw"], r["row_number"])].append(r)

    # Per-block median row length (single-entry rows as reference)
    block_lengths = defaultdict(list)
    for (block, _), entries in groups.items():
        if len(entries) == 1 and entries[0]["row_length"]:
            block_lengths[block].append(entries[0]["row_length"])

    block_rows_out   = []
    row_portions_out = []
    # Track (block_id, row_number, side) so we don't duplicate block_row records
    seen_block_rows  = set()

    for (block_raw, row_number), entries in sorted(groups.items()):
        # Use first entry's variety to help disambiguate the block
        first_variety = entries[0]["variety_raw"]
        b_match, b_id, b_score = best_match_block(block_raw, first_variety, db_blocks)

        lengths   = [e["row_length"] for e in entries]
        structure = detect_structure(lengths, block_lengths[block_raw])
        row_width = entries[0]["row_width"]

        flags = []
        if b_score < 0.6:
            flags.append(f"LOW_BLOCK({b_score})")
        if structure == "AMBIGUOUS":
            flags.append("AMBIGUOUS_STRUCTURE")

        if structure == "SIDE":
            # All sides default to "N" — user edits orientation in the CSV
            for entry in entries:
                side    = "N"
                row_key = (b_id, row_number, side)

                if row_key not in seen_block_rows:
                    seen_block_rows.add(row_key)
                    block_rows_out.append({
                        "block_raw":     block_raw,
                        "block_matched": b_match or "NO MATCH",
                        "block_id":      b_id or "NO MATCH",
                        "block_score":   b_score,
                        "row_number":    row_number,
                        "side":          side,
                        "row_length_m":  entry["row_length"] or "",
                        "row_width_m":   row_width or "",
                        "structure":     "SIDE",
                        "flags":         "|".join(flags),
                    })

                v_match, v_id, v_score = best_match(entry["variety_raw"], db_varieties)
                r_match, r_id, r_score = best_match(entry["rs_raw"], db_rootstocks)
                pf = list(flags)
                if v_score < 0.6: pf.append(f"LOW_VARIETY({v_score})")
                if r_score < 0.5: pf.append(f"LOW_RS({r_score})")

                row_portions_out.append({
                    "block_raw":         block_raw,
                    "block_matched":     b_match or "NO MATCH",
                    "row_number":        row_number,
                    "side":              side,
                    "structure":         "SIDE",
                    "variety_raw":       entry["variety_raw"] or "",
                    "variety_matched":   v_match or "NO MATCH",
                    "variety_id":        v_id or "NO MATCH",
                    "variety_score":     v_score,
                    "rootstock_raw":     entry["rs_raw"] or "",
                    "rootstock_matched": r_match or "NO MATCH",
                    "rootstock_id":      r_id or "NO MATCH",
                    "rootstock_score":   r_score,
                    "planting_year":     clean_year(entry["year_raw"]) or "",
                    "tree_count":        entry["tree_count"] or "",
                    "length_m":          entry["row_length"] or "",
                    "area_m2":           entry["area_m2"] or "",
                    "flags":             "|".join(pf),
                })

        else:
            # PORTION or AMBIGUOUS — one block_row, multiple portions
            total_len = sum(l for l in lengths if l) or None
            row_key   = (b_id, row_number, None)

            if row_key not in seen_block_rows:
                seen_block_rows.add(row_key)
                block_rows_out.append({
                    "block_raw":     block_raw,
                    "block_matched": b_match or "NO MATCH",
                    "block_id":      b_id or "NO MATCH",
                    "block_score":   b_score,
                    "row_number":    row_number,
                    "side":          "",
                    "row_length_m":  total_len or "",
                    "row_width_m":   row_width or "",
                    "structure":     structure,
                    "flags":         "|".join(flags),
                })

            for entry in entries:
                v_match, v_id, v_score = best_match(entry["variety_raw"], db_varieties)
                r_match, r_id, r_score = best_match(entry["rs_raw"], db_rootstocks)
                pf = list(flags)
                if v_score < 0.6: pf.append(f"LOW_VARIETY({v_score})")
                if r_score < 0.5: pf.append(f"LOW_RS({r_score})")

                row_portions_out.append({
                    "block_raw":         block_raw,
                    "block_matched":     b_match or "NO MATCH",
                    "row_number":        row_number,
                    "side":              "",
                    "structure":         structure,
                    "variety_raw":       entry["variety_raw"] or "",
                    "variety_matched":   v_match or "NO MATCH",
                    "variety_id":        v_id or "NO MATCH",
                    "variety_score":     v_score,
                    "rootstock_raw":     entry["rs_raw"] or "",
                    "rootstock_matched": r_match or "NO MATCH",
                    "rootstock_id":      r_id or "NO MATCH",
                    "rootstock_score":   r_score,
                    "planting_year":     clean_year(entry["year_raw"]) or "",
                    "tree_count":        entry["tree_count"] or "",
                    "length_m":          entry["row_length"] or "",
                    "area_m2":           entry["area_m2"] or "",
                    "flags":             "|".join(pf),
                })

    # ── Write CSVs ────────────────────────────────────────────────
    br_fields = ["block_raw", "block_matched", "block_id", "block_score",
                 "row_number", "side", "row_length_m", "row_width_m", "structure", "flags"]
    with open("block_rows_preview.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=br_fields)
        w.writeheader()
        w.writerows(block_rows_out)

    rp_fields = ["block_raw", "block_matched", "row_number", "side", "structure",
                 "variety_raw", "variety_matched", "variety_id", "variety_score",
                 "rootstock_raw", "rootstock_matched", "rootstock_id", "rootstock_score",
                 "planting_year", "tree_count", "length_m", "area_m2", "flags"]
    with open("row_portions_preview.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rp_fields)
        w.writeheader()
        w.writerows(row_portions_out)

    print(f"\nDone.")
    print(f"  block_rows_preview.csv   → {len(block_rows_out)} rows")
    print(f"  row_portions_preview.csv → {len(row_portions_out)} rows")

    # ── Summarise low-confidence / unmatched items ─────────────────
    print("\n── Items needing review ─────────────────────────────────")

    seen = set()
    for r in block_rows_out:
        k = r["block_raw"]
        if k in seen: continue
        seen.add(k)
        if r["block_matched"] == "NO MATCH":
            print(f"  BLOCK NO MATCH : '{r['block_raw']}'")
        elif float(r["block_score"]) < 0.6:
            print(f"  BLOCK LOW      : '{r['block_raw']}' → '{r['block_matched']}' ({r['block_score']})")

    seen = set()
    for r in row_portions_out:
        k = r["variety_raw"]
        if k in seen: continue
        seen.add(k)
        if r["variety_matched"] == "NO MATCH":
            print(f"  VARIETY NO MATCH : '{r['variety_raw']}'")
        elif float(r["variety_score"]) < 0.6:
            print(f"  VARIETY LOW      : '{r['variety_raw']}' → '{r['variety_matched']}' ({r['variety_score']})")

    seen = set()
    for r in row_portions_out:
        k = r["rootstock_raw"]
        if not k or k in seen: continue
        seen.add(k)
        if r["rootstock_matched"] == "NO MATCH":
            print(f"  ROOTSTOCK NO MATCH : '{r['rootstock_raw']}'")
        elif float(r["rootstock_score"]) < 0.5:
            print(f"  ROOTSTOCK LOW      : '{r['rootstock_raw']}' → '{r['rootstock_matched']}' ({r['rootstock_score']})")

    ambig = [r for r in block_rows_out if r["structure"] == "AMBIGUOUS"]
    if ambig:
        print(f"\n  AMBIGUOUS structure ({len(ambig)} rows) — check 'structure' column in block_rows_preview.csv")


if __name__ == "__main__":
    main()

