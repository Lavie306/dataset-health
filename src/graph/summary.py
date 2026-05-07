#!/usr/bin/env python3
"""
Hướng dẫn sử dụng Graph với Drugs & Guidelines
==============================================
"""

import json
import pathlib

def print_drugs_summary():
    """In tóm tắt các loại thuốc"""
    print("\n" + "="*70)
    print("📊 DANH SÁCH CÁC LOẠI THUỐC TRONG GRAPH")
    print("="*70)
    
    drugs_file = pathlib.Path("data/graph/drugs.json")
    if drugs_file.exists():
        with open(drugs_file, encoding="utf-8") as f:
            drugs = json.load(f)
        
        print(f"\nTổng số thuốc: {len(drugs)}\n")
        
        # Nhóm theo class
        by_class = {}
        for drug in drugs:
            cls = drug.get("class", "Unknown")
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(drug)
        
        for cls, drugs_in_class in sorted(by_class.items()):
            print(f"📌 {cls} ({len(drugs_in_class)} loại)")
            for drug in drugs_in_class:
                print(f"   • {drug['name']:<30} (ID: {drug['id']})")
    else:
        print("⚠️ Chưa tìm thấy file drugs.json")

def print_guidelines_sample():
    """In mẫu các hướng dẫn"""
    print("\n" + "="*70)
    print("📋 MẪU CÁC HƯỚNG DẪN ĐIỀU TRỊ")
    print("="*70)
    
    guidelines_file = pathlib.Path("data/graph/guidelines.json")
    if guidelines_file.exists():
        with open(guidelines_file, encoding="utf-8") as f:
            guidelines = json.load(f)
        
        print(f"\nTổng số hướng dẫn: {len(guidelines)}\n")
        
        # In 10 mẫu đầu
        print("10 Mẫu đầu tiên:\n")
        for i, g in enumerate(guidelines[:10], 1):
            print(f"{i}. [{g['id']}] {g['related_disease']}")
            print(f"   📝 {g['name'][:80]}{'...' if len(g['name']) > 80 else ''}")
            print()
    else:
        print("⚠️ Chưa tìm thấy file guidelines.json")

def print_graph_stats():
    """In thống kê graph"""
    print("\n" + "="*70)
    print("📊 THỐNG KÊ KNOWLEDGE GRAPH")
    print("="*70)
    
    nodes_file = pathlib.Path("data/graph/nodes_updated.json")
    edges_file = pathlib.Path("data/graph/edges_updated.json")
    
    if nodes_file.exists() and edges_file.exists():
        with open(nodes_file, encoding="utf-8") as f:
            nodes = json.load(f)
        with open(edges_file, encoding="utf-8") as f:
            edges = json.load(f)
        
        # Đếm theo type
        node_types = {}
        for node in nodes:
            if isinstance(node, dict):
                ntype = node.get("type", "Unknown")
                node_types[ntype] = node_types.get(ntype, 0) + 1
        
        edge_types = {}
        for edge in edges:
            if isinstance(edge, dict):
                etype = edge.get("relation", "Unknown")
                edge_types[etype] = edge_types.get(etype, 0) + 1
        
        print(f"\n📌 NODES: {len(nodes)} tổng cộng")
        for ntype, count in sorted(node_types.items()):
            bar = "█" * (count // 100) if count > 100 else "█" * min(count // 10, 5)
            print(f"   {ntype:<20} {count:>6} {bar}")
        
        print(f"\n📌 EDGES: {len(edges)} tổng cộng")
        for etype, count in sorted(edge_types.items()):
            bar = "█" * (count // 1000) if count > 1000 else "█" * min(count // 100, 5)
            print(f"   {etype:<30} {count:>6} {bar}")
    else:
        print("⚠️ Chưa tìm thấy file nodes_updated.json hoặc edges_updated.json")

def print_usage_guide():
    """In hướng dẫn sử dụng"""
    print("\n" + "="*70)
    print("🚀 HƯỚNG DẪN SỬ DỤNG")
    print("="*70)
    
    guide = """
1️⃣  THAY THẾ FILE GỐC:
   $ cp data/graph/nodes_updated.json data/graph/nodes.json
   $ cp data/graph/edges_updated.json data/graph/edges.json

2️⃣  LỰA CHỌN FILE TRONG NEO4J:
   // Import file nodes_updated.json và edges_updated.json 
   // vào Neo4j để có đầy đủ dữ liệu Drugs & Guidelines

3️⃣  QUERY GRAPH (Cypher):
   
   # Tìm thuốc cho một bệnh
   MATCH (d:Disease)-[:TREATED_BY]->(drug:Drug)
   WHERE d.name = "tên bệnh"
   RETURN drug.name, drug.class
   
   # Tìm hướng dẫn cho một bệnh
   MATCH (d:Disease)-[:FOLLOWS]->(g:Guideline)
   WHERE d.name = "tên bệnh"
   RETURN g.name
   
   # Tìm tất cả bệnh được điều trị bằng một thuốc
   MATCH (d:Disease)-[:TREATED_BY]->(drug:Drug)
   WHERE drug.name = "Prednisone"
   RETURN d.name
   
4️⃣  PHÂN TÍCH DỮ LIỆU (Python):
   import json
   
   # Đọc drugs
   with open('data/graph/drugs.json') as f:
       drugs = json.load(f)
   
   # Đọc guidelines
   with open('data/graph/guidelines.json') as f:
       guidelines = json.load(f)
   
   # Đọc edges
   with open('data/graph/edges_updated.json') as f:
       edges = json.load(f)

5️⃣  BỔ SUNG THUỐC MỚI:
   - Mở file: src/graph/enhance_graph_with_drugs_guidelines.py
   - Cập nhật dictionary COMMON_DRUGS
   - Chạy lại script
    """
    print(guide)

if __name__ == "__main__":
    print("\n🎯 GRAPH CÓ DRUGS & GUIDELINES - TÓM TẮT NHANH")
    
    print_graph_stats()
    print_drugs_summary()
    print_guidelines_sample()
    print_usage_guide()
    
    print("\n" + "="*70)
    print("✅ Graph của bạn giờ đã có đầy đủ thông tin về Drugs & Guidelines!")
    print("="*70 + "\n")
