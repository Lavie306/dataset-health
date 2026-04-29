"""
STEP 1 – CLEAN
==============
Input : data/raw/mayo_full.json, data/raw/medlineplus_full.json
Output: data/processed/mayo_clean.json, data/processed/medlineplus_clean.json

Actions per file:
  - Remove noise tokens  (Enlarge image, Close, alt-text artifacts)
  - Normalise whitespace (collapse multiple spaces/newlines)
  - Strip leading disease-name repetition inside overview/symptoms
  - Drop records with zero meaningful content after cleaning
  - Deduplicate by (disease_lower, source)
  - Standardise schema: fill missing keys with ""
"""

import json, re, unicodedata, pathlib, logging, time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("clean")

# ── paths ────────────────────────────────────────────────────────────────────
RAW_DIR  = pathlib.Path("../../data/raw")
OUT_DIR  = pathlib.Path("../../data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAYO_IN    = RAW_DIR / "mayo_full.json"
MEDLINE_IN = RAW_DIR / "medlineplus_full.json"

# ── unified schema (union of both sources) ───────────────────────────────────
SCHEMA_FIELDS = [
    "disease", "url", "source",
    "overview", "symptoms", "causes",
    "risk_factors", "prevention", "when_to_see_doc",
    "treatment", "prognosis", "complications", "exams_and_tests",
]

# ── noise patterns specific to Mayo HTML scraping ────────────────────────────
MAYO_NOISE = re.compile(
    r"Enlarge image\s*Close\s*[^\n]{0,80}\n?|"   # image captions
    r"\bEnlarge image\b|"
    r"\bClose\b(?=\s+[A-Z])|"                     # "Close " before new sentence
    r"©\s*\d{4}[^\n]*|"                           # copyright lines
    r"\[\s*\d+\s*\]",                             # citation numbers [1]
    re.IGNORECASE,
)

# Generic noise for both sources
GENERIC_NOISE = re.compile(
    r"https?://\S+|"                              # stray URLs
    r"\b(Last reviewed|Medically reviewed|Updated|Last updated)[^\n]{0,80}",
    re.IGNORECASE,
)


def normalise_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def clean_text(text: str, source: str = "") -> str:
    if not text:
        return ""
    text = normalise_unicode(text)
    if source == "mayo":
        text = MAYO_NOISE.sub(" ", text)
    text = GENERIC_NOISE.sub(" ", text)
    # collapse whitespace
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def strip_title_repetition(title: str, text: str) -> str:
    """
    Mayo often starts overview with 'Disease Name Disease Name actual text…'
    Remove leading repetitions of the title (up to 3x).
    """
    if not title or not text:
        return text
    escaped = re.escape(title.strip())
    pattern = re.compile(r"^(" + escaped + r"\s*){1,3}", re.IGNORECASE)
    return pattern.sub("", text).strip()


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def clean_record(record: dict, source: str) -> dict | None:
    disease = clean_text(record.get("disease", ""), source).strip()
    if not disease:
        return None

    cleaned = {"disease": disease, "url": record.get("url", ""), "source": source}

    for field in SCHEMA_FIELDS:
        if field in ("disease", "url", "source"):
            continue
        raw = record.get(field, "") or ""
        val = clean_text(raw, source)
        if field == "overview":
            val = strip_title_repetition(disease, val)
        cleaned[field] = val

    # Drop record if total meaningful content < 30 words
    content_words = sum(
        word_count(cleaned.get(f, ""))
        for f in SCHEMA_FIELDS
        if f not in ("disease", "url", "source")
    )
    if content_words < 30:
        return None

    return cleaned


def process_file(path: pathlib.Path, source: str) -> list[dict]:
    log.info(f"Reading {path} …")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    log.info(f"  {len(data)} raw records")

    cleaned, dropped = [], 0
    seen: set[str] = set()

    for rec in data:
        result = clean_record(rec, source)
        if result is None:
            dropped += 1
            continue
        key = result["disease"].strip().lower()
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        cleaned.append(result)

    log.info(f"  → {len(cleaned)} kept, {dropped} dropped")
    return cleaned


def run():
    t0 = time.time()

    mayo    = process_file(MAYO_IN,    source="mayo")
    medline = process_file(MEDLINE_IN, source="medlineplus")

    out_mayo    = OUT_DIR / "mayo_clean.json"
    out_medline = OUT_DIR / "medlineplus_clean.json"

    with open(out_mayo,    "w", encoding="utf-8") as f:
        json.dump(mayo,    f, ensure_ascii=False, indent=2)
    with open(out_medline, "w", encoding="utf-8") as f:
        json.dump(medline, f, ensure_ascii=False, indent=2)

    log.info(f"Saved {out_mayo} ({len(mayo)} records)")
    log.info(f"Saved {out_medline} ({len(medline)} records)")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()