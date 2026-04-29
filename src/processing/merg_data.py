"""
STEP 2 – MERGE
==============
Input : data/processed/mayo_clean.json
        data/processed/medlineplus_clean.json
Output: data/processed/merged.json

Strategy:
  - Normalize disease names (lowercase, strip punctuation) as merge key
  - If both sources have the same disease → merge fields:
      · prefer the longer / richer value per field
      · keep both URLs (list)
      · mark origin = "both"
  - Diseases only in one source → origin = "mayo" | "medlineplus"
  - Sort final list alphabetically by disease name
"""

import json, re, pathlib, logging, time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("merge")

IN_MAYO    = pathlib.Path("../../data/processed/mayo_clean.json")
IN_MEDLINE = pathlib.Path("../../data/processed/medlineplus_clean.json")
OUT_FILE   = pathlib.Path("../../data/processed/merged.json")

CONTENT_FIELDS = [
    "overview", "symptoms", "causes",
    "risk_factors", "prevention", "when_to_see_doc",
    "treatment", "prognosis", "complications", "exams_and_tests",
]


def normalize_key(name: str) -> str:
    """Lowercase, remove punctuation, collapse spaces → merge key."""
    name = name.lower().strip()
    name = re.sub(r"[''`]", "", name)          # apostrophes
    name = re.sub(r"[^a-z0-9 ]", " ", name)   # punctuation → space
    name = re.sub(r"\s+", " ", name).strip()
    return name


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def pick_richer(a: str, b: str) -> str:
    """Return whichever text is longer (more informative)."""
    return a if word_count(a) >= word_count(b) else b


def merge_records(mayo_rec: dict, medline_rec: dict) -> dict:
    merged = {
        "disease":    mayo_rec["disease"],          # prefer Mayo capitalisation
        "url":        [mayo_rec["url"], medline_rec["url"]],
        "source":     "both",
    }
    for field in CONTENT_FIELDS:
        a = mayo_rec.get(field, "") or ""
        b = medline_rec.get(field, "") or ""
        merged[field] = pick_richer(a, b)
    return merged


def run():
    t0 = time.time()
    log.info("Loading cleaned files…")

    with open(IN_MAYO,    encoding="utf-8") as f:
        mayo_list = json.load(f)
    with open(IN_MEDLINE, encoding="utf-8") as f:
        medline_list = json.load(f)

    # Index medline by normalised key
    medline_index: dict[str, dict] = {}
    for rec in medline_list:
        key = normalize_key(rec["disease"])
        medline_index[key] = rec

    merged_records: list[dict] = []
    matched = 0

    # Process Mayo first
    used_medline_keys: set[str] = set()
    for rec in mayo_list:
        key = normalize_key(rec["disease"])
        if key in medline_index:
            merged = merge_records(rec, medline_index[key])
            merged_records.append(merged)
            used_medline_keys.add(key)
            matched += 1
        else:
            # Mayo-only record: normalise URL to list
            r = dict(rec)
            r["url"] = [r["url"]]
            r["source"] = "mayo"
            # Ensure all fields present
            for f in CONTENT_FIELDS:
                r.setdefault(f, "")
            merged_records.append(r)

    # Add medline-only records
    medline_only = 0
    for rec in medline_list:
        key = normalize_key(rec["disease"])
        if key not in used_medline_keys:
            r = dict(rec)
            r["url"] = [r["url"]]
            r["source"] = "medlineplus"
            for f in CONTENT_FIELDS:
                r.setdefault(f, "")
            merged_records.append(r)
            medline_only += 1

    # Sort alphabetically
    merged_records.sort(key=lambda r: r["disease"].lower())

    # Stats
    only_mayo    = sum(1 for r in merged_records if r["source"] == "mayo")
    only_medline = sum(1 for r in merged_records if r["source"] == "medlineplus")
    both         = sum(1 for r in merged_records if r["source"] == "both")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_records, f, ensure_ascii=False, indent=2)

    log.info(f"Total merged records : {len(merged_records)}")
    log.info(f"  matched (both)     : {both}")
    log.info(f"  mayo only          : {only_mayo}")
    log.info(f"  medlineplus only   : {only_medline}")
    log.info(f"Saved → {OUT_FILE}")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()