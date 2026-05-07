"""
STEP 1 – CLEAN  (Nâng cao)
===========================
Input : data/raw/mayo_full.json, data/raw/medlineplus_full.json
Output: data/processed/mayo_clean.json, data/processed/medlineplus_clean.json

Tính năng mới bổ sung:
  ✅ validate_encoding()     – phát hiện mojibake tiếng Việt (Ã©, â€™...)
  ✅ remove_medical_special_chars() – loại ®, ™, †, ‡, footnote markers
  ✅ validate_url()          – kiểm tra URL hợp lệ từ nguồn tin cậy
  ✅ detect_length_anomaly() – cờ field > 5000 từ
  ✅ _quality_issues         – danh sách vấn đề chất lượng per record
  ✅ _quality_ok             – True nếu record hoàn toàn sạch

Tính năng giữ nguyên:
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

CONTENT_FIELDS = [f for f in SCHEMA_FIELDS if f not in ("disease", "url", "source")]

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

# ── (NEW) Medical special characters ─────────────────────────────────────────
MEDICAL_SPECIAL_CHARS = re.compile(r'[®™†‡§¶•·°]')

# ── (NEW) Mojibake / encoding error patterns (UTF-8 đọc nhầm Latin-1) ────────
MOJIBAKE_PATTERN = re.compile(
    r'Ã[©°¡¢£¤¥¦§¨ª«¬­®¯±²³´µ¶·¸¹º»¼½¾¿€‚ƒ„…†‡ˆ‰Š‹ŒŽ''""•–—˜™š›œžŸ ]|'
    r'â€[™œ•–—\x9c\x9d\x9e\x9f]|'
    r'Â[«»°²³µ¹º¼½¾]',
    re.IGNORECASE,
)

# ── (NEW) URL validation – chỉ chấp nhận nguồn y tế uy tín ───────────────────
TRUSTED_MEDICAL_DOMAINS = re.compile(
    r'^https?://(www\.)?(mayoclinic\.org|medlineplus\.gov|nlm\.nih\.gov|'
    r'who\.int|cdc\.gov|nih\.gov|webmd\.com|healthline\.com)',
    re.IGNORECASE,
)

# ── (NEW) Thresholds ──────────────────────────────────────────────────────────
MAX_FIELD_WORDS = 5000   # field > 5000 từ bị đánh dấu bất thường
MIN_CONTENT_WORDS = 30   # bỏ bản ghi < 30 từ tổng nội dung


# =============================================================================
# (NEW) VALIDATE FUNCTIONS
# =============================================================================

def detect_mojibake(text: str) -> bool:
    """Phát hiện lỗi encoding mojibake (tiếng Việt bị đọc nhầm encoding)."""
    if not text:
        return False
    return bool(MOJIBAKE_PATTERN.search(text))


def validate_url(url: str) -> bool:
    """Kiểm tra URL có hợp lệ và đến từ nguồn y tế tin cậy không."""
    if not url:
        return False
    return bool(TRUSTED_MEDICAL_DOMAINS.match(url))


def detect_length_anomaly(field: str, text: str) -> str | None:
    """Phát hiện field có độ dài bất thường (> MAX_FIELD_WORDS từ)."""
    if not text:
        return None
    wc = len(text.split())
    if wc > MAX_FIELD_WORDS:
        return f"{field}: {wc:,} từ (vượt ngưỡng {MAX_FIELD_WORDS:,})"
    return None


def remove_medical_special_chars(text: str) -> str:
    """Loại bỏ ký tự đặc biệt y tế: ®, ™, †, ‡, §..."""
    return MEDICAL_SPECIAL_CHARS.sub("", text)


def build_quality_issues(record: dict) -> list[str]:
    """
    Kiểm tra toàn diện chất lượng 1 bản ghi y tế.
    Trả về danh sách các vấn đề phát hiện được.
    """
    issues = []

    # 1. Kiểm tra URL
    url = record.get("url", "")
    if url and not validate_url(url):
        issues.append(f"url_not_trusted: {url[:80]}")

    # 2. Kiểm tra encoding + độ dài bất thường cho từng field nội dung
    for field in CONTENT_FIELDS:
        val = record.get(field, "") or ""

        if val and detect_mojibake(val):
            issues.append(f"{field}_encoding_error")

        anomaly = detect_length_anomaly(field, val)
        if anomaly:
            issues.append(anomaly)

    return issues


# =============================================================================
# CORE CLEAN FUNCTIONS
# =============================================================================

def normalise_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    # Chuẩn hóa dấu gạch nối
    text = text.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    return text


def clean_text(text: str, source: str = "") -> str:
    if not text:
        return ""
    text = normalise_unicode(text)
    if source == "mayo":
        text = MAYO_NOISE.sub(" ", text)
    text = GENERIC_NOISE.sub(" ", text)
    text = remove_medical_special_chars(text)
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

    # Drop record if total meaningful content < MIN_CONTENT_WORDS
    content_words = sum(
        word_count(cleaned.get(f, ""))
        for f in CONTENT_FIELDS
    )
    if content_words < MIN_CONTENT_WORDS:
        return None

    # ── (NEW) Quality issues tracking ─────────────────────────────────────────
    issues = build_quality_issues(cleaned)
    cleaned["_quality_issues"] = issues
    cleaned["_quality_ok"] = (len(issues) == 0)

    return cleaned


def process_file(path: pathlib.Path, source: str) -> list[dict]:
    log.info(f"Reading {path} …")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        log.error(f"  File error {path}: {e}")
        return []
    log.info(f"  {len(data)} raw records")

    cleaned, dropped = [], 0
    seen: set[str] = set()
    quality_issues_count = 0
    encoding_errors = 0
    url_issues = 0

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

        # Track quality stats
        issues = result.get("_quality_issues", [])
        quality_issues_count += len(issues)
        if any("encoding" in i for i in issues):
            encoding_errors += 1
        if any("url" in i for i in issues):
            url_issues += 1

        cleaned.append(result)

    total = len(cleaned)
    fully_clean = sum(1 for r in cleaned if r.get("_quality_ok"))

    log.info(f"  → {total} kept, {dropped} dropped")
    log.info(f"  → {quality_issues_count} quality issues tổng cộng")
    log.info(f"  → {encoding_errors} bản ghi có thể lỗi encoding")
    log.info(f"  → {url_issues} bản ghi URL không tin cậy")
    log.info(f"  → {fully_clean}/{total} bản ghi hoàn toàn sạch ({fully_clean/total*100:.1f}%)")
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

    total = len(mayo) + len(medline)
    total_ok = sum(1 for r in mayo + medline if r.get("_quality_ok"))
    log.info(f"Quality tổng: {total_ok}/{total} bản ghi sạch ({total_ok/total*100:.1f}%)")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()