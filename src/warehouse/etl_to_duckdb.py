"""
ETL Pipeline: discretized.json → DuckDB Data Warehouse
Star Schema:
    fact_disease (bảng trung tâm)
    ├── dim_disease     (tên bệnh VI/EN, icd_code)
    ├── dim_category    (nhóm bệnh, loại bệnh)
    ├── dim_source      (mayo / medlineplus / both)
    ├── dim_severity    (mức độ nặng)
    ├── dim_demographic (đối tượng)
    └── dim_content     (mức độ phong phú nội dung)
"""

import json
import os
import duckdb
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT_FILE  = os.path.join(BASE_DIR, "data", "processed", "discretized.json")
OUTPUT_DIR  = os.path.join(BASE_DIR, "data", "warehouse")
DB_PATH     = os.path.join(OUTPUT_DIR, "medical_dw.duckdb")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Load dữ liệu gốc ───────────────────────────────────────────────────────────
def load_source(path: str) -> list[dict]:
    print(f"[ETL] Doc du lieu tu: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"[ETL] Tong so ban ghi: {len(data):,}")
    return data


# ── Build dimension tables ─────────────────────────────────────────────────────
def build_dimensions(data: list[dict]) -> dict[str, pd.DataFrame]:
    """Tạo các bảng dimension từ raw data."""

    # dim_category: nhóm bệnh × loại bệnh
    categories = sorted({
        (r.get("disease_category", "Không xác định"),
         r.get("disease_type",     "Không xác định"))
        for r in data
    })
    dim_category = pd.DataFrame(categories, columns=["disease_category", "disease_type"])
    dim_category.insert(0, "category_id", range(1, len(dim_category) + 1))

    # dim_source
    sources = sorted({r.get("source", "unknown") for r in data})
    dim_source = pd.DataFrame({"source_name": sources})
    dim_source.insert(0, "source_id", range(1, len(dim_source) + 1))

    # dim_severity
    severities = sorted({r.get("severity_level", "Không xác định") for r in data})
    dim_severity = pd.DataFrame({"severity_level": severities})
    dim_severity.insert(0, "severity_id", range(1, len(dim_severity) + 1))

    # dim_demographic
    demographics = sorted({r.get("target_demographic", "Không xác định") for r in data})
    dim_demographic = pd.DataFrame({"target_demographic": demographics})
    dim_demographic.insert(0, "demographic_id", range(1, len(dim_demographic) + 1))

    # dim_content_richness
    richness_levels = sorted({r.get("content_richness", "Không xác định") for r in data})
    dim_content = pd.DataFrame({"content_richness": richness_levels})
    dim_content.insert(0, "content_id", range(1, len(dim_content) + 1))

    print(f"[ETL] dim_category:    {len(dim_category)} dong")
    print(f"[ETL] dim_source:      {len(dim_source)} dong")
    print(f"[ETL] dim_severity:    {len(dim_severity)} dong")
    print(f"[ETL] dim_demographic: {len(dim_demographic)} dong")
    print(f"[ETL] dim_content:     {len(dim_content)} dong")

    return {
        "dim_category":    dim_category,
        "dim_source":      dim_source,
        "dim_severity":    dim_severity,
        "dim_demographic": dim_demographic,
        "dim_content":     dim_content,
    }


# ── Build fact table ───────────────────────────────────────────────────────────
def build_fact(data: list[dict], dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tạo bảng fact_disease với các FK trỏ tới dim tables."""

    # Lookup maps
    cat_map  = {(r["disease_category"], r["disease_type"]): r["category_id"]
                for _, r in dims["dim_category"].iterrows()}
    src_map  = {r["source_name"]:       r["source_id"]
                for _, r in dims["dim_source"].iterrows()}
    sev_map  = {r["severity_level"]:    r["severity_id"]
                for _, r in dims["dim_severity"].iterrows()}
    dem_map  = {r["target_demographic"]: r["demographic_id"]
                for _, r in dims["dim_demographic"].iterrows()}
    con_map  = {r["content_richness"]:  r["content_id"]
                for _, r in dims["dim_content"].iterrows()}

    rows = []
    for i, r in enumerate(data, start=1):
        cat_key  = (r.get("disease_category", "Không xác định"),
                    r.get("disease_type",     "Không xác định"))
        url_val  = r.get("url", [])
        url_str  = url_val[0] if url_val else ""

        rows.append({
            "fact_id":        i,
            # FK
            "category_id":    cat_map.get(cat_key),
            "source_id":      src_map.get(r.get("source", "unknown")),
            "severity_id":    sev_map.get(r.get("severity_level",    "Không xác định")),
            "demographic_id": dem_map.get(r.get("target_demographic","Không xác định")),
            "content_id":     con_map.get(r.get("content_richness",  "Không xác định")),
            # Thuộc tính bệnh
            "disease_vi":     r.get("disease",     ""),
            "disease_en":     r.get("disease_en",  ""),
            "icd_code":       r.get("icd_code",    ""),
            "is_contagious":  r.get("is_contagious","Không xác định"),
            "total_words":    r.get("total_words",  0),
            "url":            url_str,
            # Nội dung văn bản
            "overview":       r.get("overview",       ""),
            "symptoms":       r.get("symptoms",       ""),
            "causes":         r.get("causes",         ""),
            "treatment":      r.get("treatment",      ""),
            "prevention":     r.get("prevention",     ""),
            "complications":  r.get("complications",  ""),
            "prognosis":      r.get("prognosis",      ""),
        })

    fact = pd.DataFrame(rows)
    print(f"[ETL] fact_disease:    {len(fact):,} dong")
    return fact


# ── Load vào DuckDB ────────────────────────────────────────────────────────────
def load_to_duckdb(dims: dict[str, pd.DataFrame], fact: pd.DataFrame, db_path: str):
    print(f"[ETL] Ghi vao DuckDB: {db_path}")
    con = duckdb.connect(db_path)

    # Xóa nếu đã tồn tại để chạy lại sạch
    for table in ["fact_disease", "dim_category", "dim_source",
                  "dim_severity", "dim_demographic", "dim_content"]:
        con.execute(f"DROP TABLE IF EXISTS {table}")

    # Ghi dimension tables
    for name, df in dims.items():
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
        print(f"  [OK] {name}: {len(df)} dong")

    # Ghi fact table
    con.execute("CREATE TABLE fact_disease AS SELECT * FROM fact")
    print(f"  [OK] fact_disease: {len(fact):,} dong")

    # Tạo indexes để tăng tốc query
    con.execute("CREATE INDEX idx_fact_category    ON fact_disease(category_id)")
    con.execute("CREATE INDEX idx_fact_source       ON fact_disease(source_id)")
    con.execute("CREATE INDEX idx_fact_severity     ON fact_disease(severity_id)")
    con.execute("CREATE INDEX idx_fact_demographic  ON fact_disease(demographic_id)")

    con.close()
    size_mb = os.path.getsize(db_path) / 1024 / 1024
    print(f"[ETL] Hoan tat! File DB: {size_mb:.2f} MB")


# ── Demo queries ───────────────────────────────────────────────────────────────
def run_demo_queries(db_path: str):
    print("\n" + "="*60)
    print("DEMO QUERIES")
    print("="*60)
    con = duckdb.connect(db_path, read_only=True)

    queries = {
        "So benh theo nhom (Top 10)": """
            SELECT c.disease_category, COUNT(*) AS total_diseases
            FROM fact_disease f
            JOIN dim_category c ON f.category_id = c.category_id
            GROUP BY c.disease_category
            ORDER BY total_diseases DESC
            LIMIT 10
        """,
        "Phan bo muc do nang": """
            SELECT s.severity_level, COUNT(*) AS total
            FROM fact_disease f
            JOIN dim_severity s ON f.severity_id = s.severity_id
            GROUP BY s.severity_level
            ORDER BY total DESC
        """,
        "Benh tu ca 2 nguon (Mayo + MedlinePlus)": """
            SELECT COUNT(*) AS so_benh_ca_hai_nguon
            FROM fact_disease f
            JOIN dim_source s ON f.source_id = s.source_id
            WHERE s.source_name = 'both'
        """,
        "Doi tuong x Muc do nang": """
            SELECT d.target_demographic, s.severity_level, COUNT(*) AS total
            FROM fact_disease f
            JOIN dim_demographic d ON f.demographic_id = d.demographic_id
            JOIN dim_severity    s ON f.severity_id    = s.severity_id
            GROUP BY d.target_demographic, s.severity_level
            ORDER BY d.target_demographic, total DESC
        """,
    }

    for title, sql in queries.items():
        print(f"\n>> {title}:")
        result = con.execute(sql).df()
        safe_str = result.to_string(index=False).encode("ascii", errors="replace").decode("ascii")
        print(safe_str)

    con.close()


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("ETL: discretized.json --> DuckDB Data Warehouse")
    print("=" * 60)

    data = load_source(INPUT_FILE)
    dims = build_dimensions(data)
    fact = build_fact(data, dims)
    load_to_duckdb(dims, fact, DB_PATH)
    run_demo_queries(DB_PATH)

    print("\nETL hoan tat!")
    print(f"   Database: {DB_PATH}")
    print("   Chay dashboard: streamlit run src/warehouse/dashboard.py")


if __name__ == "__main__":
    main()
