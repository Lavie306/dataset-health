"""
build_graph.py  –  Knowledge Graph từ medical data
===================================================
Input : data/processed/translated.json  (ưu tiên)
        data/processed/merged.json       (fallback)
Output:
  data/output/graph.json       – {nodes, edges}
  data/output/nodes.csv        – node table
  data/output/edges.csv        – edge table
  data/output/graph_stats.json – thống kê

Node types : disease | symptom | cause | risk_factor | treatment | test | complication | prevention
Edge types  : HAS_SYMPTOM | HAS_CAUSE | HAS_RISK | TREATED_BY | DIAGNOSED_BY | HAS_COMPLICATION | PREVENTED_BY

Fix so với code gốc:
  1. split_items() nhận dạng 3 format: newline-list / inline-list / paragraph
  2. Dedup nodes by normalized key
  3. Dedup edges (src, rel, dst)
  4. Strip boilerplate headers
  5. Degree tracking cho viz
  6. graph_stats.json với top diseases
"""

import json, re, uuid, pathlib, logging, time
from collections import defaultdict
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("graph")

TRANSLATED = pathlib.Path("../../data/processed/translated.json")
MERGED     = pathlib.Path("../../data/processed/merged.json")
OUT_DIR    = pathlib.Path("../../data/graph")
OUT_DIR.mkdir(parents=True, exist_ok=True)

_CITE_RE   = re.compile(r"\[\d+\]")


# =============================================================================
# TEXT SPLITTING
# =============================================================================

def _looks_like_concat_bullets(text):
    if "." in text:
        return False
    caps = re.findall(r"\b[A-Z][a-z]{2,}", text)
    return len(caps) >= 3


def _split_concat_bullets(text):
    marked = re.sub(r"(?<=[a-z])\s+(?=[A-Z])", "\n", text)
    return [p.strip() for p in marked.splitlines() if len(p.strip()) > 3]


def _split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    result = []
    for p in parts:
        p = p.strip().rstrip(".!?")
        if 10 <= len(p) <= 120:
            result.append(p)
    return result


def _clean_item(item):
    item = item.strip().rstrip(".,;:")
    item = re.sub(r"\s+", " ", item)
    if len(item) <= 4 or len(item) > 150:
        return ""
    if re.fullmatch(r"[^a-zA-Z]+", item):
        return ""
    return item


def split_items(text, source=""):
    """
    Tách text thành danh sách entity.
    3 format được hỗ trợ:
      A. Newline list  (MedlinePlus)
      B. Inline list   (Mayo/Medline: "may include: Item A Item B")
      C. Plain paragraph (Mayo)
    """
    if not text:
        return []

    text = _CITE_RE.sub("", text).strip()

    # Format A: newline-separated
    if "\n" in text:
        if ":" in text:
            parts = text.split(":", 1)
            if len(parts[0].split()) <= 8:
                text = parts[1]
        items = [line.strip() for line in text.splitlines()]

    # Format B: "include:" / "may include:" inline list
    elif re.search(r"\b(?:include|may include|such as)\s*:", text, re.IGNORECASE):
        match = re.search(
            r"(?:include|may include|such as)\s*:(.+)$",
            text, re.IGNORECASE | re.DOTALL
        )
        if match:
            list_part = match.group(1).strip()
            items = re.split(r"(?<=[a-z,])\s+(?=[A-Z])", list_part)
        else:
            items = _split_sentences(text)

    # Format C-bullet: concat caps "Word Word Word"
    elif _looks_like_concat_bullets(text):
        items = _split_concat_bullets(text)

    # Format C-paragraph: Mayo prose
    else:
        items = _split_sentences(text)

    # Clean + dedup
    cleaned, seen = [], set()
    for item in items:
        item = _clean_item(item)
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)

    return cleaned


# =============================================================================
# GRAPH BUILDER
# =============================================================================

def normalize_key(name):
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


