"""
STEP 3 – TRANSLATE  (English → Vietnamese)
==========================================
Dùng Google Translate FREE (deep-translator).

Tối ưu tốc độ:
  - Gom TẤT CẢ fields của 1 record thành 1 request duy nhất
    (dùng separator @@SEP@@ để tách, giảm từ 11 → 1 call/record)
  - WORKERS=15 threads song song
  - Delay tối thiểu giữa requests

Cài đặt: pip install deep-translator
"""

import json, os, pathlib, logging, time, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("translate")

ROOT      = pathlib.Path(__file__).parent.parent.parent
PIPELINE_DIR = pathlib.Path(__file__).parent
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

from medical_glossary import apply_glossary

IN_FILE   = ROOT / "data/processed/merged.json"
OUT_FILE  = ROOT / "data/processed/translated.json"
CKPT_FILE = ROOT / "data/processed/translate_checkpoint.json"

WORKERS = int(os.getenv("TRANSLATE_WORKERS", "15"))  # tăng từ 5 → 15
LIMIT   = int(os.getenv("TRANSLATE_LIMIT",   "0"))

TRANSLATE_FIELDS = [
    "overview", "symptoms", "causes",
    "risk_factors", "prevention", "when_to_see_doc",
    "treatment", "prognosis", "complications", "exams_and_tests",
]

SEP      = " @@SEP@@ "   # separator không bị Google dịch
MAX_CHARS = 4500          # giới hạn Google Translate mỗi request


# =============================================================================
# CORE TRANSLATE – 1 call cho cả record
# =============================================================================
def translate_batch(texts: list[str], retries: int = 4) -> list[str] | None:
    """
    Gom nhiều đoạn text bằng SEP → 1 request → split kết quả.
    Tiết kiệm 10x số request so với gọi riêng từng field.
    """
    joined = SEP.join(texts)

    # Nếu quá dài → chunk theo SEP boundary
    if len(joined) > MAX_CHARS:
        return _translate_chunked(texts, retries)

    for attempt in range(retries):
        try:
            result = GoogleTranslator(source="en", target="vi").translate(joined)
            if not result:
                return texts  # fallback

            # Split kết quả – Google đôi khi thêm space quanh SEP
            parts = re.split(r"\s*@@SEP@@\s*", result)

            # Số phần phải khớp
            if len(parts) == len(texts):
                return parts
            else:
                # Mismatch → dịch riêng từng cái
                log.warning(f"  SEP mismatch ({len(parts)} vs {len(texts)}), fallback riêng")
                return _translate_one_by_one(texts, retries)

        except Exception as e:
            wait = 1 + attempt * 2
            if attempt < retries - 1:
                time.sleep(wait)
            else:
                log.warning(f"  Thất bại: {str(e)[:60]}")
                return texts  # giữ nguyên tiếng Anh

    return texts


def _translate_chunked(texts: list[str], retries: int) -> list[str]:
    """Khi tổng text quá dài, chia thành nhiều nhóm nhỏ."""
    results = []
    group, group_len, group_idx = [], 0, []

    for i, t in enumerate(texts):
        if group_len + len(t) > MAX_CHARS and group:
            translated = translate_batch(group, retries)
            results.extend(translated)
            group, group_len = [], 0
        group.append(t)
        group_len += len(t) + len(SEP)

    if group:
        results.extend(translate_batch(group, retries))

    return results


def _translate_one_by_one(texts: list[str], retries: int) -> list[str]:
    """Fallback: dịch từng text riêng lẻ."""
    results = []
    for t in texts:
        try:
            r = GoogleTranslator(source="en", target="vi").translate(t)
            results.append(r or t)
            time.sleep(0.1)
        except Exception:
            results.append(t)
    return results


def translate_record(record: dict) -> dict:
    translated             = dict(record)
    translated["disease_en"] = record["disease"]

    # Gom disease + các fields có nội dung
    keys_to_translate = ["disease"]
    texts_to_translate = [record["disease"]]

    for field in TRANSLATE_FIELDS:
        text = record.get(field, "").strip()
        if text and len(text.split()) >= 5:
            keys_to_translate.append(field)
            # Cắt ngắn nếu field cực dài (hiếm)
            texts_to_translate.append(text[:2000])
        else:
            translated[field] = text  # giữ nguyên nếu rỗng

    # 1 API call cho toàn bộ record
    results = translate_batch(texts_to_translate)

    for key, result in zip(keys_to_translate, results):
        translated[key] = apply_glossary(result)

    return translated


# =============================================================================
# CHECKPOINT
# =============================================================================
def load_checkpoint() -> dict:
    if CKPT_FILE.exists():
        with open(CKPT_FILE, encoding="utf-8") as f:
            data = json.load(f)
        log.info(f"Checkpoint: {len(data)} bản ghi đã dịch")
        return data
    return {}


def save_checkpoint(done: dict):
    CKPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CKPT_FILE, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False, indent=2)


# =============================================================================
# MAIN
# =============================================================================
def run():
    log.info(f"Loading {IN_FILE} ...")
    with open(IN_FILE, encoding="utf-8") as f:
        records = json.load(f)

    if LIMIT > 0:
        records = records[:LIMIT]
        log.info(f"TRANSLATE_LIMIT={LIMIT}: chỉ dịch {LIMIT} bản ghi đầu")

    done = load_checkpoint()
    todo = [r for r in records if r["disease"] not in done]
    log.info(f"Tổng: {len(records)} | Đã dịch: {len(done)} | Cần dịch: {len(todo)}")
    log.info(f"Workers: {WORKERS} | ~1 API call/record (thay vì 11)")

    if not todo:
        log.info("Tất cả đã được dịch!")
    else:
        start = time.time()
        BATCH = 50  # tăng batch size vì mỗi record chỉ 1 call

        for batch_start in range(0, len(todo), BATCH):
            batch = todo[batch_start : batch_start + BATCH]

            with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                future_to_rec = {
                    executor.submit(translate_record, rec): rec
                    for rec in batch
                }
                for future in as_completed(future_to_rec):
                    rec = future_to_rec[future]
                    try:
                        result = future.result()
                        done[result.get("disease_en", rec["disease"])] = result
                    except Exception as e:
                        log.warning(f"  Lỗi '{rec['disease']}': {e}")
                        done[rec["disease"]] = rec

            save_checkpoint(done)

            done_count = min(batch_start + BATCH, len(todo))
            elapsed    = time.time() - start
            rate       = done_count / elapsed
            eta        = (len(todo) - done_count) / rate if rate > 0 else 0
            log.info(
                f"  {done_count}/{len(todo)} "
                f"| {rate:.1f} rec/s "
                f"| ETA {eta/60:.1f} phút"
            )

    # Xuất theo thứ tự gốc, áp glossary lại để cả checkpoint cũ cũng được chuẩn hóa.
    output = []
    normalized_fields = ["disease", *TRANSLATE_FIELDS]
    for r in records:
        rec = dict(done.get(r["disease"], r))
        for field in normalized_fields:
            if isinstance(rec.get(field), str):
                rec[field] = apply_glossary(rec[field])
        output.append(rec)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"Saved → {OUT_FILE} ({len(output)} bản ghi)")
    log.info("✅ Dịch hoàn tất!")


if __name__ == "__main__":
    run()
