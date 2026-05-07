"""
STEP 3b – DATA REDUCTION  (MỚI)
================================
Input : data/processed/translated.json
Output: data/processed/translated.json  (in-place, đã giảm/tối ưu)
        data/processed/reduction_report.json

Tính năng:
  ✅ smart_truncate()        – cắt text theo ranh giới câu, không cắt giữa chừng
  ✅ fuzzy_dedup()           – phát hiện & loại bản ghi trùng lặp mờ (≥85%)
  ✅ handle_sparse_fields()  – chiến lược cho field prognosis, when_to_see_doc
  ✅ remove_near_empty()     – loại bỏ field có quá ít từ (< MIN_FIELD_WORDS)
  ✅ reduction_report.json   – báo cáo chi tiết: số bản ghi loại, field truncate

Chạy:
  cd src/processing && python reduce_data.py
"""

import json, re, pathlib, logging, time
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("reduce")

ROOT     = pathlib.Path(__file__).parent.parent.parent
IN_FILE  = ROOT / "data/processed/translated.json"
OUT_FILE = ROOT / "data/processed/reduced.json"   # file riêng, KHÔNG đè translated.json
REPORT   = ROOT / "data/processed/reduction_report.json"

# ── Thresholds ────────────────────────────────────────────────────────────────
MAX_FIELD_CHARS     = 3000   # Giới hạn mềm: cắt nếu field > 3000 ký tự
MAX_FIELD_CHARS_HARD = 6000  # Giới hạn cứng: cắt bắt buộc nếu > 6000 ký tự
MIN_FIELD_WORDS     = 3      # Loại field nếu < 3 từ (coi là gần rỗng)
FUZZY_THRESHOLD     = 0.85   # Similarity ≥ 85% → coi là trùng lặp

CONTENT_FIELDS = [
    "overview", "symptoms", "causes",
    "risk_factors", "prevention", "when_to_see_doc",
    "treatment", "prognosis", "complications", "exams_and_tests",
]

# Các field hay bị thưa dữ liệu → xử lý đặc biệt
SPARSE_FIELDS = {"prognosis", "when_to_see_doc"}


# =============================================================================
# SMART TRUNCATION
# =============================================================================

# Dấu kết thúc câu trong tiếng Việt và tiếng Anh
SENTENCE_END = re.compile(r'[.!?]\s+')


def smart_truncate(text: str, max_chars: int = MAX_FIELD_CHARS) -> tuple[str, bool]:
    """
    Cắt text đến ranh giới câu gần nhất, KHÔNG cắt giữa câu.
    Trả về (truncated_text, was_truncated).
    """
    if not text or len(text) <= max_chars:
        return text, False

    # Tìm dấu kết thúc câu cuối cùng trước max_chars
    search_zone = text[:max_chars]

    # Tìm các vị trí kết thúc câu
    candidates = [m.end() for m in SENTENCE_END.finditer(search_zone)]

    if candidates:
        cut_pos = candidates[-1]  # Vị trí cuối câu gần nhất trước giới hạn
        truncated = text[:cut_pos].rstrip()
    else:
        # Không tìm thấy dấu câu → cắt tại dấu phẩy hoặc khoảng trắng
        cut_pos = search_zone.rfind(", ")
        if cut_pos == -1:
            cut_pos = search_zone.rfind(" ")
        if cut_pos == -1:
            cut_pos = max_chars
        truncated = text[:cut_pos].rstrip()

    return truncated, True


def hard_truncate(text: str, max_chars: int = MAX_FIELD_CHARS_HARD) -> tuple[str, bool]:
    """Cắt cứng tại giới hạn tuyệt đối (emergency fallback)."""
    if not text or len(text) <= max_chars:
        return text, False
    # Cắt tại khoảng trắng gần nhất
    cut = text[:max_chars].rfind(" ")
    if cut == -1:
        cut = max_chars
    return text[:cut].rstrip() + "…", True


