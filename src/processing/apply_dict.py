"""Apply the medical glossary to translated data.

This script is safe to re-run. It rewrites translated.json in place and writes a
small report so the normalization step is auditable.
"""

import json
import logging
import pathlib
import sys

PIPELINE_DIR = pathlib.Path(__file__).parent
ROOT = PIPELINE_DIR.parent.parent
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

from medical_glossary import apply_glossary_to_record

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("apply_dict")

IN_FILE = ROOT / "data" / "processed" / "translated.json"
REPORT_FILE = ROOT / "data" / "processed" / "glossary_report.json"

FIELDS = [
    "disease", "overview", "symptoms", "causes", "risk_factors",
    "prevention", "when_to_see_doc", "treatment", "prognosis",
    "complications", "exams_and_tests",
]


def run():
    with open(IN_FILE, encoding="utf-8") as f:
        data = json.load(f)

    changed_records = 0
    changed_fields = 0
    for rec in data:
        rec, count = apply_glossary_to_record(rec, FIELDS)
        if count:
            changed_records += 1
            changed_fields += count

    with open(IN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    report = {
        "input_file": str(IN_FILE),
        "records": len(data),
        "changed_records": changed_records,
        "changed_fields": changed_fields,
    }
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log.info(f"Glossary normalized {changed_fields} fields in {changed_records} records")
    log.info(f"Saved report -> {REPORT_FILE}")


if __name__ == "__main__":
    run()
