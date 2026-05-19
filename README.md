# 🏥 Medical Data Mining & Knowledge Graph Pipeline

> Hệ thống khai phá dữ liệu y tế toàn diện — từ thu thập, làm sạch, dịch thuật, rời rạc hóa cho đến xây dựng Đồ thị Tri thức (Knowledge Graph) và tích hợp Neo4j.

**Nguồn dữ liệu:** Mayo Clinic · MedlinePlus &nbsp;|&nbsp; **Tổng số bản ghi:** ~3,014 bệnh lý &nbsp;|&nbsp; **Ngôn ngữ:** Python 3.10+

---

## 📐 Tổng quan kiến trúc

```
Raw Data (EN)          Pipeline (7 bước)          Output
──────────────   →   ──────────────────────   →   ─────────────────────
Mayo Clinic            1. Clean                    ✅ discretized.json
MedlinePlus            2. Merge                    ✅ medical_vi.csv
                       3. Translate (VI)           ✅ Knowledge Graph
                       4. Reduce                   ✅ Biểu đồ thống kê
                       5. Export                   ✅ Neo4j Database
                       6. Discretize
                       7. Quality Report
```

---

## 🏗️ Pipeline xử lý dữ liệu (7 bước)

Toàn bộ quy trình được điều phối qua `src/processing/run_pipeline.py`:

| Bước | Module               | Chức năng                                                        |
| ---- | -------------------- | ---------------------------------------------------------------- |
| 1    | `Clean_data.py`      | Loại bỏ nhiễu HTML, chuẩn hóa encoding, gắn cờ quality issues    |
| 2    | `merg_data.py`       | Hợp nhất Mayo + MedlinePlus, xử lý trùng lặp, lưu vết provenance |
| 3    | `translate_data.py`  | Dịch nội dung sang tiếng Việt                                    |
| 4    | `reduce_data.py`     | Smart truncation, loại bỏ trường thưa thớt, bảo toàn cấu trúc    |
| 5    | `export_data.py`     | Xuất JSON, CSV và thống kê tổng quan                             |
| 6    | `discretize_data.py` | Gắn ICD-10, phân nhóm bệnh, Severity, Acute/Chronic, Demographic |
| 7    | `quality_report.py`  | Sinh báo cáo chất lượng dữ liệu tự động (JSON + Markdown)        |

---

## 📊 Phân tích & Trực quan hóa dữ liệu

### Dữ liệu thô — `src/utils/raw_data_analysis.py`

Phân tích **trước** khi vào pipeline. Kết quả lưu tại `image/raw/`.

| Biểu đồ                        | Mô tả                                                         |
| ------------------------------ | ------------------------------------------------------------- |
| `raw_1_overview_stats.png`     | Số lượng bản ghi, trùng lặp, nhiễu HTML (Mayo vs MedlinePlus) |
| `raw_2_field_completeness.png` | Tỷ lệ điền đầy đủ từng trường theo nguồn                      |
| `raw_3_wordcount_boxplot.png`  | Phân bố độ dài văn bản (boxplot)                              |
| `raw_4_noise_ratio.png`        | Tỷ lệ bản ghi sạch vs chứa nhiễu (pie chart)                  |

### Dữ liệu đã xử lý — `src/utils/data_analysis.py`

Khai phá sâu sau Discretization. Kết quả lưu tại `image/processed/`.

| Biểu đồ                             | Mô tả                                      |
| ----------------------------------- | ------------------------------------------ |
| `1_overview.png`                    | Thống kê tổng quan bộ dữ liệu              |
| `2_sources.png`                     | Phân bố theo nguồn dữ liệu                 |
| `3_field_coverage.png`              | Tỷ lệ điền đầy đủ từng trường              |
| `4_wordcount_distribution.png`      | Phân bố số từ trên mỗi bệnh lý             |
| `5_top_diseases.png`                | Top bệnh lý phổ biến nhất                  |
| `7_discretization.png`              | Phân bố ICD-10, Severity, Disease Category |
| `8_organ_system_distribution.png`   | Phân bố bệnh lý theo Hệ Cơ Quan            |
| `9_organ_field_heatmap.png`         | Heatmap tỷ lệ điền trường theo Hệ Cơ Quan  |
| `10_organ_severity_stacked.png`     | Mức độ nguy hiểm theo Hệ Cơ Quan           |
| `11_organ_disease_type_stacked.png` | Cấp tính / Mãn tính theo Hệ Cơ Quan        |

---

## 🕸️ Knowledge Graph & Neo4j

### Cấu trúc đồ thị

