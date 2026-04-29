"""
run_pipeline.py  –  Chạy toàn bộ pipeline một lệnh
===================================================
Usage:
  python run_pipeline.py                  # chạy full 4 bước
  python run_pipeline.py --steps 1 2      # chỉ chạy step 1 và 2
  python run_pipeline.py --steps 3 --limit 50   # test dịch 50 bản ghi
  python run_pipeline.py --skip-translate # chạy 1+2+4, bỏ qua dịch

Env:
  ANTHROPIC_API_KEY   – cần thiết cho step 3
  TRANSLATE_CONCURRENT – số request song song (default 8)

Thư mục kỳ vọng:
  data/
    raw/
      mayo_full.json
      medlineplus_full.json
    processed/   ← tạo tự động
    output/      ← tạo tự động
"""

import argparse, importlib.util, logging, os, pathlib, sys, time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")

PIPELINE_DIR = pathlib.Path(__file__).parent

STEPS = {
    1: ("step1_clean.py",     "Clean – loại noise, chuẩn hóa schema"),
    2: ("step2_merge.py",     "Merge – gộp Mayo + MedlinePlus"),
    3: ("step3_translate.py", "Translate – dịch sang tiếng Việt (Anthropic API)"),
    4: ("step4_export.py",    "Export – JSON / JSONL / CSV + stats"),

}


def run_step(step_num: int, extra_env: dict = None):
    fname, desc = STEPS[step_num]
    log.info("=" * 60)
    log.info(f"STEP {step_num}: {desc}")
    log.info("=" * 60)

    if extra_env:
        for k, v in extra_env.items():
            os.environ[k] = str(v)

    spec = importlib.util.spec_from_file_location(
        f"step{step_num}", PIPELINE_DIR / fname
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Each step exposes a run() or main() coroutine
    import asyncio
    if hasattr(mod, "run"):
        mod.run()
    elif hasattr(mod, "main"):
        if asyncio.iscoroutinefunction(mod.main):
            asyncio.run(mod.main())
        else:
            mod.main()
    else:
        raise RuntimeError(f"{fname} không có hàm run() hoặc main()")


def check_inputs():
    missing = []
    for p in ["../../data/raw/mayo_full.json", "../../data/raw/medlineplus_full.json"]:
        if not pathlib.Path(p).exists():
            missing.append(p)
    if missing:
        log.error("File đầu vào không tồn tại:")
        for m in missing:
            log.error(f"  {m}")
        log.error("Hãy đặt mayo_full.json và medlineplus_full.json vào data/raw/")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Medical data pipeline: clean → merge → translate → export"
    )
    parser.add_argument(
        "--steps", nargs="+", type=int, choices=[1, 2, 3, 4],
        help="Chỉ chạy các bước được chỉ định (mặc định: 1 2 3 4)"
    )
    parser.add_argument(
        "--skip-translate", action="store_true",
        help="Bỏ qua bước 3 (translate), chạy 1 2 4"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Giới hạn số bản ghi dịch (0 = tất cả) – chỉ ảnh hưởng step 3"
    )
    args = parser.parse_args()

    steps_to_run = args.steps or [1, 2, 3, 4]
    if args.skip_translate and 3 in steps_to_run:
        steps_to_run = [s for s in steps_to_run if s != 3]
        log.info("--skip-translate: bỏ qua step 3")

    if 1 in steps_to_run:
        check_inputs()

    if 3 in steps_to_run and not os.getenv("GEMINI_API_KEY"):
        log.error("GEMINI_API_KEY chưa được set!")
        log.error("  Windows : set GEMINI_API_KEY=AIza...")
        log.error("  Linux   : export GEMINI_API_KEY=AIza...")
        sys.exit(1)

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
        log.info(f"Step {step} hoàn thành trong {time.time() - t_step:.1f}s\n")

    log.info("=" * 60)
    log.info(f"✅ Pipeline hoàn thành trong {time.time()-t_total:.1f}s")
    log.info("Output files:")
    for p in [
        "../../data/processed/mayo_clean.json",
        "../../data/processed/medlineplus_clean.json",
        "../../data/processed/merged.json",
        "../../data/processed/translated.json",
        "../../data/output/medical_vi.json",
        "../../data/output/medical_vi.jsonl",
        "../../data/output/medical_vi.csv",
        "../../data/output/stats.json",
    ]:
        icon = "✓" if pathlib.Path(p).exists() else "✗"
        log.info(f"  [{icon}] {p}")


if __name__ == "__main__":
    main()