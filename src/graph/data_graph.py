"""
build_graph.py  –  Knowledge Graph từ medical data
===================================================
Input : data/processed/translated.json  (ưu tiên)
        data/processed/merged.json       (fallback)
Output:
  data/graph/nodes.csv         – node table
  data/graph/edges.csv         – edge table
  data/graph/nodes.json        – nodes in JSON
  data/graph/edges.json        – edges in JSON

Node types: disease | symptom | drug | test | organ | risk_factor | complication | treatment | guideline
Edge types: HAS_SYMPTOM | TREATED_BY | DIAGNOSED_BY | AFFECTS | INCREASES_RISK_OF | CAN_CAUSE | MANAGED_BY | FOLLOWS

Cấu trúc:
  - diseases: {id, name, icd, description}
  - symptoms: {id, name, description}
  - drugs: {id, name, generic, class}
  - tests: {id, name, description, normal}
  - organs: {id, name, system}
  - risk_factors: {id, name, description}
  - complications: {id, name, severity}
  - treatments: {id, name, type}
  - guidelines: {id, name, source}
"""

import csv, re, json, uuid, pathlib, logging, time, argparse
from collections import defaultdict
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("graph")

INPUT_FILE = pathlib.Path("../../data/processed/discretized.json")

OUT_DIR    = pathlib.Path("../../data/graph")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Organ Mapping (Từ khóa ánh xạ Cơ quan từ tên bệnh) ────────────────────────
ORGAN_MAPPING = [
    {"name": "Tim", "system": "Hệ tuần hoàn", "keywords": ["tim", "mạch vành", "cơ tim", "huyết áp", "động mạch", "tĩnh mạch", "nhồi máu"], "excludes": []},
    {"name": "Phổi", "system": "Hệ hô hấp", "keywords": ["phổi", "hô hấp", "phế quản", "hen suyễn", "lao", "tràn dịch màng phổi"], "excludes": []},
    {"name": "Gan - Mật", "system": "Hệ tiêu hóa", "keywords": ["gan", "viêm gan", "xơ gan", "mật", "túi mật", "đường mật", "sỏi mật"], "excludes": ["bảo mật"]},
    {"name": "Dạ dày - Ruột", "system": "Hệ tiêu hóa", "keywords": ["dạ dày", "bao tử", "tá tràng", "tiêu hóa", "ruột", "đại tràng", "trĩ"], "excludes": []},
    {"name": "Thận - Tiết niệu", "system": "Hệ bài tiết", "keywords": ["thận", "tiết niệu", "bàng quang", "niệu đạo", "sỏi niệu"], "excludes": []},
    {"name": "Não - Thần kinh", "system": "Hệ thần kinh", "keywords": ["não", "thần kinh", "đột quỵ", "chứng mất trí", "alzheimer", "động kinh", "parkinson", "chóng mặt", "tai biến mạch máu"], "excludes": []},
    {"name": "Mắt", "system": "Cơ quan cảm giác", "keywords": ["mắt", "thị giác", "giác mạc", "võng mạc", "thủy tinh thể", "đục", "cườm", "lác"], "excludes": ["chóng mặt", "thâm mắt", "rửa mắt", "hoa mắt"]},
    {"name": "Xương khớp", "system": "Hệ vận động", "keywords": ["xương", "khớp", "cột sống", "thoái hóa khớp", "loãng xương", "gút", "cơ", "dây chằng"], "excludes": ["cơ tim", "cơ trơn", "cơ quan", "cơ năng", "cơ địa", "cơ bắp", "nguy cơ"]},
    {"name": "Da", "system": "Hệ vỏ bọc", "keywords": ["da", "viêm da", "vảy nến", "hắc lào", "lang ben", "mụn", "mề đay", "nấm", "zona"], "excludes": ["nấm móng", "nấm âm đạo", "nấm miệng"]},
    {"name": "Máu", "system": "Hệ tuần hoàn", "keywords": ["máu", "huyết học", "bạch cầu", "hồng cầu", "tiểu cầu", "thiếu máu", "huyết khối"], "excludes": ["chảy máu cam", "chảy máu chân răng", "máu tụ", "tai biến mạch máu"]},
    {"name": "Tuyến nội tiết", "system": "Hệ nội tiết", "keywords": ["tuyến giáp", "cường giáp", "suy giáp", "đái tháo đường", "tiểu đường", "nội tiết"], "excludes": []},
    {"name": "Tai Mũi Họng", "system": "Cơ quan cảm giác / Hô hấp", "keywords": ["tai", "mũi", "họng", "amidan", "viêm xoang", "thanh quản", "viêm mũi"], "excludes": ["tai biến", "tai nạn", "mũi nhọn", "trái có cuống họng"]},
    {"name": "Hệ sinh dục nữ", "system": "Hệ sinh sản", "keywords": ["tử cung", "buồng trứng", "âm đạo", "kinh nguyệt", "phụ khoa", "tuyến vú", "mang thai", "tiền mãn kinh"], "excludes": []},
    {"name": "Hệ sinh dục nam", "system": "Hệ sinh sản", "keywords": ["tuyến tiền liệt", "tinh hoàn", "dương vật", "nam khoa", "tinh trùng"], "excludes": []},
    {"name": "Tụy", "system": "Hệ tiêu hóa / Hệ nội tiết", "keywords": ["tụy"], "excludes": []},
    {"name": "Hệ miễn dịch - Bạch huyết", "system": "Hệ miễn dịch", "keywords": ["miễn dịch", "bạch huyết", "hạch", "lách", "lupus", "hiv", "aids", "tự miễn"], "excludes": ["lao hạch"]},
    {"name": "Răng Miệng", "system": "Hệ tiêu hóa", "keywords": ["răng", "nướu", "nha chu", "tủy răng", "lưỡi", "miệng", "sâu răng", "viêm lợi"], "excludes": ["nấm miệng"]},
    {"name": "Tuyến vú", "system": "Hệ sinh sản", "keywords": ["vú", "tuyến vú", "nhũ hoa", "áp xe vú"], "excludes": []},
    {"name": "Tóc và Móng", "system": "Hệ vỏ bọc", "keywords": ["tóc", "hói", "rụng tóc", "móng", "nấm móng"], "excludes": []},
    {"name": "Tâm lý - Tâm thần", "system": "Hệ thần kinh", "keywords": ["tâm thần", "tâm lý", "trầm cảm", "lo âu", "tự kỷ", "stress", "rối loạn cảm xúc", "rối loạn phổ tự kỷ"], "excludes": []},
    {"name": "Truyền nhiễm - Toàn thân", "system": "Toàn thân", "keywords": ["sốt", "nhiễm trùng", "truyền nhiễm", "sốt rét", "sốt xuất huyết", "covid", "cúm", "sởi", "thủy đậu", "ký sinh trùng", "giun", "sán", "dịch tả", "béo phì", "suy dinh dưỡng", "sốt phát ban"], "excludes": []}
]
# ── Node type prefix & labels ─────────────────────────────────────────────────
PREFIX = {
    "diseases": "D",
    "symptoms": "S",
    "drugs": "DR",
    "tests": "T",
    "organs": "O",
    "risk_factors": "RF",
    "complications": "C",
    "treatments": "TR",
    "guidelines": "G",
    "categories": "CAT",
    "causes": "CA",
}

