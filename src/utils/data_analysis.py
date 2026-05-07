"""
analysis_vi.py – Thống kê & biểu đồ bộ dữ liệu medical_vi.csv
===============================================================
Input : medical_vi.csv  (đặt cùng thư mục hoặc chỉnh INPUT_FILE)
Output: charts/  (6 PNG files)

Cài đặt:
  pip install matplotlib wordcloud

Chạy:
  python analysis_vi.py
"""

import csv, re, pathlib, logging
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib import rcParams
import pandas as pd
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("analysis_vi")

# ── config ────────────────────────────────────────────────────────────────────
ROOT      = pathlib.Path(__file__).parent.parent.parent
INPUT_FILE = ROOT / "data/processed/discretized.json"
OUT_DIR    = ROOT / "image/processed"
OUT_DIR.mkdir(exist_ok=True)

CONTENT_FIELDS = [
    "overview", "symptoms", "causes", "risk_factors",
    "prevention", "when_to_see_doc", "treatment",
    "prognosis", "complications", "exams_and_tests",
]
FIELD_LABELS_VI = {
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

# Palette
C = {
    "blue":   "#378ADD",
    "green":  "#1D9E75",
    "coral":  "#D85A30",
    "purple": "#7F77DD",
    "amber":  "#BA7517",
    "gray":   "#888780",
    "teal":   "#0F6E56",
}

rcParams.update({
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.2,
    "grid.linestyle":    "--",
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.titlepad":     14,
    "axes.labelsize":    11,
    "xtick.labelsize":   10,
    "ytick.labelsize":   10,
    "figure.dpi":        150,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.25,
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

# ── ORGAN MAPPING ────────────────────────────────────────────────────────────
ORGAN_MAPPING = [
    {"system": "Hệ tuần hoàn", "keywords": ["tim", "mạch vành", "cơ tim", "huyết áp", "động mạch", "tĩnh mạch", "nhồi máu", "máu", "bạch cầu", "hồng cầu", "thiếu máu", "huyết khối"]},
    {"system": "Hệ hô hấp", "keywords": ["phổi", "hô hấp", "phế quản", "hen suyễn", "lao", "tràn dịch", "viêm xoang", "thanh quản"]},
    {"system": "Hệ tiêu hóa", "keywords": ["gan", "viêm gan", "xơ gan", "mật", "dạ dày", "bao tử", "tá tràng", "tiêu hóa", "ruột", "đại tràng", "trĩ", "tụy", "túi mật", "đường mật", "răng", "nướu", "nha chu", "miệng", "viêm lợi"]},
    {"system": "Hệ bài tiết", "keywords": ["thận", "tiết niệu", "bàng quang", "niệu đạo", "sỏi niệu"]},
    {"system": "Hệ thần kinh", "keywords": ["não", "thần kinh", "đột quỵ", "chứng mất trí", "alzheimer", "động kinh", "parkinson", "chóng mặt"]},
    {"system": "Hệ vận động", "keywords": ["xương", "khớp", "cột sống", "thoái hóa khớp", "loãng xương", "gút", "cơ", "dây chằng"]},
    {"system": "Hệ vỏ bọc", "keywords": ["da", "viêm da", "vảy nến", "hắc lào", "lang ben", "mụn", "mề đay", "nấm"]},
    {"system": "Hệ nội tiết", "keywords": ["tuyến giáp", "cường giáp", "suy giáp", "đái tháo đường", "tiểu đường", "nội tiết"]},
    {"system": "Hệ sinh sản", "keywords": ["tử cung", "buồng trứng", "âm đạo", "kinh nguyệt", "phụ khoa", "vú", "mang thai", "tiền liệt", "tinh hoàn", "dương vật", "nam khoa", "tinh trùng"]},
    {"system": "Cơ quan cảm giác", "keywords": ["mắt", "thị giác", "giác mạc", "võng mạc", "thủy tinh thể", "đục", "cườm", "lác", "tai", "mũi", "họng"]},
    {"system": "Hệ miễn dịch", "keywords": ["miễn dịch", "bạch huyết", "hạch", "lách", "lupus", "hiv", "aids", "tự miễn"]},
]

def assign_organ_system(disease_name):
    name_lower = str(disease_name).lower()
    for o in ORGAN_MAPPING:
        if any(kw in name_lower for kw in o["keywords"]):
            return o["system"]
    return "Khác"

# =============================================================================
# LOAD
# =============================================================================
def load():
    log.info(f"Loading {INPUT_FILE} ...")
    import json
    with open(INPUT_FILE, encoding="utf-8") as f:
        rows = json.load(f)
    log.info(f"  {len(rows)} records")
    return rows


def wc_total(r):
    return sum(len((r.get(f,"") or "").split()) for f in CONTENT_FIELDS)


def save(fig, name):
    p = OUT_DIR / name
    fig.savefig(p)
    plt.close(fig)
    log.info(f"  Saved → {p}")


# =============================================================================
# CHART 1 – Tổng quan dataset (metric summary)
# =============================================================================
def chart_overview(rows):
    log.info("Chart 1: Tổng quan...")
    total   = len(rows)
    src_cnt = Counter(r["source"] for r in rows)
    complete = sum(1 for r in rows
                   if all((r.get(f,"") or "").strip()
                          for f in ["symptoms","causes","treatment","prognosis","complications","exams_and_tests"]))
    total_words = sum(wc_total(r) for r in rows)
    avg_words   = total_words / total

    fig, axes = plt.subplots(2, 4, figsize=(14, 6))
    fig.suptitle("Tổng quan bộ dữ liệu medical_vi.csv", fontsize=14, fontweight="bold", y=1.01)

    metrics = [
        ("Tổng bệnh",          f"{total:,}",          C["blue"]),
        ("MedlinePlus",        f"{src_cnt['medlineplus']:,}", C["green"]),
        ("Mayo Clinic",        f"{src_cnt['mayo']:,}",  C["coral"]),
        ("Cả 2 nguồn",         f"{src_cnt['both']:,}",  C["purple"]),
        ("Tổng từ (tất cả)",   f"{total_words/1e6:.2f}M", C["teal"]),
        ("Avg từ/bệnh",        f"{avg_words:.0f}",      C["amber"]),
        ("Đầy đủ 6 fields",    f"{complete:,}",         C["gray"]),
        ("Tỉ lệ hoàn chỉnh",   f"{complete/total*100:.1f}%", C["blue"]),
    ]

    for ax, (label, val, col) in zip(axes.flat, metrics):
        ax.set_facecolor(col + "18")
        ax.text(0.5, 0.62, val,  ha="center", va="center",
                fontsize=22, fontweight="bold", color=col, transform=ax.transAxes)
        ax.text(0.5, 0.28, label, ha="center", va="center",
                fontsize=10, color="#555", transform=ax.transAxes)
        for spine in ax.spines.values():
            spine.set_edgecolor(col + "55")
        ax.set_xticks([]); ax.set_yticks([])
        ax.grid(False)

    plt.tight_layout()
    save(fig, "1_overview.png")


# =============================================================================
# CHART 2 – Phân bố nguồn
# =============================================================================
def chart_sources(rows):
    log.info("Chart 2: Phân bố nguồn...")
    src_cnt = Counter(r["source"] for r in rows)
    src_wc  = defaultdict(list)
    for r in rows:
        src_wc[r["source"]].append(wc_total(r))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Donut
    labels = ["MedlinePlus\nonly", "Mayo Clinic\nonly", "Cả 2 nguồn"]
    sizes  = [src_cnt["medlineplus"], src_cnt["mayo"], src_cnt["both"]]
    colors = [C["blue"], C["coral"], C["green"]]
    wedges, _, autotexts = ax1.pie(
        sizes, colors=colors, autopct="%1.1f%%",
        startangle=140, pctdistance=0.78,
        explode=(0.02,0.02,0.06),
        wedgeprops={"linewidth":2,"edgecolor":"white"},
    )
    for at in autotexts:
        at.set_fontsize(10); at.set_fontweight("bold"); at.set_color("white")
    centre = plt.Circle((0,0), 0.55, fc="white")
    ax1.add_patch(centre)
    ax1.text(0, 0.08, f"{sum(sizes):,}", ha="center", fontsize=18, fontweight="bold")
    ax1.text(0, -0.15, "bệnh", ha="center", fontsize=11, color="#888")
    patches = [mpatches.Patch(color=colors[i], label=f"{labels[i]}: {sizes[i]:,}")
               for i in range(3)]
    ax1.legend(handles=patches, loc="lower center",
               bbox_to_anchor=(0.5,-0.13), ncol=1, frameon=False, fontsize=9)
    ax1.set_title("Phân bố theo nguồn")

    # Avg word count by source
    src_order = ["medlineplus","mayo","both"]
    src_labels = ["MedlinePlus", "Mayo", "Cả 2"]
    avgs = [sum(src_wc[s])/len(src_wc[s]) for s in src_order]
    bars = ax2.bar(src_labels, avgs, color=[C["blue"],C["coral"],C["green"]],
                   alpha=0.88, width=0.5)
    for bar, val in zip(bars, avgs):
        ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+8,
                 f"{val:.0f}", ha="center", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Số từ trung bình")
    ax2.set_title("Độ dài nội dung trung bình theo nguồn")
    ax2.set_ylim(0, max(avgs)*1.2)

    plt.tight_layout()
    save(fig, "2_sources.png")


# =============================================================================
# CHART 3 – Field coverage
# =============================================================================
def chart_field_coverage(rows):
    log.info("Chart 3: Field coverage...")
    total = len(rows)

    labels, fill_rates, avg_wcs = [], [], []
    for f in CONTENT_FIELDS:
        filled = sum(1 for r in rows if (r.get(f,"") or "").strip())
        avg_w  = sum(len((r.get(f,"") or "").split()) for r in rows) / total
        labels.append(FIELD_LABELS_VI[f])
        fill_rates.append(filled / total * 100)
        avg_wcs.append(avg_w)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Fill rate bar
    colors = [C["blue"] if v >= 70 else C["amber"] if v >= 40 else C["coral"]
              for v in fill_rates]
    bars = ax1.barh(labels, fill_rates, color=colors, height=0.65, alpha=0.88)
    for bar, val in zip(bars, fill_rates):
        ax1.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
                 f"{val:.1f}%", va="center", fontsize=9)
    ax1.set_xlim(0, 115)
    ax1.set_xlabel("Tỉ lệ điền (%)")
    ax1.set_title("Tỉ lệ điền theo field")
    ax1.axvline(70, color=C["blue"],  linestyle="--", alpha=0.4, linewidth=1)
    ax1.axvline(40, color=C["amber"], linestyle="--", alpha=0.4, linewidth=1)
    ax1.grid(axis="y", alpha=0)

    legend_els = [
        mpatches.Patch(color=C["blue"],  label="≥70% (tốt)"),
        mpatches.Patch(color=C["amber"], label="40–70% (trung bình)"),
        mpatches.Patch(color=C["coral"], label="<40% (thiếu)"),
    ]
    ax1.legend(handles=legend_els, frameon=False, fontsize=9,
               loc="lower right")

    # Avg word count per field
    bars2 = ax2.barh(labels, avg_wcs, color=C["purple"], height=0.65, alpha=0.8)
    for bar, val in zip(bars2, avg_wcs):
        ax2.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
                 f"{val:.0f}", va="center", fontsize=9)
    ax2.set_xlabel("Số từ trung bình / bệnh")
    ax2.set_title("Độ dài trung bình theo field (từ/bệnh)")
    ax2.grid(axis="y", alpha=0)

    plt.tight_layout()
    save(fig, "3_field_coverage.png")


# =============================================================================
# CHART 4 – Phân bố số từ tổng
# =============================================================================
def chart_wordcount_dist(rows):
    log.info("Chart 4: Phân bố số từ...")
    wcs = [wc_total(r) for r in rows]

    bin_edges  = [0, 100, 300, 500, 800, 1200, 1700, 9999]
    bin_labels = ["<100","100–300","300–500","500–800","800–1200","1200–1700",">1700"]
    counts = [0]*len(bin_labels)
    for w in wcs:
        for i in range(len(bin_edges)-1):
            if bin_edges[i] <= w < bin_edges[i+1]:
                counts[i] += 1; break

    # Màu gradient
    grad = ["#B5D4F4","#85B7EB","#378ADD","#185FA5","#0C447C","#085041","#04342C"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    bars = ax1.bar(bin_labels, counts, color=grad, alpha=0.9, edgecolor="white", linewidth=0.8)
    for bar, val in zip(bars, counts):
        ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5,
                 str(val), ha="center", fontsize=9, fontweight="bold")
    ax1.set_xlabel("Tổng số từ / bệnh")
    ax1.set_ylabel("Số bệnh")
    ax1.set_title("Phân bố độ dài nội dung (tổng từ/bệnh)")
    ax1.tick_params(axis="x", rotation=20)

    # Box plot theo source
    src_data = defaultdict(list)
    for r in rows:
        src_data[r["source"]].append(wc_total(r))

    src_order  = ["medlineplus","mayo","both"]
    src_labels = ["MedlinePlus","Mayo","Cả 2 nguồn"]
    bp = ax2.boxplot(
        [src_data[s] for s in src_order],
        labels=src_labels, patch_artist=True,
        medianprops={"color":"white","linewidth":2},
        flierprops={"marker":"o","markersize":3,"alpha":0.3},
    )
    bp_colors = [C["blue"], C["coral"], C["green"]]
    for patch, col in zip(bp["boxes"], bp_colors):
        patch.set_facecolor(col); patch.set_alpha(0.7)
    for whisker in bp["whiskers"]: whisker.set_color("#888")
    for cap in bp["caps"]:         cap.set_color("#888")

    ax2.set_ylabel("Tổng số từ")
    ax2.set_title("Phân bố số từ theo nguồn")

    plt.tight_layout()
    save(fig, "4_wordcount_distribution.png")


# =============================================================================
# CHART 5 – Top bệnh nhiều nội dung nhất
# =============================================================================
def chart_top_diseases(rows):
    log.info("Chart 5: Top diseases...")
    # Top 15 richest
    top = sorted(rows, key=wc_total, reverse=True)[:15]

    names  = []
    for r in reversed(top):
        n = r.get("disease_en") or r["disease"]
        n = n[:42] + "…" if len(n) > 42 else n
        names.append(n)
    vals = [wc_total(r) for r in reversed(top)]
    srcs = [r["source"] for r in reversed(top)]

    src_color_map = {"medlineplus": C["blue"], "mayo": C["coral"], "both": C["green"]}
    colors = [src_color_map.get(s, C["gray"]) for s in srcs]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(names, vals, color=colors, height=0.65, alpha=0.88)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_width()+10, bar.get_y()+bar.get_height()/2,
                f"{val:,}", va="center", fontsize=9)

    ax.set_xlabel("Tổng số từ (tất cả fields)")
    ax.set_title("Top 15 bệnh có nội dung phong phú nhất")
    ax.set_xlim(0, max(vals)*1.15)
    ax.grid(axis="y", alpha=0)

    patches = [mpatches.Patch(color=v, label=k.capitalize())
               for k, v in src_color_map.items()]
    ax.legend(handles=patches, frameon=False, fontsize=9)

    plt.tight_layout()
    save(fig, "5_top_diseases.png")


