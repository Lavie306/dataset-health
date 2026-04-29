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

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("analysis_vi")

# ── config ────────────────────────────────────────────────────────────────────
ROOT      = pathlib.Path(__file__).parent.parent.parent
INPUT_FILE = ROOT / "data/output/medical_vi.csv"
OUT_DIR    = ROOT / "data/output"
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

# =============================================================================
# LOAD
# =============================================================================
def load():
    log.info(f"Loading {INPUT_FILE} ...")
    with open(INPUT_FILE, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    log.info(f"  {len(rows)} records | {len(rows[0])} columns")
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

    pngs = list(OUT_DIR.glob("*.png"))
    log.info("─" * 55)
    log.info(f"✅ Xong! {len(pngs)} charts saved to {OUT_DIR}/")
    for p in sorted(pngs):
        log.info(f"   {p.name}")


if __name__ == "__main__":
    run()