NODE_LABELS = {
    "diseases": "Disease",
    "symptoms": "Symptom",
    "drugs": "Drug",
    "tests": "Test",
    "organs": "Organ",
    "risk_factors": "RiskFactor",
    "complications": "Complication",
    "treatments": "Treatment",
    "guidelines": "Guideline",
    "categories": "Category",
    "causes": "Cause",
}

# ── field CSV → category MEDICAL_DATA ────────────────────────────────────────
FIELD_TO_CATEGORY = {
    "symptoms": "symptoms",
    "causes": "causes",
    "risk_factors": "risk_factors",
    "treatment": "treatments",
    "exams_and_tests": "tests",
    "complications": "complications",
    "prevention": "treatments",  # prevention cũng được lưu vào treatments
}

# ── relationship per category ─────────────────────────────────────────────────
CATEGORY_TO_REL = {
    "symptoms": ("disease", "HAS_SYMPTOM", "node"),
    "causes": ("disease", "HAS_CAUSE", "node"),
    "risk_factors": ("node", "INCREASES_RISK_OF", "disease"),  # RF→D
    "treatments": ("disease", "MANAGED_BY", "node"),
    "tests": ("disease", "DIAGNOSED_BY", "node"),
    "complications": ("disease", "CAN_CAUSE", "node"),
}