# =============================================================================
# CHART 6 – Word cloud triệu chứng tiếng Việt
# =============================================================================
def chart_wordcloud(rows):
    log.info("Chart 6: Word cloud...")
    try:
        from wordcloud import WordCloud
    except ImportError:
        log.warning("Chưa cài wordcloud. Chạy: pip install wordcloud  → Bỏ qua chart 6.")
        return

    text_all = " ".join(
        (r.get("symptoms","") or "") + " " + (r.get("causes","") or "")
        for r in rows
    )
    # Lọc từ ngắn và stopwords
    tokens = [w for w in re.findall(r"\b[\wÀ-ỹ]{4,}\b", text_all.lower())
              if w not in STOPWORDS_VI]
    freq = Counter(tokens)
    # Bỏ top noise tokens
    noise = {"chứng","triệu","bệnh","thường","thể","được","người",
             "khác","động","phát","chân","chảy","giác","nước","kinh","hiện"}
    for n in noise:
        freq.pop(n, None)

    wc_obj = WordCloud(
        width=1100, height=520,
        background_color="white",
        colormap="Blues_r",
        max_words=130,
        min_font_size=9,
        max_font_size=95,
        prefer_horizontal=0.82,
        collocations=False,
        margin=3,
    ).generate_from_frequencies(freq)

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.imshow(wc_obj, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("Word Cloud — triệu chứng & nguyên nhân phổ biến (tiếng Việt)",
                 pad=14, fontsize=13)
    save(fig, "6_wordcloud_vi.png")


# =============================================================================
# CHART 7 – Discretization (Phân loại & Thuộc tính mới)
# =============================================================================
def chart_discretization(rows):
    log.info("Chart 7: Discretization attributes...")
    # Check if we have the new fields
    if not rows or "disease_category" not in rows[0]:
        log.warning("Không tìm thấy trường discretization trong dữ liệu. Bỏ qua chart 7.")
        return

    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(2, 3, height_ratios=[1, 1], width_ratios=[1.5, 1, 1])
    
    # 1. Disease Categories (Barh)
    ax1 = fig.add_subplot(gs[:, 0])
    cat_cnt = Counter(r.get("disease_category", "Khác") for r in rows)
    # Sort by count
    cats = sorted(cat_cnt.items(), key=lambda x: x[1])
    labels = [k for k, v in cats]
    vals = [v for k, v in cats]
    bars = ax1.barh(labels, vals, color=C["blue"], alpha=0.8)
    for bar, val in zip(bars, vals):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, str(val), va="center", fontsize=9)
    ax1.set_title("Phân bố theo nhóm bệnh")
    
    # 2. Severity Level (Bar)
    ax2 = fig.add_subplot(gs[0, 1])
    sev_cnt = Counter(r.get("severity_level", "Trung bình") for r in rows)
    sev_order = ["Nhẹ", "Trung bình", "Nặng", "Đe dọa tính mạng"]
    sev_vals = [sev_cnt.get(s, 0) for s in sev_order]
    sev_colors = [C["green"], C["blue"], C["amber"], C["coral"]]
    bars2 = ax2.bar(sev_order, sev_vals, color=sev_colors, alpha=0.85)
    for bar, val in zip(bars2, sev_vals):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, str(val), ha="center", fontsize=9)
    ax2.set_title("Mức độ nghiêm trọng")
    ax2.tick_params(axis="x", rotation=15)
    
    # 3. Disease Type (Pie)
    ax3 = fig.add_subplot(gs[0, 2])
    type_cnt = Counter(r.get("disease_type", "Không xác định") for r in rows)
    # Remove "Không xác định" if we want a cleaner pie, or keep it
    type_labels = list(type_cnt.keys())
    type_vals = list(type_cnt.values())
    ax3.pie(type_vals, labels=type_labels, autopct="%1.1f%%", startangle=90, colors=[C["purple"], C["teal"], C["amber"], C["gray"]])
    ax3.set_title("Tính chất bệnh (Cấp/Mãn tính)")
    
    # 4. Target Demographic (Pie)
    ax4 = fig.add_subplot(gs[1, 1])
    demo_cnt = Counter(r.get("target_demographic", "Mọi lứa tuổi") for r in rows)
    demo_labels = list(demo_cnt.keys())
    demo_vals = list(demo_cnt.values())
    ax4.pie(demo_vals, labels=demo_labels, autopct="%1.1f%%", startangle=140, colors=[C["blue"], C["green"], C["amber"], C["coral"]])
    ax4.set_title("Đối tượng mục tiêu")
    
    # 5. Contagious Status (Donut)
    ax5 = fig.add_subplot(gs[1, 2])
    cont_cnt = Counter(r.get("is_contagious", "Không xác định") for r in rows)
    cont_labels = list(cont_cnt.keys())
    cont_vals = list(cont_cnt.values())
    wedges, _, autotexts = ax5.pie(cont_vals, labels=cont_labels, autopct="%1.1f%%", startangle=90, colors=[C["coral"], C["green"], C["gray"]], wedgeprops={"width":0.4, "edgecolor":"w"})
    ax5.set_title("Tính lây nhiễm")
    
    plt.tight_layout()
    save(fig, "7_discretization.png")

