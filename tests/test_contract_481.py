"""Frozen observations from the published 4.8.1 wheel; never regenerate in CI."""

import json

import pytest

from tests.contract_481 import FIXTURE, observe

CONTRACT = json.loads(FIXTURE.read_text())


@pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["id"])
def test_published_481_contract(case):
    assert observe(case) == case["expected"], (
        f"4.8.1 contract changed: {case['id']} ({case['classification']}). "
        "Review the migration policy before changing the frozen baseline."
    )