```
(Disease) ──HAS_SYMPTOM──→ (Symptom)
(Disease) ──HAS_CAUSE────→ (Cause)
(Disease) ──HAS_RISK─────→ (RiskFactor)
(Disease) ──HAS_COMPLICATION→ (Complication)
(Disease) ──TREATED_BY───→ (Drug)
(Disease) ──TREATED_BY───→ (Treatment)
(Disease) ──HAS_GUIDELINE→ (Guideline)
(Disease) ──AFFECTS──────→ (Organ)
```

**Thuộc tính Node Disease:** `icd_code`, `disease_category`, `severity_level`, `disease_type`, `is_contagious`, `target_demographic`

### Thứ tự chạy

```bash
python src/graph/data_graph.py                         # Bước 1: Tạo graph cơ bản
python src/graph/enhance_graph_with_drugs_guidelines.py # Bước 2: Bổ sung Drug + Guideline
python src/neo4j/up_neo4j.py                           # Bước 3: Đẩy lên Neo4j
```

---

## 📂 Cấu trúc thư mục

```
Project/
│
├── data/
│   ├── raw/                              # 📥 Dữ liệu đầu vào
│   │   ├── mayo_full.json               #    ~1,300 bệnh – crawl từ Mayo Clinic
│   │   └── medlineplus_full.json        #    ~2,200 bệnh – crawl từ MedlinePlus
│   │
│   ├── processed/                        # ⚙️  File trung gian qua từng bước pipeline
│   │   ├── mayo_clean.json              #    Bước 1 – Làm sạch (Mayo)
│   │   ├── medlineplus_clean.json       #    Bước 1 – Làm sạch (MedlinePlus)
│   │   ├── merged.json                  #    Bước 2 – Hợp nhất hai nguồn
│   │   ├── translated.json              #    Bước 3 – Đã dịch sang tiếng Việt
│   │   ├── reduced.json                 #    Bước 4 – Đã cắt tỉa, tối ưu kích thước
│   │   ├── reduction_report.json        #    Bước 4 – Báo cáo thống kê Reduce
│   │   └── discretized.json             #    Bước 6 – Gắn ICD-10, phân loại bệnh ✅
│   │
│   ├── output/                           # 📤 File xuất cuối cùng
│   │   ├── medical_vi.json              #    Toàn bộ dữ liệu (JSON)
│   │   ├── medical_vi.jsonl             #    Toàn bộ dữ liệu (JSONL – streamable)
│   │   ├── medical_vi.csv               #    Toàn bộ dữ liệu (CSV) ✅
│   │   ├── stats.json                   #    Thống kê tổng quan
│   │   ├── quality_report.json          #    Báo cáo chất lượng (JSON)
│   │   └── quality_report.md            #    Báo cáo chất lượng (Markdown) ✅
│   │
│   └── graph/                            # 🕸️  Knowledge Graph (đầu vào Neo4j)
│       ├── nodes.json                   #    Node cơ bản (Disease, Symptom, Organ…)
│       ├── nodes_updated.json           #    Node đã bổ sung Drug + Guideline
│       ├── edges.json                   #    Quan hệ cơ bản
│       ├── edges_updated.json           #    Quan hệ đầy đủ
│       ├── drugs.json                   #    Danh sách thuốc & phân loại
│       ├── guidelines.json              #    Hướng dẫn điều trị theo bệnh
│       ├── nodes.csv / edges.csv        #    Định dạng CSV để import Neo4j
│       ├── neo4j_import.cypher          #    Script Cypher import hàng loạt
│       └── README_DRUGS_GUIDELINES.md   #    Hướng dẫn schema đồ thị
│
├── image/
│   ├── raw/                              # 📊 Biểu đồ phân tích dữ liệu thô
│   │   ├── raw_1_overview_stats.png     #    Tổng quan: bản ghi, trùng lặp, nhiễu
│   │   ├── raw_2_field_completeness.png #    Tỷ lệ điền đầy đủ từng trường
│   │   ├── raw_3_wordcount_boxplot.png  #    Phân bố số từ (Boxplot)
│   │   ├── raw_4_noise_ratio.png        #    Tỷ lệ sạch / nhiễu HTML (Pie chart)
│   │   └── raw_data_report.md           #    Báo cáo phân tích thô (Markdown)
│   │
│   └── processed/                        # 📊 Biểu đồ dữ liệu đã xử lý
│       ├── 1_overview.png               #    Thống kê tổng quan
│       ├── 2_sources.png                #    Phân bố theo nguồn
│       ├── 3_field_coverage.png         #    Tỷ lệ điền đầy đủ từng trường
│       ├── 4_wordcount_distribution.png #    Phân bố số từ
│       ├── 5_top_diseases.png           #    Top bệnh lý phổ biến nhất
│       ├── 7_discretization.png         #    ICD-10 · Severity · Disease Category
│       ├── 8_organ_system_distribution.png  # Phân bố bệnh theo Hệ Cơ Quan
│       ├── 9_organ_field_heatmap.png        # Heatmap tỷ lệ điền theo Hệ Cơ Quan
│       ├── 10_organ_severity_stacked.png    # Mức độ nguy hiểm theo Hệ Cơ Quan
│       └── 11_organ_disease_type_stacked.png # Cấp/Mãn tính theo Hệ Cơ Quan
│
├── src/
│   ├── main.py                           # 🚪 Entry point chính
│   │
│   ├── crawler/                          # 🕷️ Bot thu thập dữ liệu (Scraping)
│   │   ├── mayo_crawler.py              #    Script cào dữ liệu từ Mayo Clinic
│   │   └── medlineplus_crawl.py         #    Script cào dữ liệu từ MedlinePlus
│   │
│   ├── processing/                       # ⚙️  7 bước pipeline
│   │   ├── run_pipeline.py              #    Điều phối CLI (--steps, --skip-*)
│   │   ├── Clean_data.py                #    Bước 1: Làm sạch
│   │   ├── merg_data.py                 #    Bước 2: Hợp nhất nguồn
│   │   ├── translate_data.py            #    Bước 3: Dịch tiếng Việt
│   │   ├── reduce_data.py               #    Bước 4: Cắt tỉa thông minh
│   │   ├── export_data.py               #    Bước 5: Xuất JSON / CSV
│   │   └── discretize_data.py           #    Bước 6: Rời rạc hóa & metadata
│   │
│   ├── utils/                            # 🔧 Phân tích & Báo cáo
│   │   ├── data_analysis.py             #    Vẽ 10 biểu đồ (processed)
│   │   ├── raw_data_analysis.py         #    Vẽ 4 biểu đồ (raw)
│   │   └── quality_report.py            #    Sinh báo cáo chất lượng (Bước 7)
│   │
│   ├── graph/                            # 🕸️  Knowledge Graph
│   │   ├── data_graph.py                #    Tạo node & edge cơ bản
│   │   ├── enhance_graph_with_drugs_guidelines.py  # Bổ sung Drug / Guideline
│   │   └── summary.py                   #    Thống kê tóm tắt Graph
│   │
│   └── neo4j/                            # 🗄️ Database Connector
│       └── up_neo4j.py                  #    Auth & Bulk Load dữ liệu lên Neo4j AuraDB
│
├── .gitignore                            # Cấu hình Git
├── requirements.txt                      # 📦 Các thư viện Python (pandas, seaborn, neo4j...)
└── README.md                             # Tài liệu kiến trúc dự án
```

