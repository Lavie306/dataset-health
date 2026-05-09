# 📊 Báo Cáo Chất Lượng Dữ Liệu Y Tế

> **Thời gian tạo:** 2026-05-09 13:01:15  
> **Tổng bản ghi:** 3,298  
> **Nguồn dữ liệu:** Mayo Clinic + MedlinePlus

---

## 1. 🌐 Chất Lượng Dịch Thuật

| Trạng thái | Số lượng | Tỷ lệ |
|-----------|---------|-------|
| ✅ Dịch hoàn toàn | 3,105 | 94.1% |
| ⚠️ Còn một phần tiếng Anh | 3 | - |
| ❌ Phần lớn tiếng Anh | 0 | - |
| ❌ Chưa dịch tên bệnh | 190 | - |
| ℹ️ Không có nội dung | 0 | - |
| **Tổng vấn đề dịch** | - | **5.9%** |

---

## 2. 🔤 Chất Lượng Encoding

- **Bản ghi lỗi encoding:** 0 / 3,298 (0.0%)
- **Đánh giá:** Tốt

---

## 3. 📋 Độ Hoàn Chỉnh Từng Field

- **Bản ghi hoàn chỉnh (≥6 field):** 291 / 3,298 (8.8%)

| Field | Tỷ lệ điền | Avg từ | Đánh giá |
|-------|-----------|--------|---------|
| Tổng quan | 50.1% | 128.8 | Trung bình |
| Triệu chứng | 77.6% | 106.8 | Tốt |
| Nguyên nhân | 76.7% | 145.5 | Tốt |
| Yếu tố nguy cơ | 34.0% | 50.3 | Kém |
| Phòng ngừa | 44.9% | 58.6 | Trung bình |
| Khi nào gặp bác sĩ | 71.5% | 89.3 | Tốt |
| Điều trị | 44.8% | 81.0 | Trung bình |
| Tiên lượng | 64.3% | 41.5 | Trung bình |
| Biến chứng | 33.3% | 16.6 | Kém |
| Xét nghiệm/Khám | 44.4% | 51.3 | Trung bình |

---

## 4. 🔁 Trùng Lặp & Xung Đột

| Chỉ số | Giá trị |
|--------|---------|
| Tổng bản ghi | 3,298 |
| Trùng lặp exact | 62 |
| Bản ghi có xung đột nguồn | 445 |
| Tổng field xung đột | 817 |

**Phân bố theo nguồn:**
- medlineplus: 2,112
- both: 461
- mayo: 725

---

## 5. 🏥 Độ Bao Phủ ICD-10

- **Có mã ICD:** 453 / 3,298 (**13.7%**)
- **Đánh giá:** Cần cải thiện

**Phân bố theo chapter ICD:**

| Chapter | Số lượng |
|---------|---------|
| C – Ung thư | 80 |
| J – Hô hấp | 70 |
| I – Tim mạch | 40 |
| F – Tâm thần & hành vi | 35 |
| G – Thần kinh | 34 |
| E – Nội tiết & chuyển hóa | 32 |
| A – Bệnh nhiễm khuẩn & ký sinh trùng | 31 |
| D – U lành & rối loạn máu | 26 |
| B – Bệnh nhiễm khuẩn & virus | 25 |
| M – Cơ xương khớp | 20 |
| H – Mắt & Tai | 19 |
| N – Sinh dục & tiết niệu | 15 |
| L – Da liễu | 13 |
| K – Tiêu hóa | 13 |

---

## 6. 🗂️ Phân Bố Nhóm Bệnh

| Nhóm bệnh | Số lượng | Tỷ lệ |
|----------|---------|-------|
| Tim mạch | 907 | 27.5% |
| Ung thư | 707 | 21.4% |
| Nhiễm khuẩn & Virus | 566 | 17.2% |
| Thần kinh & Tâm thần | 423 | 12.8% |
| Cơ xương khớp | 132 | 4.0% |
| Tiêu hóa | 131 | 4.0% |
| Da liễu | 112 | 3.4% |
| Nội tiết & Chuyển hóa | 98 | 3.0% |
| Khác | 90 | 2.7% |
| Hô hấp | 55 | 1.7% |
| Mắt & Tai | 44 | 1.3% |
| Sinh dục & Tiết niệu | 31 | 0.9% |
| Miễn dịch & Tự miễn | 2 | 0.1% |

**Phân loại mãn tính / cấp tính:**

- Không xác định: 2,039 (61.8%)
- Mãn tính: 807 (24.5%)
- Cả hai: 234 (7.1%)
- Cấp tính: 218 (6.6%)

**Tình trạng lây nhiễm:**

- Không xác định: 2,711 (82.2%)
- Có lây: 527 (16.0%)
- Không lây: 60 (1.8%)

---

*Báo cáo được tạo tự động bởi `quality_report.py`*