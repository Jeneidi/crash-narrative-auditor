from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core import FIELD_NAMES, accuracy, bootstrap_ci


def main() -> None:
    processed = ROOT / "data/processed"
    rows = json.loads((processed / "eval_rows.json").read_text())
    baseline = {item["id"]: item for item in json.loads((processed / "baseline_results.json").read_text())}
    model = {item["id"]: item for item in json.loads((processed / "model_results.json").read_text())}
    scored = []
    for row in rows:
        item = model.get(row["id"])
        if item:
            scored.append({**row, "model": item["prediction"], "model_valid": item["valid"], "baseline": baseline[row["id"]]["prediction"]})
    metrics = {"rows": len(rows), "model_rows": len(scored), "fields": {}, "evidence_exact_rate": 0.0, "abstention_rate": 0.0, "non_abstained_accuracy": 0.0}
    model_field_scores = []
    baseline_field_scores = []
    evidence_total = evidence_exact = 0
    abstained = total_fields = 0
    non_abstained_correct = non_abstained_total = 0
    for field in FIELD_NAMES:
        predictions = [row["model"][field] for row in scored]
        gold = [row[field] for row in scored]
        baseline_predictions = [row["baseline"][field] for row in scored]
        model_accuracy = accuracy(predictions, gold)
        baseline_accuracy = accuracy(baseline_predictions, gold)
        ci_low, ci_high = bootstrap_ci(predictions, gold)
        metrics["fields"][field] = {"model_accuracy": model_accuracy, "baseline_accuracy": baseline_accuracy, "ci95": [ci_low, ci_high]}
        model_field_scores.append(model_accuracy)
        baseline_field_scores.append(baseline_accuracy)
        for row in scored:
            prediction = row["model"][field]
            evidence = row["model"].get(f"{field}_evidence", "")
            evidence_total += 1
            evidence_exact += int(not evidence or evidence in row["narrative"])
            total_fields += 1
            abstained += int(prediction == "not stated")
            if prediction != "not stated":
                non_abstained_total += 1
                non_abstained_correct += int(prediction == row[field])
    metrics["macro_accuracy"] = sum(model_field_scores) / len(model_field_scores) if model_field_scores else 0.0
    metrics["baseline_macro_accuracy"] = sum(baseline_field_scores) / len(baseline_field_scores) if baseline_field_scores else 0.0
    metrics["evidence_exact_rate"] = evidence_exact / evidence_total if evidence_total else 0.0
    metrics["abstention_rate"] = abstained / total_fields if total_fields else 0.0
    metrics["non_abstained_accuracy"] = non_abstained_correct / non_abstained_total if non_abstained_total else 0.0
    metrics["valid_output_rate"] = sum(int(row["model_valid"]) for row in scored) / len(scored) if scored else 0.0
    metrics["cash_cost_per_1000"] = 0.0
    (processed / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"model_rows={len(scored)}")
    print(f"macro_accuracy={metrics['macro_accuracy']:.6f}")
    print(f"baseline_macro_accuracy={metrics['baseline_macro_accuracy']:.6f}")
    print(f"evidence_exact_rate={metrics['evidence_exact_rate']:.6f}")
    print(f"abstention_rate={metrics['abstention_rate']:.6f}")
    print(f"non_abstained_accuracy={metrics['non_abstained_accuracy']:.6f}")
    print(f"valid_output_rate={metrics['valid_output_rate']:.6f}")
    print("cash_cost_per_1000=$0.00 via subscription CLI")


if __name__ == "__main__":
    main()
