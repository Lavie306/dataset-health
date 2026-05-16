import json
import pathlib
from neo4j import GraphDatabase
from collections import defaultdict
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

# ==================== HÀM FETCH DỮ LIỆU TỪ NEO4J ====================
def fetch_nodes_from_neo4j(tx):
    """Lấy tất cả nodes từ Neo4j (kèm labels)"""
    result = tx.run("MATCH (n) RETURN n, labels(n) AS lbls")
    nodes = []
    for record in result:
        node = dict(record['n'])
        # Lấy label đầu tiên làm type (mỗi node chỉ có 1 label)
        labels = record['lbls']
        if labels:
            node['type'] = labels[0]
        nodes.append(node)
    return nodes

def fetch_edges_from_neo4j(tx):
    """Lấy tất cả edges từ Neo4j"""
    result = tx.run("MATCH (src)-[r]->(dst) RETURN src.id as src_id, type(r) as relation, dst.id as dst_id")
    edges = []
    for record in result:
        edge = {
            'src_id': record['src_id'],
            'relation': record['relation'],
            'dst_id': record['dst_id']
        }
        edges.append(edge)
    return edges

# ==================== HÀM SO SÁNH ====================
def make_node_key(node):
    """Tạo key so sánh cho node (bỏ qua id vì đã dùng id để match)"""
    return tuple(sorted(
        (k, str(v)) for k, v in node.items()
        if k != 'id' and v is not None and v != ""
    ))

def make_edge_key(edge):
    """Tạo key duy nhất cho edge"""
    return (edge['src_id'], edge['relation'], edge['dst_id'])

# ==================== HÀM XÓA ====================
def delete_edges_batch(tx, edges_to_delete):
    """Xóa edges - nhóm theo relation type rồi xóa batch"""
    if not edges_to_delete:
        return
    # Nhóm edges theo relation type 
    by_relation = defaultdict(list)
    for edge in edges_to_delete:
        by_relation[edge['relation']].append(edge)
    
    for rel_type, edges in by_relation.items():
        pairs = [{'src_id': e['src_id'], 'dst_id': e['dst_id']} for e in edges]
        query = f"""
            UNWIND $pairs AS pair
            MATCH (src {{id: pair.src_id}})-[r:{rel_type}]->(dst {{id: pair.dst_id}})
            DELETE r
        """
        tx.run(query, pairs=pairs)

def delete_nodes_batch(tx, node_ids):
    """Xóa nodes theo danh sách ids"""
    if not node_ids:
        return
    query = """
        UNWIND $ids AS id
        MATCH (n {id: id})
        DETACH DELETE n
    """
    tx.run(query, ids=node_ids)

# ==================== HÀM PUSH DỮ LIỆU ====================
def push_nodes_batch(tx, label, batch):
    """Đẩy batch nodes lên Neo4j với label đúng"""
    # Loại bỏ field 'type' khỏi properties 
    clean_batch = []
    for node in batch:
        clean_node = {k: v for k, v in node.items() if k != 'type'}
        clean_batch.append(clean_node)
    
    query = f"""
        UNWIND $rows AS row
        MERGE (n:{label} {{id: row.id}})
        SET n += row
    """
    tx.run(query, rows=clean_batch)

def update_nodes_batch(tx, label, batch):
    """Cập nhật nodes đã thay đổi (MERGE + SET, không cần xóa)"""
    clean_batch = []
    for node in batch:
        clean_node = {k: v for k, v in node.items() if k != 'type'}
        clean_batch.append(clean_node)
    
    query = f"""
        UNWIND $rows AS row
        MATCH (n {{id: row.id}})
        DETACH DELETE n
    """
    tx.run(query, rows=clean_batch)
    
    # Tạo lại với label mới
    query_create = f"""
        UNWIND $rows AS row
        CREATE (n:{label})
        SET n += row
    """
    tx.run(query_create, rows=clean_batch)

def push_edges_batch(tx, relation, batch):
    """Đẩy batch edges lên Neo4j (nhóm theo relation type)"""
    pairs = [{'src_id': e['src_id'], 'dst_id': e['dst_id']} for e in batch]
    query = f"""
        UNWIND $pairs AS pair
        MATCH (src {{id: pair.src_id}})
        MATCH (dst {{id: pair.dst_id}})
        MERGE (src)-[:{relation}]->(dst)
    """
    tx.run(query, pairs=pairs)