# =============================================================================
# CHART 8, 9, 10, 11 – Phân tích theo Hệ Cơ Quan (Organ System)
# =============================================================================
def chart_organ_analysis(rows):
    log.info("Chart 8-11: Organ Systems analysis...")
    
    # 1. Gắn tag Hệ cơ quan
    for r in rows:
        r["organ_system"] = assign_organ_system(r.get("disease", ""))
    
    # Lấy các hệ cơ quan
    sys_cnt = Counter(r["organ_system"] for r in rows)
    systems_sorted = [k for k, v in sorted(sys_cnt.items(), key=lambda x: x[1]) if k != "Khác"]
    if "Khác" in sys_cnt:
        systems_sorted.insert(0, "Khác")
        
    # --- Biểu đồ 8: Phân bố bệnh theo hệ cơ quan ---
    fig1 = plt.figure(figsize=(12, 8))
    labels = systems_sorted
    vals = [sys_cnt[s] for s in labels]
    
    bars = plt.barh(labels, vals, color=C["teal"], alpha=0.8)
    for bar, val in zip(bars, vals):
        plt.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2, str(val), va="center", fontsize=9)
    plt.title("Phân bố số lượng bệnh lý theo Hệ Cơ Quan", pad=15)
    plt.xlabel("Số lượng bản ghi")
    plt.tight_layout()
    save(fig1, "8_organ_system_distribution.png")

    # --- Biểu đồ 9: Heatmap tỷ lệ điền field theo hệ cơ quan ---
    sys_field_filled = defaultdict(lambda: defaultdict(int))
    sys_total = defaultdict(int)

    for r in rows:
        sys = r["organ_system"]
        sys_total[sys] += 1
        for f in CONTENT_FIELDS:
            val = r.get(f)
            if val and (isinstance(val, list) or len(str(val).strip()) > 3):
                sys_field_filled[sys][f] += 1

    heatmap_data = []
    heatmap_systems = [s for s in reversed(systems_sorted) if sys_total[s] > 0]
    for sys in heatmap_systems:
        row_data = {"Hệ Cơ Quan": sys}
        for f in CONTENT_FIELDS:
            pct = (sys_field_filled[sys][f] / sys_total[sys]) * 100
            row_data[FIELD_LABELS_VI.get(f, f)] = pct
        heatmap_data.append(row_data)

    df_heat = pd.DataFrame(heatmap_data).set_index("Hệ Cơ Quan")
    
    fig2 = plt.figure(figsize=(14, 10))
    sns.heatmap(df_heat, annot=True, fmt=".0f", cmap="YlGnBu", cbar_kws={'label': 'Tỷ lệ điền (%)'}, linewidths=.5)
    plt.title("Heatmap tỷ lệ điền dữ liệu theo Hệ Cơ Quan (%)", pad=15)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    save(fig2, "9_organ_field_heatmap.png")

    # --- Biểu đồ 10: Mức độ nguy hiểm THEO Hệ Cơ Quan (Stacked Bar) ---
    sev_order = ["Nhẹ", "Trung bình", "Nặng", "Đe dọa tính mạng"]
    sev_colors = [C["green"], C["blue"], C["amber"], C["coral"]]
    
    sys_sev = defaultdict(lambda: {s: 0 for s in sev_order})
    for r in rows:
        sys = r["organ_system"]
        sev = r.get("severity_level", "Không xác định")
        if sev in sys_sev[sys]:
            sys_sev[sys][sev] += 1

    df_sev = pd.DataFrame([
        {"System": sys, **sys_sev[sys]} for sys in heatmap_systems
    ]).set_index("System")

    fig3, ax3 = plt.subplots(figsize=(12, 8))
    df_sev.plot(kind="barh", stacked=True, ax=ax3, color=sev_colors, width=0.8)
    ax3.set_title("Mức độ nguy hiểm theo Hệ Cơ Quan", pad=15)
    ax3.set_xlabel("Số lượng bệnh")
    ax3.set_ylabel("")
    ax3.legend(title="Mức độ", loc="lower right")
    plt.tight_layout()
    save(fig3, "10_organ_severity_stacked.png")

    # --- Biểu đồ 11: Cấp tính/Mãn tính THEO Hệ Cơ Quan (Stacked Bar) ---
    type_order = ["Cấp tính", "Mãn tính", "Cả hai"]
    type_colors = [C["teal"], C["purple"], C["amber"]]
    
    sys_type = defaultdict(lambda: {t: 0 for t in type_order})
    for r in rows:
        sys = r["organ_system"]
        dt = r.get("disease_type", "Không xác định")
        if dt in sys_type[sys]:
            sys_type[sys][dt] += 1

    df_type = pd.DataFrame([
        {"System": sys, **sys_type[sys]} for sys in heatmap_systems
    ]).set_index("System")

    fig4, ax4 = plt.subplots(figsize=(12, 8))
    df_type.plot(kind="barh", stacked=True, ax=ax4, color=type_colors, width=0.8)
    ax4.set_title("Tính chất bệnh (Cấp/Mãn tính) theo Hệ Cơ Quan", pad=15)
    ax4.set_xlabel("Số lượng bệnh")
    ax4.set_ylabel("")
    ax4.legend(title="Tính chất bệnh", loc="lower right")
    plt.tight_layout()
    save(fig4, "11_organ_disease_type_stacked.png")


# =============================================================================
# MAIN
# =============================================================================
def run():
    rows = load()
    log.info(f"Saving charts → {OUT_DIR}/")

    chart_overview(rows)
    chart_sources(rows)
    chart_field_coverage(rows)
    chart_wordcount_dist(rows)
    chart_top_diseases(rows)
    chart_wordcloud(rows)
    chart_discretization(rows)
    chart_organ_analysis(rows)

    pngs = list(OUT_DIR.glob("*.png"))
    log.info("─" * 55)
    log.info(f"✅ Xong! {len(pngs)} charts saved to {OUT_DIR}/")
    for p in sorted(pngs):
        log.info(f"   {p.name}")


if __name__ == "__main__":
    run()