"""
STEP 6 – QUALITY REPORT  (MỚI HOÀN TOÀN)
==========================================
Input : data/processed/discretized.json  (ưu tiên)
        data/processed/translated.json   (fallback)
        data/processed/merged.json       (để lấy conflict stats)
        data/processed/reduction_report.json (nếu có)
Output:
  data/output/quality_report.json  – báo cáo dạng JSON
  data/output/quality_report.md    – báo cáo dạng Markdown dễ đọc

6 sections báo cáo:
  1. Translation Quality   – % dịch hoàn toàn / còn tiếng Anh / fallback
  2. Encoding Quality      – % lỗi encoding, encoding issues
  3. Field Completeness    – null/empty breakdown chi tiết từng field
  4. Duplicate Summary     – trùng lặp exact / fuzzy
  5. ICD Coverage          – % bản ghi có mã ICD, phân bố mã
  6. Category Distribution – phân bố theo 13 nhóm bệnh

Chạy:
  cd src/utils && python quality_report.py
"""

import json, re, pathlib, logging, time
from collections import Counter
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("quality_report")

ROOT = pathlib.Path(__file__).parent.parent.parent

# Input files (ưu tiên discretized, fallback translated)
DISCRETIZED_FILE   = ROOT / "data/processed/discretized.json"
TRANSLATED_FILE    = ROOT / "data/processed/translated.json"
MERGED_FILE        = ROOT / "data/processed/merged.json"
REDUCTION_REPORT   = ROOT / "data/processed/reduction_report.json"

# Output
OUT_DIR    = ROOT / "data/output"
OUT_JSON   = OUT_DIR / "quality_report.json"
OUT_MD     = OUT_DIR / "quality_report.md"

CONTENT_FIELDS = [
    "overview", "symptoms", "causes",
    "risk_factors", "prevention", "when_to_see_doc",
    "treatment", "prognosis", "complications", "exams_and_tests",
]

FIELD_LABELS = {
    "overview":        "Tổng quan",
    "symptoms":        "Triệu chứng",
    "causes":          "Nguyên nhân",
    "risk_factors":    "Yếu tố nguy cơ",
    "prevention":      "Phòng ngừa",
    "when_to_see_doc": "Khi nào gặp bác sĩ",
    "treatment":       "Điều trị",
    "prognosis":       "Tiên lượng",
    "complications":   "Biến chứng",
    "exams_and_tests": "Xét nghiệm/Khám",
}

# Regex phát hiện tiếng Anh còn sót trong field tiếng Việt
ENGLISH_PATTERN = re.compile(
    r'\b(the|and|or|is|are|was|were|have|has|with|that|this|for|from|by|an|a)\b',
    re.IGNORECASE
)

MOJIBAKE_PATTERN = re.compile(
    r'Ã[©°¡-ÿ]|â€[™œ•–—]|Â[«»°²³µ]',
    re.IGNORECASE,
)


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def wc(text: str) -> int:
    return len(text.split()) if text else 0


def has_english_remnant(text: str) -> bool:
    """Phát hiện text tiếng Việt còn sót tiếng Anh đáng kể."""
    if not text or len(text) < 20:
        return False
    matches = ENGLISH_PATTERN.findall(text)
    # Nếu > 15% từ là tiếng Anh → coi là còn sót
    total = len(text.split())
    return total > 0 and len(matches) / total > 0.15


def is_disease_translated(record: dict) -> str:
    """Kiểm tra trạng thái dịch của record."""
    disease_en = record.get("disease_en", "")
    disease_vi = record.get("disease", "")

    if not disease_en or disease_en == disease_vi:
        return "not_translated"   # tên bệnh không được dịch

    # Kiểm tra nội dung field có còn tiếng Anh không
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
    """Section 1: Phân tích chất lượng dịch thuật."""
    status_counts = Counter(is_disease_translated(r) for r in records)
    total = len(records)
    return {
        "total_records":      total,
        "fully_translated":   status_counts.get("fully_translated", 0),
        "partial_english":    status_counts.get("partial_english", 0),
        "mostly_english":     status_counts.get("mostly_english", 0),
        "not_translated":     status_counts.get("not_translated", 0),
        "no_content":         status_counts.get("no_content", 0),
        "pct_fully_translated": round(status_counts.get("fully_translated", 0) / total * 100, 1),
        "pct_issues":         round((total - status_counts.get("fully_translated", 0) - status_counts.get("no_content", 0)) / total * 100, 1),
    }


