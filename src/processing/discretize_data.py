"""
STEP 5 – DATA DISCRETIZATION  (MỚI HOÀN TOÀN)
===============================================
Input : data/processed/translated.json
Output: data/processed/discretized.json

Tính năng:
  ✅ ICD-10 mapping        – 200+ bệnh phổ biến → mã ICD-10 chuẩn quốc tế
  ✅ Disease category      – phân 13 nhóm bệnh
  ✅ Chronic vs Acute      – mãn tính / cấp tính / không xác định
  ✅ Contagious flag       – bệnh lây / không lây / không xác định
  ✅ Severity level        – Nhẹ / Trung bình / Nặng / Đe dọa tính mạng
  ✅ Target demographic    – Trẻ em / Người lớn / Người cao tuổi / Mọi lứa tuổi
  ✅ Word count bins       – phân nhóm độ phong phú nội dung

Chạy:
  cd src/processing && python discretize_data.py
"""

import json, re, pathlib, logging, time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("discretize")

ROOT     = pathlib.Path(__file__).parent.parent.parent
# Ưu tiên đọc reduced.json (sau bước Reduce), fallback về translated.json
REDUCED_FILE    = ROOT / "data/processed/reduced.json"
TRANSLATED_FILE = ROOT / "data/processed/translated.json"
IN_FILE  = REDUCED_FILE if REDUCED_FILE.exists() else TRANSLATED_FILE
OUT_FILE = ROOT / "data/processed/discretized.json"

