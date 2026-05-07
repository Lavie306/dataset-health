"""
raw_data_analysis.py – Phân tích và thống kê dữ liệu y tế thô (Raw Data)
========================================================================
Mục tiêu: Đánh giá chất lượng dữ liệu trước khi qua pipeline (Bước 0).
Giúp báo cáo Data Mining thấy rõ lý do vì sao cần tiền xử lý.

Đầu vào:
  - data/raw/mayo_full.json
  - data/raw/medlineplus_full.json
Đầu ra:
  - data/output/raw_data_report.md (Báo cáo chi tiết)
  - data/output/raw_data_stats.png (Biểu đồ minh họa)

Chạy lệnh:
  python src/utils/raw_data_analysis.py
"""

import json
import re
import pathlib
import logging
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("raw_analysis")

ROOT = pathlib.Path(__file__).parent.parent.parent
RAW_MAYO = ROOT / "data/raw/mayo_full.json"
RAW_MEDLINE = ROOT / "data/raw/medlineplus_full.json"
OUT_DIR = ROOT / "image/raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_PATH = OUT_DIR / "raw_data_report.md"
CHART_PATH = OUT_DIR / "raw_data_stats.png"

CONTENT_FIELDS = [
    "overview", "symptoms", "causes", "risk_factors",
    "prevention", "when_to_see_doc", "treatment",
    "prognosis", "complications", "exams_and_tests"
]

# Patterns để kiểm tra nhiễu (noise)
HTML_NOISE_PATTERN = re.compile(r"<[^>]+>|Enlarge image|Close|\[\d+\]")


def load_json(path):
    if not path.exists():
        log.warning(f"Không tìm thấy file: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Lỗi đọc file {path}: {e}")
        return []


def analyze_source(name, data):
    total = len(data)
    if total == 0:
        return None

    names = [str(r.get("disease", "")).strip().lower() for r in data]
    unique_names = set(n for n in names if n)
    duplicates = total - len(unique_names)

    field_fill_counts = {f: 0 for f in CONTENT_FIELDS}
    noise_count = 0
    total_words = 0
    word_counts = []

    for r in data:
        has_noise = False
        record_words = 0
        for f in CONTENT_FIELDS:
            val = r.get(f, "")
            if val and isinstance(val, str) and len(val.strip()) > 5:
                field_fill_counts[f] += 1
                w_count = len(val.split())
                total_words += w_count
                record_words += w_count
                if HTML_NOISE_PATTERN.search(val):
                    has_noise = True
        word_counts.append(record_words)
        if has_noise:
            noise_count += 1

    return {
        "name": name,
        "total": total,
        "duplicates": duplicates,
        "noise_count": noise_count,
        "noise_pct": round(noise_count / total * 100, 1),
        "total_words": total_words,
        "avg_words": round(total_words / total, 1) if total > 0 else 0,
        "word_counts": word_counts,
        "field_fill": field_fill_counts,
        "field_fill_pct": {f: round(c / total * 100, 1) for f, c in field_fill_counts.items()}
    }


