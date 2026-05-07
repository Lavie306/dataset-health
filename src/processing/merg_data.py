"""
STEP 2 – MERGE  (Nâng cao)
===========================
Input : data/processed/mayo_clean.json
        data/processed/medlineplus_clean.json
Output: data/processed/merged.json

Tính năng mới bổ sung:
  ✅ Disease alias dictionary  – "Tiểu đường" = "Đái tháo đường" = "Diabetes"
  ✅ Provenance tracking       – field_sources: {overview: "mayo", symptoms: "medlineplus"...}
  ✅ Conflict detection        – đánh dấu khi 2 nguồn khác nhau > ngưỡng
  ✅ Fuzzy duplicate detection – dùng difflib.SequenceMatcher sau exact merge
  ✅ Content combination       – với field thưa, kết hợp cả 2 nguồn thay vì chọn 1

Tính năng giữ nguyên:
  - Normalize disease names (lowercase, strip punctuation) as merge key
  - prefer the longer / richer value per field
  - keep both URLs (list), mark origin = "both"
  - Sort final list alphabetically by disease name
"""

import json, re, pathlib, logging, time
from difflib import SequenceMatcher

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

# ── (NEW) Disease alias dictionary ───────────────────────────────────────────
# Ánh xạ nhiều tên → 1 tên chuẩn (normalized key)
# Key = alias (lowercase, normalized), Value = canonical normalized name
DISEASE_ALIASES: dict[str, str] = {
    # Tiểu đường
    "diabetes":                       "diabetes mellitus",
    "diabetes mellitus":              "diabetes mellitus",
    "tieu duong":                     "diabetes mellitus",
    "benh tieu duong":                "diabetes mellitus",
    "dai thao duong":                 "diabetes mellitus",
    # HIV/AIDS
    "hiv":                            "hiv aids",
    "aids":                           "hiv aids",
    "hiv infection":                  "hiv aids",
    # Tim mạch
    "heart attack":                   "myocardial infarction",
    "myocardial infarction":          "myocardial infarction",
    "nhoi mau co tim":                "myocardial infarction",
    # Ung thư
    "cancer":                         "cancer",
    "ung thu":                        "cancer",
    # Cao huyết áp
    "hypertension":                   "high blood pressure",
    "high blood pressure":            "high blood pressure",
    "huyet ap cao":                   "high blood pressure",
    "cao huyet ap":                   "high blood pressure",
    # Hen suyễn
    "asthma":                         "asthma",
    "hen suyen":                      "asthma",
    "hen phe quan":                   "asthma",
    # Viêm phổi
    "pneumonia":                      "pneumonia",
    "viem phoi":                      "pneumonia",
    # Alzheimer
    "alzheimers disease":             "alzheimer disease",
    "alzheimer disease":              "alzheimer disease",
    "alzheimers":                     "alzheimer disease",
    # Parkinson
    "parkinsons disease":             "parkinson disease",
    "parkinson disease":              "parkinson disease",
    # Gút
    "gout":                           "gout",
    "gut":                            "gout",
    "benh gut":                       "gout",
    # Loãng xương
    "osteoporosis":                   "osteoporosis",
    "loang xuong":                    "osteoporosis",
    # Đột quỵ
    "stroke":                         "stroke",
    "dot quy":                        "stroke",
    # COPD
    "copd":                           "chronic obstructive pulmonary disease",
    "chronic obstructive pulmonary disease": "chronic obstructive pulmonary disease",
    # Trầm cảm
    "depression":                     "depression",
    "tram cam":                       "depression",
    # Lo âu
    "anxiety":                        "anxiety disorder",
    "anxiety disorder":               "anxiety disorder",
    "lo au":                          "anxiety disorder",
    # Ung thư vú
    "breast cancer":                  "breast cancer",
    "ung thu vu":                     "breast cancer",
    # Ung thư phổi
    "lung cancer":                    "lung cancer",
    "ung thu phoi":                   "lung cancer",
    # Viêm gan
    "hepatitis":                      "hepatitis",
    "hepatitis b":                    "hepatitis b",
    "hepatitis c":                    "hepatitis c",
    "viem gan":                       "hepatitis",
    "viem gan b":                     "hepatitis b",
    "viem gan c":                     "hepatitis c",
    # Lao
    "tuberculosis":                   "tuberculosis",
    "lao":                            "tuberculosis",
    "benh lao":                       "tuberculosis",
    # Sốt xuất huyết
    "dengue":                         "dengue fever",
    "dengue fever":                   "dengue fever",
    "sot xuat huyet":                 "dengue fever",
    # Sởi
    "measles":                        "measles",
    "soi":                            "measles",
}