---

## 🚀 Hướng dẫn sử dụng

### Cài đặt

```bash
pip install -r requirements.txt
```

### Chạy bằng Entry Point chính (Khuyến nghị)

```bash
python src/main.py pipeline      # Chạy đầy đủ 7 bước pipeline
python src/main.py analyze       # Vẽ 10 biểu đồ dữ liệu đã xử lý
python src/main.py analyze-raw   # Vẽ 4 biểu đồ dữ liệu thô
python src/main.py graph         # Xây dựng Knowledge Graph (2 bước)
python src/main.py all           # Pipeline + Analyze cùng lúc
```

### Hoặc chạy từng module riêng lẻ

```bash
# Pipeline
python src/processing/run_pipeline.py
python src/processing/run_pipeline.py --skip-translate   # Bỏ qua bước dịch
python src/processing/run_pipeline.py --steps 6 7        # Chỉ chạy Discretize + Report

# Phân tích
python src/utils/raw_data_analysis.py
python src/utils/data_analysis.py

# Data Warehouse & Dashboard
python src/warehouse/etl_to_duckdb.py
streamlit run src/warehouse/dashboard.py
```

---

## 🧪 Ví dụ truy vấn Neo4j (Cypher)

```cypher
// Tìm thuốc điều trị bệnh Tiểu đường loại 2
MATCH (d:Disease {name: "Tiểu đường loại 2"})-[:TREATED_BY]->(r:Drug)
RETURN r.name AS Drug, r.class AS Class

// Bệnh lý nặng liên quan đến Tim
MATCH (o:Organ {name: "Tim"})<-[:AFFECTS]-(d:Disease)
WHERE d.severity_level IN ["Nặng", "Đe dọa tính mạng"]
RETURN d.name AS Disease, d.severity_level AS Severity
ORDER BY Severity

// Bệnh mãn tính có hướng dẫn điều trị
MATCH (d:Disease)-[:HAS_GUIDELINE]->(g:Guideline)
WHERE d.disease_type = "Mãn tính"
RETURN d.name, g.content LIMIT 10
```

---

## 📞 Liên hệ

- **Email:** ngthanhtam3006@gmail.com
- **GitHub:** [Lavie306/dataset-health](https://github.com/Lavie306/dataset-health)
