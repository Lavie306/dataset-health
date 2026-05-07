"""
run_pipeline.py  –  Chạy toàn bộ pipeline một lệnh
===================================================
Usage:
  python run_pipeline.py                        # chạy full 6 bước
  python run_pipeline.py --steps 1 2            # chỉ chạy step 1 và 2
  python run_pipeline.py --steps 3 --limit 50  # test dịch 50 bản ghi
  python run_pipeline.py --skip-translate       # chạy 1+2+3b+4+5+6
  python run_pipeline.py --steps 5 6           # chỉ discretize + report

Pipeline đầy đủ:
  Step 1: Clean          – loại noise, chuẩn hóa, quality flags
  Step 2: Merge          – gộp Mayo + MedlinePlus (provenance + conflict)
  Step 3: Translate      – dịch sang tiếng Việt
  Step 3b: Reduce        – smart truncation, fuzzy dedup, sparse handling
  Step 4: Export         – JSON / JSONL / CSV + stats
  Step 5: Discretize     – ICD-10, phân loại bệnh, chronic/acute, flags
  Step 6: Quality Report – báo cáo chất lượng toàn diện 6 sections
"""

import argparse, importlib.util, logging, os, pathlib, sys, time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")

PIPELINE_DIR = pathlib.Path(__file__).parent
ROOT         = PIPELINE_DIR.parent.parent
UTILS_DIR    = ROOT / "src" / "utils"

STEPS = {
    1:   (PIPELINE_DIR / "Clean_data.py",      "Clean – loại noise, chuẩn hóa, quality flags"),
    2:   (PIPELINE_DIR / "merg_data.py",        "Merge – gộp Mayo + MedlinePlus (provenance + conflict)"),
    3:   (PIPELINE_DIR / "translate_data.py",   "Translate – dịch sang tiếng Việt"),
    4:   (PIPELINE_DIR / "reduce_data.py",      "Reduce – smart truncation, fuzzy dedup, sparse handling"),
    5:   (PIPELINE_DIR / "export_data.py",      "Export – JSON / JSONL / CSV + stats"),
    6:   (PIPELINE_DIR / "discretize_data.py",  "Discretize – ICD-10, phân loại bệnh, chronic/acute, flags"),
    7:   (UTILS_DIR    / "quality_report.py",   "Quality Report – báo cáo chất lượng toàn diện"),
}


def run_step(step_num: int, extra_env: dict = None):
    fpath, desc = STEPS[step_num]
    log.info("=" * 65)
    log.info(f"STEP {step_num}: {desc}")
    log.info("=" * 65)

    if not fpath.exists():
        log.error(f"  File không tồn tại: {fpath}")
        raise FileNotFoundError(str(fpath))

    if extra_env:
        for k, v in extra_env.items():
            os.environ[k] = str(v)

    spec = importlib.util.spec_from_file_location(f"step{step_num}", fpath)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    import asyncio
    if hasattr(mod, "run"):
        mod.run()
    elif hasattr(mod, "main"):
        if asyncio.iscoroutinefunction(mod.main):
            asyncio.run(mod.main())
        else:
            mod.main()
    else:
        raise RuntimeError(f"{fpath.name} không có hàm run() hoặc main()")


def check_inputs():
    missing = []
    for p in [
        ROOT / "data/raw/mayo_full.json",
        ROOT / "data/raw/medlineplus_full.json",
    ]:
        if not p.exists():
            missing.append(str(p))
    if missing:
        log.error("File đầu vào không tồn tại:")
        for m in missing:
            log.error(f"  {m}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Medical data pipeline: clean → merge → translate → reduce → export → discretize → quality"
    )
    parser.add_argument(
        "--steps", nargs="+", type=int, choices=list(STEPS.keys()),
        help="Chỉ chạy các bước được chỉ định (mặc định: 1–7)"
    )
    parser.add_argument(
        "--skip-translate", action="store_true",
        help="Bỏ qua step 3 (translate)"
    )
    parser.add_argument(
        "--skip-reduce", action="store_true",
        help="Bỏ qua step 4 (reduce)"
    )
    parser.add_argument(
        "--skip-discretize", action="store_true",
        help="Bỏ qua step 6 (discretize)"
    )
    parser.add_argument(
        "--skip-quality", action="store_true",
        help="Bỏ qua step 7 (quality report)"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Giới hạn số bản ghi dịch (0 = tất cả)"
    )
    args = parser.parse_args()

    steps_to_run = args.steps or list(STEPS.keys())

    if args.skip_translate and 3 in steps_to_run:
        steps_to_run = [s for s in steps_to_run if s != 3]
        log.info("--skip-translate: bỏ qua step 3")

    if args.skip_reduce and 4 in steps_to_run:
        steps_to_run = [s for s in steps_to_run if s != 4]
        log.info("--skip-reduce: bỏ qua step 4")

    if args.skip_discretize and 6 in steps_to_run:
        steps_to_run = [s for s in steps_to_run if s != 6]
        log.info("--skip-discretize: bỏ qua step 6")

    if args.skip_quality and 7 in steps_to_run:
        steps_to_run = [s for s in steps_to_run if s != 7]
        log.info("--skip-quality: bỏ qua step 7")

    if 1 in steps_to_run:
        check_inputs()

    t_total = time.time()

    for step in sorted(steps_to_run):
        t_step = time.time()
        extra = {}
        if step == 3 and args.limit > 0:
            extra["TRANSLATE_LIMIT"] = args.limit
        try:
            run_step(step, extra)
        except Exception as e:
            log.error(f"Step {step} thất bại: {e}")
            raise
        elapsed = time.time() - t_step
        log.info(f"Step {step} hoàn thành trong {elapsed:.1f}s\n")

    log.info("=" * 65)
    log.info(f"✅ Pipeline hoàn thành trong {time.time()-t_total:.1f}s")
    log.info("")
    log.info("📁 Output files  ([GHI ĐÈ] = đè file cũ | [MỚI] = file mới):")
    log.info("")

    # (fpath, label, overwrites_old_file)
    output_files = [
        (ROOT / "data/processed/mayo_clean.json",          "Step 1 – Clean Mayo",            True),
        (ROOT / "data/processed/medlineplus_clean.json",   "Step 1 – Clean MedlinePlus",     True),
        (ROOT / "data/processed/merged.json",              "Step 2 – Merged",                True),
        (ROOT / "data/processed/translated.json",          "Step 3 – Translated",            True),
        (ROOT / "data/processed/reduced.json",             "Step 4 – Reduced (GIỮ nguyên translated)", False),
        (ROOT / "data/processed/reduction_report.json",    "Step 4 – Reduction report",      False),
        (ROOT / "data/output/medical_vi.json",             "Step 5 – Export JSON",           True),
        (ROOT / "data/output/medical_vi.csv",              "Step 5 – Export CSV",            True),
        (ROOT / "data/output/stats.json",                  "Step 5 – Stats",                 True),
        (ROOT / "data/processed/discretized.json",         "Step 6 – Discretized",           False),
        (ROOT / "data/output/quality_report.json",         "Step 7 – Quality JSON",          True),
        (ROOT / "data/output/quality_report.md",           "Step 7 – Quality MD",            True),
    ]

    for fpath, label, overwrites in output_files:
        exists = fpath.exists()
        icon   = "✓" if exists else "✗"
        size   = f"{fpath.stat().st_size/1024:.0f} KB" if exists else "---"
        ow_tag = "[GHI ĐÈ]" if overwrites else "[MỚI]   "
        log.info(f"  [{icon}] {ow_tag}  {label:<48} {size}")


if __name__ == "__main__":
    main()