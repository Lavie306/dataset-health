"""
quality_report.py – QUALITY REPORT (Đã chuẩn hóa thống kê)
=========================================================
Sử dụng chung hàm đếm từ wc và cấu hình fields từ shared_metrics.py
"""

import json, re, pathlib, logging, time, sys
from collections import Counter
from datetime import datetime

# Import từ thư viện dùng chung
from shared_metrics import CONTENT_FIELDS, FIELD_LABELS_VI, wc

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("quality_report")

ROOT = pathlib.Path(__file__).parent.parent.parent
PROCESSING_DIR = ROOT / "src" / "processing"
if str(PROCESSING_DIR) not in sys.path:
    sys.path.insert(0, str(PROCESSING_DIR))

try:
    from medical_glossary import glossary_remaining_hits, load_glossary
except ImportError:
    log.warning("Không tìm thấy medical_glossary. Cần có file dictionary cho section 7.")
    def glossary_remaining_hits(val): return []
    def load_glossary(): return {}

# Input files
DISCRETIZED_FILE   = ROOT / "data/processed/discretized.json"
TRANSLATED_FILE    = ROOT / "data/processed/translated.json"
MERGED_FILE        = ROOT / "data/processed/merged.json"
REDUCTION_REPORT   = ROOT / "data/processed/reduction_report.json"

# Output
OUT_DIR    = ROOT / "data/output"
OUT_JSON   = OUT_DIR / "quality_report.json"
OUT_MD     = OUT_DIR / "quality_report.md"

# Regex cải tiến: chỉ match các từ tiếng Anh thông dụng đứng độc lập, không dính chữ Việt (VD: "và", "như", "là")
ENGLISH_PATTERN = re.compile(
    r'\b(the|and|or|is|are|was|were|have|has|with|that|this|for|from|by|an)\b',
    re.IGNORECASE
)

MOJIBAKE_PATTERN = re.compile(
    r'Ã[©°¡-ÿ]|â€[™œ•–—]|Â[«»°²³µ]',
    re.IGNORECASE,
)

def has_english_remnant(text: str) -> bool:
    """Phát hiện text tiếng Việt còn sót tiếng Anh đáng kể."""
    if not text or wc(text) < 20:
        return False
    matches = ENGLISH_PATTERN.findall(text)
    total = wc(text)
    # Tỷ lệ từ tiếng Anh > 10%
    return total > 0 and len(matches) / total > 0.10

def is_disease_translated(record: dict) -> str:
    """Kiểm tra trạng thái dịch của record."""
    disease_en = record.get("disease_en", "")
    disease_vi = record.get("disease", "")

    if not disease_en or disease_en == disease_vi:
        return "not_translated"

    english_fields = 0
    filled_fields  = 0
    for field in CONTENT_FIELDS:
        val = record.get(field, "") or ""
        if wc(val) >= 5:
            filled_fields += 1
            if has_english_remnant(val):
                english_fields += 1

    if filled_fields == 0:
        return "no_content"
    ratio = english_fields / filled_fields
    if ratio > 0.5:
        return "mostly_english"
    if ratio > 0:
        return "partial_english"
    return "fully_translated"

def analyze_translation(records: list[dict]) -> dict:
    status_counts = Counter(is_disease_translated(r) for r in records)
    total = len(records)
    return {
        "total_records":      total,
        "fully_translated":   status_counts.get("fully_translated", 0),
        "partial_english":    status_counts.get("partial_english", 0),
        "mostly_english":     status_counts.get("mostly_english", 0),
        "not_translated":     status_counts.get("not_translated", 0),
        "no_content":         status_counts.get("no_content", 0),
        "pct_fully_translated": round(status_counts.get("fully_translated", 0) / total * 100, 1) if total else 0,
        "pct_issues":         round((total - status_counts.get("fully_translated", 0) - status_counts.get("no_content", 0)) / total * 100, 1) if total else 0,
    }

