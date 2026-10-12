from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core import FIELD_NAMES, FIELD_COLUMNS, clean_value, stable_id

RAW = ROOT / "data/raw/SGO-2021-01_Incident_Reports_ADS.csv"
PROCESSED = ROOT / "data/processed"


def parse_month(row: dict[str, str]) -> datetime:
    raw = row.get("Report Submission Date", "").strip().upper()
    try:
        return datetime.strptime(raw, "%b-%Y")
    except ValueError:
        year = row.get("Report Year", "").strip()
        return datetime(int(year), 1, 1) if year.isdigit() else datetime.min


def compact_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "id": stable_id(row),
        "report_id": row.get("Report ID", ""),
        "report_version": row.get("Report Version", ""),
        "reporting_entity": row.get("Reporting Entity", "") or "Unknown entity",
        "submission_date": row.get("Report Submission Date", "") or "not stated",
        "narrative": row.get("Narrative", "").strip(),
        **{field: clean_value(row.get(column, "")) for field, column in FIELD_COLUMNS.items()},
    }


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"missing {RAW}; download the verified NHTSA CSV first")
    rows = pd.read_csv(RAW, dtype=str, keep_default_na=False).to_dict(orient="records")
    rows = [row for row in rows if row.get("Narrative", "").strip()]
    rows.sort(key=lambda row: (parse_month(row), row.get("Report ID", "")), reverse=True)
    entity_counts = {}
    for row in rows:
        entity = row.get("Reporting Entity", "") or "Unknown entity"
        entity_counts[entity] = entity_counts.get(entity, 0) + 1
    smallest_entity = sorted(entity_counts.items(), key=lambda item: (item[1], item[0]))[0][0]
    newest_count = max(1, math.ceil(len(rows) * 0.30))
    test_rows = rows[:newest_count]
    test_ids = {stable_id(row) for row in test_rows}
    test_ids.update(stable_id(row) for row in rows if (row.get("Reporting Entity", "") or "Unknown entity") == smallest_entity)
    test_rows = [compact_row(row) for row in rows if stable_id(row) in test_ids]
    test_rows.sort(key=lambda row: (row["submission_date"], row["report_id"]), reverse=True)

    demo = []
    seen_entities = set()
    for row in test_rows:
        if row["reporting_entity"] not in seen_entities:
            demo.append(row)
            seen_entities.add(row["reporting_entity"])
        if len(demo) == 20:
            break
    if len(demo) < 20:
        demo.extend(row for row in test_rows if row not in demo)
        demo = demo[:20]
    labels = {
        "allowed": {field: sorted({str(row[field]) for row in test_rows}) for field in FIELD_NAMES},
        "smallest_entity": smallest_entity,
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "eval_rows.json").write_text(json.dumps(test_rows, indent=2, ensure_ascii=False) + "\n")
    (PROCESSED / "demo_rows.json").write_text(json.dumps(demo, indent=2, ensure_ascii=False) + "\n")
    (PROCESSED / "labels.json").write_text(json.dumps(labels, indent=2, ensure_ascii=False) + "\n")
    print(f"source_rows={len(rows)}")
    print(f"test_rows={len(test_rows)}")
    print(f"newest_count={newest_count}")
    print(f"smallest_entity={smallest_entity}")
    print(f"demo_rows={len(demo)}")


if __name__ == "__main__":
    main()