# =============================================================================
# TEXT SPLITTER
# =============================================================================
_HEADER_VI = re.compile(
    r"^(Các triệu chứng|Những triệu chứng|Triệu chứng|Nguyên nhân|"
    r"Yếu tố nguy cơ|Biến chứng|Điều trị|Xét nghiệm|Những xét nghiệm|"
    r"Những biến chứng|Những yếu tố|Bao gồm|Phòng ngừa|Phòng bệnh|"
    r"Chẩn đoán|Nguyên nhân có thể)[^:]*:\s*",
    re.IGNORECASE
)
_INCLUDE_RE = re.compile(
    r'(?:bao gồm|gồm có|như sau|sau đây)\s*:(.+)$',
    re.IGNORECASE | re.DOTALL
)
_BOUNDARY_VI = re.compile(
    r'(?<=[a-zàáâãèéêìíòóôõùúýăđơư])\s+(?=[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐƠƯ])'
)


def split_items(text: str, max_items: int = 12, max_len: int = 100) -> list[str]:
    if not text or len(text.strip()) < 3:
        return []

    text = _HEADER_VI.sub("", text.strip())
    m = _INCLUDE_RE.search(text)
    if m:
        text = m.group(1).strip()

    if "\n" in text:
        items = text.splitlines()
    else:
        marked = _BOUNDARY_VI.sub("\n", text)
        items = marked.splitlines()
        if len(items) == 1 and len(items[0]) > 60:
            items = re.split(r'[,;]\s+', items[0])

    cleaned, seen = [], set()
    for item in items:
        item = item.strip().strip(".,;:-–•*")
        if len(item) < 3 or len(item) > max_len:
            continue
        if not re.search(r'[a-zA-ZàáâãèéêìíòóôõùúýăđơưÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐƠƯ]', item):
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)

    return cleaned[:max_items]


# =============================================================================
# LOAD INPUT
# =============================================================================
def load_file(path: pathlib.Path) -> list[dict]:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        log.info(f"  CSV: {len(rows)} records")
        return rows

    with open(path, encoding="utf-8") as f:
        raw = f.read().strip()

    # JSONL
    if raw.startswith("{") and "\n{" in raw[:2000]:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        log.info(f"  JSONL: {len(rows)} records")
        return rows

    data = json.loads(raw)
    if isinstance(data, list):
        log.info(f"  JSON array: {len(data)} records")
        return data

    for key in ("records", "data", "diseases", "items", "results"):
        if key in data and isinstance(data[key], list):
            log.info(f"  JSON['{key}']: {len(data[key])} records")
            return data[key]

    log.error("Không đọc được file JSON")
    return []


def normalize_row(row: dict) -> dict:
    """Chuẩn hoá key khác nhau về schema thống nhất."""
    aliases = {
        "name": "disease", "disease_name": "disease",
        "symptom": "symptoms", "cause": "causes",
        "risk_factor": "risk_factors", "treatments": "treatment",
        "exam": "exams_and_tests", "tests": "exams_and_tests",
        "complication": "complications",
    }
    out = dict(row)
    for old, new in aliases.items():
        if old in out and new not in out:
            out[new] = out.pop(old)
    # list → string
    for f in FIELD_TO_CATEGORY:
        val = out.get(f)
        if isinstance(val, list):
            out[f] = "\n".join(str(v) for v in val if v)
    return out