def analyze_encoding(records: list[dict]) -> dict:
    """Section 2: Phân tích lỗi encoding."""
    total = len(records)
    encoding_errors = 0
    fields_with_errors: Counter = Counter()

    for rec in records:
        has_error = False
        for field in CONTENT_FIELDS:
            val = rec.get(field, "") or ""
            if MOJIBAKE_PATTERN.search(val):
                fields_with_errors[field] += 1
                has_error = True
        if has_error:
            encoding_errors += 1

    return {
        "total_records":         total,
        "records_with_encoding_errors": encoding_errors,
        "pct_encoding_errors":   round(encoding_errors / total * 100, 2),
        "fields_error_counts":   dict(fields_with_errors.most_common()),
        "encoding_health":       "Tốt" if encoding_errors / total < 0.02 else
                                 "Cần xem xét" if encoding_errors / total < 0.1 else "Cần xử lý",
    }


def analyze_field_completeness(records: list[dict]) -> dict:
    """Section 3: Phân tích độ hoàn chỉnh từng field."""
    total = len(records)
    fields_stats = {}

    for field in CONTENT_FIELDS:
        empty   = sum(1 for r in records if not (r.get(field, "") or "").strip())
        sparse  = sum(1 for r in records if 0 < wc(r.get(field, "") or "") < 10)
        filled  = sum(1 for r in records if wc(r.get(field, "") or "") >= 10)
        avg_wc  = sum(wc(r.get(field, "") or "") for r in records) / total

        fields_stats[field] = {
            "label":      FIELD_LABELS.get(field, field),
            "empty":      empty,
            "sparse":     sparse,
            "filled":     filled,
            "pct_filled": round(filled / total * 100, 1),
            "avg_words":  round(avg_wc, 1),
            "quality":    "Tốt" if filled / total >= 0.7 else
                          "Trung bình" if filled / total >= 0.4 else "Kém",
        }

    # Tỷ lệ bản ghi hoàn chỉnh (có đủ 6 field quan trọng)
    key_fields = ["overview", "symptoms", "causes", "treatment", "complications", "prognosis"]
    complete = sum(
        1 for r in records
        if all(wc(r.get(f, "") or "") >= 5 for f in key_fields)
    )

    return {
        "total_records":   total,
        "complete_records": complete,
        "pct_complete":    round(complete / total * 100, 1),
        "fields":          fields_stats,
    }


def analyze_duplicates(records: list[dict], merged_path: pathlib.Path) -> dict:
    """Section 4: Phân tích trùng lặp."""
    # Exact duplicate names
    names = [r.get("disease", "").lower().strip() for r in records]
    name_counts = Counter(names)
    exact_dups = {k: v for k, v in name_counts.items() if v > 1}

    # Conflict fields từ merged.json
    conflict_count = 0
    total_conflict_fields = 0
    if merged_path.exists():
        with open(merged_path, encoding="utf-8") as f:
            merged = json.load(f)
        conflict_count = sum(1 for r in merged if r.get("conflict_fields"))
        total_conflict_fields = sum(len(r.get("conflict_fields", [])) for r in merged)

    # Source distribution
    source_counts = Counter(r.get("source", "unknown") for r in records)

    return {
        "total_records":         len(records),
        "exact_duplicates":      len(exact_dups),
        "duplicate_names":       list(exact_dups.keys())[:20],  # Top 20
        "source_distribution":   dict(source_counts),
        "conflict_records":      conflict_count,
        "total_conflict_fields": total_conflict_fields,
    }