class GraphBuilder:
    def __init__(self):
        self.nodes      = []
        self.edges      = []
        self._node_map  = {}
        self._edge_set  = set()
        self._degree    = defaultdict(int)

    def get_or_create_node(self, name, node_type):
        key = f"{node_type}:{normalize_key(name)}"
        if key not in self._node_map:
            node_id = f"{node_type[0].upper()}_{uuid.uuid4().hex[:8]}"
            self._node_map[key] = node_id
            self.nodes.append({"id": node_id, "name": name, "type": node_type})
        return self._node_map[key]

    def add_edge(self, src, relation, dst):
        key = (src, relation, dst)
        if key in self._edge_set:
            return
        self._edge_set.add(key)
        self.edges.append({"source": src, "relation": relation, "target": dst})
        self._degree[src] += 1
        self._degree[dst] += 1

    def finalize(self):
        for node in self.nodes:
            node["degree"] = self._degree.get(node["id"], 0)


FIELD_MAP = {
    "symptoms":        ("symptom",      "HAS_SYMPTOM"),
    "causes":          ("cause",        "HAS_CAUSE"),
    "risk_factors":    ("risk_factor",  "HAS_RISK"),
    "treatment":       ("treatment",    "TREATED_BY"),
    "exams_and_tests": ("test",         "DIAGNOSED_BY"),
    "complications":   ("complication", "HAS_COMPLICATION"),
    "prevention":      ("prevention",   "PREVENTED_BY"),
}


def build_graph(records):
    g = GraphBuilder()
    for rec in records:
        disease = rec.get("disease", "").strip()
        if not disease:
            continue
        d_id   = g.get_or_create_node(disease, "disease")
        source = rec.get("source", "")
        for field, (node_type, relation) in FIELD_MAP.items():
            raw = rec.get(field, "") or ""
            for item_name in split_items(raw, source):
                n_id = g.get_or_create_node(item_name, node_type)
                g.add_edge(d_id, relation, n_id)
    g.finalize()
    return g


# =============================================================================
# EXPORT
# =============================================================================

def export_all(g):
    with open(OUT_DIR / "graph.json", "w", encoding="utf-8") as f:
        json.dump({"nodes": g.nodes, "edges": g.edges}, f,
                  ensure_ascii=False, indent=2)
    log.info(f"Saved graph.json  -> {OUT_DIR}/graph.json")

    pd.DataFrame(g.nodes).to_csv(
        OUT_DIR / "nodes.csv", index=False, encoding="utf-8-sig")
    log.info(f"Saved nodes.csv   -> {OUT_DIR}/nodes.csv")

    pd.DataFrame(g.edges).to_csv(
        OUT_DIR / "edges.csv", index=False, encoding="utf-8-sig")
    log.info(f"Saved edges.csv   -> {OUT_DIR}/edges.csv")

    type_counts = defaultdict(int)
    for node in g.nodes:
        type_counts[node["type"]] += 1

    rel_counts = defaultdict(int)
    for edge in g.edges:
        rel_counts[edge["relation"]] += 1

    disease_nodes = {n["id"]: n["name"] for n in g.nodes if n["type"] == "disease"}
    top_diseases  = sorted(
        [(g._degree[nid], name) for nid, name in disease_nodes.items()],
        reverse=True
    )[:10]

    stats = {
        "total_nodes":     len(g.nodes),
        "total_edges":     len(g.edges),
        "nodes_by_type":   dict(type_counts),
        "edges_by_relation": dict(rel_counts),
        "top10_most_connected_diseases": [
            {"disease": name, "degree": deg} for deg, name in top_diseases
        ],
    }
    with open(OUT_DIR / "graph_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    log.info(f"Saved graph_stats -> {OUT_DIR}/graph_stats.json")
    return stats


# =============================================================================
# MAIN
# =============================================================================

def run():
    t0 = time.time()
    input_file = TRANSLATED if TRANSLATED.exists() else MERGED
    log.info(f"Loading {input_file} ...")
    with open(input_file, encoding="utf-8") as f:
        records = json.load(f)
    log.info(f"  {len(records)} records")

    log.info("Building graph ...")
    g = build_graph(records)

    log.info("Exporting ...")
    stats = export_all(g)

    log.info("-" * 50)
    log.info(f"Nodes           : {stats['total_nodes']:,}")
    log.info(f"Edges           : {stats['total_edges']:,}")
    log.info(f"Nodes by type   : {stats['nodes_by_type']}")
    log.info(f"Edges by rel    : {stats['edges_by_relation']}")
    log.info("Top 10 diseases :")
    for e in stats["top10_most_connected_diseases"]:
        log.info(f"  {e['degree']:>4}  {e['disease']}")
    log.info(f"Done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    run()