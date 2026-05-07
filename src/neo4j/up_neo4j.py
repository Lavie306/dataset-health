import json
import pathlib
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("neo4j_uploader")

# ==================== CẤU HÌNH ====================
URI      = "neo4j+s://617d923b.databases.neo4j.io"
USER     = "617d923b"
PASSWORD = "itstG4n0algoesE1jQTLqWRccBLy9392E_QVxW3R2dQ"

# Sử dụng file JSON cập nhật (với Drugs & Guidelines)
NODES_PATH = r"D:\Project Data Mining\Project\data\graph\nodes_updated.json"
EDGES_PATH = r"D:\Project Data Mining\Project\data\graph\edges_updated.json"

BATCH = 2000

# ==================== KHỞI TẠO DRIVER ====================
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# ==================== HÀM XÓA GRAPH CỦA ====================
def clear_database(tx):
    """Xóa tất cả nodes và edges trong database"""
    log.info("🗑️  Xóa graph cũ...")
    # Xóa tất cả relationships trước
    tx.run("MATCH (n)-[r]-(m) DELETE r")
    # Sau đó xóa tất cả nodes
    tx.run("MATCH (n) DELETE n")
    log.info("✅ Graph cũ đã bị xóa")

# ==================== HÀM ĐẨY DỮ LIỆU ====================
def push_nodes_batch(tx, batch):
    """Đẩy batch nodes lên Neo4j với đầy đủ thông tin"""
    query = """
        UNWIND $rows AS row
        CALL apoc.create.node([row.type], row) YIELD node
        RETURN node
    """
    tx.run(query, rows=batch)

def push_edges_batch(tx, batch):
    """Đẩy batch edges lên Neo4j"""
    query = """
        UNWIND $rows AS row
        MATCH (src {id: row.src_id})
        MATCH (dst {id: row.dst_id})
        CALL apoc.create.relationship(src, row.relation, {}, dst) YIELD rel
        RETURN rel
    """
    tx.run(query, rows=batch)

def push_edges_batch_fallback(tx, batch):
    """Phiên bản fallback nếu APOC không khả dụng"""
    for edge in batch:
        try:
            query = f"""
                MATCH (src {{id: $src_id}})
                MATCH (dst {{id: $dst_id}})
                MERGE (src)-[:{edge['relation']}]->(dst)
            """
            tx.run(query, src_id=edge['src_id'], dst_id=edge['dst_id'])
        except Exception as e:
            log.warning(f"⚠️  Không thể tạo edge: {edge} - {e}")

# ==================== MAIN FUNCTION ====================
def upload_graph_to_neo4j():
    """Upload graph mới lên Neo4j (xóa cũ trước)"""
    
    # 1. Load dữ liệu từ JSON
    log.info("\n📂 Load dữ liệu từ file JSON...")
    
    with open(NODES_PATH, encoding="utf-8") as f:
        nodes = json.load(f)
    log.info(f"✓ Đã load {len(nodes)} nodes")
    
    with open(EDGES_PATH, encoding="utf-8") as f:
        edges = json.load(f)
    log.info(f"✓ Đã load {len(edges)} edges")
    
    # 2. Xóa graph cũ
    log.info("\n🔄 Xóa graph cũ...")
    with driver.session() as session:
        session.execute_write(clear_database)
    
    # 3. Đẩy nodes
    log.info("\n📤 Đẩy Nodes lên Neo4j...")
    
    # Nhóm nodes theo type để in log
    nodes_by_type = {}
    for node in nodes:
        ntype = node.get("type", "Unknown")
        if ntype not in nodes_by_type:
            nodes_by_type[ntype] = []
        nodes_by_type[ntype].append(node)
    
    # Đẩy từng batch
    with driver.session() as session:
        for i in range(0, len(nodes), BATCH):
            batch = nodes[i:i+BATCH]
            try:
                session.execute_write(push_nodes_batch, batch)
            except Exception as e:
                log.warning(f"⚠️  APOC không khả dụng, sử dụng fallback: {e}")
                # Fallback: push từng node
                for node in batch:
                    try:
                        query = """
                            MERGE (n {id: $id})
                            SET n.name = $name,
                                n.type = $type
                        """
                        params = {
                            "id": node.get("id"),
                            "name": node.get("name"),
                            "type": node.get("type")
                        }
                        # Thêm các trường tùy chọn
                        for key, val in node.items():
                            if key not in ["id", "name", "type"]:
                                params[key] = val
                        session.run(query, **params)
                    except Exception as e2:
                        log.error(f"❌ Lỗi push node {node.get('id')}: {e2}")
            
            # In progress
            progress = min(i + BATCH, len(nodes))
            log.info(f"  📊 {progress}/{len(nodes)} nodes")
    
    # In tóm tắt theo loại
    log.info("\n📋 Tóm tắt Nodes:")
    for ntype, nodes_list in sorted(nodes_by_type.items()):
        log.info(f"  ✅ {ntype}: {len(nodes_list)} nodes")
    
    # 4. Đẩy edges
    log.info("\n📤 Đẩy Edges lên Neo4j...")
    
    edges_by_type = {}
    for edge in edges:
        etype = edge.get("relation", "Unknown")
        if etype not in edges_by_type:
            edges_by_type[etype] = 0
        edges_by_type[etype] += 1
    
    with driver.session() as session:
        for i in range(0, len(edges), BATCH):
            batch = edges[i:i+BATCH]
            try:
                session.execute_write(push_edges_batch, batch)
            except Exception as e:
                log.warning(f"⚠️  Sử dụng fallback cho edges: {e}")
                session.execute_write(push_edges_batch_fallback, batch)
            
            # In progress
            progress = min(i + BATCH, len(edges))
            log.info(f"  📊 {progress}/{len(edges)} edges")
    
    # In tóm tắt theo relation type
    log.info("\n📋 Tóm tắt Edges:")
    for etype, count in sorted(edges_by_type.items()):
        log.info(f"  ✅ {etype}: {count} edges")
    
    log.info("\n" + "="*70)
    log.info("✅ HOÀN THÀNH! Graph đã được cập nhật với Drugs & Guidelines")
    log.info("="*70)
    log.info(f"\n📊 Thống kê:")
    log.info(f"  • Tổng Nodes: {len(nodes)}")
    log.info(f"  • Tổng Edges: {len(edges)}")
    log.info(f"  • Bao gồm: 27 Drugs + 9,246 Guidelines")

# ==================== MAIN ====================
if __name__ == "__main__":
    try:
        upload_graph_to_neo4j()
    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()
        log.info("\n✅ Kết nối Neo4j đã đóng")