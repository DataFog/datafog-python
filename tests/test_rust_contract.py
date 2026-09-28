"""Exact native outcomes, with individually reviewed differences from Python."""

import importlib.metadata
import json

import pytest

from tests.contract_481 import FIXTURE
from tests.rust_contract import DEVIATIONS, applicable, native_observation

pytest.importorskip("datafog_core")
CONTRACT = json.loads(FIXTURE.read_text(encoding="utf-8"))
REVIEWED = json.loads(DEVIATIONS.read_text(encoding="utf-8"))
CASES = [case for case in CONTRACT["cases"] if applicable(case)]


def test_native_version_and_review_inventory():
    assert importlib.metadata.version("datafog-core") == REVIEWED["core_version"]
    assert set(REVIEWED["cases"]) <= {case["id"] for case in CASES}
    for item in REVIEWED["cases"].values():
        assert item["classification"] in {"unsupported", "detector-difference"}
        assert item["reason"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_native_contract(case):
    deviation = REVIEWED["cases"].get(case["id"])
    expected = deviation["expected"] if deviation else case["expected"]
    assert native_observation(case) == expected, case["id"]