# =============================================================================
# ICD-10 MAPPING TABLE  (tên bệnh tiếng Anh/Việt → mã ICD-10)
# =============================================================================
ICD10_MAP: dict[str, str] = {
    # Bệnh nhiễm khuẩn & ký sinh trùng (A00–B99)
    "cholera": "A00", "typhoid fever": "A01", "salmonella": "A02",
    "shigellosis": "A03", "tuberculosis": "A15", "lao": "A15",
    "leprosy": "A30", "tetanus": "A33", "diphtheria": "A36",
    "whooping cough": "A37", "meningococcal": "A39",
    "sepsis": "A41", "many septicemia": "A41",
    "lyme disease": "A69.2", "syphilis": "A50", "gonorrhea": "A54",
    "chlamydia": "A56", "hiv": "B20", "aids": "B20", "hiv aids": "B20",
    "mumps": "B26", "rubella": "B06", "measles": "B05", "sởi": "B05",
    "chickenpox": "B01", "shingles": "B02", "herpes zoster": "B02",
    "dengue fever": "A90", "dengue": "A90", "malaria": "B50",
    "hepatitis a": "B15", "hepatitis b": "B16", "viêm gan b": "B16",
    "hepatitis c": "B17.1", "viêm gan c": "B17.1",
    "influenza": "J10", "flu": "J10",

    # Ung thư (C00–D49)
    "lip cancer": "C00", "oral cancer": "C06",
    "esophageal cancer": "C15", "stomach cancer": "C16",
    "colorectal cancer": "C18", "colon cancer": "C18",
    "rectal cancer": "C20", "liver cancer": "C22",
    "pancreatic cancer": "C25", "lung cancer": "C34", "ung thư phổi": "C34",
    "breast cancer": "C50", "ung thư vú": "C50",
    "cervical cancer": "C53", "uterine cancer": "C54",
    "ovarian cancer": "C56", "prostate cancer": "C61",
    "bladder cancer": "C67", "kidney cancer": "C64",
    "thyroid cancer": "C73", "brain tumor": "C71",
    "leukemia": "C95", "lymphoma": "C85",
    "melanoma": "C43", "skin cancer": "C44",
    "multiple myeloma": "C90",

    # Rối loạn nội tiết & chuyển hóa (E00–E90)
    "hypothyroidism": "E03", "suy giáp": "E03",
    "hyperthyroidism": "E05", "cường giáp": "E05",
    "diabetes mellitus": "E11", "diabetes": "E11", "tiểu đường": "E11",
    "type 1 diabetes": "E10", "type 2 diabetes": "E11",
    "obesity": "E66", "béo phì": "E66",
    "gout": "M10", "gut": "M10",
    "vitamin d deficiency": "E55", "thiếu vitamin d": "E55",
    "anemia": "D64", "thiếu máu": "D64",
    "iron deficiency anemia": "D50",

    # Tâm thần & thần kinh (F00–G99)
    "alzheimer disease": "F00", "alzheimers disease": "F00",
    "alzheimer": "F00", "dementia": "F03",
    "depression": "F32", "trầm cảm": "F32",
    "anxiety disorder": "F41", "lo âu": "F41",
    "bipolar disorder": "F31", "rối loạn lưỡng cực": "F31",
    "schizophrenia": "F20", "tâm thần phân liệt": "F20",
    "panic disorder": "F41.0",
    "obsessive compulsive disorder": "F42", "ocd": "F42",
    "post traumatic stress disorder": "F43.1", "ptsd": "F43.1",
    "autism": "F84.0", "tự kỷ": "F84.0",
    "adhd": "F90",
    "parkinson disease": "G20", "parkinson": "G20",
    "epilepsy": "G40", "động kinh": "G40",
    "migraine": "G43", "đau nửa đầu": "G43",
    "multiple sclerosis": "G35",
    "amyotrophic lateral sclerosis": "G12.2", "als": "G12.2",
    "carpal tunnel syndrome": "G56.0",

    # Tim mạch (I00–I99)
    "rheumatic fever": "I00",
    "high blood pressure": "I10", "hypertension": "I10", "cao huyết áp": "I10",
    "coronary artery disease": "I25", "bệnh mạch vành": "I25",
    "myocardial infarction": "I21", "heart attack": "I21", "nhồi máu cơ tim": "I21",
    "heart failure": "I50", "suy tim": "I50",
    "atrial fibrillation": "I48", "rung nhĩ": "I48",
    "stroke": "I64", "đột quỵ": "I64",
    "deep vein thrombosis": "I82", "dvt": "I82",
    "pulmonary embolism": "I26", "thuyên tắc phổi": "I26",
    "aortic aneurysm": "I71",
    "peripheral artery disease": "I73",
    "varicose veins": "I83", "giãn tĩnh mạch": "I83",

    # Hô hấp (J00–J99)
    "common cold": "J00", "cảm lạnh": "J00",
    "sinusitis": "J32", "viêm xoang": "J32",
    "asthma": "J45", "hen suyễn": "J45",
    "pneumonia": "J18", "viêm phổi": "J18",
    "copd": "J44", "chronic obstructive pulmonary disease": "J44",
    "pulmonary fibrosis": "J84",
    "sleep apnea": "G47.3", "ngưng thở khi ngủ": "G47.3",

    # Tiêu hóa (K00–K95)
    "gastroesophageal reflux": "K21", "gerd": "K21", "trào ngược": "K21",
    "peptic ulcer": "K25", "loét dạ dày": "K25",
    "irritable bowel syndrome": "K58", "ibs": "K58",
    "crohn disease": "K50", "ulcerative colitis": "K51",
    "appendicitis": "K37", "viêm ruột thừa": "K37",
    "gallstones": "K80", "sỏi mật": "K80",
    "cirrhosis": "K74", "xơ gan": "K74",
    "celiac disease": "K90.0",
    "hemorrhoids": "K64", "trĩ": "K64",

    # Da liễu (L00–L99)
    "psoriasis": "L40", "vảy nến": "L40",
    "eczema": "L20", "chàm": "L20",
    "atopic dermatitis": "L20",
    "acne": "L70", "mụn trứng cá": "L70",
    "urticaria": "L50", "mề đay": "L50",
    "rosacea": "L71",
    "alopecia": "L63", "rụng tóc": "L63",

    # Cơ xương khớp (M00–M99)
    "rheumatoid arthritis": "M05", "viêm khớp dạng thấp": "M05",
    "osteoarthritis": "M15", "thoái hóa khớp": "M15",
    "osteoporosis": "M81", "loãng xương": "M81",
    "fibromyalgia": "M79.3",
    "back pain": "M54.5", "đau lưng": "M54.5",
    "scoliosis": "M41",
    "lupus": "M32", "lupus erythematosus": "M32",

    # Sinh dục & tiết niệu (N00–N99)
    "kidney stones": "N20", "sỏi thận": "N20",
    "urinary tract infection": "N39.0", "uti": "N39.0",
    "chronic kidney disease": "N18", "suy thận mạn": "N18",
    "kidney failure": "N17",
    "benign prostatic hyperplasia": "N40", "u xơ tuyến tiền liệt": "N40",
    "endometriosis": "N80",
    "polycystic ovary syndrome": "N83.0", "pcos": "N83.0",
    "erectile dysfunction": "N52",

    # Mắt (H00–H59)
    "cataracts": "H26", "đục thủy tinh thể": "H26",
    "glaucoma": "H40", "tăng nhãn áp": "H40",
    "macular degeneration": "H35.3",
    "diabetic retinopathy": "H36.0",

    # Tai (H60–H95)
    "hearing loss": "H91", "điếc": "H91",
    "tinnitus": "H93.1", "ù tai": "H93.1",
    "vertigo": "H81", "chóng mặt": "H81",
}

