"""
main.py – Entry point chính của dự án Medical Data Mining
==========================================================
Điều phối các tác vụ: pipeline, phân tích, knowledge graph.

Cách dùng:
  python src/main.py pipeline       # Chạy toàn bộ pipeline xử lý dữ liệu (7 bước)
  python src/main.py analyze        # Vẽ biểu đồ phân tích dữ liệu đã xử lý
  python src/main.py analyze-raw    # Vẽ biểu đồ phân tích dữ liệu thô
  python src/main.py graph          # Xây dựng Knowledge Graph
  python src/main.py all            # Chạy pipeline + analyze
"""

import argparse
import pathlib
import sys
import importlib.util

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))


def load_and_run(fpath: pathlib.Path):
    """Nạp một module Python theo đường dẫn và gọi hàm run()."""
    if not fpath.exists():
        print(f"[ERROR] Không tìm thấy file: {fpath}")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location(fpath.stem, fpath)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "run"):
        mod.run()
    elif hasattr(mod, "main"):
        mod.main()
    else:
        print(f"[ERROR] {fpath.name} không có hàm run() hoặc main()")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Medical Data Mining – Entry Point Chính",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "task",
        choices=["pipeline", "analyze", "analyze-raw", "graph", "all"],
        help="Tác vụ muốn thực hiện"
    )
    args = parser.parse_args()

    PROCESSING_DIR = ROOT / "src/processing"
    UTILS_DIR      = ROOT / "src/utils"

    task = args.task

    if task in ("pipeline", "all"):
        print("=" * 60)
        print("🚀 Chạy Pipeline Xử Lý Dữ Liệu (7 bước)...")
        print("=" * 60)
        load_and_run(PROCESSING_DIR / "run_pipeline.py")

    if task in ("analyze", "all"):
        print("=" * 60)
        print("📊 Vẽ biểu đồ phân tích dữ liệu đã xử lý...")
        print("=" * 60)
        load_and_run(UTILS_DIR / "data_analysis.py")

    if task == "analyze-raw":
        print("=" * 60)
        print("📊 Vẽ biểu đồ phân tích dữ liệu thô...")
        print("=" * 60)
        load_and_run(UTILS_DIR / "raw_data_analysis.py")

    if task == "graph":
        print("=" * 60)
        print("🕸️  Xây dựng Knowledge Graph...")
        print("=" * 60)
        GRAPH_DIR = ROOT / "src/graph"
        load_and_run(GRAPH_DIR / "data_graph.py")
        load_and_run(GRAPH_DIR / "enhance_graph_with_drugs_guidelines.py")


if __name__ == "__main__":
    main()