def plot_stats(mayo_stats, med_stats):
    # 1. Bar chart: Tổng quan lỗi/trùng lặp
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    labels = ["Tổng bản ghi", "Trùng lặp tên", "Bản ghi chứa nhiễu (Noise)"]
    
    mayo_vals = [mayo_stats["total"], mayo_stats["duplicates"], mayo_stats["noise_count"]]
    med_vals = [med_stats["total"], med_stats["duplicates"], med_stats["noise_count"]]
    
    x = range(len(labels))
    width = 0.35

    ax1.bar([i - width/2 for i in x], mayo_vals, width, label='Mayo Clinic', color="#D85A30", alpha=0.8)
    ax1.bar([i + width/2 for i in x], med_vals, width, label='MedlinePlus', color="#378ADD", alpha=0.8)

    ax1.set_ylabel('Số lượng')
    ax1.set_title('Thống kê cơ bản Dữ liệu thô (Raw Data)', pad=15)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.legend()
    ax1.grid(axis='y', linestyle='--', alpha=0.3)
    
    fig1.tight_layout()
    fig1.savefig(OUT_DIR / "raw_1_overview_stats.png", dpi=150)
    plt.close(fig1)

    # 2. Line chart: Tỷ lệ điền dữ liệu
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    fields = [f.replace("_", " ").title() for f in CONTENT_FIELDS]
    mayo_fill = [mayo_stats["field_fill_pct"][f] for f in CONTENT_FIELDS]
    med_fill = [med_stats["field_fill_pct"][f] for f in CONTENT_FIELDS]

    ax2.plot(fields, mayo_fill, marker='o', label='Mayo Clinic', color="#D85A30", linewidth=2)
    ax2.plot(fields, med_fill, marker='s', label='MedlinePlus', color="#378ADD", linewidth=2)
    
    ax2.set_ylabel('Tỷ lệ có dữ liệu (%)')
    ax2.set_title('Mức độ đầy đủ của từng trường (Field Completeness)', pad=15)
    ax2.set_ylim(0, 105)
    ax2.tick_params(axis="x", rotation=45)
    ax2.legend()
    ax2.grid(axis='both', linestyle='--', alpha=0.3)
    
    fig2.tight_layout()
    fig2.savefig(OUT_DIR / "raw_2_field_completeness.png", dpi=150)
    plt.close(fig2)

    # 3. Boxplot: Phân bố độ dài văn bản (Word Count)
    fig3, ax3 = plt.subplots(figsize=(8, 6))
    data_to_plot = [mayo_stats["word_counts"], med_stats["word_counts"]]
    
    bp = ax3.boxplot(data_to_plot, patch_artist=True, showfliers=False) # Ẩn outlier để dễ nhìn
    colors = ["#D85A30", "#378ADD"]
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
        
    ax3.set_xticks([1, 2])
    ax3.set_xticklabels(['Mayo Clinic', 'MedlinePlus'])
    ax3.set_ylabel('Số từ (Word count)')
    ax3.set_title('Phân bố số từ trên mỗi bệnh lý (Đã ẩn các giá trị ngoại lai)', pad=15)
    ax3.grid(axis='y', linestyle='--', alpha=0.3)
    
    fig3.tight_layout()
    fig3.savefig(OUT_DIR / "raw_3_wordcount_boxplot.png", dpi=150)
    plt.close(fig3)

    # 4. Pie charts: Tỷ lệ nhiễu
    fig4, (ax4a, ax4b) = plt.subplots(1, 2, figsize=(10, 5))
    
    mayo_clean = mayo_stats["total"] - mayo_stats["noise_count"]
    ax4a.pie([mayo_clean, mayo_stats["noise_count"]], labels=['Sạch', 'Chứa nhiễu HTML'], 
             autopct='%1.1f%%', startangle=90, colors=["#2ecc71", "#e74c3c"])
    ax4a.set_title(f'Mayo Clinic ({mayo_stats["total"]} bản ghi)')
    
    med_clean = med_stats["total"] - med_stats["noise_count"]
    ax4b.pie([med_clean, med_stats["noise_count"]], labels=['Sạch', 'Chứa nhiễu HTML'], 
             autopct='%1.1f%%', startangle=90, colors=["#2ecc71", "#e74c3c"])
    ax4b.set_title(f'MedlinePlus ({med_stats["total"]} bản ghi)')
    
    fig4.suptitle('Tỷ lệ bản ghi chứa nhiễu (HTML Tags/Rác)', fontsize=14, y=1.05)
    fig4.tight_layout()
    fig4.savefig(OUT_DIR / "raw_4_noise_ratio.png", dpi=150)
    plt.close(fig4)

    log.info("Đã lưu 4 biểu đồ Raw Data vào thư mục " + str(OUT_DIR))


