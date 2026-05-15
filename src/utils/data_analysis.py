"""
data_analysis.py – Thống kê & biểu đồ bộ dữ liệu medical_vi.csv
===============================================================
Input : data/processed/discretized.json
Output: image/processed/ (các file PNG)
Sử dụng logic chuẩn từ shared_metrics.py
"""

import json, re, pathlib, logging
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib import rcParams
import pandas as pd
import seaborn as sns

from shared_metrics import CONTENT_FIELDS, FIELD_LABELS_VI, wc, wc_total, assign_organ_systems

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("data_analysis")

ROOT = pathlib.Path(__file__).parent.parent.parent
INPUT_FILE = ROOT / "data/processed/discretized.json"
OUT_DIR = ROOT / "image/processed"
OUT_DIR.mkdir(exist_ok=True, parents=True)

# Palette sang trọng
C = {
    "blue":   "#2B5B84",
    "sky":    "#378ADD",
    "green":  "#1D9E75",
    "coral":  "#D85A30",
    "purple": "#7F77DD",
    "amber":  "#D99A29",
    "gray":   "#888780",
    "teal":   "#0F6E56",
}

sns.set_theme(style="whitegrid", rc={
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "grid.alpha":        0.3,
    "grid.linestyle":    "--",
    "axes.titlesize":    14,
    "axes.titleweight":  "bold",
    "axes.titlepad":     15,
    "axes.labelsize":    11,
    "figure.dpi":        150,
})

STOPWORDS_VI = {
    "và","của","là","có","các","được","trong","với","này","một","cho","đến",
    "không","bạn","khi","như","thể","những","từ","cũng","sau","nếu","hoặc",
    "theo","do","vì","tại","ra","về","lên","đã","sẽ","mà","người","thường",
    "bao","gồm","triệu","chứng","bệnh","hay","rất","cần","hoặc","đây","đó",
    "còn","nên","phải","đặc","khác","thêm","qua","dưới","trên","bởi","giữa",
    "nhiều","ít","rất","hơn","nhất","mỗi","cùng","luôn","thường","chỉ",
    "ngay","lúc","khi","vậy","tuy","nhiên","hội","chứng","phần","lớn",
    "bình","thường","thấy","được","dùng","dụng","thành","giúp","điều",
    "kiện","năng","tính","sinh","phát","triển","trưởng","giai","đoạn",
    "nhân","tế","bào","mạch","máu","cơ","thể","vùng","vấn","đề","loại",
    "nhóm","mức","độ","dấu","hiệu","liên","quan","thực","hiện","biểu","hiện",
}

def load():
    log.info(f"Loading {INPUT_FILE} ...")
    if not INPUT_FILE.exists():
        log.error("File discretized.json không tồn tại!")
        return []
    with open(INPUT_FILE, encoding="utf-8") as f:
        rows = json.load(f)
    log.info(f"  {len(rows)} records")
    return rows

def save(fig, name):
    p = OUT_DIR / name
    fig.savefig(p, bbox_inches='tight', pad_inches=0.2)
    plt.close(fig)
    log.info(f"  Saved → {p}")

def chart_overview(rows):
    log.info("Chart 1: Tổng quan...")
    total = len(rows)
    src_cnt = Counter(r["source"] for r in rows)
    
    # Một bản ghi được coi là hoàn chỉnh nếu 6 trường trọng yếu có >= 5 từ
    key_fields = ["symptoms","causes","treatment","prognosis","complications","exams_and_tests"]
    complete = sum(1 for r in rows if all(wc(r.get(f,"")) >= 5 for f in key_fields))
    
    total_words = sum(wc_total(r) for r in rows)
    avg_words = total_words / total if total else 0

    fig, axes = plt.subplots(2, 4, figsize=(14, 6))
    fig.suptitle("TỔNG QUAN BỘ DỮ LIỆU ĐÃ QUA TIỀN XỬ LÝ", fontsize=16, fontweight="bold", y=1.05)

    metrics = [
        ("Tổng bệnh",          f"{total:,}",          C["blue"]),
        ("MedlinePlus",        f"{src_cnt['medlineplus']:,}", C["green"]),
        ("Mayo Clinic",        f"{src_cnt['mayo']:,}",  C["coral"]),
        ("Cả 2 nguồn",         f"{src_cnt['both']:,}",  C["purple"]),
        ("Tổng từ (tất cả)",   f"{total_words/1e6:.2f}M", C["teal"]),
        ("Avg từ/bệnh",        f"{avg_words:.0f}",      C["amber"]),
        ("Đầy đủ 6 fields lõi",f"{complete:,}",         C["gray"]),
        ("Tỉ lệ hoàn chỉnh",   f"{complete/total*100:.1f}%", C["sky"]),
    ]

    for ax, (label, val, col) in zip(axes.flat, metrics):
        ax.set_facecolor(col + "15") # 15% opacity
        ax.text(0.5, 0.62, val,  ha="center", va="center",
                fontsize=24, fontweight="bold", color=col, transform=ax.transAxes)
        ax.text(0.5, 0.28, label, ha="center", va="center",
                fontsize=11, color="#444", transform=ax.transAxes)
        for spine in ax.spines.values():
            spine.set_edgecolor(col + "55")
            spine.set_linewidth(1.5)
            spine.set_visible(True)
        ax.set_xticks([]); ax.set_yticks([])
        ax.grid(False)

    plt.tight_layout()
    save(fig, "1_overview.png")

