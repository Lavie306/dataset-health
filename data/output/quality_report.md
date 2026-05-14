# 📊 Báo Cáo Chất Lượng Dữ Liệu Y Tế

> **Thời gian tạo:** 2026-05-15 00:03:06  
> **Tổng bản ghi:** 3,234  
> **Nguồn dữ liệu:** Mayo Clinic + MedlinePlus

---

## 1. 🌐 Chất Lượng Dịch Thuật

| Trạng thái | Số lượng | Tỷ lệ |
|-----------|---------|-------|
| ✅ Dịch hoàn toàn | 3,044 | 94.1% |
| ⚠️ Còn một phần tiếng Anh | 3 | - |
| ❌ Phần lớn tiếng Anh | 0 | - |
| ❌ Chưa dịch tên bệnh | 187 | - |
| ℹ️ Không có nội dung | 0 | - |
| **Tổng vấn đề dịch** | - | **5.9%** |

---

## 2. 🔤 Chất Lượng Encoding

- **Bản ghi lỗi encoding:** 0 / 3,234 (0.0%)
- **Đánh giá:** Tốt

---

## 3. 📋 Độ Hoàn Chỉnh Từng Field

- **Bản ghi hoàn chỉnh (≥6 field):** 314 / 3,234 (9.7%)

| Field | Tỷ lệ điền | Avg từ | Đánh giá |
|-------|-----------|--------|---------|
| Tổng quan | 50.8% | 130.6 | Trung bình |
| Triệu chứng | 77.6% | 107.0 | Tốt |
| Nguyên nhân | 76.3% | 146.0 | Tốt |
| Yếu tố nguy cơ | 34.4% | 51.1 | Kém |
| Phòng ngừa | 45.0% | 59.0 | Trung bình |
| Khi nào gặp bác sĩ | 71.4% | 90.0 | Tốt |
| Điều trị | 45.3% | 82.0 | Trung bình |
| Tiên lượng | 64.9% | 42.1 | Trung bình |
| Biến chứng | 33.8% | 16.9 | Kém |
| Xét nghiệm/Khám | 44.9% | 52.0 | Trung bình |

---

## 4. 🔁 Trùng Lặp & Xung Đột

| Chỉ số | Giá trị |
|--------|---------|
| Tổng bản ghi | 3,234 |
| Trùng lặp exact | 0 |
| Bản ghi có xung đột nguồn | 455 |
| Tổng field xung đột | 836 |

**Phân bố theo nguồn:**
- medlineplus: 2,056
- both: 499
- mayo: 679

---

## 5. 🏥 Độ Bao Phủ ICD-10

- **Có mã ICD:** 403 / 3,234 (**12.5%**)
- **Đánh giá:** Cần cải thiện

**Phân bố theo chapter ICD:**

| Chapter | Số lượng |
|---------|---------|
| C – Ung thư | 74 |
| J – Hô hấp | 42 |
| I – Tim mạch | 39 |
| F – Tâm thần & hành vi | 34 |
| E – Nội tiết & chuyển hóa | 30 |
| A – Bệnh nhiễm khuẩn & ký sinh trùng | 29 |
| D – U lành & rối loạn máu | 26 |
| G – Thần kinh | 25 |
| B – Bệnh nhiễm khuẩn & virus | 21 |
| H – Mắt & Tai | 19 |
| M – Cơ xương khớp | 18 |
| L – Da liễu | 15 |
| N – Sinh dục & tiết niệu | 15 |
| K – Tiêu hóa | 15 |
| T – Khác | 1 |

---

## 6. 🗂️ Phân Bố Nhóm Bệnh

| Nhóm bệnh | Số lượng | Tỷ lệ |
|----------|---------|-------|
| Tim mạch | 731 | 22.6% |
| Ung thư | 496 | 15.3% |
| Thần kinh & Tâm thần | 414 | 12.8% |
| Nhiễm khuẩn & Virus | 408 | 12.6% |
| Cơ xương khớp | 206 | 6.4% |
| Tiêu hóa | 200 | 6.2% |
| Sinh dục & Tiết niệu | 161 | 5.0% |
| Mắt & Tai | 131 | 4.1% |
| Khác | 130 | 4.0% |
| Nội tiết & Chuyển hóa | 129 | 4.0% |
| Hô hấp | 94 | 2.9% |
| Da liễu | 92 | 2.8% |
| Miễn dịch & Tự miễn | 42 | 1.3% |

**Phân loại mãn tính / cấp tính:**

- Không xác định: 1,996 (61.7%)
- Mãn tính: 793 (24.5%)
- Cả hai: 229 (7.1%)
- Cấp tính: 216 (6.7%)

**Tình trạng lây nhiễm:**

- Không xác định: 2,659 (82.2%)
- Có lây: 516 (16.0%)
- Không lây: 59 (1.8%)

---

## 7. Chuẩn Hóa Thuật Ngữ Y Khoa

- **Số thuật ngữ trong glossary:** 136
- **Bản ghi còn thuật ngữ chưa chuẩn:** 0 / 3,234 (0.0%)
- **Đánh giá:** Tốt

---

*Báo cáo được tạo tự động bởi `quality_report.py`*