# =============================================================================
# DISEASE CATEGORY TABLE  (13 nhóm)
# =============================================================================
DISEASE_CATEGORIES: list[tuple[str, list[str]]] = [
    ("Ung thư", [
        "ung thư", "cancer", "carcinoma", "lymphoma", "leukemia",
        "tumor", "melanoma", "sarcoma", "myeloma", "neoplasm",
        "malignant", "khối u ác tính",
    ]),
    ("Tim mạch", [
        "tim", "heart", "cardiac", "mạch vành", "coronary",
        "huyết áp", "blood pressure", "hypertension", "nhồi máu",
        "myocardial", "atrial", "artery", "arterial", "vascular",
        "stroke", "đột quỵ", "thrombosis", "embolism",
    ]),
    ("Thần kinh & Tâm thần", [
        "alzheimer", "parkinson", "epilepsy", "động kinh", "migraine",
        "multiple sclerosis", "dementia", "neuropathy", "thần kinh",
        "depression", "trầm cảm", "anxiety", "lo âu", "bipolar",
        "schizophrenia", "tâm thần", "autism", "tự kỷ", "adhd",
        "insomnia", "mất ngủ", "ptsd",
    ]),
    ("Nhiễm khuẩn & Virus", [
        "infection", "nhiễm", "viêm gan", "hepatitis", "hiv", "aids",
        "tuberculosis", "lao", "pneumonia", "viêm phổi",
        "influenza", "dengue", "malaria", "sepsis", "bacterial",
        "viral", "fungal", "parasitic", "covid",
    ]),
    ("Nội tiết & Chuyển hóa", [
        "tiểu đường", "diabetes", "thyroid", "tuyến giáp",
        "obesity", "béo phì", "metabolic", "gout", "vitamin",
        "hormone", "adrenal", "pituitary", "endocrine",
    ]),
    ("Hô hấp", [
        "phổi", "lung", "asthma", "hen", "copd", "respiratory",
        "bronchitis", "sinusitis", "xoang", "pneumonia",
        "sleep apnea", "pulmonary", "trachea",
    ]),
    ("Tiêu hóa", [
        "gan", "liver", "dạ dày", "stomach", "ruột", "bowel",
        "intestin", "colon", "gallbladder", "mật", "tụy", "pancreas",
        "gastro", "digest", "ulcer", "loét", "cirrhosis", "xơ gan",
    ]),
    ("Cơ xương khớp", [
        "xương", "bone", "khớp", "joint", "arthritis", "viêm khớp",
        "osteo", "cột sống", "spine", "muscle", "fibromyalgia",
        "lupus", "gout", "scoliosis",
    ]),
    ("Da liễu", [
        "da", "skin", "dermatitis", "eczema", "chàm",
        "psoriasis", "vảy nến", "acne", "mụn", "rash",
        "urticaria", "mề đay", "rosacea", "alopecia", "tóc",
    ]),
    ("Sinh dục & Tiết niệu", [
        "thận", "kidney", "renal", "tiết niệu", "urinary",
        "bàng quang", "bladder", "prostate", "tuyến tiền liệt",
        "phụ khoa", "gynecol", "buồng trứng", "ovarian",
        "tử cung", "uterus", "endometriosis",
    ]),
    ("Mắt & Tai", [
        "mắt", "eye", "vision", "retina", "glaucoma", "cataract",
        "tai", "ear", "hearing", "tinnitus", "vertigo", "chóng mặt",
    ]),
    ("Miễn dịch & Tự miễn", [
        "miễn dịch", "immune", "autoimmune", "tự miễn", "allergy",
        "dị ứng", "rheumatoid", "lupus", "sjogren", "hashimoto",
    ]),
    ("Khác", []),  # Fallback
]

# =============================================================================
# CHRONIC / ACUTE KEYWORDS
# =============================================================================
CHRONIC_KEYWORDS = re.compile(
    r'\b(mãn tính|chronic|long.term|lifelong|suốt đời|không chữa được'
    r'|kiểm soát|ongoing|persistent|recurrent|relapsing)\b',
    re.IGNORECASE
)
ACUTE_KEYWORDS = re.compile(
    r'\b(cấp tính|acute|sudden|onset|sudden onset|đột ngột|cơn cấp'
    r'|short.term|temporary|transient)\b',
    re.IGNORECASE
)

