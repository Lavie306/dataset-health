"""
enhance_graph_with_drugs_guidelines.py - Bổ sung Drugs và Guidelines vào Knowledge Graph
========================================================================================

Tinh chỉnh mục tiêu:
  - Trích xuất các tên thuốc từ field 'treatment' và 'prevention'
  - Tạo Guideline nodes từ các hướng dẫn điều trị
  - Tạo thêm relationship:
      * Disease -[TREATED_BY]-> Drug
      * Disease -[MANAGED_BY]-> Treatment (cải thiện hiện có)
      * Disease -[FOLLOWS]-> Guideline

Input:  
  - data/processed/translated.json (dữ liệu bệnh)
  - Tệp drug database (nếu có)
  
Output:
  - data/graph/drugs.json (danh sách thuốc)
  - data/graph/guidelines.json (danh sách hướng dẫn)
  - Cập nhật edges.json với mối quan hệ mới
"""

import json
import re
import pathlib
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("enhance_graph")

# ============================= CẤU HÌNH ======================================

# Danh sách các tên thuốc thông dụng (tiếng Việt & tiếng Anh)
COMMON_DRUGS = {
    # Kháng sinh
    "amoxicillin": {"generic": "Amoxicillin", "class": "Kháng sinh"},
    "penicillin": {"generic": "Penicillin", "class": "Kháng sinh"},
    "azithromycin": {"generic": "Azithromycin", "class": "Kháng sinh"},
    "doxycycline": {"generic": "Doxycycline", "class": "Kháng sinh"},
    "metronidazole": {"generic": "Metronidazole", "class": "Kháng sinh"},
    "tetracycline": {"generic": "Tetracycline", "class": "Kháng sinh"},
    "erythromycin": {"generic": "Erythromycin", "class": "Kháng sinh"},
    "ciprofloxacin": {"generic": "Ciprofloxacin", "class": "Kháng sinh"},
    
    # Thuốc chống viêm
    "ibuprofen": {"generic": "Ibuprofen", "class": "Thuốc chống viêm"},
    "aspirin": {"generic": "Aspirin", "class": "Thuốc chống viêm"},
    "paracetamol": {"generic": "Paracetamol", "class": "Thuốc hạ sốt"},
    "acetaminophen": {"generic": "Acetaminophen", "class": "Thuốc hạ sốt"},
    "naproxen": {"generic": "Naproxen", "class": "Thuốc chống viêm"},
    
    # Thuốc điều trị tiểu đường
    "insulin": {"generic": "Insulin", "class": "Thuốc tiểu đường"},
    "metformin": {"generic": "Metformin", "class": "Thuốc tiểu đường"},
    "glibenclamide": {"generic": "Glibenclamide", "class": "Thuốc tiểu đường"},
    
    # Thuốc tim mạch
    "lisinopril": {"generic": "Lisinopril", "class": "Thuốc huyết áp"},
    "atorvastatin": {"generic": "Atorvastatin", "class": "Thuốc hạ cholesterol"},
    "warfarin": {"generic": "Warfarin", "class": "Thuốc chống đông"},
    "heparin": {"generic": "Heparin", "class": "Thuốc chống đông"},
    
    # Thuốc dạ dày
    "omeprazole": {"generic": "Omeprazole", "class": "Thuốc trị loét dạ dày"},
    "ranitidine": {"generic": "Ranitidine", "class": "Thuốc trị loét dạ dày"},
    
    # Hormone
    "estrogen": {"generic": "Estrogen", "class": "Hormone nữ"},
    "testosterone": {"generic": "Testosterone", "class": "Hormone nam"},
    "cortisol": {"generic": "Cortisol", "class": "Corticosteroid"},
    "prednisone": {"generic": "Prednisone", "class": "Corticosteroid"},
    "hydrocortisone": {"generic": "Hydrocortisone", "class": "Corticosteroid"},
    
    # Thuốc tâm thần
    "sertraline": {"generic": "Sertraline", "class": "Thuốc chống trầm cảm"},
    "fluoxetine": {"generic": "Fluoxetine", "class": "Thuốc chống trầm cảm"},
    
    # Kiểm tra mở rộng - các biến thể
    "benzoyl peroxide": {"generic": "Benzoyl Peroxide", "class": "Thuốc trị mụn"},
    "tretinoin": {"generic": "Tretinoin", "class": "Thuốc trị mụn"},
    "isotretinoin": {"generic": "Isotretinoin", "class": "Thuốc trị mụn"},
}