def chart_sources(rows):
    log.info("Chart 2: Phân bố nguồn...")
    src_cnt = Counter(r["source"] for r in rows)
    src_wc  = defaultdict(list)
    for r in rows:
        src_wc[r["source"]].append(wc_total(r))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Donut
    labels = ["MedlinePlus", "Mayo Clinic", "Cả 2 nguồn"]
    sizes  = [src_cnt["medlineplus"], src_cnt["mayo"], src_cnt["both"]]
    colors = [C["sky"], C["coral"], C["green"]]
    
    wedges, _, autotexts = ax1.pie(
        sizes, colors=colors, autopct="%1.1f%%",
        startangle=140, pctdistance=0.78,
        explode=(0.02, 0.02, 0.05),
        wedgeprops={"linewidth": 2, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(10); at.set_fontweight("bold"); at.set_color("white")
    centre = plt.Circle((0,0), 0.55, fc="white")
    ax1.add_patch(centre)
    ax1.text(0, 0.08, f"{sum(sizes):,}", ha="center", fontsize=20, fontweight="bold", color="#333")
    ax1.text(0, -0.15, "Bệnh lý", ha="center", fontsize=12, color="#777")
    
    patches = [mpatches.Patch(color=colors[i], label=f"{labels[i]}: {sizes[i]:,}") for i in range(3)]
    ax1.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.5,-0.15), ncol=3, frameon=False)
    ax1.set_title("Phân bố theo nguồn", pad=20)

    # Avg word count
    src_order = ["medlineplus", "mayo", "both"]
    src_labels = ["MedlinePlus", "Mayo Clinic", "Giao thoa"]
    avgs = [sum(src_wc[s])/len(src_wc[s]) if src_wc[s] else 0 for s in src_order]
    
    bars = sns.barplot(x=src_labels, y=avgs, ax=ax2, palette=[C["sky"], C["coral"], C["green"]], alpha=0.9)
    for bar in bars.patches:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
                 f"{bar.get_height():.0f}", ha="center", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Số từ trung bình / Bệnh")
    ax2.set_title("Độ dài nội dung trung bình theo nguồn", pad=20)
    ax2.set_ylim(0, max(avgs) * 1.2)

    plt.tight_layout()
    save(fig, "2_sources.png")