# =============================================================================
# CONTAGIOUS KEYWORDS
# =============================================================================
CONTAGIOUS_KEYWORDS = re.compile(
    r'\b(lây|truyền nhiễm|contagious|infectious|transmissible|spread'
    r'|airborne|droplet|contact|lây lan|lây qua|truyền qua)\b',
    re.IGNORECASE
)
NON_CONTAGIOUS_KEYWORDS = re.compile(
    r'\b(không lây|not contagious|non.infectious|không truyền nhiễm'
    r'|cannot spread|không thể lây)\b',
    re.IGNORECASE
)

# =============================================================================
# SEVERITY KEYWORDS
# =============================================================================
LIFE_THREATENING = re.compile(
    r'\b(tử vong|fatal|life.threatening|mortal|deadly|death'
    r'|đe dọa tính mạng|nguy hiểm tính mạng|tỷ lệ tử vong)\b',
    re.IGNORECASE
)
SEVERE_KEYWORDS = re.compile(
    r'\b(nghiêm trọng|severe|serious|critical|nặng|biến chứng nặng'
    r'|nhập viện|hospitalization|emergency)\b',
    re.IGNORECASE
)
MILD_KEYWORDS = re.compile(
    r'\b(nhẹ|mild|minor|benign|self.limiting|tự khỏi'
    r'|không nghiêm trọng|manageable)\b',
    re.IGNORECASE
)

# =============================================================================
# DEMOGRAPHIC KEYWORDS
# =============================================================================
CHILDREN_KEYWORDS = re.compile(
    r'\b(trẻ em|children|pediatric|infant|newborn|trẻ sơ sinh'
    r'|childhood|nhi|congenital|bẩm sinh)\b',
    re.IGNORECASE
)
ELDERLY_KEYWORDS = re.compile(
    r'\b(người cao tuổi|elderly|older adults|aging|geriatric'
    r'|người già|lão hóa|tuổi già|age.related)\b',
    re.IGNORECASE
)

# =============================================================================
# CONTENT WORD COUNT BINS
# =============================================================================
WORD_COUNT_BINS = [
    (0,    99,   "Rất ít (<100 từ)"),
    (100,  299,  "Ít (100-299 từ)"),
    (300,  599,  "Trung bình (300-599 từ)"),
    (600,  999,  "Khá đầy đủ (600-999 từ)"),
    (1000, 1999, "Đầy đủ (1000-1999 từ)"),
    (2000, 9999, "Rất đầy đủ (≥2000 từ)"),
]

