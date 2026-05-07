# 📊 Báo Cáo Chất Lượng Dữ Liệu Y Tế

> **Thời gian tạo:** 2026-05-07 22:55:53  
> **Tổng bản ghi:** 3,014  
> **Nguồn dữ liệu:** Mayo Clinic + MedlinePlus

---

## 1. 🌐 Chất Lượng Dịch Thuật

| Trạng thái | Số lượng | Tỷ lệ |
|-----------|---------|-------|
| ✅ Dịch hoàn toàn | 2,829 | 93.9% |
| ⚠️ Còn một phần tiếng Anh | 2 | - |
| ❌ Phần lớn tiếng Anh | 0 | - |
| ❌ Chưa dịch tên bệnh | 183 | - |
| ℹ️ Không có nội dung | 0 | - |
| **Tổng vấn đề dịch** | - | **6.1%** |

---

## 2. 🔤 Chất Lượng Encoding

- **Bản ghi lỗi encoding:** 0 / 3,014 (0.0%)
- **Đánh giá:** Tốt

---

## 3. 📋 Độ Hoàn Chỉnh Từng Field

- **Bản ghi hoàn chỉnh (≥6 field):** 281 / 3,014 (9.3%)

| Field | Tỷ lệ điền | Avg từ | Đánh giá |
|-------|-----------|--------|---------|
| Tổng quan | 51.3% | 131.3 | Trung bình |
| Triệu chứng | 77.3% | 107.7 | Tốt |
| Nguyên nhân | 76.7% | 145.9 | Tốt |
| Yếu tố nguy cơ | 34.9% | 51.8 | Kém |
| Phòng ngừa | 45.5% | 60.2 | Trung bình |
| Khi nào gặp bác sĩ | 71.9% | 91.1 | Tốt |
| Điều trị | 44.5% | 80.3 | Trung bình |
| Tiên lượng | 64.1% | 41.5 | Trung bình |
| Biến chứng | 33.2% | 16.4 | Kém |
| Xét nghiệm/Khám | 44.1% | 50.8 | Trung bình |

---

## 4. 🔁 Trùng Lặp & Xung Đột

| Chỉ số | Giá trị |
|--------|---------|
| Tổng bản ghi | 3,014 |
| Trùng lặp exact | 0 |
| Bản ghi có xung đột nguồn | 445 |
| Tổng field xung đột | 817 |

**Phân bố theo nguồn:**
- medlineplus: 1,902
- both: 444
- mayo: 668

---

## 5. 🏥 Độ Bao Phủ ICD-10

- **Có mã ICD:** 392 / 3,014 (**13.0%**)
- **Đánh giá:** Cần cải thiện

**Phân bố theo chapter ICD:**

| Chapter | Số lượng |
|---------|---------|
| C – Ung thư | 63 |
| J – Hô hấp | 61 |
| I – Tim mạch | 34 |
| F – Tâm thần & hành vi | 33 |
| G – Thần kinh | 30 |
| A – Bệnh nhiễm khuẩn & ký sinh trùng | 28 |
| E – Nội tiết & chuyển hóa | 27 |
| D – U lành & rối loạn máu | 23 |
| H – Mắt & Tai | 19 |
| M – Cơ xương khớp | 19 |
| B – Bệnh nhiễm khuẩn & virus | 19 |
| L – Da liễu | 13 |
| N – Sinh dục & tiết niệu | 12 |
| K – Tiêu hóa | 11 |

---

## 6. 🗂️ Phân Bố Nhóm Bệnh

| Nhóm bệnh | Số lượng | Tỷ lệ |
|----------|---------|-------|
| Tim mạch | 824 | 27.3% |
| Ung thư | 647 | 21.5% |
| Nhiễm khuẩn & Virus | 519 | 17.2% |
| Thần kinh & Tâm thần | 380 | 12.6% |
| Cơ xương khớp | 128 | 4.2% |
| Tiêu hóa | 117 | 3.9% |
| Da liễu | 106 | 3.5% |
| Nội tiết & Chuyển hóa | 87 | 2.9% |
| Khác | 82 | 2.7% |
| Hô hấp | 51 | 1.7% |
| Mắt & Tai | 41 | 1.4% |
| Sinh dục & Tiết niệu | 30 | 1.0% |
| Miễn dịch & Tự miễn | 2 | 0.1% |

**Phân loại mãn tính / cấp tính:**

- Không xác định: 1,869 (62.0%)
- Mãn tính: 729 (24.2%)
- Cả hai: 210 (7.0%)
- Cấp tính: 206 (6.8%)

**Tình trạng lây nhiễm:**

- Không xác định: 2,480 (82.3%)
- Có lây: 478 (15.9%)
- Không lây: 56 (1.9%)

---

*Báo cáo được tạo tự động bởi `quality_report.py`*