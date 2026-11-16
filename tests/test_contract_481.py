"""Frozen observations from the published 4.8.1 wheel; never regenerate in CI."""

import json

import pytest

from tests.contract_481 import FIXTURE, observe
from tests.rust_contract import WRAPPER_DEVIATIONS, expected_observation

CONTRACT = json.loads(FIXTURE.read_text(encoding="utf-8"))
REVIEWED_WRAPPER = json.loads(WRAPPER_DEVIATIONS.read_text(encoding="utf-8"))


def expected_49(case):
    """The immutable oracle plus individually explained native/wrapper fixes."""
    return expected_observation(case)


def test_reviewed_wrapper_deviations_are_explicit_and_in_scope():
    cases = {case["id"]: case for case in CONTRACT["cases"]}
    assert set(REVIEWED_WRAPPER["cases"]) <= set(cases)
    for case_id, deviation in REVIEWED_WRAPPER["cases"].items():
        assert deviation["reason"]
        assert deviation["classification"] in {
            "behavioral-fix",
            "validation-difference",
            "diagnostic-difference",
            "signature-addition",
        }
        assert deviation["expected"] != cases[case_id]["expected"]


@pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["id"])
def test_published_481_contract(case):
    assert observe(case) == expected_49(case), (
        f"4.8.1 contract changed: {case['id']} ({case['classification']}). "
        "Review the migration policy before changing the frozen baseline."
    )
