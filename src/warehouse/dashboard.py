"""
Dashboard Streamlit — Medical Data Warehouse
Truy vấn DuckDB bằng giao diện web
"""

import os
import duckdb
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, "data", "warehouse", "medical_dw.duckdb")

st.set_page_config(
    page_title="Medical Data Warehouse",
    page_icon="🏥",
    layout="wide",
)

# ── CSS tùy chỉnh ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    h1, h2, h3 { color: #4fc3f7; }
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f, #0d2137);
        border: 1px solid #4fc3f7;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    .stDataFrame { font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ── Kết nối DB ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"❌ Chưa tìm thấy database. Chạy ETL trước:\n`python src/warehouse/etl_to_duckdb.py`")
        st.stop()
    return duckdb.connect(DB_PATH, read_only=True)

@st.cache_data
def query(_con, sql: str) -> pd.DataFrame:
    return _con.execute(sql).df()

con = get_connection()

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/color/96/hospital.png", width=80)
st.sidebar.title("🏥 Medical DW")
page = st.sidebar.radio(
    "Chọn trang",
    ["📊 Tổng quan", "🔍 Truy vấn SQL", "📋 Duyệt dữ liệu"],
)

# ── Helper ─────────────────────────────────────────────────────────────────────
def plot_bar(df: pd.DataFrame, x_col: str, y_col: str, title: str, color="#4fc3f7"):
    fig, ax = plt.subplots(figsize=(9, 4), facecolor="#0f1117")
    ax.set_facecolor("#0f1117")
    bars = ax.barh(df[x_col].astype(str), df[y_col], color=color, edgecolor="none")
    ax.bar_label(bars, fmt="%d", color="white", fontsize=9, padding=4)
    ax.set_xlabel(y_col, color="white")
    ax.tick_params(colors="white")
    ax.spines[:].set_visible(False)
    ax.invert_yaxis()
    ax.set_title(title, color="#4fc3f7", fontsize=13, pad=10)
    st.pyplot(fig)
    plt.close()