# =============================================================================
# BUILD MEDICAL_DATA + RELATIONSHIPS
# =============================================================================
def build(rows: list[dict]):
    # node_store[category] = list of node dicts
    node_store: dict[str, list] = defaultdict(list)
    # node_index[category][norm_name] = id
    node_index: dict[str, dict] = defaultdict(dict)
    # counters per category
    counters: dict[str, int] = defaultdict(int)
    # relationships list
    relationships: list[tuple] = []

    def norm(name: str) -> str:
        return re.sub(r"\s+", " ", name.lower().strip())

    def get_or_create(category: str, name: str, extra: dict = None) -> str:
        key = norm(name)
        if key not in node_index[category]:
            counters[category] += 1
            n = counters[category]
            pre = PREFIX.get(category, category[:2].upper())
            nid = f"{pre}{n:03d}"
            node = {"id": nid, "name": name}
            
            # Add default fields per category
            if category == "diseases":
                node["icd"] = extra.get("icd", "") if extra else ""
                node["description"] = extra.get("description", "") if extra else ""
                node["disease_type"] = extra.get("disease_type", "") if extra else ""
                node["severity"] = extra.get("severity", "") if extra else ""
                node["demographic"] = extra.get("demographic", "") if extra else ""
                node["contagious"] = extra.get("contagious", "") if extra else ""
            elif category == "drugs":
                node["generic"] = extra.get("generic", "") if extra else ""
                node["class"] = extra.get("class", "Chưa phân loại") if extra else "Chưa phân loại"
            elif category == "tests":
                node["description"] = extra.get("description", "") if extra else ""
                node["normal"] = extra.get("normal", "") if extra else ""
            elif category == "organs":
                node["system"] = extra.get("system", "") if extra else ""
            elif category == "risk_factors":
                node["description"] = extra.get("description", "") if extra else ""
            elif category == "complications":
                node["severity"] = extra.get("severity", "Chưa phân loại") if extra else "Chưa phân loại"
            elif category == "treatments":
                node["type"] = extra.get("type", "Non-pharmacological") if extra else "Non-pharmacological"
            elif category == "guidelines":
                node["source"] = extra.get("source", "Chưa phân loại") if extra else "Chưa phân loại"
            elif category == "symptoms":
                node["description"] = extra.get("description", "") if extra else ""
            
            node_store[category].append(node)
            node_index[category][key] = nid
        return node_index[category][key]

    for i, raw_row in enumerate(rows):
        row = normalize_row(raw_row)
        name_vi = (row.get("disease") or "").strip()
        name_en = (row.get("disease_en") or name_vi).strip()
        if not name_vi:
            continue

        # Tạo Disease node
        d_id = get_or_create("diseases", name_vi, {
            "icd": row.get("icd_code", ""),
            "description": (row.get("overview") or "")[:150].replace("\n", " "),
            "disease_type": row.get("disease_type", ""),
            "severity": row.get("severity_level", ""),
            "demographic": row.get("target_demographic", ""),
            "contagious": row.get("is_contagious", ""),
        })

        # ─────────────────────────────────────────────────────────────
        # BỔ SUNG: Trích xuất Cơ quan (Organ) dựa vào tên bệnh
        # ─────────────────────────────────────────────────────────────
        name_lower = name_vi.lower()
        for organ_data in ORGAN_MAPPING:
            # Bỏ qua nếu nằm trong danh sách loại trừ (excludes)
            excludes = organ_data.get("excludes", [])
            if any(exc in name_lower for exc in excludes):
                continue
            
            # Sử dụng regex word boundary để khớp chính xác từ khóa
            match = False
            for kw in organ_data["keywords"]:
                if re.search(r'\b' + re.escape(kw) + r'\b', name_lower):
                    match = True
                    break
                    
            if match:
                # Tạo node Organ
                o_id = get_or_create("organs", organ_data["name"], {
                    "system": organ_data["system"]
                })
                # Thêm quan hệ Disease -[AFFECTS]-> Organ
                relationships.append((d_id, "AFFECTS", o_id))
        # ─────────────────────────────────────────────────────────────
        # Tạo các node liên quan + relationship
        for field, category in FIELD_TO_CATEGORY.items():
            text = row.get(field, "") or ""
            items = split_items(text)

            for item_name in items:
                # Extra props theo category
                extra = {}
                if category == "symptoms":
                    extra = {"description": item_name}
                elif category == "tests":
                    extra = {"description": item_name, "normal": ""}
                elif category == "risk_factors":
                    extra = {"description": item_name}
                elif category == "complications":
                    extra = {"severity": "Chưa phân loại"}
                elif category == "treatments":
                    extra = {"type": "Non-pharmacological"}
                elif category == "drugs":
                    extra = {"generic": item_name, "class": "Chưa phân loại"}
                elif category == "organs":
                    extra = {"system": "Chưa phân loại"}
                elif category == "guidelines":
                    extra = {"source": "Chưa phân loại"}

                n_id = get_or_create(category, item_name, extra)

                # Build relationship tuple
                src_type, rel, dst_type = CATEGORY_TO_REL[category]
                if src_type == "disease":
                    relationships.append((d_id, rel, n_id))
                else:  # RF → Disease
                    relationships.append((n_id, rel, d_id))

        if (i + 1) % 500 == 0:
            total_nodes = sum(len(v) for v in node_store.values())
            log.info(f"  {i + 1}/{len(rows)} records | nodes={total_nodes:,} | rels={len(relationships):,}")

    return node_store, relationships


