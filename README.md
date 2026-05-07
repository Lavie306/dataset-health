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

| Bước | Module | Chức năng |
|------|--------|-----------|
| 1 | `Clean_data.py` | Loại bỏ nhiễu HTML, chuẩn hóa encoding, gắn cờ quality issues |
| 2 | `merg_data.py` | Hợp nhất Mayo + MedlinePlus, xử lý trùng lặp, lưu vết provenance |
| 3 | `translate_data.py` | Dịch nội dung sang tiếng Việt |
| 4 | `reduce_data.py` | Smart truncation, loại bỏ trường thưa thớt, bảo toàn cấu trúc |
| 5 | `export_data.py` | Xuất JSON, CSV và thống kê tổng quan |
| 6 | `discretize_data.py` | Gắn ICD-10, phân nhóm bệnh, Severity, Acute/Chronic, Demographic |
| 7 | `quality_report.py` | Sinh báo cáo chất lượng dữ liệu tự động (JSON + Markdown) |

---

## 📊 Phân tích & Trực quan hóa dữ liệu

### Dữ liệu thô — `src/utils/raw_data_analysis.py`
Phân tích **trước** khi vào pipeline. Kết quả lưu tại `image/raw/`.

| Biểu đồ | Mô tả |
|---------|-------|
| `raw_1_overview_stats.png` | Số lượng bản ghi, trùng lặp, nhiễu HTML (Mayo vs MedlinePlus) |
| `raw_2_field_completeness.png` | Tỷ lệ điền đầy đủ từng trường theo nguồn |
| `raw_3_wordcount_boxplot.png` | Phân bố độ dài văn bản (boxplot) |
| `raw_4_noise_ratio.png` | Tỷ lệ bản ghi sạch vs chứa nhiễu (pie chart) |

### Dữ liệu đã xử lý — `src/utils/data_analysis.py`
Khai phá sâu sau Discretization. Kết quả lưu tại `image/processed/`.

| Biểu đồ | Mô tả |
|---------|-------|
| `1_overview.png` | Thống kê tổng quan bộ dữ liệu |
| `2_sources.png` | Phân bố theo nguồn dữ liệu |
| `3_field_coverage.png` | Tỷ lệ điền đầy đủ từng trường |
| `4_wordcount_distribution.png` | Phân bố số từ trên mỗi bệnh lý |
| `5_top_diseases.png` | Top bệnh lý phổ biến nhất |
| `7_discretization.png` | Phân bố ICD-10, Severity, Disease Category |
| `8_organ_system_distribution.png` | Phân bố bệnh lý theo Hệ Cơ Quan |
| `9_organ_field_heatmap.png` | Heatmap tỷ lệ điền trường theo Hệ Cơ Quan |
| `10_organ_severity_stacked.png` | Mức độ nguy hiểm theo Hệ Cơ Quan |
| `11_organ_disease_type_stacked.png` | Cấp tính / Mãn tính theo Hệ Cơ Quan |

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
├── data/
│   ├── raw/          # Dữ liệu gốc (mayo_full.json, medlineplus_full.json)
│   ├── processed/    # File trung gian: cleaned, merged, translated, reduced, discretized
│   ├── output/       # Xuất cuối: medical_vi.csv, stats.json, quality_report.md
│   └── graph/        # Knowledge Graph: nodes.json, edges.json, drugs.json, guidelines.json
├── image/
│   ├── raw/          # 4 biểu đồ phân tích dữ liệu thô
│   └── processed/    # 10 biểu đồ phân tích dữ liệu đã xử lý
├── src/
│   ├── main.py       # Entry point chính (xem hướng dẫn bên dưới)
│   ├── processing/   # 7 module pipeline: Clean → Merge → Translate → Reduce → Export → Discretize → Report
│   ├── utils/        # Phân tích & Biểu đồ: data_analysis.py, raw_data_analysis.py, quality_report.py
│   ├── graph/        # Xây dựng Knowledge Graph
│   └── neo4j/        # Kết nối và đẩy dữ liệu lên Neo4j
├── requirements.txt
└── README.md
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