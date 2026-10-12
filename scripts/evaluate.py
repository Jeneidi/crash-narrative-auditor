from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core import FIELD_NAMES, accuracy, bootstrap_ci, majority_values


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

    majority = majority_values(rows)
    total_slots = len(scored) * len(FIELD_NAMES)
    metrics = {
        "rows": len(rows),
        "model_rows": len(scored),
        "fields": {},
        "evidence_exact_rate": 0.0,
        "abstention_rate": 0.0,
        "coverage": 0.0,
        "non_abstained_accuracy": 0.0,
        "answered_slot_accuracy": {"model": 0.0, "majority": 0.0, "keyword": 0.0},
        "answered_slot_count": 0,
        "answered_slot_total": total_slots,
    }
    model_all_scores = []
    keyword_all_scores = []
    majority_all_scores = []
    answered_scores = {"model": [], "majority": [], "keyword": []}
    evidence_total = evidence_exact = 0
    abstained = total_fields = 0
    non_abstained_correct = non_abstained_total = 0

    for field in FIELD_NAMES:
        model_predictions = [row["model"][field] for row in scored]
        keyword_predictions = [row["baseline"][field] for row in scored]
        gold = [row[field] for row in scored]
        majority_predictions = [majority[field]] * len(scored)
        answered_indexes = [index for index, prediction in enumerate(model_predictions) if prediction != "not stated"]
        answered_gold = [gold[index] for index in answered_indexes]
        model_answered = [model_predictions[index] for index in answered_indexes]
        keyword_answered = [keyword_predictions[index] for index in answered_indexes]
        majority_answered = [majority_predictions[index] for index in answered_indexes]
        model_all_accuracy = accuracy(model_predictions, gold)
        keyword_all_accuracy = accuracy(keyword_predictions, gold)
        majority_all_accuracy = accuracy(majority_predictions, gold)
        answered_accuracies = {
            "model": accuracy(model_answered, answered_gold),
            "majority": accuracy(majority_answered, answered_gold),
            "keyword": accuracy(keyword_answered, answered_gold),
        }
        ci_low, ci_high = bootstrap_ci(model_predictions, gold)
        metrics["fields"][field] = {
            "majority_value": majority[field],
            "answered_slots": len(answered_indexes),
            "coverage": {
                "model": len(answered_indexes) / len(scored) if scored else 0.0,
                "majority": 1.0 if scored else 0.0,
                "keyword": sum(prediction != "not stated" for prediction in keyword_predictions) / len(scored) if scored else 0.0,
            },
            "answered_slot_accuracy": answered_accuracies,
            "all_rows_accuracy": {
                "model": model_all_accuracy,
                "majority": majority_all_accuracy,
                "keyword": keyword_all_accuracy,
            },
            "model_accuracy": model_all_accuracy,
            "baseline_accuracy": keyword_all_accuracy,
            "ci95": [ci_low, ci_high],
        }
        model_all_scores.append(model_all_accuracy)
        keyword_all_scores.append(keyword_all_accuracy)
        majority_all_scores.append(majority_all_accuracy)
        for name, value in answered_accuracies.items():
            answered_scores[name].append((value, len(answered_indexes)))
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

    metrics["macro_accuracy"] = sum(model_all_scores) / len(model_all_scores) if model_all_scores else 0.0
    metrics["keyword_macro_accuracy"] = sum(keyword_all_scores) / len(keyword_all_scores) if keyword_all_scores else 0.0
    metrics["majority_macro_accuracy"] = sum(majority_all_scores) / len(majority_all_scores) if majority_all_scores else 0.0
    metrics["baseline_macro_accuracy"] = metrics["keyword_macro_accuracy"]
    metrics["evidence_exact_rate"] = evidence_exact / evidence_total if evidence_total else 0.0
    metrics["abstention_rate"] = abstained / total_fields if total_fields else 0.0
    metrics["coverage"] = 1 - metrics["abstention_rate"]
    metrics["non_abstained_accuracy"] = non_abstained_correct / non_abstained_total if non_abstained_total else 0.0
    metrics["answered_slot_count"] = non_abstained_total
    for name in metrics["answered_slot_accuracy"]:
        correct = sum(value * count for value, count in answered_scores[name])
        metrics["answered_slot_accuracy"][name] = correct / non_abstained_total if non_abstained_total else 0.0
    metrics["valid_output_rate"] = sum(int(row["model_valid"]) for row in scored) / len(scored) if scored else 0.0
    metrics["cash_cost_per_1000"] = 0.0
    (processed / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"model_rows={len(scored)}")
    print(f"answered_slots={non_abstained_total}/{total_slots}")
    print(f"model_answered_accuracy={metrics['answered_slot_accuracy']['model']:.6f}")
    print(f"majority_answered_accuracy={metrics['answered_slot_accuracy']['majority']:.6f}")
    print(f"keyword_answered_accuracy={metrics['answered_slot_accuracy']['keyword']:.6f}")
    print(f"macro_accuracy={metrics['macro_accuracy']:.6f}")
    print(f"keyword_macro_accuracy={metrics['keyword_macro_accuracy']:.6f}")
    print(f"majority_macro_accuracy={metrics['majority_macro_accuracy']:.6f}")
    print(f"evidence_exact_rate={metrics['evidence_exact_rate']:.6f}")
    print(f"abstention_rate={metrics['abstention_rate']:.6f}")
    print(f"valid_output_rate={metrics['valid_output_rate']:.6f}")
    print("cash_cost_per_1000=$0.00 via subscription CLI")
    for field in FIELD_NAMES:
        item = metrics["fields"][field]
        print(
            f"field={field} coverage={item['coverage']['model']:.6f} "
            f"answered_model={item['answered_slot_accuracy']['model']:.6f} "
            f"answered_majority={item['answered_slot_accuracy']['majority']:.6f} "
            f"answered_keyword={item['answered_slot_accuracy']['keyword']:.6f} "
            f"all_model={item['all_rows_accuracy']['model']:.6f} "
            f"all_majority={item['all_rows_accuracy']['majority']:.6f} "
            f"all_keyword={item['all_rows_accuracy']['keyword']:.6f}"
        )


if __name__ == "__main__":
    main()