# Danh sách từ khoá định nghĩa "hướng dẫn" trong text
GUIDELINE_KEYWORDS = [
    "hướng dẫn", "kiến nghị", "khuyến cáo", "lưu ý", "cần phải",
    "nên", "phải", "thực hiện", "bước", "cách", "điều chỉnh",
    "theo dõi", "kiểm tra", "ngăn ngừa", "phòng ngừa", "phòng bệnh",
    "chẩn đoán", "mục tiêu", "mục đích", "điều trị",
]

# ================================ HÀM ========================================

def norm(text: str) -> str:
    """Chuẩn hóa text (chữ thường, loại bỏ dấu cách thừa)"""
    return re.sub(r"\s+", " ", text.lower().strip())

def extract_drugs_from_text(text: str) -> list[dict]:
    """
    Trích xuất tên thuốc từ text (field treatment/prevention)
    Trả về list các dict {name, generic, class}
    """
    if not text:
        return []
    
    text_lower = text.lower()
    found_drugs = []
    seen = set()
    
    # Tìm kiếm theo từ khoá drug
    for drug_name, drug_info in COMMON_DRUGS.items():
        # Tìm từ khoá exact hoặc trong cấu trúc câu
        pattern = r'\b' + re.escape(drug_name) + r'\b'
        if re.search(pattern, text_lower):
            key = drug_info["generic"].lower()
            if key not in seen:
                found_drugs.append({
                    "name": drug_info["generic"],
                    "generic": drug_info["generic"],
                    "class": drug_info["class"]
                })
                seen.add(key)
    
    return found_drugs

def extract_guidelines_from_text(text: str, disease_name: str) -> list[dict]:
    """
    Trích xuất hướng dẫn từ text treatment/prevention
    Trả về list các dict {name, type, source_text}
    """
    if not text:
        return []
    
    guidelines = []
    
    # Tách thành câu/dòng
    sentences = re.split(r'[.\n]', text)
    
    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 20:
            continue
        
        # Kiểm tra xem câu có từ khoá guideline không
        if any(kw in sent.lower() for kw in GUIDELINE_KEYWORDS):
            # Rút gọn nếu quá dài
            if len(sent) > 200:
                sent = sent[:197] + "..."
            
            guidelines.append({
                "name": sent,
                "type": "Treatment",
                "related_disease": disease_name
            })
    
    return guidelines

