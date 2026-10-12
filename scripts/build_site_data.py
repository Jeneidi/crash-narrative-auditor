from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core import FIELD_NAMES


def main() -> None:
    processed = ROOT / "data/processed"
    site_data = ROOT / "site/data"
    site_data.mkdir(parents=True, exist_ok=True)
    rows = json.loads((processed / "eval_rows.json").read_text())
    model = {item["id"]: item for item in json.loads((processed / "model_results.json").read_text())}
    metrics = json.loads((processed / "metrics.json").read_text())
    demo_rows = json.loads((processed / "demo_rows.json").read_text())
    fields = {
        "crash_partner": "Crash partner",
        "roadway_type": "Roadway type",
        "other_party_movement": "Other party movement",
        "injury_severity": "Injury severity",
    }
    runs = []
    disagreements = []
    for row in rows:
        result = model[row["id"]]
        mismatches = []
        for field in FIELD_NAMES:
            if result["prediction"][field] != row[field]:
                mismatches.append(field)
        if mismatches and len(disagreements) < 50:
            disagreements.append({
                "id": row["id"],
                "report_id": row["report_id"],
                "narrative": row["narrative"],
                "mismatches": mismatches,
                "filed": {field: row[field] for field in FIELD_NAMES},
                "model": {field: result["prediction"][field] for field in FIELD_NAMES},
            })
    for row in demo_rows:
        result = model[row["id"]]
        runs.append({
            "id": row["id"],
            "report_id": row["report_id"],
            "reporting_entity": row["reporting_entity"],
            "submission_date": row["submission_date"],
            "narrative": row["narrative"],
            "valid": result["valid"],
            "fields": [
                {
                    "key": field,
                    "label": fields[field],
                    "predicted": result["prediction"][field],
                    "filed": row[field],
                    "evidence": result["prediction"].get(f"{field}_evidence", ""),
                    "agree": result["prediction"][field] == row[field],
                }
                for field in FIELD_NAMES
            ],
        })
    site_metrics = {
        "rows": metrics["rows"],
        "model_rows": metrics["model_rows"],
        "macro_accuracy": metrics["macro_accuracy"],
        "baseline_macro_accuracy": metrics["baseline_macro_accuracy"],
        "evidence_exact_rate": metrics["evidence_exact_rate"],
        "abstention_rate": metrics["abstention_rate"],
        "non_abstained_accuracy": metrics["non_abstained_accuracy"],
        "valid_output_rate": metrics["valid_output_rate"],
        "cash_cost_per_1000": metrics["cash_cost_per_1000"],
        "measured_seconds": 1676.315,
        "seconds_per_report": 1676.315 / metrics["model_rows"],
        "recorded_with": "Claude Haiku 5.5 via Claude Code, 2026-10-12",
        "split": "Newest 30% by report submission month plus every report from the smallest reporting entity",
        "smallest_entity": json.loads((processed / "labels.json").read_text())["smallest_entity"],
        "fields": metrics["fields"],
    }
    (site_data / "demo.json").write_text(json.dumps({"recorded_with": site_metrics["recorded_with"], "runs": runs}, indent=2, ensure_ascii=False) + "\n")
    (site_data / "metrics.json").write_text(json.dumps(site_metrics, indent=2) + "\n")
    (site_data / "disagreements.json").write_text(json.dumps({"count_listed": len(disagreements), "note": "These are queued for human review. No automated label was treated as a hand check.", "items": disagreements}, indent=2, ensure_ascii=False) + "\n")
    print(f"site_runs={len(runs)}")
    print(f"disagreements_listed={len(disagreements)}")


if __name__ == "__main__":
    main()
