# 🏥 Medical Data Mining & Knowledge Graph Pipeline

Hệ thống xử lý, phân tích và khai phá dữ liệu y tế toàn diện. Dự án này lấy dữ liệu thô từ các nguồn y tế uy tín (Mayo Clinic, MedlinePlus), trải qua một quy trình (pipeline) nghiêm ngặt gồm 7 bước để làm sạch, hợp nhất, rời rạc hóa (discretization), và cuối cùng là xây dựng Đồ thị tri thức (Knowledge Graph) để truy vấn thông qua Neo4j.

---

## 🏗️ Kiến trúc & Quy trình (Data Pipeline)

Quy trình xử lý dữ liệu được tự động hóa thông qua `src/processing/run_pipeline.py` với 7 bước liên tiếp:

1. **`Clean_data.py`**: Loại bỏ nhiễu HTML, chuẩn hóa encoding, và gắn cờ (flag) các bản ghi có vấn đề về chất lượng (quality issues).
2. **`merg_data.py`**: Hợp nhất dữ liệu từ Mayo Clinic và MedlinePlus. Xử lý trùng lặp dựa trên từ điển bí danh (disease aliases), thuật toán text matching (SequenceMatcher) và lưu vết nguồn gốc (provenance).
3. **`translate_data.py`**: (Tùy chọn) Dịch thuật tự động các trường dữ liệu bằng các mô hình dịch hoặc API.
4. **`reduce_data.py`**: Cắt tỉa dữ liệu thông minh (smart truncation) để tránh bùng nổ kích thước, đồng thời bảo toàn định dạng và ý nghĩa y khoa của các trường quan trọng.
5. **`export_data.py`**: Xuất dữ liệu đã xử lý ra các định dạng chuẩn (JSON, CSV).
6. **`discretize_data.py`**: Trích xuất siêu dữ liệu y khoa (Metadata) - bao gồm ánh xạ mã ICD-10, mức độ nguy hiểm (Severity), phân loại cấp tính/mãn tính, đối tượng nguy cơ, và nhóm bệnh hệ cơ quan.
7. **`quality_report.py`**: Sinh báo cáo đánh giá chất lượng tự động sau xử lý (Data Quality Report).

---

## 📊 Phân tích Dữ liệu (Data Analytics)

Dự án cung cấp hai công cụ khai phá và thống kê chuyên sâu:

- **Phân tích Dữ liệu Thô (`src/utils/raw_data_analysis.py`)**: Đánh giá dữ liệu trước xử lý.
  - Phân tích số lượng, trùng lặp và tỷ lệ nhiễu HTML.
  - Vẽ biểu đồ mức độ đầy đủ của từng trường (Field Completeness) và phân bố độ dài văn bản (Word Count).
  - Kết quả lưu tại: `image/raw/`

- **Phân tích Dữ liệu Tinh (`src/utils/data_analysis.py`)**: Khai phá sâu dữ liệu y tế đã qua Discretization.
  - Tạo 11 biểu đồ trực quan, bao gồm: Phân bố bệnh lý, Heatmap tỷ lệ điền trường theo hệ cơ quan, Biểu đồ mức độ nguy hiểm (Severity), Tính chất bệnh (Acute/Chronic), và Word Cloud.
  - Kết quả lưu tại: `image/processed/`

---

## 🕸️ Đồ thị Tri thức (Knowledge Graph)

Sau khi xử lý, dữ liệu được chuyển hóa thành Đồ thị Tri thức (Graph) hỗ trợ các truy vấn y tế nâng cao.

- **`src/graph/data_graph.py`**: Tạo bộ xương đồ thị gồm các node trung tâm: `Diseases` (Node gốc chứa toàn bộ thuộc tính discretization), `Symptoms`, `Causes`, `RiskFactors`, `Complications`, `Organs`.
- **`src/graph/enhance_graph_with_drugs_guidelines.py`**: Bổ sung chuyên sâu các node điều trị (`Drugs`, `Treatments`, `Guidelines`) vào Graph.
- **`src/neo4j/up_neo4j.py`**: Pipeline tự động đồng bộ hóa đồ thị JSON vào hệ quản trị cơ sở dữ liệu đồ thị Neo4j.

---

## 📂 Cấu trúc thư mục (Directory Structure)

```text
Project/
├── data/
│   ├── raw/                  # Dữ liệu gốc thu thập (mayo_full.json, medlineplus_full.json)
│   ├── processed/            # Dữ liệu lưu trung gian qua từng bước của pipeline
│   └── output/               # Các file xuất cuối cùng (.csv, quality report, graph.json)
├── image/
│   ├── raw/                  # Biểu đồ phân tích dữ liệu gốc
│   └── processed/            # Biểu đồ phân tích dữ liệu tinh & Heatmaps
├── src/
│   ├── processing/           # 7 module xử lý pipeline chính
│   ├── utils/                # Công cụ Data Mining, Charting & Phân tích
│   ├── graph/                # Khởi tạo và nâng cấp mô hình Knowledge Graph
│   └── neo4j/                # Script kết nối và đẩy dữ liệu lên Neo4j
└── README.md
```

---

## 🚀 Hướng dẫn sử dụng (Usage)

### 1. Cài đặt thư viện

Cài đặt các gói phân tích dữ liệu cần thiết:
```bash
pip install pandas matplotlib seaborn wordcloud neo4j python-dotenv
```

### 2. Chạy Pipeline Xử Lý Dữ Liệu
Quy trình được tự động hóa chỉ bằng một lệnh duy nhất:
```bash
python src/processing/run_pipeline.py
```

### 3. Phân tích Dữ liệu và Xuất Biểu đồ
Sau (hoặc trước) khi chạy pipeline, bạn có thể chạy các module thống kê để tạo báo cáo và biểu đồ:
```bash
# Phân tích dữ liệu gốc
python src/utils/raw_data_analysis.py

# Phân tích dữ liệu đã xử lý (Discretized Data)
python src/utils/data_analysis.py
```

### 4. Đẩy lên Neo4j
Mở phần mềm Neo4j Desktop hoặc Neo4j Aura. Cấu hình thông tin kết nối (URI, Username, Password) trong file `up_neo4j.py` hoặc `.env`, sau đó chạy:
```bash
# Bước 1: Khởi tạo đồ thị
python src/graph/data_graph.py

# Bước 2: Nâng cấp đồ thị (Thêm thuốc, Guideline)
python src/graph/enhance_graph_with_drugs_guidelines.py

# Bước 3: Đẩy vào Neo4j
python src/neo4j/up_neo4j.py
```

## 🧪 Ví dụ truy vấn Neo4j (Cypher Query)

**Tìm các phương pháp điều trị cho bệnh Tiểu đường loại 2:**
```cypher
MATCH (d:Disease {name: "Tiểu đường loại 2"})
MATCH (d)-[:TREATED_BY]->(r:Drug)
RETURN r.name AS Drug, r.class AS Class
```

**Tìm bệnh lý liên quan đến hệ cơ quan (Organ):**
```cypher
MATCH (o:Organ {name: "Tim"})<-[:AFFECTS]-(d:Disease)
RETURN d.name AS Disease, d.severity_level AS Severity
```