# ==================== MAIN FUNCTION ====================
def update_graph_in_neo4j():
    """Cập nhật graph: giữ nguyên cái giống nhau, xóa cái cũ khác, đẩy cái mới"""
    
    # 1. Load dữ liệu từ JSON
    log.info("\n📂 Load dữ liệu từ file JSON...")
    
    with open(NODES_PATH, encoding="utf-8") as f:
        new_nodes = json.load(f)
    log.info(f"✓ Đã load {len(new_nodes)} nodes từ file")
    
    with open(EDGES_PATH, encoding="utf-8") as f:
        new_edges = json.load(f)
    log.info(f"✓ Đã load {len(new_edges)} edges từ file")
    
    # 2. Fetch dữ liệu hiện tại từ Neo4j
    log.info("\n🔍 Lấy dữ liệu hiện tại từ Neo4j...")
    with driver.session() as session:
        old_nodes = session.execute_read(fetch_nodes_from_neo4j)
        old_edges = session.execute_read(fetch_edges_from_neo4j)
    
    log.info(f"✓ Đã lấy {len(old_nodes)} nodes từ Neo4j")
    log.info(f"✓ Đã lấy {len(old_edges)} edges từ Neo4j")
    
    # 3. So sánh Nodes (dùng dict theo id → O(n))
    log.info("\n📊 So sánh Nodes...")
    old_nodes_dict = {node.get('id'): node for node in old_nodes}
    new_nodes_dict = {node.get('id'): node for node in new_nodes}
    
    nodes_to_delete = []    # IDs nodes cần xóa 
    nodes_to_update = []    # Nodes cần cập nhật 
    nodes_to_add = []       # Nodes hoàn toàn mới
    nodes_kept = 0
    
    # Check nodes cũ: xóa nếu không còn, cập nhật nếu thay đổi
    for node_id, old_node in old_nodes_dict.items():
        if node_id not in new_nodes_dict:
            nodes_to_delete.append(node_id)
            log.info(f"  🗑️  Xóa node (không còn tồn tại): {node_id}")
        elif make_node_key(old_node) != make_node_key(new_nodes_dict[node_id]):
            nodes_to_update.append(new_nodes_dict[node_id])
            log.info(f"  🔄 Cập nhật node (dữ liệu thay đổi): {node_id}")
        else:
            nodes_kept += 1
    
    # Check nodes mới: thêm nếu chưa tồn tại
    for node_id, new_node in new_nodes_dict.items():
        if node_id not in old_nodes_dict:
            nodes_to_add.append(new_node)
            log.info(f"  ➕ Thêm node mới: {node_id}")
    
    log.info(f"\n📋 Tóm tắt Nodes:")
    log.info(f"  ✅ Giữ nguyên: {nodes_kept} nodes")
    log.info(f"  🗑️  Xóa: {len(nodes_to_delete)} nodes")
    log.info(f"  🔄 Cập nhật: {len(nodes_to_update)} nodes")
    log.info(f"  ➕ Thêm mới: {len(nodes_to_add)} nodes")
    
    # 4. So sánh Edges 
    log.info("\n📊 So sánh Edges...")
    
    old_edge_set = set(make_edge_key(e) for e in old_edges)
    new_edge_set = set(make_edge_key(e) for e in new_edges)
    
    # Edges cần xóa = có trong cũ mà không có trong mới
    edges_to_delete_keys = old_edge_set - new_edge_set
    edges_to_delete = [e for e in old_edges if make_edge_key(e) in edges_to_delete_keys]
    
    # Edges cần thêm = có trong mới mà không có trong cũ
    edges_to_add_keys = new_edge_set - old_edge_set
    edges_to_add = [e for e in new_edges if make_edge_key(e) in edges_to_add_keys]
    
    edges_kept = len(old_edge_set & new_edge_set)
    
    for e in edges_to_delete:
        log.info(f"  🗑️  Xóa edge: {e['src_id']} -[{e['relation']}]-> {e['dst_id']}")
    for e in edges_to_add:
        log.info(f"  ➕ Thêm edge: {e['src_id']} -[{e['relation']}]-> {e['dst_id']}")
    
    log.info(f"\n📋 Tóm tắt Edges:")
    log.info(f"  ✅ Giữ nguyên: {edges_kept} edges")
    log.info(f"  🗑️  Xóa: {len(edges_to_delete)} edges")
    log.info(f"  ➕ Thêm mới: {len(edges_to_add)} edges")
    
    # 5. Thực hiện cập nhật (thứ tự: xóa edges → xóa nodes → cập nhật nodes → thêm nodes → thêm edges)
    log.info("\n⚙️  Thực hiện cập nhật...")
    
    with driver.session() as session:
        # Bước 1: Xóa edges cũ TRƯỚC (để không mất edges khi xóa nodes)
        if edges_to_delete:
            log.info(f"\n🗑️  Xóa {len(edges_to_delete)} edges...")
            for i in range(0, len(edges_to_delete), BATCH):
                batch = edges_to_delete[i:i+BATCH]
                try:
                    session.execute_write(delete_edges_batch, batch)
                except Exception as e:
                    log.error(f"❌ Lỗi xóa edges: {e}")
                progress = min(i + BATCH, len(edges_to_delete))
                log.info(f"  📊 Đã xóa {progress}/{len(edges_to_delete)} edges")
            log.info("✅ Xóa edges thành công")
        
        # Bước 2: Xóa nodes không còn tồn tại
        if nodes_to_delete:
            log.info(f"\n🗑️  Xóa {len(nodes_to_delete)} nodes...")
            for i in range(0, len(nodes_to_delete), BATCH):
                batch = nodes_to_delete[i:i+BATCH]
                try:
                    session.execute_write(delete_nodes_batch, batch)
                except Exception as e:
                    log.error(f"❌ Lỗi xóa nodes: {e}")
                progress = min(i + BATCH, len(nodes_to_delete))
                log.info(f"  📊 Đã xóa {progress}/{len(nodes_to_delete)} nodes")
            log.info("✅ Xóa nodes thành công")
        
        # Bước 3: Cập nhật nodes đã thay đổi (xóa cũ + tạo mới với label đúng)
        if nodes_to_update:
            log.info(f"\n🔄 Cập nhật {len(nodes_to_update)} nodes...")
            # Nhóm theo type/label
            by_label = defaultdict(list)
            for node in nodes_to_update:
                label = node.get('type', 'Unknown')
                by_label[label].append(node)
            
            for label, group in by_label.items():
                for i in range(0, len(group), BATCH):
                    batch = group[i:i+BATCH]
                    try:
                        session.execute_write(update_nodes_batch, label, batch)
                    except Exception as e:
                        log.error(f"❌ Lỗi cập nhật nodes [{label}]: {e}")
                log.info(f"  ✅ Cập nhật {len(group)} nodes [{label}]")
            log.info("✅ Cập nhật nodes thành công")
        
        # Bước 4: Thêm nodes mới (có label đúng)
        if nodes_to_add:
            log.info(f"\n📤 Đẩy {len(nodes_to_add)} nodes mới lên Neo4j...")
            # Nhóm theo type để tạo đúng label
            by_label = defaultdict(list)
            for node in nodes_to_add:
                label = node.get('type', 'Unknown')
                by_label[label].append(node)
            
            for label, group in by_label.items():
                for i in range(0, len(group), BATCH):
                    batch = group[i:i+BATCH]
                    try:
                        session.execute_write(push_nodes_batch, label, batch)
                    except Exception as e:
                        log.error(f"❌ Lỗi push nodes [{label}]: {e}")
                log.info(f"  ✅ Đẩy {len(group)} nodes [{label}]")
            log.info("✅ Push nodes thành công")
        
        # Bước 5: Thêm edges mới
        if edges_to_add:
            log.info(f"\n📤 Đẩy {len(edges_to_add)} edges mới lên Neo4j...")
            # Nhóm theo relation type
            by_relation = defaultdict(list)
            for edge in edges_to_add:
                by_relation[edge['relation']].append(edge)
            
            for relation, group in by_relation.items():
                for i in range(0, len(group), BATCH):
                    batch = group[i:i+BATCH]
                    try:
                        session.execute_write(push_edges_batch, relation, batch)
                    except Exception as e:
                        log.error(f"❌ Lỗi push edges [{relation}]: {e}")
                log.info(f"  ✅ Đẩy {len(group)} edges [{relation}]")
            log.info("✅ Push edges thành công")
    
    # 6. In kết quả cuối cùng
    log.info("\n" + "="*70)
    log.info("✅ HOÀN THÀNH! Graph đã được cập nhật")
    log.info("="*70)
    log.info(f"\n📊 Kết quả cập nhật:")
    log.info(f"  • Nodes giữ nguyên: {nodes_kept}")
    log.info(f"  • Nodes xóa: {len(nodes_to_delete)}")
    log.info(f"  • Nodes cập nhật: {len(nodes_to_update)}")
    log.info(f"  • Nodes thêm mới: {len(nodes_to_add)}")
    log.info(f"  • Edges giữ nguyên: {edges_kept}")
    log.info(f"  • Edges xóa: {len(edges_to_delete)}")
    log.info(f"  • Edges thêm mới: {len(edges_to_add)}")
    log.info(f"\n  📈 Tổng nodes hiện tại: {len(new_nodes_dict)}")
    log.info(f"  📈 Tổng edges hiện tại: {len(new_edges)}")


# ==================== MAIN ====================
if __name__ == "__main__":
    try:
        update_graph_in_neo4j()
    except Exception as e:
        log.error(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()
        log.info("\n✅ Kết nối Neo4j đã đóng")