# =============================================================================
# EXPORT GRAPH DATA
# =============================================================================
def export_graph(node_store: dict, relationships: list, output_dir: pathlib.Path):
    """Export graph to CSV and JSON formats."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ─ Export nodes.csv + nodes.json ─────────────────────────────────────────
    nodes_csv = output_dir / "nodes.csv"
    nodes_json = output_dir / "nodes.json"
    
    all_nodes = []
    
    for category, nodes in node_store.items():
        for node in nodes:
            node_copy = dict(node)
            node_copy["type"] = NODE_LABELS.get(category, category)
            all_nodes.append(node_copy)
    
    # CSV format
    if all_nodes:
        df_nodes = pd.DataFrame(all_nodes)
        df_nodes.to_csv(nodes_csv, index=False, encoding="utf-8")
        log.info(f"  Nodes CSV: {len(all_nodes)} → {nodes_csv}")
    
    # JSON format
    with open(nodes_json, "w", encoding="utf-8") as f:
        json.dump(all_nodes, f, ensure_ascii=False, indent=2)
    log.info(f"  Nodes JSON: {len(all_nodes)} → {nodes_json}")
    
    # ─ Export edges.csv + edges.json ─────────────────────────────────────────
    edges_csv = output_dir / "edges.csv"
    edges_json = output_dir / "edges.json"
    
    edges_list = []
    for src_id, rel_type, dst_id in relationships:
        edges_list.append({
            "src_id": src_id,
            "relation": rel_type,
            "dst_id": dst_id
        })
    
    # CSV format
    if edges_list:
        df_edges = pd.DataFrame(edges_list)
        df_edges.to_csv(edges_csv, index=False, encoding="utf-8")
        log.info(f"  Edges CSV: {len(edges_list)} → {edges_csv}")
    
    # JSON format
    with open(edges_json, "w", encoding="utf-8") as f:
        json.dump(edges_list, f, ensure_ascii=False, indent=2)
    log.info(f"  Edges JSON: {len(edges_list)} → {edges_json}")



# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Xây dựng Knowledge Graph từ medical data"
    )
    parser.add_argument("--input", default=str(INPUT_FILE),
                        help="Path đến medical_vi.csv hoặc .json")
    parser.add_argument("--output-dir", default=str(OUT_DIR),
                        help="Thư mục output cho CSV/JSON files")
    parser.add_argument("--limit", type=int, default=0,
                        help="Giới hạn số bản ghi (0 = tất cả)")
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    output_dir = pathlib.Path(args.output_dir)

    if not input_path.exists():
        log.error(f"Không tìm thấy file: {input_path}")
        return

    t0 = time.time()
    log.info(f"Loading {input_path} ...")
    rows = load_file(input_path)

    if args.limit > 0:
        rows = rows[:args.limit]
        log.info(f"  Giới hạn: {args.limit} records")

    log.info("Building graph ...")
    node_store, relationships = build(rows)

    # Dedup relationships
    relationships = list(dict.fromkeys(relationships))

    total_nodes = sum(len(v) for v in node_store.values())
    log.info("─" * 55)
    log.info(f"Nodes : {total_nodes:,}")
    log.info(f"Rels  : {len(relationships):,}")
    log.info("Nodes by category:")
    
    category_order = [
        "diseases", "symptoms", "drugs", "tests", "organs",
        "risk_factors", "complications", "treatments", "guidelines",
    ]
    
    for cat in category_order:
        nodes = node_store.get(cat, [])
        log.info(f"  {cat:<15}: {len(nodes):>6,}")

    from collections import Counter
    rel_cnt = Counter(r[1] for r in relationships)
    log.info("Rels by type:")
    for k, v in rel_cnt.most_common():
        log.info(f"  {k:<25}: {v:>6,}")

    log.info(f"\nExporting to {output_dir} ...")
    export_graph(node_store, relationships, output_dir)
    log.info(f"✅ Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()