def chart_field_coverage(rows):
    log.info("Chart 3: Field coverage...")
    total = len(rows)

    labels, fill_rates, avg_wcs = [], [], []
    for f in CONTENT_FIELDS:
        # Check field > 5 words
        filled = sum(1 for r in rows if wc(r.get(f, "")) >= 5)
        avg_w = sum(wc(r.get(f, "")) for r in rows) / total
        
        labels.append(FIELD_LABELS_VI[f])
        fill_rates.append(filled / total * 100)
        avg_wcs.append(avg_w)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Fill rate bar
    colors = [C["green"] if v >= 70 else C["amber"] if v >= 40 else C["coral"] for v in fill_rates]
    sns.barplot(x=fill_rates, y=labels, ax=ax1, palette=colors, alpha=0.9)
    for i, p in enumerate(ax1.patches):
        ax1.text(p.get_width() + 1, p.get_y() + p.get_height()/2, f"{fill_rates[i]:.1f}%", va="center", fontsize=10)
        
    ax1.set_xlim(0, 110)
    ax1.set_xlabel("Tỉ lệ điền hợp lệ (%)")
    ax1.set_title("Tỉ lệ điền theo trường dữ liệu (>= 5 từ)")
    ax1.axvline(70, color=C["green"], linestyle="--", alpha=0.5)
    ax1.axvline(40, color=C["amber"], linestyle="--", alpha=0.5)

    legend_els = [
        mpatches.Patch(color=C["green"], label="≥70% (Tốt)"),
        mpatches.Patch(color=C["amber"], label="40–70% (Trung bình)"),
        mpatches.Patch(color=C["coral"], label="<40% (Thưa thớt)"),
    ]
    ax1.legend(handles=legend_els, frameon=False, loc="lower right")

    # Avg word count
    sns.barplot(x=avg_wcs, y=labels, ax=ax2, color=C["sky"], alpha=0.8)
    for i, p in enumerate(ax2.patches):
        ax2.text(p.get_width() + 2, p.get_y() + p.get_height()/2, f"{avg_wcs[i]:.0f}", va="center", fontsize=10)
        
    ax2.set_xlabel("Số từ trung bình / Bệnh")
    ax2.set_title("Độ dài trung bình theo từng trường")

    plt.tight_layout()
    save(fig, "3_field_coverage.png")

def chart_discretization(rows):
    log.info("Chart 7: Discretization attributes...")
    if not rows or "disease_category" not in rows[0]:
        return

    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(2, 3, height_ratios=[1, 1], width_ratios=[1.5, 1, 1])
    
    # 1. Disease Categories
    ax1 = fig.add_subplot(gs[:, 0])
    cat_cnt = Counter(r.get("disease_category", "Khác") for r in rows)
    cats = sorted(cat_cnt.items(), key=lambda x: x[1], reverse=False)
    
    sns.barplot(x=[v for k, v in cats], y=[k for k, v in cats], ax=ax1, color=C["teal"], alpha=0.85)
    for p in ax1.patches:
        ax1.text(p.get_width() + 5, p.get_y() + p.get_height()/2, f"{p.get_width():.0f}", va="center", fontsize=10)
    ax1.set_title("Phân bố theo nhóm bệnh ICD-10")
    
    # 2. Severity Level
    ax2 = fig.add_subplot(gs[0, 1])
    sev_cnt = Counter(r.get("severity_level", "Trung bình") for r in rows)
    sev_order = ["Nhẹ", "Trung bình", "Nặng", "Đe dọa tính mạng"]
    sev_vals = [sev_cnt.get(s, 0) for s in sev_order]
    
    sns.barplot(x=sev_order, y=sev_vals, ax=ax2, palette=[C["green"], C["sky"], C["amber"], C["coral"]], alpha=0.9)
    for p in ax2.patches:
        ax2.text(p.get_x() + p.get_width()/2, p.get_height() + 5, f"{p.get_height():.0f}", ha="center", fontsize=10)
    ax2.set_title("Mức độ nghiêm trọng")
    ax2.tick_params(axis="x", rotation=15)
    
    # 3. Disease Type
    ax3 = fig.add_subplot(gs[0, 2])
    type_cnt = Counter(r.get("disease_type", "Không xác định") for r in rows)
    ax3.pie(type_cnt.values(), labels=type_cnt.keys(), autopct="%1.1f%%", startangle=90, 
            colors=[C["purple"], C["sky"], C["amber"], C["gray"]], wedgeprops={"edgecolor":"w"})
    ax3.set_title("Tính chất bệnh")
    
    # 4. Target Demographic
    ax4 = fig.add_subplot(gs[1, 1])
    demo_cnt = Counter(r.get("target_demographic", "Mọi lứa tuổi") for r in rows)
    ax4.pie(demo_cnt.values(), labels=demo_cnt.keys(), autopct="%1.1f%%", startangle=140, 
            colors=[C["sky"], C["green"], C["amber"], C["coral"]], wedgeprops={"edgecolor":"w"})
    ax4.set_title("Đối tượng mục tiêu")
    
    # 5. Contagious
    ax5 = fig.add_subplot(gs[1, 2])
    cont_cnt = Counter(r.get("is_contagious", "Không xác định") for r in rows)
    ax5.pie(cont_cnt.values(), labels=cont_cnt.keys(), autopct="%1.1f%%", startangle=90, 
            colors=[C["coral"], C["green"], C["gray"]], wedgeprops={"width":0.4, "edgecolor":"w"})
    ax5.set_title("Tính lây nhiễm")
    
    plt.tight_layout()
    save(fig, "7_discretization.png")