CONTENT_FIELDS = [
    "overview", "symptoms", "causes",
    "risk_factors", "prevention", "when_to_see_doc",
    "treatment", "prognosis", "complications", "exams_and_tests",
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_name(name: str) -> str:
    """Chuẩn hóa tên bệnh để tra cứu ICD."""
    name = name.lower().strip()
    name = re.sub(r"[''`']", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def total_words(record: dict) -> int:
    return sum(len((record.get(f, "") or "").split()) for f in CONTENT_FIELDS)


def full_text(record: dict) -> str:
    """Ghép tất cả nội dung để phân tích từ khóa."""
    parts = [record.get(f, "") or "" for f in ["disease", "overview", "symptoms", "causes", "treatment"]]
    return " ".join(parts)


# =============================================================================
# DISCRETIZATION FUNCTIONS
# =============================================================================

def assign_icd10(record: dict) -> str:
    """Tra cứu mã ICD-10 theo tên bệnh tiếng Anh và tiếng Việt."""
    name_vi  = normalize_name(record.get("disease", ""))
    name_en  = normalize_name(record.get("disease_en", "") or record.get("disease", ""))

    # Tra cứu trực tiếp
    if name_en in ICD10_MAP:
        return ICD10_MAP[name_en]
    if name_vi in ICD10_MAP:
        return ICD10_MAP[name_vi]

    # Partial match — tìm key nào là substring của tên bệnh
    for key, code in ICD10_MAP.items():
        if key in name_en or key in name_vi:
            return code
        if len(key) > 5 and (key in name_en or key in name_vi):
            return code

    return ""  # Chưa có mã ICD


def assign_category(record: dict) -> str:
    """Phân loại bệnh vào 1 trong 13 nhóm."""
    text = full_text(record).lower()

    for category_name, keywords in DISEASE_CATEGORIES[:-1]:  # Bỏ "Khác"
        if any(kw in text for kw in keywords):
            return category_name

    return "Khác"


def assign_chronic_acute(record: dict) -> str:
    """Phân loại: Mãn tính / Cấp tính / Không xác định."""
    text = full_text(record)
    is_chronic = bool(CHRONIC_KEYWORDS.search(text))
    is_acute   = bool(ACUTE_KEYWORDS.search(text))

    if is_chronic and not is_acute:
        return "Mãn tính"
    if is_acute and not is_chronic:
        return "Cấp tính"
    if is_chronic and is_acute:
        return "Cả hai"   # VD: bệnh có đợt cấp
    return "Không xác định"


def assign_contagious(record: dict) -> str:
    """Phân loại: Có lây / Không lây / Không xác định."""
    text = full_text(record)
    is_contagious     = bool(CONTAGIOUS_KEYWORDS.search(text))
    is_non_contagious = bool(NON_CONTAGIOUS_KEYWORDS.search(text))

    if is_non_contagious:
        return "Không lây"
    if is_contagious:
        return "Có lây"
    return "Không xác định"


def assign_severity(record: dict) -> str:
    """Phân loại mức độ nặng: Nhẹ / Trung bình / Nặng / Đe dọa tính mạng."""
    text = full_text(record)
    if LIFE_THREATENING.search(text):
        return "Đe dọa tính mạng"
    if SEVERE_KEYWORDS.search(text):
        return "Nặng"
    if MILD_KEYWORDS.search(text):
        return "Nhẹ"
    return "Trung bình"


def assign_demographic(record: dict) -> str:
    """Phân loại đối tượng: Trẻ em / Người cao tuổi / Mọi lứa tuổi / Người lớn."""
    text = full_text(record)
    is_children = bool(CHILDREN_KEYWORDS.search(text))
    is_elderly  = bool(ELDERLY_KEYWORDS.search(text))

    if is_children and is_elderly:
        return "Mọi lứa tuổi"
    if is_children:
        return "Trẻ em"
    if is_elderly:
        return "Người cao tuổi"
    return "Người lớn"


def assign_content_bin(record: dict) -> str:
    """Phân nhóm độ phong phú nội dung theo tổng số từ."""
    wc = total_words(record)
    for lo, hi, label in WORD_COUNT_BINS:
        if lo <= wc <= hi:
            return label
    return f"Rất đầy đủ (≥2000 từ)"


def discretize_record(record: dict) -> dict:
    """Áp dụng tất cả discretization cho 1 record."""
    rec = dict(record)

    rec["icd_code"]          = assign_icd10(rec)
    rec["disease_category"]  = assign_category(rec)
    rec["disease_type"]      = assign_chronic_acute(rec)
    rec["is_contagious"]     = assign_contagious(rec)
    rec["severity_level"]    = assign_severity(rec)
    rec["target_demographic"]= assign_demographic(rec)
    rec["content_richness"]  = assign_content_bin(rec)
    rec["total_words"]       = total_words(rec)

    return rec


# =============================================================================
# MAIN
# =============================================================================

def run():
    t0 = time.time()

    log.info(f"Loading {IN_FILE} …")
    with open(IN_FILE, encoding="utf-8") as f:
        records = json.load(f)
    log.info(f"  {len(records)} records")

    discretized = [discretize_record(r) for r in records]

    # ── Stats ─────────────────────────────────────────────────────────────────
    total = len(discretized)
    icd_covered   = sum(1 for r in discretized if r["icd_code"])
    cat_counts    = {}
    type_counts   = {}
    contagious_counts = {}
    severity_counts   = {}

    for r in discretized:
        cat = r["disease_category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        t = r["disease_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
        c = r["is_contagious"]
        contagious_counts[c] = contagious_counts.get(c, 0) + 1
        s = r["severity_level"]
        severity_counts[s] = severity_counts.get(s, 0) + 1

    # ── Save ──────────────────────────────────────────────────────────────────
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(discretized, f, ensure_ascii=False, indent=2)

    log.info(f"Saved → {OUT_FILE}")
    log.info("─" * 55)
    log.info(f"ICD-10 coverage    : {icd_covered}/{total} ({icd_covered/total*100:.1f}%)")
    log.info("Disease categories :")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {cat:<30}: {cnt:>5,}")
    log.info("Disease type       :")
    for t, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {t:<20}: {cnt:>5,}")
    log.info("Contagious         :")
    for c, cnt in sorted(contagious_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {c:<20}: {cnt:>5,}")
    log.info("Severity           :")
    for s, cnt in sorted(severity_counts.items(), key=lambda x: -x[1]):
        log.info(f"  {s:<30}: {cnt:>5,}")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()