def analyze_icd_coverage(records: list[dict]) -> dict:
    """Section 5: Phân tích độ bao phủ ICD-10."""
    total = len(records)
    with_icd = sum(1 for r in records if r.get("icd_code", ""))
    without_icd = total - with_icd

    # Phân bố theo chapter ICD (ký tự đầu)
    chapter_map = {
        "A": "Bệnh nhiễm khuẩn & ký sinh trùng",
        "B": "Bệnh nhiễm khuẩn & virus",
        "C": "Ung thư",
        "D": "U lành & rối loạn máu",
        "E": "Nội tiết & chuyển hóa",
        "F": "Tâm thần & hành vi",
        "G": "Thần kinh",
        "H": "Mắt & Tai",
        "I": "Tim mạch",
        "J": "Hô hấp",
        "K": "Tiêu hóa",
        "L": "Da liễu",
        "M": "Cơ xương khớp",
        "N": "Sinh dục & tiết niệu",
        "O": "Thai sản",
        "Q": "Dị tật bẩm sinh",
    }
    chapter_counts: Counter = Counter()
    for r in records:
        code = r.get("icd_code", "")
        if code:
            ch = code[0].upper()
            chapter_counts[ch] += 1

    chapter_dist = {
        f"{ch} – {chapter_map.get(ch, 'Khác')}": cnt
        for ch, cnt in chapter_counts.most_common()
    }

    return {
        "total_records":    total,
        "with_icd":         with_icd,
        "without_icd":      without_icd,
        "icd_coverage_pct": round(with_icd / total * 100, 1),
        "chapter_distribution": chapter_dist,
        "coverage_quality": "Tốt" if with_icd / total >= 0.6 else
                            "Trung bình" if with_icd / total >= 0.3 else "Cần cải thiện",
    }


def analyze_categories(records: list[dict]) -> dict:
    """Section 6: Phân bố theo nhóm bệnh và các flags."""
    total = len(records)
    cat_counts    = Counter(r.get("disease_category", "Khác") for r in records)
    type_counts   = Counter(r.get("disease_type", "Không xác định") for r in records)
    contagious    = Counter(r.get("is_contagious", "Không xác định") for r in records)
    severity      = Counter(r.get("severity_level", "Trung bình") for r in records)
    demographic   = Counter(r.get("target_demographic", "Người lớn") for r in records)
    richness      = Counter(r.get("content_richness", "") for r in records)

    def to_pct(counts: Counter) -> dict:
        return {
            k: {"count": v, "pct": round(v / total * 100, 1)}
            for k, v in counts.most_common()
        }

    return {
        "total_records":       total,
        "category_distribution": to_pct(cat_counts),
        "disease_type":          to_pct(type_counts),
        "contagious_status":     to_pct(contagious),
        "severity_distribution": to_pct(severity),
        "demographic":           to_pct(demographic),
        "content_richness":      to_pct(richness),
    }


# =============================================================================
# MARKDOWN REPORT GENERATOR
# =============================================================================

