import re

CONTENT_FIELDS = [
    "overview", "symptoms", "causes", "risk_factors",
    "prevention", "when_to_see_doc", "treatment",
    "prognosis", "complications", "exams_and_tests",
]

FIELD_LABELS_VI = {
    "overview":        "Tổng quan",
    "symptoms":        "Triệu chứng",
    "causes":          "Nguyên nhân",
    "risk_factors":    "Yếu tố nguy cơ",
    "prevention":      "Phòng ngừa",
    "when_to_see_doc": "Khi nào gặp bác sĩ",
    "treatment":       "Điều trị",
    "prognosis":       "Tiên lượng",
    "complications":   "Biến chứng",
    "exams_and_tests": "Xét nghiệm/Khám",
}

# Regex đếm từ chuẩn xác: chỉ đếm các từ bao gồm chữ cái (có tiếng Việt) và số, bỏ qua các dấu câu đứng riêng lẻ.
WORD_PATTERN = re.compile(r'\b[\wÀ-ỹ]+\b')

def wc(text):
    """Đếm số lượng từ trong văn bản."""
    if not text or not isinstance(text, str):
        return 0
    return len(WORD_PATTERN.findall(text))

def wc_total(record):
    """Tính tổng số từ của tất cả các field nội dung trong bản ghi."""
    return sum(wc(record.get(f, "")) for f in CONTENT_FIELDS)

ORGAN_MAPPING = [
    {"system": "Hệ tuần hoàn", "keywords": ["tim", "mạch vành", "cơ tim", "huyết áp", "động mạch", "tĩnh mạch", "nhồi máu", "máu", "bạch cầu", "hồng cầu", "thiếu máu", "huyết khối"]},
    {"system": "Hệ hô hấp", "keywords": ["phổi", "hô hấp", "phế quản", "hen suyễn", "lao", "tràn dịch", "viêm xoang", "thanh quản"]},
    {"system": "Hệ tiêu hóa", "keywords": ["gan", "viêm gan", "xơ gan", "mật", "dạ dày", "bao tử", "tá tràng", "tiêu hóa", "ruột", "đại tràng", "trĩ", "tụy", "túi mật", "đường mật", "răng", "nướu", "nha chu", "miệng", "viêm lợi"]},
    {"system": "Hệ bài tiết", "keywords": ["thận", "tiết niệu", "bàng quang", "niệu đạo", "sỏi niệu"]},
    {"system": "Hệ thần kinh", "keywords": ["não", "thần kinh", "đột quỵ", "chứng mất trí", "alzheimer", "động kinh", "parkinson", "chóng mặt"]},
    {"system": "Hệ vận động", "keywords": ["xương", "khớp", "cột sống", "thoái hóa khớp", "loãng xương", "gút", "cơ", "dây chằng"]},
    {"system": "Hệ vỏ bọc", "keywords": ["da", "viêm da", "vảy nến", "hắc lào", "lang ben", "mụn", "mề đay", "nấm"]},
    {"system": "Hệ nội tiết", "keywords": ["tuyến giáp", "cường giáp", "suy giáp", "đái tháo đường", "tiểu đường", "nội tiết"]},
    {"system": "Hệ sinh sản", "keywords": ["tử cung", "buồng trứng", "âm đạo", "kinh nguyệt", "phụ khoa", "vú", "mang thai", "tiền liệt", "tinh hoàn", "dương vật", "nam khoa", "tinh trùng", "rối loạn cương dương"]},
    {"system": "Cơ quan cảm giác", "keywords": ["mắt", "thị giác", "giác mạc", "võng mạc", "thủy tinh thể", "đục", "cườm", "lác", "tai", "mũi", "họng"]},
    {"system": "Hệ miễn dịch", "keywords": ["miễn dịch", "bạch huyết", "hạch", "lách", "lupus", "hiv", "aids", "tự miễn"]},
]

def assign_organ_systems(disease_name):
    """Hỗ trợ Multi-label: trả về danh sách các hệ cơ quan liên quan đến bệnh. Trả về ['Khác'] nếu không tìm thấy."""
    if not disease_name:
        return ["Khác"]
    name_lower = str(disease_name).lower()
    systems = []
    for o in ORGAN_MAPPING:
        if any(kw in name_lower for kw in o["keywords"]):
            systems.append(o["system"])
    return systems if systems else ["Khác"]