# ── (NEW) Conflict detection threshold ───────────────────────────────────────
CONFLICT_SIMILARITY_THRESHOLD = 0.3  # Nếu similarity < 30% → conflict
MIN_WORDS_FOR_CONFLICT_CHECK = 20    # Chỉ check nếu cả 2 field có ≥ 20 từ

# ── (NEW) Fuzzy dedup threshold ───────────────────────────────────────────────
FUZZY_DEDUP_THRESHOLD = 0.88         # Similarity ≥ 88% → coi là trùng


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def normalize_key(name: str) -> str:
    """Lowercase, remove punctuation, collapse spaces → merge key."""
    name = name.lower().strip()
    name = re.sub(r"[''`]", "", name)          # apostrophes
    name = re.sub(r"[^a-z0-9 ]", " ", name)   # punctuation → space
    name = re.sub(r"\s+", " ", name).strip()
    return name


def resolve_alias(key: str) -> str:
    """Tra cứu alias dictionary để map về tên chuẩn."""
    return DISEASE_ALIASES.get(key, key)


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def text_similarity(a: str, b: str) -> float:
    """Tính độ tương đồng giữa 2 text (0.0 - 1.0)."""
    if not a or not b:
        return 0.0
    # Dùng 500 ký tự đầu để tăng tốc so sánh
    return SequenceMatcher(None, a[:500].lower(), b[:500].lower()).ratio()


def pick_richer(a: str, b: str) -> str:
    """Return whichever text is longer (more informative)."""
    return a if word_count(a) >= word_count(b) else b


def combine_texts(a: str, b: str) -> str:
    """Kết hợp 2 text nếu chúng khác nhau (cho field thưa dữ liệu)."""
    if not a:
        return b
    if not b:
        return a
    if a.strip().lower() == b.strip().lower():
        return a
    # Nếu b bổ sung thêm thông tin, ghép vào
    if word_count(b) > 20 and text_similarity(a, b) < 0.6:
        return a.rstrip() + "\n\n" + b.strip()
    return pick_richer(a, b)


def detect_conflict(field: str, a: str, b: str) -> bool:
    """
    Phát hiện xung đột: 2 nguồn mô tả khác nhau đáng kể cho cùng 1 field.
    Chỉ check các field nội dung quan trọng.
    """
    if field not in ("symptoms", "causes", "treatment", "prognosis"):
        return False
    if word_count(a) < MIN_WORDS_FOR_CONFLICT_CHECK:
        return False
    if word_count(b) < MIN_WORDS_FOR_CONFLICT_CHECK:
        return False
    sim = text_similarity(a, b)
    return sim < CONFLICT_SIMILARITY_THRESHOLD


def is_fuzzy_duplicate(name1: str, name2: str) -> bool:
    """Kiểm tra 2 tên bệnh có gần giống nhau không (fuzzy match)."""
    k1 = normalize_key(name1)
    k2 = normalize_key(name2)
    if k1 == k2:
        return True
    ratio = SequenceMatcher(None, k1, k2).ratio()
    return ratio >= FUZZY_DEDUP_THRESHOLD


# =============================================================================
# MERGE LOGIC
# =============================================================================

def merge_records(mayo_rec: dict, medline_rec: dict) -> dict:
    """
    Merge 2 records từ Mayo và MedlinePlus.
    Bổ sung: provenance tracking per field + conflict detection.
    """
    merged = {
        "disease":    mayo_rec["disease"],   # prefer Mayo capitalisation
        "url":        [mayo_rec["url"], medline_rec["url"]],
        "source":     "both",
        "field_sources":  {},                # (NEW) nguồn của từng field
        "conflict_fields": [],               # (NEW) các field có conflict
    }

    # Kế thừa quality issues từ 2 nguồn
    all_issues = (
        mayo_rec.get("_quality_issues", []) +
        medline_rec.get("_quality_issues", [])
    )
    merged["_quality_issues"] = list(set(all_issues))
    merged["_quality_ok"] = (len(merged["_quality_issues"]) == 0)

    for field in CONTENT_FIELDS:
        a = mayo_rec.get(field, "") or ""
        b = medline_rec.get(field, "") or ""

        # (NEW) Conflict detection
        if detect_conflict(field, a, b):
            merged["conflict_fields"].append(field)
            log.debug(f"  CONFLICT in '{field}' for '{mayo_rec['disease']}'")

        # (NEW) Combine strategy: sparse fields → combine, others → pick richer
        SPARSE_FIELDS = {"prognosis", "when_to_see_doc", "complications", "prevention"}
        if field in SPARSE_FIELDS:
            merged[field] = combine_texts(a, b)
            merged["field_sources"][field] = "combined"
        elif word_count(a) >= word_count(b):
            merged[field] = a
            merged["field_sources"][field] = "mayo"
        else:
            merged[field] = b
            merged["field_sources"][field] = "medlineplus"

    return merged


