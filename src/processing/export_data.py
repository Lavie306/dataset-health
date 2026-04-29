"""
STEP 4 – EXPORT
===============
Input : data/processed/translated.json
Output:
  data/output/medical_vi.json    – full JSON (pretty)
  data/output/medical_vi.jsonl   – one record per line (for ML training)
  data/output/medical_vi.csv     – flat CSV (Excel-friendly)
  data/output/stats.json         – dataset statistics

CSV columns: disease_vi, disease_en, source, url,
             overview, symptoms, causes, risk_factors,
             prevention, treatment, prognosis, complications,
             exams_and_tests, when_to_see_doc
"""

import json, csv, pathlib, logging, time, re
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("export")

IN_FILE  = pathlib.Path("../../data/processed/translated.json")
OUT_DIR  = pathlib.Path("../../data/output")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_FIELDS = [
    "disease", "disease_en", "source",
    "overview", "symptoms", "causes",
    "risk_factors", "prevention", "when_to_see_doc",
    "treatment", "prognosis", "complications", "exams_and_tests",
    "url",
]

CONTENT_FIELDS = [
    "overview", "symptoms", "causes", "risk_factors",
    "prevention", "when_to_see_doc", "treatment",
    "prognosis", "complications", "exams_and_tests",
]


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def flatten_url(url) -> str:
    """URL is list in merged, string in single-source."""
    if isinstance(url, list):
        return " | ".join(url)
    return url or ""


def prepare_record(rec: dict) -> dict:
    out = {}
    for f in CSV_FIELDS:
        val = rec.get(f, "")
        if f == "url":
            val = flatten_url(val)
        elif f == "disease_en":
            # Fallback: if not set, use disease (untranslated source)
            val = rec.get("disease_en") or rec.get("disease", "")
        out[f] = val or ""
    return out


def build_stats(records: list[dict]) -> dict:
    source_counts = Counter(r.get("source", "unknown") for r in records)
    field_coverage = {}
    for f in CONTENT_FIELDS:
        filled = sum(1 for r in records if word_count(r.get(f, "")) >= 5)
        field_coverage[f] = {
            "filled":  filled,
            "empty":   len(records) - filled,
            "pct":     round(filled / len(records) * 100, 1) if records else 0,
        }
    total_words = sum(
        word_count(r.get(f, ""))
        for r in records
        for f in CONTENT_FIELDS
    )
    return {
        "total_records":  len(records),
        "by_source":      dict(source_counts),
        "field_coverage": field_coverage,
        "total_words":    total_words,
        "avg_words_per_record": round(total_words / len(records), 1) if records else 0,
    }


def run():
    t0 = time.time()

    log.info(f"Loading {IN_FILE} …")
    with open(IN_FILE, encoding="utf-8") as f:
        records = json.load(f)
    log.info(f"  {len(records)} records")

    prepared = [prepare_record(r) for r in records]

    # ── 1. Full JSON ──────────────────────────────────────────────────────────
    out_json = OUT_DIR / "medical_vi.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(prepared, f, ensure_ascii=False, indent=2)
    log.info(f"Saved JSON  → {out_json}")

    # ── 2. JSONL  (for ML / fine-tuning) ─────────────────────────────────────
    out_jsonl = OUT_DIR / "medical_vi.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for rec in prepared:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log.info(f"Saved JSONL → {out_jsonl}")

    # ── 3. CSV ────────────────────────────────────────────────────────────────
    out_csv = OUT_DIR / "medical_vi.csv"
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        # utf-8-sig → Excel opens correctly without BOM issues
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(prepared)
    log.info(f"Saved CSV   → {out_csv}")

    # ── 4. Stats ──────────────────────────────────────────────────────────────
    stats = build_stats(records)
    out_stats = OUT_DIR / "stats.json"
    with open(out_stats, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    log.info("─" * 50)
    log.info(f"Total records  : {stats['total_records']}")
    log.info(f"By source      : {stats['by_source']}")
    log.info(f"Total words    : {stats['total_words']:,}")
    log.info(f"Avg words/rec  : {stats['avg_words_per_record']}")
    log.info("Field coverage :")
    for f, v in stats["field_coverage"].items():
        log.info(f"  {f:<22}: {v['filled']:>4}/{stats['total_records']} ({v['pct']}%)")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()