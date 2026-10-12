from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, ValidationError


FIELD_NAMES = (
    "crash_partner",
    "roadway_type",
    "other_party_movement",
    "injury_severity",
)
FIELD_COLUMNS = {
    "crash_partner": "Crash With",
    "roadway_type": "Roadway Type",
    "other_party_movement": "CP Pre-Crash Movement",
    "injury_severity": "Highest Injury Severity Alleged",
}


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    crash_partner: str = Field(min_length=1)
    crash_partner_evidence: str = ""
    roadway_type: str = Field(min_length=1)
    roadway_type_evidence: str = ""
    other_party_movement: str = Field(min_length=1)
    other_party_movement_evidence: str = ""
    injury_severity: str = Field(min_length=1)
    injury_severity_evidence: str = ""


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    errors: tuple[str, ...]


def clean_value(value: object) -> str:
    text = "" if value is None else str(value).strip()
    return text if text else "not stated"


def stable_id(row: dict[str, object]) -> str:
    source = "|".join(str(row.get(key, "")) for key in ("Report ID", "Report Version", "Narrative"))
    return sha256(source.encode("utf-8")).hexdigest()[:12]


def validate_extraction(extraction: Extraction, narrative: str, allowed: dict[str, set[str]]) -> ValidationReport:
    errors: list[str] = []
    for field in FIELD_NAMES:
        value = getattr(extraction, field)
        evidence = getattr(extraction, f"{field}_evidence")
        if value not in allowed[field] and value != "not stated":
            errors.append(f"{field}: answer is outside the enumerated set")
        if evidence and evidence not in narrative:
            errors.append(f"{field}: evidence is not an exact narrative substring")
        if value == "not stated" and evidence:
            errors.append(f"{field}: not stated must have empty evidence")
    return ValidationReport(not errors, tuple(errors))


def _contains(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def keyword_baseline(narrative: str, allowed: dict[str, set[str]]) -> Extraction:
    """Small transparent baseline: exact labels plus a few narrative synonyms."""
    text = narrative.lower()

    def choose(field: str, aliases: dict[str, tuple[str, ...]]) -> str:
        hits = []
        for label in allowed[field]:
            terms = (label.lower(),) + aliases.get(label, ())
            if any(_contains(text, term) for term in terms):
                hits.append(label)
        return sorted(hits, key=lambda value: (-len(value), value))[0] if hits else "not stated"

    crash_aliases = {
        "Passenger Car": ("passenger vehicle", "sedan"),
        "Heavy Truck": ("semi truck", "tractor-trailer", "tractor trailer"),
        "Other Fixed Object": ("fixed object", "barrier"),
        "Non-Motorist: Pedestrian": ("pedestrian",),
        "Non-Motorist: Cyclist": ("cyclist", "bicycle", "bike"),
    }
    roadway_aliases = {"Highway / Freeway": ("highway", "freeway"), "Parking Lot": ("parking lot", "parking area")}
    movement_aliases = {
        "Proceeding Straight": ("proceeding straight", "traveling straight", "travelling straight"),
        "Making Right Turn": ("turning right", "right turn"),
        "Making Left Turn": ("turning left", "left turn"),
        "Backing": ("backing", "reversing"),
        "Parked": ("parked",),
        "Stopped": ("stopped", "stationary"),
    }
    injury_aliases = {
        "Fatality": ("fatal", "died", "death"),
        "Serious W/ Hospitalization": ("serious injury",),
        "Moderate W/ Hospitalization": ("hospitalized",),
        "Minor W/O Hospitalization": ("minor injury",),
        "No Injured Reported": ("no injuries", "no injury"),
        "Property Damage. No Injured Reported": ("property damage",),
    }
    values = {
        field: choose(field, aliases)
        for field, aliases in (
            ("crash_partner", crash_aliases),
            ("roadway_type", roadway_aliases),
            ("other_party_movement", movement_aliases),
            ("injury_severity", injury_aliases),
        )
    }
    return Extraction(
        **values,
        **{f"{field}_evidence": "" for field in FIELD_NAMES},
    )


def accuracy(predictions: Iterable[str], gold: Iterable[str]) -> float:
    pairs = list(zip(predictions, gold))
    return sum(pred == actual for pred, actual in pairs) / len(pairs) if pairs else 0.0


def bootstrap_ci(predictions: list[str], gold: list[str], seed: int = 42, rounds: int = 1000) -> tuple[float, float]:
    import random

    if not predictions:
        return 0.0, 0.0
    rng = random.Random(seed)
    scores = []
    indexes = range(len(predictions))
    for _ in range(rounds):
        sample = [rng.choice(tuple(indexes)) for _ in indexes]
        scores.append(sum(predictions[i] == gold[i] for i in sample) / len(sample))
    scores.sort()
    return scores[int(0.025 * rounds)], scores[int(0.975 * rounds) - 1]


def macro_field_accuracy(rows: list[dict[str, object]], prediction_key: str) -> dict[str, float]:
    results = {}
    for field in FIELD_NAMES:
        results[field] = accuracy((str(row[prediction_key][field]) for row in rows), (str(row[field]) for row in rows))
    return results


def allowed_values(rows: Iterable[dict[str, object]]) -> dict[str, set[str]]:
    return {
        field: {clean_value(row.get(FIELD_COLUMNS[field], "")) for row in rows}
        for field in FIELD_NAMES
    }


def validate_json_object(payload: object) -> Extraction:
    try:
        return Extraction.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