def analyze_encoding(records: list[dict]) -> dict:
    total = len(records)
    encoding_errors = 0
    fields_with_errors = Counter()

    for rec in records:
        has_error = False
        for field in CONTENT_FIELDS:
            val = rec.get(field, "") or ""
            if MOJIBAKE_PATTERN.search(val):
                fields_with_errors[field] += 1
                has_error = True
        if has_error:
            encoding_errors += 1

    pct_errors = encoding_errors / total if total else 0
    return {
        "total_records":         total,
        "records_with_encoding_errors": encoding_errors,
        "pct_encoding_errors":   round(pct_errors * 100, 2),
        "fields_error_counts":   dict(fields_with_errors.most_common()),
        "encoding_health":       "Tốt" if pct_errors < 0.02 else
                                 "Cần xem xét" if pct_errors < 0.1 else "Cần xử lý",
    }

def analyze_field_completeness(records: list[dict]) -> dict:
    total = len(records)
    fields_stats = {}

    for field in CONTENT_FIELDS:
        empty   = sum(1 for r in records if wc(r.get(field, "")) == 0)
        sparse  = sum(1 for r in records if 0 < wc(r.get(field, "")) < 5)
        filled  = sum(1 for r in records if wc(r.get(field, "")) >= 5)
        avg_wc  = sum(wc(r.get(field, "")) for r in records) / total if total else 0

        fields_stats[field] = {
            "label":      FIELD_LABELS_VI.get(field, field),
            "empty":      empty,
            "sparse":     sparse,
            "filled":     filled,
            "pct_filled": round(filled / total * 100, 1) if total else 0,
            "avg_words":  round(avg_wc, 1),
            "quality":    "Tốt" if filled / total >= 0.7 else
                          "Trung bình" if filled / total >= 0.4 else "Kém" if total else "Kém",
        }

    key_fields = ["overview", "symptoms", "causes", "treatment", "complications", "prognosis"]
    complete = sum(1 for r in records if all(wc(r.get(f, "")) >= 5 for f in key_fields))

    return {
        "total_records":   total,
        "complete_records": complete,
        "pct_complete":    round(complete / total * 100, 1) if total else 0,
        "fields":          fields_stats,
    }

def analyze_icd_coverage(records: list[dict]) -> dict:
    total = len(records)
    with_icd = sum(1 for r in records if r.get("icd_code", ""))
    without_icd = total - with_icd

    chapter_map = {
        "A": "Nhiễm khuẩn & ký sinh", "B": "Nhiễm khuẩn & virus", "C": "Ung thư",
        "D": "U lành & rối loạn máu", "E": "Nội tiết & chuyển hóa", "F": "Tâm thần",
        "G": "Thần kinh", "H": "Mắt & Tai", "I": "Tim mạch", "J": "Hô hấp",
        "K": "Tiêu hóa", "L": "Da liễu", "M": "Cơ xương khớp", "N": "Tiết niệu sinh dục",
        "O": "Thai sản", "Q": "Dị tật bẩm sinh",
    }
    chapter_counts = Counter()
    for r in records:
        code = r.get("icd_code", "")
        if code:
            ch = code[0].upper()
            chapter_counts[ch] += 1

    chapter_dist = {
        f"{ch} – {chapter_map.get(ch, 'Khác')}": cnt
        for ch, cnt in chapter_counts.most_common()
    }

    coverage_pct = with_icd / total if total else 0
    return {
        "total_records":    total,
        "with_icd":         with_icd,
        "without_icd":      without_icd,
        "icd_coverage_pct": round(coverage_pct * 100, 1),
        "chapter_distribution": chapter_dist,
        "coverage_quality": "Tốt" if coverage_pct >= 0.6 else
                            "Trung bình" if coverage_pct >= 0.3 else "Cần cải thiện",
    }