def generate_markdown(mayo, med):
    lines = [
        "# 📊 Báo Cáo Phân Tích Dữ Liệu Thô (Raw Data Analysis)",
        "",
        "> Báo cáo này thống kê tình trạng dữ liệu ngay sau khi thu thập (Crawl) từ Mayo Clinic và MedlinePlus, trước khi đưa vào hệ thống Tiền xử lý (Preprocessing).",
        "",
        "## 1. Số liệu tổng quan",
        "",
        "| Chỉ số | Mayo Clinic | MedlinePlus | Tổng cộng |",
        "|--------|-------------|-------------|-----------|",
        f"| Tổng bản ghi cào được | **{mayo['total']:,}** | **{med['total']:,}** | **{(mayo['total'] + med['total']):,}** |",
        f"| Trùng lặp (cùng tên bệnh) | {mayo['duplicates']:,} | {med['duplicates']:,} | {(mayo['duplicates'] + med['duplicates']):,} |",
        f"| Bản ghi chứa nhiễu (Noise)* | {mayo['noise_count']:,} ({mayo['noise_pct']}%) | {med['noise_count']:,} ({med['noise_pct']}%) | - |",
        f"| Tổng số từ | {mayo['total_words']:,} | {med['total_words']:,} | {(mayo['total_words'] + med['total_words']):,} |",
        f"| Trung bình từ/bản ghi | {mayo['avg_words']} | {med['avg_words']} | - |",
        "",
        "*(Nhiễu bao gồm: dính thẻ HTML chưa xử lý hết, các text rác như 'Enlarge image', 'Close', citation marks).* ",
        "",
        "---",
        "",
        "## 2. Mức độ đầy đủ của các trường (Field Completeness)",
        "",
        "| Trường dữ liệu (Field) | Mayo Clinic (%) | MedlinePlus (%) |",
        "|------------------------|-----------------|-----------------|",
    ]

    for f in CONTENT_FIELDS:
        f_name = f.replace("_", " ").title()
        lines.append(f"| {f_name} | {mayo['field_fill_pct'][f]}% | {med['field_fill_pct'][f]}% |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Kết luận về tính cấp thiết của Tiền xử lý",
        "",
        "Qua các số liệu trên, ta thấy được các vấn đề rõ rệt của dữ liệu thô:",
        "1. **Nhiễu cấu trúc (Noise):** Dữ liệu thu thập từ HTML thường kèm theo text thừa của giao diện website. Cần thực hiện làm sạch (Data Cleaning).",
        "2. **Dữ liệu thưa thớt (Sparsity):** Có những trường tỷ lệ điền rất thấp (như Prognosis, Complications). Nếu để nguyên sẽ gây loãng dữ liệu. Cần chiến lược gộp hai nguồn để bổ sung cho nhau (Data Integration).",
        "3. **Dữ liệu trùng lặp (Duplication):** Các bệnh bị lưu trùng dưới nhiều URL. Cần hợp nhất (Data Reduction/Merge).",
        "",
        "*(Các biểu đồ tương ứng: `raw_1_overview_stats.png`, `raw_2_field_completeness.png`, `raw_3_wordcount_boxplot.png`, `raw_4_noise_ratio.png` được lưu cùng thư mục)*"
    ])

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log.info(f"Đã lưu báo cáo: {REPORT_PATH}")


def run():
    log.info("Bắt đầu phân tích dữ liệu thô...")
    
    mayo_data = load_json(RAW_MAYO)
    med_data = load_json(RAW_MEDLINE)

    if not mayo_data or not med_data:
        log.error("Không đủ dữ liệu thô để phân tích. Vui lòng kiểm tra lại data/raw/")
        return

    mayo_stats = analyze_source("Mayo Clinic", mayo_data)
    med_stats = analyze_source("MedlinePlus", med_data)

    plot_stats(mayo_stats, med_stats)
    generate_markdown(mayo_stats, med_stats)

    log.info("Phân tích hoàn tất!")

if __name__ == "__main__":
    run()
