# 📊 Báo Cáo Phân Tích Dữ Liệu Thô (Raw Data Analysis)

> Báo cáo này thống kê tình trạng dữ liệu ngay sau khi thu thập (Crawl) từ Mayo Clinic và MedlinePlus, trước khi đưa vào hệ thống Tiền xử lý (Preprocessing).

## 1. Số liệu tổng quan

| Chỉ số | Mayo Clinic | MedlinePlus | Tổng cộng sau khi gộp |
|--------|-------------|-------------|-----------|
| Bản ghi độc quyền | **679** | **2,056** | - |
| Bản ghi giao thoa (Cả hai) | **499** | **499** | - |
| **Tổng bản ghi duy nhất** | 1,186 | 2,583 | **3,234** |
| Bản ghi chứa nhiễu HTML | 469 (39.5%) | 24 (0.9%) | - |
| Tổng số từ (Word Count) | 928,683 | 1,160,754 | 2,089,437 |
| Trung bình từ/bản ghi | 783.0 | 449.4 | - |

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
3. **Dữ liệu trùng lặp (Duplication):** Rất nhiều bệnh xuất hiện ở cả hai nền tảng. Cần thực thi thuật toán SequenceMatcher để tìm và hợp nhất.

*(Các biểu đồ minh họa đã được lưu cùng thư mục)*