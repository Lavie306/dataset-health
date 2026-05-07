# 📊 Báo Cáo Phân Tích Dữ Liệu Thô (Raw Data Analysis)

> Báo cáo này thống kê tình trạng dữ liệu ngay sau khi thu thập (Crawl) từ Mayo Clinic và MedlinePlus, trước khi đưa vào hệ thống Tiền xử lý (Preprocessing).

## 1. Số liệu tổng quan

| Chỉ số | Mayo Clinic | MedlinePlus | Tổng cộng |
|--------|-------------|-------------|-----------|
| Tổng bản ghi cào được | **1,186** | **2,583** | **3,769** |
| Trùng lặp (cùng tên bệnh) | 0 | 0 | 0 |
| Bản ghi chứa nhiễu (Noise)* | 469 (39.5%) | 24 (0.9%) | - |
| Tổng số từ | 911,703 | 1,157,511 | 2,069,214 |
| Trung bình từ/bản ghi | 768.7 | 448.1 | - |

*(Nhiễu bao gồm: dính thẻ HTML chưa xử lý hết, các text rác như 'Enlarge image', 'Close', citation marks).* 

---

## 2. Mức độ đầy đủ của các trường (Field Completeness)

| Trường dữ liệu (Field) | Mayo Clinic (%) | MedlinePlus (%) |
|------------------------|-----------------|-----------------|
| Overview | 100.0% | 18.2% |
| Symptoms | 99.7% | 70.0% |
| Causes | 99.1% | 70.2% |
| Risk Factors | 94.5% | 0.0% |
| Prevention | 54.6% | 40.3% |
| When To See Doc | 88.8% | 65.5% |
| Treatment | 0.0% | 57.3% |
| Prognosis | 0.0% | 73.9% |
| Complications | 0.0% | 43.1% |
| Exams And Tests | 0.0% | 56.7% |

---

## 3. Kết luận về tính cấp thiết của Tiền xử lý

Qua các số liệu trên, ta thấy được các vấn đề rõ rệt của dữ liệu thô:
1. **Nhiễu cấu trúc (Noise):** Dữ liệu thu thập từ HTML thường kèm theo text thừa của giao diện website. Cần thực hiện làm sạch (Data Cleaning).
2. **Dữ liệu thưa thớt (Sparsity):** Có những trường tỷ lệ điền rất thấp (như Prognosis, Complications). Nếu để nguyên sẽ gây loãng dữ liệu. Cần chiến lược gộp hai nguồn để bổ sung cho nhau (Data Integration).
3. **Dữ liệu trùng lặp (Duplication):** Các bệnh bị lưu trùng dưới nhiều URL. Cần hợp nhất (Data Reduction/Merge).

*(Các biểu đồ tương ứng: `raw_1_overview_stats.png`, `raw_2_field_completeness.png`, `raw_3_wordcount_boxplot.png`, `raw_4_noise_ratio.png` được lưu cùng thư mục)*