def fuzzy_dedup(records: list[dict]) -> tuple[list[dict], int]:
    """
    Phát hiện và loại bỏ các bản ghi trùng lặp mờ (sau exact merge).
    Trả về (deduplicated_records, removed_count).
    """
    kept = []
    removed = 0
    seen_names = []  # List để so sánh fuzzy

    for rec in records:
        name = rec["disease"].lower()
        is_dup = False

        for seen_name in seen_names:
            if is_fuzzy_duplicate(name, seen_name):
                is_dup = True
                log.info(f"  Fuzzy dup: '{rec['disease']}' ≈ '{seen_name}' → loại bỏ")
                removed += 1
                break

        if not is_dup:
            kept.append(rec)
            seen_names.append(name)

    return kept, removed


def run():
    t0 = time.time()
    log.info("Loading cleaned files…")

    with open(IN_MAYO,    encoding="utf-8") as f:
        mayo_list = json.load(f)
    with open(IN_MEDLINE, encoding="utf-8") as f:
        medline_list = json.load(f)

    # ── Index medline by normalised + alias-resolved key ──────────────────────
    medline_index: dict[str, dict] = {}
    for rec in medline_list:
        raw_key = normalize_key(rec["disease"])
        canonical = resolve_alias(raw_key)
        medline_index[canonical] = rec

    merged_records: list[dict] = []
    matched = 0

    # ── Process Mayo first ────────────────────────────────────────────────────
    used_medline_keys: set[str] = set()
    for rec in mayo_list:
        raw_key  = normalize_key(rec["disease"])
        canonical = resolve_alias(raw_key)

        if canonical in medline_index:
            merged = merge_records(rec, medline_index[canonical])
            merged_records.append(merged)
            used_medline_keys.add(canonical)
            matched += 1
        else:
            # Mayo-only record: normalise URL to list
            r = dict(rec)
            r["url"]    = [r["url"]]
            r["source"] = "mayo"
            r["field_sources"]   = {f: "mayo" for f in CONTENT_FIELDS}
            r["conflict_fields"] = []
            for f in CONTENT_FIELDS:
                r.setdefault(f, "")
            merged_records.append(r)

    # ── Add medline-only records ──────────────────────────────────────────────
    medline_only = 0
    for rec in medline_list:
        raw_key   = normalize_key(rec["disease"])
        canonical = resolve_alias(raw_key)
        if canonical not in used_medline_keys:
            r = dict(rec)
            r["url"]    = [r["url"]]
            r["source"] = "medlineplus"
            r["field_sources"]   = {f: "medlineplus" for f in CONTENT_FIELDS}
            r["conflict_fields"] = []
            for f in CONTENT_FIELDS:
                r.setdefault(f, "")
            merged_records.append(r)
            medline_only += 1

    # ── Sort alphabetically ───────────────────────────────────────────────────
    merged_records.sort(key=lambda r: r["disease"].lower())

    # ── (NEW) Fuzzy dedup pass ────────────────────────────────────────────────
    log.info("Fuzzy dedup pass…")
    merged_records, fuzzy_removed = fuzzy_dedup(merged_records)

    # ── Stats ─────────────────────────────────────────────────────────────────
    only_mayo    = sum(1 for r in merged_records if r["source"] == "mayo")
    only_medline = sum(1 for r in merged_records if r["source"] == "medlineplus")
    both         = sum(1 for r in merged_records if r["source"] == "both")
    conflicts    = sum(1 for r in merged_records if r.get("conflict_fields"))
    total_conflict_fields = sum(len(r.get("conflict_fields", [])) for r in merged_records)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_records, f, ensure_ascii=False, indent=2)

    log.info(f"Total merged records : {len(merged_records):,}")
    log.info(f"  matched (both)     : {both:,}")
    log.info(f"  mayo only          : {only_mayo:,}")
    log.info(f"  medlineplus only   : {only_medline:,}")
    log.info(f"  fuzzy dups removed : {fuzzy_removed:,}")
    log.info(f"  conflict records   : {conflicts:,} ({total_conflict_fields} fields)")
    log.info(f"Saved → {OUT_FILE}")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()