# =============================================================================
# NEAR-EMPTY FIELD REMOVAL
# =============================================================================

def remove_near_empty_fields(record: dict) -> tuple[dict, list[str]]:
    """
    Loại bỏ (set = "") các field có quá ít từ.
    Trả về (updated_record, cleared_fields).
    """
    cleared = []
    for field in CONTENT_FIELDS:
        val = record.get(field, "") or ""
        wc = len(val.split()) if val.strip() else 0
        if 0 < wc < MIN_FIELD_WORDS:
            record[field] = ""
            cleared.append(f"{field}({wc}w)")
    return record, cleared


# =============================================================================
# SPARSE FIELD STRATEGY
# =============================================================================

def handle_sparse_field(record: dict, field: str) -> dict:
    """
    Chiến lược cho field thưa dữ liệu:
    - Nếu field rỗng nhưng có thông tin liên quan → tạo placeholder gợi ý
    - Không bịa nội dung y tế
    """
    val = (record.get(field, "") or "").strip()
    if val:
        return record  # Đã có nội dung → không làm gì

    disease = record.get("disease", "")

    # Chỉ thêm gợi ý tìm kiếm, không bịa nội dung y tế
    if field == "prognosis":
        # Kiểm tra overview có đề cập tiên lượng không
        overview = record.get("overview", "") or ""
        prognosis_hints = re.findall(
            r'[^.!?]*(?:tiên lượng|prognosis|khỏi|hồi phục|mãn tính|chữa được|điều trị được)[^.!?]*[.!?]',
            overview,
            re.IGNORECASE
        )
        if prognosis_hints:
            record[field] = " ".join(prognosis_hints[:2]).strip()

    elif field == "when_to_see_doc":
        # Kiểm tra symptoms có đề cập "gặp bác sĩ" không
        symptoms = record.get("symptoms", "") or ""
        doc_hints = re.findall(
            r'[^.!?]*(?:gặp bác sĩ|đến bệnh viện|cấp cứu|khám ngay|see a doctor|seek medical)[^.!?]*[.!?]',
            symptoms,
            re.IGNORECASE
        )
        if doc_hints:
            record[field] = " ".join(doc_hints[:2]).strip()

    return record


# =============================================================================
# FUZZY DEDUP
# =============================================================================

