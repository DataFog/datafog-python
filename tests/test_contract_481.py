"""Frozen observations from the published 4.8.1 wheel; never regenerate in CI."""

import copy
import json

import pytest

from tests.contract_481 import FIXTURE, observe

CONTRACT = json.loads(FIXTURE.read_text(encoding="utf-8"))


def expected_49(case):
    """Allow only the four added backend parameters and revised shim notices."""
    expected = copy.deepcopy(case["expected"])
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
                    "default": "python",
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
                    "The earlier promise to retain this shim through 5.x has been revised."
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
