from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core import FIELD_NAMES


FIELD_LABELS = {
    "crash_partner": "Crash partner",
    "roadway_type": "Roadway type",
    "other_party_movement": "Other party movement",
    "injury_severity": "Injury severity",
}


def main() -> None:
    processed = ROOT / "data/processed"
    site_data = ROOT / "site/data"
    site_data.mkdir(parents=True, exist_ok=True)
    rows = json.loads((processed / "eval_rows.json").read_text())
    model = {item["id"]: item for item in json.loads((processed / "model_results.json").read_text())}
    metrics = json.loads((processed / "metrics.json").read_text())
    demo_rows = json.loads((processed / "demo_rows.json").read_text())
    runs = []
    disagreements = []
    disagreement_pairs = {}
    for row in rows:
        result = model[row["id"]]
        mismatches = []
        answered_mismatches = []
        for field in FIELD_NAMES:
            filed = row[field]
            predicted = result["prediction"][field]
            if predicted == filed:
                continue
            mismatches.append(field)
            if predicted == "not stated":
                continue
            answered_mismatches.append(field)
            pair_key = (field, filed, predicted)
            pair = disagreement_pairs.setdefault(
                pair_key,
                {
                    "field": field,
                    "label": FIELD_LABELS[field],
                    "filed": filed,
                    "model": predicted,
                    "count": 0,
                    "example": {
                        "id": row["id"],
                        "report_id": row["report_id"],
                        "narrative": row["narrative"],
                        "evidence": result["prediction"].get(f"{field}_evidence", ""),
                    },
                },
            )
            pair["count"] += 1
        if answered_mismatches and len(disagreements) < 50:
            disagreements.append(
                {
                    "id": row["id"],
                    "report_id": row["report_id"],
                    "narrative": row["narrative"],
                    "mismatches": answered_mismatches,
                    "filed": {field: row[field] for field in FIELD_NAMES},
                    "model": {field: result["prediction"][field] for field in FIELD_NAMES},
                }
            )
    top_pairs = sorted(disagreement_pairs.values(), key=lambda item: (-item["count"], item["label"], item["filed"], item["model"]))[:8]
    for row in demo_rows:
        result = model[row["id"]]
        runs.append(
            {
                "id": row["id"],
                "report_id": row["report_id"],
                "reporting_entity": row["reporting_entity"],
                "submission_date": row["submission_date"],
                "narrative": row["narrative"],
                "valid": result["valid"],
                "fields": [
                    {
                        "key": field,
                        "label": FIELD_LABELS[field],
                        "predicted": result["prediction"][field],
                        "filed": row[field],
                        "evidence": result["prediction"].get(f"{field}_evidence", ""),
                        "agree": result["prediction"][field] == row[field],
                    }
                    for field in FIELD_NAMES
                ],
            }
        )
    labels = json.loads((processed / "labels.json").read_text())
    site_metrics = {
        "rows": metrics["rows"],
        "model_rows": metrics["model_rows"],
        "macro_accuracy": metrics["macro_accuracy"],
        "keyword_macro_accuracy": metrics["keyword_macro_accuracy"],
        "majority_macro_accuracy": metrics["majority_macro_accuracy"],
        "baseline_macro_accuracy": metrics["baseline_macro_accuracy"],
        "answered_slot_accuracy": metrics["answered_slot_accuracy"],
        "answered_slot_count": metrics["answered_slot_count"],
        "answered_slot_total": metrics["answered_slot_total"],
        "evidence_exact_rate": metrics["evidence_exact_rate"],
        "abstention_rate": metrics["abstention_rate"],
        "coverage": metrics["coverage"],
        "non_abstained_accuracy": metrics["non_abstained_accuracy"],
        "valid_output_rate": metrics["valid_output_rate"],
        "cash_cost_per_1000": metrics["cash_cost_per_1000"],
        "measured_seconds": 1676.315,
        "seconds_per_report": 1676.315 / metrics["model_rows"],
        "recorded_with": "Claude Haiku 5.5 via Claude Code, 2026-10-12",
        "split": "Newest 30% by report submission month plus every report from the smallest reporting entity",
        "smallest_entity": labels["smallest_entity"],
        "fields": metrics["fields"],
    }
    (site_data / "demo.json").write_text(json.dumps({"recorded_with": site_metrics["recorded_with"], "runs": runs}, indent=2, ensure_ascii=False) + "\n")
    (site_data / "metrics.json").write_text(json.dumps(site_metrics, indent=2) + "\n")
    (site_data / "disagreements.json").write_text(
        json.dumps(
            {
                "count_listed": len(disagreements),
                "pair_count": len(disagreement_pairs),
                "disagreement_slots": sum(pair["count"] for pair in disagreement_pairs.values()),
                "note": "These answered mismatches are queued for human review. Intentional not stated abstentions are counted in coverage, not as disagreements. No automated label was treated as a hand check.",
                "top_pairs": top_pairs,
                "items": disagreements,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(f"site_runs={len(runs)}")
    print(f"disagreements_listed={len(disagreements)}")
    print(f"disagreement_pairs={len(disagreement_pairs)}")
    for pair in top_pairs:
        print(f"disagreement_pair={pair['label']} | {pair['filed']} -> {pair['model']} | count={pair['count']}")


if __name__ == "__main__":
    main()