# ══════════════════════════════════════════════════════════════════════════════
# Trang 1: Tổng quan
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Tổng quan":
    st.title("📊 Medical Data Warehouse — Tổng quan")

    # Metrics
    total   = query(con, "SELECT COUNT(*) AS n FROM fact_disease")["n"][0]
    cats    = query(con, "SELECT COUNT(*) AS n FROM dim_category")["n"][0]
    sources = query(con, "SELECT COUNT(*) AS n FROM dim_source")["n"][0]
    heavy   = query(con, """
        SELECT COUNT(*) AS n FROM fact_disease f
        JOIN dim_severity s ON f.severity_id = s.severity_id
        WHERE s.severity_level = 'Đe dọa tính mạng'
    """)["n"][0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🦠 Tổng số bệnh",        f"{total:,}")
    c2.metric("📂 Nhóm bệnh",            f"{cats}")
    c3.metric("📰 Nguồn dữ liệu",        f"{sources}")
    c4.metric("⚠️ Đe dọa tính mạng",     f"{heavy:,}")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Phân bố theo Nhóm bệnh")
        df_cat = query(con, """
            SELECT c.disease_category, COUNT(*) AS total
            FROM fact_disease f
            JOIN dim_category c ON f.category_id = c.category_id
            GROUP BY c.disease_category
            ORDER BY total DESC
        """)
        plot_bar(df_cat, "disease_category", "total",
                 "Số bệnh theo nhóm", color="#4fc3f7")

    with col2:
        st.subheader("Phân bố theo Mức độ nặng")
        df_sev = query(con, """
            SELECT s.severity_level, COUNT(*) AS total
            FROM fact_disease f
            JOIN dim_severity s ON f.severity_id = s.severity_id
            GROUP BY s.severity_level
            ORDER BY total DESC
        """)
        colors_sev = ["#ef5350","#ff7043","#ffa726","#66bb6a","#42a5f5"]
        fig, ax = plt.subplots(figsize=(5, 4), facecolor="#0f1117")
        ax.set_facecolor("#0f1117")
        wedges, texts, autotexts = ax.pie(
            df_sev["total"],
            labels=df_sev["severity_level"],
            autopct="%1.1f%%",
            colors=colors_sev[:len(df_sev)],
            textprops={"color": "white", "fontsize": 10},
        )
        for at in autotexts:
            at.set_fontsize(8)
        ax.set_title("Mức độ nặng", color="#4fc3f7", fontsize=13)
        st.pyplot(fig)
        plt.close()

    st.divider()

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Nguồn dữ liệu")
        df_src = query(con, """
            SELECT s.source_name, COUNT(*) AS total
            FROM fact_disease f
            JOIN dim_source s ON f.source_id = s.source_id
            GROUP BY s.source_name ORDER BY total DESC
        """)
        plot_bar(df_src, "source_name", "total", "Bệnh theo nguồn", color="#ab47bc")

    with col4:
        st.subheader("Đối tượng bệnh nhân")
        df_dem = query(con, """
            SELECT d.target_demographic, COUNT(*) AS total
            FROM fact_disease f
            JOIN dim_demographic d ON f.demographic_id = d.demographic_id
            GROUP BY d.target_demographic ORDER BY total DESC
        """)
        plot_bar(df_dem, "target_demographic", "total", "Đối tượng", color="#26a69a")

# ══════════════════════════════════════════════════════════════════════════════
# Trang 2: Truy vấn SQL tuỳ chỉnh
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Truy vấn SQL":
    st.title("🔍 Truy vấn SQL tuỳ chỉnh")

    st.info("Các bảng có thể dùng: `fact_disease`, `dim_category`, `dim_source`, `dim_severity`, `dim_demographic`, `dim_content`")

    PRESETS = {
        "Top 10 nhóm bệnh": """SELECT c.disease_category, COUNT(*) AS total
FROM fact_disease f
JOIN dim_category c ON f.category_id = c.category_id
GROUP BY c.disease_category
ORDER BY total DESC LIMIT 10""",
        "Bệnh đe dọa tính mạng": """SELECT f.disease_vi, f.disease_en, c.disease_category, f.icd_code
FROM fact_disease f
JOIN dim_category c ON f.category_id = c.category_id
JOIN dim_severity s ON f.severity_id = s.severity_id
WHERE s.severity_level = 'Đe dọa tính mạng'
LIMIT 20""",
        "Bệnh từ cả 2 nguồn": """SELECT f.disease_vi, f.disease_en, f.total_words
FROM fact_disease f
JOIN dim_source s ON f.source_id = s.source_id
WHERE s.source_name = 'both'
ORDER BY f.total_words DESC LIMIT 20""",
        "Thống kê đối tượng × mức độ": """SELECT d.target_demographic, s.severity_level, COUNT(*) AS total
FROM fact_disease f
JOIN dim_demographic d ON f.demographic_id = d.demographic_id
JOIN dim_severity    s ON f.severity_id    = s.severity_id
GROUP BY d.target_demographic, s.severity_level
ORDER BY d.target_demographic, total DESC""",
    }

    preset = st.selectbox("Chọn query mẫu:", ["(tuỳ chỉnh)"] + list(PRESETS.keys()))
    default_sql = PRESETS.get(preset, "SELECT * FROM fact_disease LIMIT 10")

    sql = st.text_area("SQL:", value=default_sql, height=150)

    if st.button("▶ Chạy query", type="primary"):
        try:
            result = query(con, sql)
            st.success(f"✅ {len(result):,} kết quả")
            st.dataframe(result, use_container_width=True)

            csv = result.to_csv(index=False).encode("utf-8")
            st.download_button("⬇ Tải CSV", csv, "result.csv", "text/csv")
        except Exception as e:
            st.error(f"❌ Lỗi: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# Trang 3: Duyệt dữ liệu
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Duyệt dữ liệu":
    st.title("📋 Duyệt dữ liệu bệnh")

    # Filters
    col1, col2, col3 = st.columns(3)

    categories = ["Tất cả"] + query(con, "SELECT DISTINCT disease_category FROM dim_category ORDER BY disease_category")["disease_category"].tolist()
    severities = ["Tất cả"] + query(con, "SELECT severity_level FROM dim_severity ORDER BY severity_level")["severity_level"].tolist()
    sources_list = ["Tất cả"] + query(con, "SELECT source_name FROM dim_source ORDER BY source_name")["source_name"].tolist()

    with col1:
        sel_cat = st.selectbox("Nhóm bệnh", categories)
    with col2:
        sel_sev = st.selectbox("Mức độ nặng", severities)
    with col3:
        sel_src = st.selectbox("Nguồn", sources_list)

    search = st.text_input("🔎 Tìm tên bệnh (VI hoặc EN):")

    # Build WHERE clause
    where_parts = []
    if sel_cat != "Tất cả":
        where_parts.append(f"c.disease_category = '{sel_cat}'")
    if sel_sev != "Tất cả":
        where_parts.append(f"s.severity_level = '{sel_sev}'")
    if sel_src != "Tất cả":
        where_parts.append(f"src.source_name = '{sel_src}'")
    if search:
        where_parts.append(f"(LOWER(f.disease_vi) LIKE '%{search.lower()}%' OR LOWER(f.disease_en) LIKE '%{search.lower()}%')")

    where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    sql_browse = f"""
        SELECT
            f.disease_vi        AS "Tên bệnh (VI)",
            f.disease_en        AS "Tên bệnh (EN)",
            f.icd_code          AS "ICD",
            c.disease_category  AS "Nhóm bệnh",
            c.disease_type      AS "Loại",
            s.severity_level    AS "Mức độ",
            d.target_demographic AS "Đối tượng",
            src.source_name     AS "Nguồn",
            f.is_contagious     AS "Lây nhiễm",
            f.total_words       AS "Số từ"
        FROM fact_disease f
        JOIN dim_category    c   ON f.category_id    = c.category_id
        JOIN dim_severity    s   ON f.severity_id    = s.severity_id
        JOIN dim_demographic d   ON f.demographic_id = d.demographic_id
        JOIN dim_source      src ON f.source_id      = src.source_id
        {where_clause}
        ORDER BY f.total_words DESC
        LIMIT 200
    """

    df_browse = query(con, sql_browse)
    st.info(f"Hiển thị {len(df_browse)} bản ghi (tối đa 200)")
    st.dataframe(df_browse, use_container_width=True, height=420)

    if len(df_browse) > 0:
        sel_row = st.selectbox("Xem chi tiết bệnh:", df_browse["Tên bệnh (VI)"].tolist())
        if sel_row:
            detail = con.execute(
                "SELECT * FROM fact_disease WHERE disease_vi = ?", [sel_row]
            ).df()
            if not detail.empty:
                r = detail.iloc[0]
                st.subheader(f"🔬 {r['disease_vi']} ({r['disease_en']})")
                tabs = st.tabs(["Triệu chứng", "Nguyên nhân", "Điều trị", "Phòng ngừa", "Tiên lượng", "Biến chứng"])
                fields = ["symptoms", "causes", "treatment", "prevention", "prognosis", "complications"]
                labels = ["Triệu chứng", "Nguyên nhân", "Điều trị", "Phòng ngừa", "Tiên lượng", "Biến chứng"]
                for tab, field, label in zip(tabs, fields, labels):
                    with tab:
                        val = r.get(field, "")
                        st.write(val if val else f"_(Không có dữ liệu {label})_")
