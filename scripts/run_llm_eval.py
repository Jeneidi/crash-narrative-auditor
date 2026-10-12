from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core import FIELD_NAMES, Extraction, validate_extraction


def parse_result(stdout: str) -> tuple[object, dict[str, object]]:
    envelope = json.loads(stdout)
    result = envelope.get("result", envelope)
    if isinstance(result, str):
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        payload = json.loads(result)
    else:
        payload = result
    usage = envelope.get("modelUsage", {})
    return payload, usage


def prompt_for(batch: list[dict[str, object]], labels: dict[str, list[str]]) -> str:
    rows = json.dumps([{"id": row["id"], "narrative": row["narrative"]} for row in batch], ensure_ascii=False)
    allowed = json.dumps(labels, ensure_ascii=False)
    return f"""You extract four fields from NHTSA automated-driving crash narratives. Return only a JSON array, one object per input row, in the same order. No markdown. Each object must have id plus these exact keys: crash_partner, crash_partner_evidence, roadway_type, roadway_type_evidence, other_party_movement, other_party_movement_evidence, injury_severity, injury_severity_evidence. Choose answers only from the supplied enumerations, or exactly not stated when the narrative does not support a choice. Evidence must be a verbatim, case-sensitive substring of that row's narrative. Use an empty string for evidence when the answer is not stated. Do not infer from outside knowledge. The target is the other crash party, not the autonomous vehicle.\n\nAllowed values:\n{allowed}\n\nRows:\n{rows}"""


def main() -> None:
    processed = ROOT / "data/processed"
    cache_dir = ROOT / "data/cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows = json.loads((processed / "eval_rows.json").read_text())
    labels = json.loads((processed / "labels.json").read_text())["allowed"]
    result_path = processed / "model_results.json"
    existing = {item["id"]: item for item in json.loads(result_path.read_text())} if result_path.exists() else {}
    batch_size = 20
    total_seconds = 0.0
    provider_cost = 0.0
    for batch_start in range(0, len(rows), batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        cache = cache_dir / f"batch-{batch_start:04d}.json"
        if cache.exists():
            payload = json.loads(cache.read_text())["payload"]
            usage = json.loads(cache.read_text()).get("usage", {})
        else:
            started = time.perf_counter()
            command = ["claude", "-p", "--model", "claude-haiku-5-5", "--output-format", "json", prompt_for(batch, labels)]
            completed = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
            total_seconds += time.perf_counter() - started
            if completed.returncode != 0:
                raise RuntimeError(f"Claude CLI failed for batch {batch_start}: {completed.stderr[-1000:]}")
            payload, usage = parse_result(completed.stdout)
            cache.write_text(json.dumps({"payload": payload, "usage": usage}, indent=2, ensure_ascii=False) + "\n")
        if not isinstance(payload, list) or len(payload) != len(batch):
            raise ValueError(f"batch {batch_start} returned {type(payload).__name__} with wrong length")
        allowed_sets = {field: set(values) for field, values in labels.items()}
        for row, item in zip(batch, payload):
            if item.get("id") != row["id"]:
                raise ValueError(f"batch {batch_start} returned rows out of order")
            extraction = Extraction.model_validate({key: value for key, value in item.items() if key != "id"})
            validation = validate_extraction(extraction, row["narrative"], allowed_sets)
            existing[row["id"]] = {"id": row["id"], "prediction": extraction.model_dump(), "valid": validation.valid, "errors": list(validation.errors)}
        for model_usage in usage.values() if isinstance(usage, dict) else []:
            if isinstance(model_usage, dict):
                provider_cost += float(model_usage.get("costUSD", 0) or 0)
        result_path.write_text(json.dumps([existing[row["id"]] for row in rows if row["id"] in existing], indent=2, ensure_ascii=False) + "\n")
        print(f"batch_start={batch_start} rows_done={min(batch_start + batch_size, len(rows))} seconds={total_seconds:.3f}")
    print(f"model_rows={len(existing)}")
    print(f"provider_reported_cost_usd={provider_cost:.6f}")
    print(f"measured_seconds={total_seconds:.3f}")


if __name__ == "__main__":
    main()