def normalize_for_compare(name: str) -> str:
    """Chuẩn hóa tên bệnh để so sánh fuzzy."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\u00c0-\u024f\u1e00-\u1eff ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def fuzzy_dedup(records: list[dict], threshold: float = FUZZY_THRESHOLD) -> tuple[list[dict], list[dict]]:
    """
    Phát hiện và loại bỏ bản ghi trùng lặp mờ.
    Giữ lại bản ghi có nhiều nội dung hơn khi 2 bản ghi gần giống nhau.
    Trả về (kept_records, removed_records).
    """
    kept = []
    removed = []
    kept_normalized = []

    def total_words(r):
        return sum(len((r.get(f, "") or "").split()) for f in CONTENT_FIELDS)

    for rec in records:
        name_norm = normalize_for_compare(rec["disease"])
        is_dup = False

        for i, kept_name in enumerate(kept_normalized):
            sim = SequenceMatcher(None, name_norm, kept_name).ratio()
            if sim >= threshold:
                is_dup = True
                log.info(f"  Fuzzy dup ({sim:.2f}): '{rec['disease']}' ≈ '{kept[i]['disease']}'")
                # Giữ bản ghi có nhiều nội dung hơn
                if total_words(rec) > total_words(kept[i]):
                    log.info(f"    → Thay bằng bản phong phú hơn: '{rec['disease']}'")
                    removed.append(kept[i])
                    kept[i] = rec
                    kept_normalized[i] = name_norm
                else:
                    removed.append(rec)
                break

        if not is_dup:
            kept.append(rec)
            kept_normalized.append(name_norm)

    return kept, removed


# =============================================================================
# MAIN REDUCTION PIPELINE
# =============================================================================

def reduce_record(record: dict) -> tuple[dict, dict]:
    """
    Áp dụng tất cả reduction cho 1 record.
    Trả về (reduced_record, stats_dict).
    """
    stats = {
        "truncated_fields":    [],
        "hard_truncated_fields": [],
        "cleared_fields":      [],
        "sparse_fields_filled": [],
    }

    # 1. Smart truncation
    for field in CONTENT_FIELDS:
        val = record.get(field, "") or ""
        if not val:
            continue

        truncated, was_cut = smart_truncate(val, MAX_FIELD_CHARS)
        if was_cut:
            # Nếu vẫn còn quá dài → hard truncate
            truncated2, was_hard = hard_truncate(truncated, MAX_FIELD_CHARS_HARD)
            if was_hard:
                record[field] = truncated2
                stats["hard_truncated_fields"].append(field)
            else:
                record[field] = truncated
                stats["truncated_fields"].append(field)

    # 2. Remove near-empty fields
    record, cleared = remove_near_empty_fields(record)
    stats["cleared_fields"] = cleared

    # 3. Handle sparse fields
    for field in SPARSE_FIELDS:
        old_val = record.get(field, "") or ""
        record = handle_sparse_field(record, field)
        new_val = record.get(field, "") or ""
        if not old_val and new_val:
            stats["sparse_fields_filled"].append(field)

    return record, stats


def run():
    t0 = time.time()

    log.info(f"Loading {IN_FILE} …")
    with open(IN_FILE, encoding="utf-8") as f:
        records = json.load(f)
    log.info(f"  {len(records)} records")

    # ── Phase 1: Record-level reduction ──────────────────────────────────────
    log.info("Phase 1: Per-record reduction (truncation, sparse handling)…")
    reduced = []
    all_stats = []
    for rec in records:
        r, stats = reduce_record(rec)
        reduced.append(r)
        all_stats.append(stats)

    # ── Phase 2: Fuzzy dedup ──────────────────────────────────────────────────
    log.info("Phase 2: Fuzzy dedup…")
    kept, removed = fuzzy_dedup(reduced, FUZZY_THRESHOLD)

    # ── Build report ──────────────────────────────────────────────────────────
    truncated_total  = sum(len(s["truncated_fields"]) for s in all_stats)
    hard_trunc_total = sum(len(s["hard_truncated_fields"]) for s in all_stats)
    cleared_total    = sum(len(s["cleared_fields"]) for s in all_stats)
    sparse_filled    = sum(len(s["sparse_fields_filled"]) for s in all_stats)

    report = {
        "input_records":       len(records),
        "output_records":      len(kept),
        "fuzzy_dups_removed":  len(removed),
        "removed_diseases":    [r["disease"] for r in removed],
        "fields_smart_truncated": truncated_total,
        "fields_hard_truncated":  hard_trunc_total,
        "fields_cleared_near_empty": cleared_total,
        "sparse_fields_auto_filled": sparse_filled,
        "reduction_ratio":     f"{(1 - len(kept)/len(records))*100:.1f}%" if records else "0%",
    }

    # ── Save ──────────────────────────────────────────────────────────────────
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
    log.info(f"Saved → {OUT_FILE} ({len(kept)} records)")

    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log.info("─" * 55)
    log.info(f"Input records        : {report['input_records']:,}")
    log.info(f"Output records       : {report['output_records']:,}")
    log.info(f"Fuzzy dups removed   : {report['fuzzy_dups_removed']:,}")
    log.info(f"Smart truncated      : {report['fields_smart_truncated']:,} fields")
    log.info(f"Hard truncated       : {report['fields_hard_truncated']:,} fields")
    log.info(f"Cleared near-empty   : {report['fields_cleared_near_empty']:,} fields")
    log.info(f"Sparse fields filled : {report['sparse_fields_auto_filled']:,}")
    log.info(f"Reduction ratio      : {report['reduction_ratio']}")
    log.info(f"Report saved → {REPORT}")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()
