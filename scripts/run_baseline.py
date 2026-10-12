from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core import FIELD_NAMES, keyword_baseline, validate_extraction


def main() -> None:
    processed = ROOT / "data/processed"
    rows = json.loads((processed / "eval_rows.json").read_text())
    labels = json.loads((processed / "labels.json").read_text())["allowed"]
    results = []
    for row in rows:
        prediction = keyword_baseline(row["narrative"], {field: set(values) for field, values in labels.items()})
        validation = validate_extraction(prediction, row["narrative"], {field: set(values) for field, values in labels.items()})
        results.append({"id": row["id"], "prediction": prediction.model_dump(), "valid": validation.valid, "errors": list(validation.errors)})
    (processed / "baseline_results.json").write_text(json.dumps(results, indent=2) + "\n")
    for field in FIELD_NAMES:
        correct = sum(item["prediction"][field] == next(row[field] for row in rows if row["id"] == item["id"]) for item in results)
        print(f"baseline_{field}={correct / len(results):.6f}")
    print(f"baseline_rows={len(results)}")


if __name__ == "__main__":
    main()
