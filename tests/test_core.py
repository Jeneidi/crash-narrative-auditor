import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core import Extraction, accuracy, bootstrap_ci, keyword_baseline, validate_extraction


LABELS = {
    "crash_partner": {"Passenger Car", "SUV", "not stated"},
    "roadway_type": {"Street", "Intersection", "not stated"},
    "other_party_movement": {"Proceeding Straight", "Making Right Turn", "not stated"},
    "injury_severity": {"Property Damage. No Injured Reported", "Fatality", "not stated"},
}


def test_schema_rejects_extra_keys_and_evidence_is_exact():
    narrative = "A passenger car was parked on the street."
    extraction = Extraction(
        crash_partner="Passenger Car",
        crash_partner_evidence="passenger car",
        roadway_type="Street",
        roadway_type_evidence="street",
        other_party_movement="not stated",
        injury_severity="not stated",
    )
    report = validate_extraction(extraction, narrative, LABELS)
    assert report.valid
    assert Extraction.model_validate_json(extraction.model_dump_json()) == extraction


def test_validator_rejects_non_substring_and_bad_label():
    extraction = Extraction(
        crash_partner="Truck",
        crash_partner_evidence="truck",
        roadway_type="Street",
        other_party_movement="not stated",
        injury_severity="not stated",
    )
    report = validate_extraction(extraction, "A passenger car was parked.", LABELS)
    assert not report.valid
    assert any("outside" in error for error in report.errors)
    assert any("exact narrative" in error for error in report.errors)


def test_keyword_baseline_uses_transparent_aliases():
    extraction = keyword_baseline("An SUV was turning right on the street. No injuries were reported.", LABELS)
    assert extraction.crash_partner == "SUV"
    assert extraction.roadway_type == "Street"
    assert extraction.other_party_movement == "Making Right Turn"
    assert extraction.injury_severity == "not stated"


def test_metric_math_and_ci_are_bounded():
    predictions = ["a", "b", "a", "a"]
    gold = ["a", "x", "a", "y"]
    assert accuracy(predictions, gold) == 0.5
    low, high = bootstrap_ci(predictions, gold, rounds=200)
    assert 0 <= low <= high <= 1