def load_medical_data(path: pathlib.Path) -> list[dict]:
    """Load translated.json"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    log.info(f"Đã load {len(data)} bệnh từ {path.name}")
    return data

def load_existing_graph(nodes_path: pathlib.Path, edges_path: pathlib.Path):
    """Load existing nodes và edges"""
    with open(nodes_path, encoding="utf-8") as f:
        nodes = json.load(f)
    with open(edges_path, encoding="utf-8") as f:
        edges = json.load(f)
    log.info(f"Đã load {len(nodes)} nodes và {len(edges)} edges hiện có")
    return nodes, edges

def build_drug_and_guideline_graph(
    input_file: pathlib.Path,
    nodes_file: pathlib.Path,
    edges_file: pathlib.Path,
    output_dir: pathlib.Path
):
    """
    Main function: bổ sung drugs và guidelines vào graph
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load dữ liệu
    log.info("\n=== BƯỚC 1: Load dữ liệu ===")
    medical_data = load_medical_data(input_file)
    existing_nodes, existing_edges = load_existing_graph(nodes_file, edges_file)
    
    # 2. Tích lũy drugs và guidelines
    log.info("\n=== BƯỚC 2: Trích xuất Drugs và Guidelines ===")
    all_drugs = {}  # {normalized_name: drug_dict}
    all_guidelines = {}  # {id: guideline_dict}
    new_edges = []
    
    drug_counter = 0
    guideline_counter = 0
    
    # Bảng ánh xạ disease_name -> disease_id
    disease_map = {}
    for node in existing_nodes:
        if node.get("type") == "Disease":
            disease_map[norm(node["name"])] = node["id"]
    
    # Duyệt qua từng bệnh
    for medical_record in medical_data:
        disease_name = medical_record.get("disease", "").strip()
        if not disease_name:
            continue
        
        disease_id = disease_map.get(norm(disease_name))
        if not disease_id:
            log.warning(f"Không tìm thấy disease_id cho: {disease_name}")
            continue
        
        # Trích xuất drugs từ treatment + prevention
        treatment_text = medical_record.get("treatment", "") or ""
        prevention_text = medical_record.get("prevention", "") or ""
        
        drugs_from_treatment = extract_drugs_from_text(treatment_text)
        drugs_from_prevention = extract_drugs_from_text(prevention_text)
        
        all_drugs_for_disease = drugs_from_treatment + drugs_from_prevention
        
        # Lưu drugs vào map và tạo edges
        for drug in all_drugs_for_disease:
            drug_key = norm(drug["generic"])
            
            if drug_key not in all_drugs:
                drug_counter += 1
                drug_id = f"DR{drug_counter:03d}"
                all_drugs[drug_key] = {
                    "id": drug_id,
                    "name": drug["name"],
                    "generic": drug["generic"],
                    "class": drug["class"],
                    "type": "Drug"
                }
            else:
                drug_id = all_drugs[drug_key]["id"]
            
            # Tạo edge Disease -[TREATED_BY]-> Drug
            new_edges.append({
                "src_id": disease_id,
                "relation": "TREATED_BY",
                "dst_id": drug_id
            })
            log.info(f"  ✓ {disease_name} -[TREATED_BY]-> {drug['generic']}")
        
        # Trích xuất guidelines từ treatment + prevention
        guidelines_from_treatment = extract_guidelines_from_text(treatment_text, disease_name)
        guidelines_from_prevention = extract_guidelines_from_text(prevention_text, disease_name)
        
        all_guidelines_for_disease = guidelines_from_treatment + guidelines_from_prevention
        
        # Lưu guidelines và tạo edges
        for guideline in all_guidelines_for_disease:
            guideline_counter += 1
            guideline_id = f"G{guideline_counter:03d}"
            
            all_guidelines[guideline_id] = {
                "id": guideline_id,
                "name": guideline["name"],
                "type": "Guideline",
                "source": "Treatment recommendation",
                "related_disease": guideline["related_disease"]
            }
            
            # Tạo edge Disease -[FOLLOWS]-> Guideline
            new_edges.append({
                "src_id": disease_id,
                "relation": "FOLLOWS",
                "dst_id": guideline_id
            })
    
    log.info(f"\n✓ Tìm thấy {len(all_drugs)} loại thuốc duy nhất")
    log.info(f"✓ Tạo {len(all_guidelines)} hướng dẫn điều trị")
    log.info(f"✓ Tạo {len(new_edges)} mối quan hệ mới")
    
    # 3. Ghi output
    log.info("\n=== BƯỚC 3: Ghi kết quả ===")
    
    # Ghi drugs.json
    drugs_list = list(all_drugs.values())
    drugs_file = output_dir / "drugs.json"
    with open(drugs_file, "w", encoding="utf-8") as f:
        json.dump(drugs_list, f, ensure_ascii=False, indent=2)
    log.info(f"✓ Đã ghi {drugs_file.name}")
    
    # Ghi guidelines.json
    guidelines_list = list(all_guidelines.values())
    guidelines_file = output_dir / "guidelines.json"
    with open(guidelines_file, "w", encoding="utf-8") as f:
        json.dump(guidelines_list, f, ensure_ascii=False, indent=2)
    log.info(f"✓ Đã ghi {guidelines_file.name}")
    
    # Cập nhật nodes.json - thêm drug và guideline nodes
    drug_nodes = [{"id": d["id"], "name": d["name"], "type": "Drug", "class": d.get("class", "")} 
                  for d in drugs_list]
    guideline_nodes = [{"id": g["id"], "name": g["name"], "type": "Guideline"} 
                       for g in guidelines_list]
    
    updated_nodes = existing_nodes + drug_nodes + guideline_nodes
    updated_nodes_file = output_dir / "nodes_updated.json"
    with open(updated_nodes_file, "w", encoding="utf-8") as f:
        json.dump(updated_nodes, f, ensure_ascii=False, indent=2)
    log.info(f"✓ Đã cập nhật {len(updated_nodes)} nodes (thêm {len(drug_nodes)} drugs + {len(guideline_nodes)} guidelines)")
    
    # Cập nhật edges.json
    updated_edges = existing_edges + new_edges
    updated_edges_file = output_dir / "edges_updated.json"
    with open(updated_edges_file, "w", encoding="utf-8") as f:
        json.dump(updated_edges, f, ensure_ascii=False, indent=2)
    log.info(f"✓ Đã cập nhật {len(updated_edges)} edges (thêm {len(new_edges)} mối quan hệ)")
    
    # Summary
    log.info("\n" + "="*70)
    log.info("TỔNG KẾT BỔ SUNG DRUGS & GUIDELINES VÀO GRAPH")
    log.info("="*70)
    log.info(f"  • Tổng bệnh xử lý: {len(medical_data)}")
    log.info(f"  • Thuốc được bổ sung: {len(drugs_list)}")
    log.info(f"  • Hướng dẫn được tạo: {len(guidelines_list)}")
    log.info(f"  • Nodes ban đầu: {len(existing_nodes)}")
    log.info(f"  • Nodes sau cập nhật: {len(updated_nodes)}")
    log.info(f"  • Edges ban đầu: {len(existing_edges)}")
    log.info(f"  • Edges sau cập nhật: {len(updated_edges)}")
    log.info("="*70)
    
    return {
        "drugs": drugs_list,
        "guidelines": guidelines_list,
        "new_edges": new_edges,
        "updated_nodes": updated_nodes,
        "updated_edges": updated_edges
    }

# ========================== MAIN =============================================

if __name__ == "__main__":
    # Đường dẫn
    BASE_DIR = pathlib.Path(__file__).parent.parent.parent
    INPUT_FILE = BASE_DIR / "data" / "processed" / "translated.json"
    NODES_FILE = BASE_DIR / "data" / "graph" / "nodes.json"
    EDGES_FILE = BASE_DIR / "data" / "graph" / "edges.json"
    OUTPUT_DIR = BASE_DIR / "data" / "graph"
    
    # Chạy
    result = build_drug_and_guideline_graph(
        input_file=INPUT_FILE,
        nodes_file=NODES_FILE,
        edges_file=EDGES_FILE,
        output_dir=OUTPUT_DIR
    )
    
    log.info("\n✅ HOÀN THÀNH! Graph của bạn đã được cập nhật với Drugs và Guidelines")
    log.info(f"\n📁 Các file đầu ra:")
    log.info(f"  - {OUTPUT_DIR / 'drugs.json'}")
    log.info(f"  - {OUTPUT_DIR / 'guidelines.json'}")
    log.info(f"  - {OUTPUT_DIR / 'nodes_updated.json'}")
    log.info(f"  - {OUTPUT_DIR / 'edges_updated.json'}")