def analyze_categories(records: list[dict]) -> dict:
    total = len(records)
    cat_counts    = Counter(r.get("disease_category", "Khác") for r in records)
    type_counts   = Counter(r.get("disease_type", "Không xác định") for r in records)
    contagious    = Counter(r.get("is_contagious", "Không xác định") for r in records)
    severity      = Counter(r.get("severity_level", "Trung bình") for r in records)

    def to_pct(counts: Counter) -> dict:
        return {
            k: {"count": v, "pct": round(v / total * 100, 1) if total else 0}
            for k, v in counts.most_common()
        }

    return {
        "total_records":       total,
        "category_distribution": to_pct(cat_counts),
        "disease_type":          to_pct(type_counts),
        "contagious_status":     to_pct(contagious),
        "severity_distribution": to_pct(severity),
    }

def generate_markdown(report: dict) -> str:
    ts = report["generated_at"]
    s1 = report["translation_quality"]
    s2 = report["encoding_quality"]
    s3 = report["field_completeness"]
    s5 = report["icd_coverage"]
    s6 = report["category_distribution"]

    lines = [
        f"# 📊 Báo Cáo Chất Lượng Dữ Liệu Y Tế Đầu Ra",
        f"",
        f"> **Thời gian tạo:** {ts}  ",
        f"> **Tổng bản ghi:** {s1['total_records']:,}  ",
        f"",
        f"---",
        f"",
        f"## 1. 🌐 Chất Lượng Dịch Thuật",
        f"",
        f"| Trạng thái | Số lượng | Tỷ lệ |",
        f"|-----------|---------|-------|",
        f"| ✅ Dịch hoàn toàn | {s1['fully_translated']:,} | {s1['pct_fully_translated']}% |",
        f"| ⚠️ Còn một phần tiếng Anh | {s1['partial_english']:,} | - |",
        f"| ❌ Phần lớn tiếng Anh | {s1['mostly_english']:,} | - |",
        f"| ❌ Chưa dịch tên bệnh | {s1['not_translated']:,} | - |",
        f"| ℹ️ Không có nội dung | {s1['no_content']:,} | - |",
        f"",
        f"---",
        f"",
        f"## 2. 🔤 Chất Lượng Encoding",
        f"",
        f"- **Bản ghi lỗi encoding:** {s2['records_with_encoding_errors']:,} / {s2['total_records']:,} ({s2['pct_encoding_errors']}%)",
        f"- **Đánh giá:** {s2['encoding_health']}",
        f"",
    ]

    lines += [
        f"---",
        f"",
        f"## 3. 📋 Độ Hoàn Chỉnh Từng Field (>= 5 từ)",
        f"",
        f"- **Bản ghi hoàn chỉnh (đầy đủ 6 field lõi):** {s3['complete_records']:,} / {s3['total_records']:,} ({s3['pct_complete']}%)",
        f"",
        f"| Field | Tỷ lệ điền hợp lệ | Avg từ | Đánh giá |",
        f"|-------|-----------|--------|---------|",
    ]
    for fld, stats in s3["fields"].items():
        lines.append(f"| {stats['label']} | {stats['pct_filled']}% | {stats['avg_words']} | {stats['quality']} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 4. 🏥 Độ Bao Phủ ICD-10",
        f"",
        f"- **Có mã ICD:** {s5['with_icd']:,} / {s5['total_records']:,} (**{s5['icd_coverage_pct']}%**)",
        f"- **Đánh giá:** {s5['coverage_quality']}",
        f"",
    ]

    return "\n".join(lines)

def run():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data_file = DISCRETIZED_FILE if DISCRETIZED_FILE.exists() else TRANSLATED_FILE
    if not data_file.exists():
        log.error("Không tìm thấy file json đã xử lý.")
        return
        
    with open(data_file, encoding="utf-8") as f:
        records = json.load(f)

    s1 = analyze_translation(records)
    s2 = analyze_encoding(records)
    s3 = analyze_field_completeness(records)
    s5 = analyze_icd_coverage(records)
    s6 = analyze_categories(records)

    report = {
        "generated_at":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "translation_quality":   s1,
        "encoding_quality":      s2,
        "field_completeness":    s3,
        "icd_coverage":          s5,
        "category_distribution": s6,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(generate_markdown(report))

    log.info(f"Done in {time.time()-t0:.1f}s")

if __name__ == "__main__":
    run()