def chart_organ_analysis(rows):
    log.info("Chart 8-11: Organ Systems analysis (Multi-label)...")
    
    # Tạo list phẳng vì 1 bệnh có thể thuộc nhiều hệ cơ quan
    organ_records = []
    for r in rows:
        systems = assign_organ_systems(r.get("disease", ""))
        for sys in systems:
            organ_records.append({"system": sys, **r})
            
    df_organs = pd.DataFrame(organ_records)
    
    # 1. Phân bố hệ cơ quan
    sys_cnt = df_organs["system"].value_counts().sort_values(ascending=True)
    
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    bars = sns.barplot(x=sys_cnt.values, y=sys_cnt.index, color=C["blue"], alpha=0.85, ax=ax1)
    for p in ax1.patches:
        ax1.text(p.get_width() + 5, p.get_y() + p.get_height()/2, f"{p.get_width():.0f}", va="center")
    ax1.set_title("Tần suất xuất hiện theo Hệ Cơ Quan (Đa nhãn)", pad=15)
    ax1.set_xlabel("Số lượng lần gắn nhãn")
    save(fig1, "8_organ_system_distribution.png")

    # 2. Heatmap tỷ lệ điền field theo hệ cơ quan
    systems_list = sys_cnt.index[::-1].tolist()
    heatmap_data = []
    for sys in systems_list:
        sys_df = df_organs[df_organs["system"] == sys]
        sys_total = len(sys_df)
        row = {"Hệ Cơ Quan": sys}
        for f in CONTENT_FIELDS:
            # Field điền nếu có >= 5 từ
            filled = sum(1 for text in sys_df[f].fillna("") if wc(text) >= 5)
            row[FIELD_LABELS_VI[f]] = (filled / sys_total) * 100 if sys_total else 0
        heatmap_data.append(row)
        
    df_heat = pd.DataFrame(heatmap_data).set_index("Hệ Cơ Quan")
    
    fig2 = plt.figure(figsize=(14, 10))
    sns.heatmap(df_heat, annot=True, fmt=".0f", cmap="Blues", cbar_kws={'label': 'Tỷ lệ điền (%)'}, linewidths=.5)
    plt.title("Heatmap tỷ lệ dữ liệu hợp lệ (>= 5 từ) theo Hệ Cơ Quan", pad=15)
    plt.xticks(rotation=45, ha='right')
    save(fig2, "9_organ_field_heatmap.png")

    # 3. Stacked bar Severity
    sev_order = ["Nhẹ", "Trung bình", "Nặng", "Đe dọa tính mạng"]
    sev_colors = [C["green"], C["sky"], C["amber"], C["coral"]]
    
    df_sev = df_organs.groupby(["system", "severity_level"]).size().unstack(fill_value=0)
    # Reorder columns and rows
    df_sev = df_sev.reindex(columns=sev_order, fill_value=0).reindex(systems_list)
    
    fig3, ax3 = plt.subplots(figsize=(12, 8))
    df_sev.plot(kind="barh", stacked=True, ax=ax3, color=sev_colors, width=0.8, alpha=0.9)
    ax3.set_title("Mức độ nguy hiểm theo Hệ Cơ Quan", pad=15)
    ax3.set_xlabel("Số lượng lần gắn nhãn")
    ax3.set_ylabel("")
    ax3.legend(title="Mức độ", loc="lower right")
    save(fig3, "10_organ_severity_stacked.png")


def run():
    rows = load()
    if not rows: return
    log.info(f"Saving charts → {OUT_DIR}/")

    chart_overview(rows)
    chart_sources(rows)
    chart_field_coverage(rows)
    chart_discretization(rows)
    chart_organ_analysis(rows)

    pngs = list(OUT_DIR.glob("*.png"))
    log.info("─" * 55)
    log.info(f"✅ Xong! Saved to {OUT_DIR}/")

if __name__ == "__main__":
    run()