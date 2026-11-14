"""Frozen observations from the published 4.8.1 wheel; never regenerate in CI."""

import copy
import json

import pytest

from tests.contract_481 import FIXTURE, observe
from tests.rust_contract import DEVIATIONS

CONTRACT = json.loads(FIXTURE.read_text(encoding="utf-8"))
# The default backend is native from 4.10.0, so the reviewed native
# differences are the published 4.10 observations for those cases.
REVIEWED = json.loads(DEVIATIONS.read_text(encoding="utf-8"))


def expected_49(case):
    """Allow only the added backend parameter, revised shim notices and the
    reviewed native differences."""

    deviation = REVIEWED["cases"].get(case["id"])
    expected = (
        copy.deepcopy(deviation["expected"])
        if deviation
        else copy.deepcopy(case["expected"])
    )
    if case["id"] == "public-signatures":
        for target in (
            "datafog:scan",
            "datafog:redact",
            "datafog.engine:scan",
            "datafog.engine:scan_and_redact",
        ):
            expected["value"][target]["parameters"].append(
                {
                    "name": "backend",
                    "kind": "KEYWORD_ONLY",
                    "required": False,
                    "default": None,
                }
            )
    if case.get("target") in {"datafog:detect", "datafog:process"}:
        name = case["target"].split(":")[1]
        replacement = (
            "datafog.scan()"
            if name == "detect"
            else "datafog.scan() or datafog.redact()"
        )
        expected["warnings"] = [
            {
                "type": "FutureWarning",
                "message": (
                    f"datafog.{name}() is deprecated and will be removed in 5.0. "
                    f"Use {replacement} instead. "
                    'Last supported version is 4.10.0. Pin it with: pip install "datafog==4.10.0". '
                    "The earlier promise to retain this shim through 5.x has been revised. "
                    "See docs/retirement.rst."
                ),
            }
        ]
    return expected


@pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["id"])
def test_published_481_contract(case):
    assert observe(case) == expected_49(case), (
        f"4.8.1 contract changed: {case['id']} ({case['classification']}). "
        "Review the migration policy before changing the frozen baseline."
    )