def generate_markdown(report: dict) -> str:
    ts = report["generated_at"]
    s1 = report["translation_quality"]
    s2 = report["encoding_quality"]
    s3 = report["field_completeness"]
    s4 = report["duplicate_summary"]
    s5 = report["icd_coverage"]
    s6 = report["category_distribution"]

    lines = [
        f"# 📊 Báo Cáo Chất Lượng Dữ Liệu Y Tế",
        f"",
        f"> **Thời gian tạo:** {ts}  ",
        f"> **Tổng bản ghi:** {s1['total_records']:,}  ",
        f"> **Nguồn dữ liệu:** Mayo Clinic + MedlinePlus",
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
        f"| **Tổng vấn đề dịch** | - | **{s1['pct_issues']}%** |",
        f"",
        f"---",
        f"",
        f"## 2. 🔤 Chất Lượng Encoding",
        f"",
        f"- **Bản ghi lỗi encoding:** {s2['records_with_encoding_errors']:,} / {s2['total_records']:,} ({s2['pct_encoding_errors']}%)",
        f"- **Đánh giá:** {s2['encoding_health']}",
        f"",
    ]

    if s2["fields_error_counts"]:
        lines += ["| Field | Số lỗi |", "|-------|--------|"]
        for fld, cnt in s2["fields_error_counts"].items():
            lines.append(f"| {fld} | {cnt} |")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## 3. 📋 Độ Hoàn Chỉnh Từng Field",
        f"",
        f"- **Bản ghi hoàn chỉnh (≥6 field):** {s3['complete_records']:,} / {s3['total_records']:,} ({s3['pct_complete']}%)",
        f"",
        f"| Field | Tỷ lệ điền | Avg từ | Đánh giá |",
        f"|-------|-----------|--------|---------|",
    ]
    for fld, stats in s3["fields"].items():
        lines.append(f"| {stats['label']} | {stats['pct_filled']}% | {stats['avg_words']} | {stats['quality']} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 4. 🔁 Trùng Lặp & Xung Đột",
        f"",
        f"| Chỉ số | Giá trị |",
        f"|--------|---------|",
        f"| Tổng bản ghi | {s4['total_records']:,} |",
        f"| Trùng lặp exact | {s4['exact_duplicates']:,} |",
        f"| Bản ghi có xung đột nguồn | {s4['conflict_records']:,} |",
        f"| Tổng field xung đột | {s4['total_conflict_fields']:,} |",
        f"",
        f"**Phân bố theo nguồn:**",
    ]
    for src, cnt in s4["source_distribution"].items():
        lines.append(f"- {src}: {cnt:,}")

    lines += [
        f"",
        f"---",
        f"",
        f"## 5. 🏥 Độ Bao Phủ ICD-10",
        f"",
        f"- **Có mã ICD:** {s5['with_icd']:,} / {s5['total_records']:,} (**{s5['icd_coverage_pct']}%**)",
        f"- **Đánh giá:** {s5['coverage_quality']}",
        f"",
        f"**Phân bố theo chapter ICD:**",
        f"",
        f"| Chapter | Số lượng |",
        f"|---------|---------|",
    ]
    for ch, cnt in s5["chapter_distribution"].items():
        lines.append(f"| {ch} | {cnt:,} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 6. 🗂️ Phân Bố Nhóm Bệnh",
        f"",
        f"| Nhóm bệnh | Số lượng | Tỷ lệ |",
        f"|----------|---------|-------|",
    ]
    for cat, data in s6["category_distribution"].items():
        lines.append(f"| {cat} | {data['count']:,} | {data['pct']}% |")

    lines += [
        f"",
        f"**Phân loại mãn tính / cấp tính:**",
        f"",
    ]
    for t, data in s6["disease_type"].items():
        lines.append(f"- {t}: {data['count']:,} ({data['pct']}%)")

    lines += [
        f"",
        f"**Tình trạng lây nhiễm:**",
        f"",
    ]
    for c, data in s6["contagious_status"].items():
        lines.append(f"- {c}: {data['count']:,} ({data['pct']}%)")

    lines += [
        f"",
        f"---",
        f"",
        f"*Báo cáo được tạo tự động bởi `quality_report.py`*",
    ]

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def run():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    data_file = DISCRETIZED_FILE if DISCRETIZED_FILE.exists() else TRANSLATED_FILE
    log.info(f"Loading {data_file} …")
    with open(data_file, encoding="utf-8") as f:
        records = json.load(f)
    log.info(f"  {len(records)} records")

    # Run all 6 analyses
    log.info("Analyzing translation quality…")
    s1 = analyze_translation(records)

    log.info("Analyzing encoding quality…")
    s2 = analyze_encoding(records)

    log.info("Analyzing field completeness…")
    s3 = analyze_field_completeness(records)

    log.info("Analyzing duplicates…")
    s4 = analyze_duplicates(records, MERGED_FILE)

    log.info("Analyzing ICD coverage…")
    s5 = analyze_icd_coverage(records)

    log.info("Analyzing category distribution…")
    s6 = analyze_categories(records)

    # Reduction report (if available)
    reduction = {}
    if REDUCTION_REPORT.exists():
        with open(REDUCTION_REPORT, encoding="utf-8") as f:
            reduction = json.load(f)

    report = {
        "generated_at":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source":           str(data_file.name),
        "translation_quality":   s1,
        "encoding_quality":      s2,
        "field_completeness":    s3,
        "duplicate_summary":     s4,
        "icd_coverage":          s5,
        "category_distribution": s6,
        "reduction_summary":     reduction,
    }

    # Save JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log.info(f"Saved JSON  → {OUT_JSON}")

    # Save Markdown
    md = generate_markdown(report)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    log.info(f"Saved MD    → {OUT_MD}")

    # Console summary
    log.info("─" * 60)
    log.info(f"✅ Dịch hoàn toàn    : {s1['pct_fully_translated']}%")
    log.info(f"🔤 Lỗi encoding      : {s2['pct_encoding_errors']}%")
    log.info(f"📋 Hoàn chỉnh fields : {s3['pct_complete']}%")
    log.info(f"🔁 Trùng lặp exact   : {s4['exact_duplicates']}")
    log.info(f"🏥 ICD coverage      : {s5['icd_coverage_pct']}%")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()
