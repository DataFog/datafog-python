"""Black-box runner shared by the released-wheel oracle and checkout tests.

Run with ``python -I tests/contract_481.py`` to check an installed package.
This runner deliberately contains no detection or transformation implementation.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import inspect
import json
import os
import warnings
from pathlib import Path
from unittest.mock import patch

FIXTURE = Path(__file__).parent / "contracts" / "4.8.1.json"


def normalize(value):
    if dataclasses.is_dataclass(value):
        return {
            "result_type": type(value).__name__,
            "fields": {
                field.name: normalize(getattr(value, field.name))
                for field in dataclasses.fields(value)
            },
        }
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported contract result: {type(value).__name__}")


def resolve(target):
    module, name = target.rsplit(":", 1)
    return getattr(importlib.import_module(module), name)


def invoke(case):
    kwargs = dict(case.get("kwargs", {}))
    operation = case.get("operation", "call")
    if "entities" in kwargs:
        entity = resolve("datafog.engine:Entity")
        kwargs["entities"] = [entity(**item) for item in kwargs["entities"]]
    if operation == "schema":
        result = {}
        for target in case["targets"]:
            value = resolve(target)
            result[target] = {
                "parameters": [
                    {
                        "name": param.name,
                        "kind": param.kind.name,
                        "required": param.default is inspect.Parameter.empty,
                        "default": (
                            None
                            if param.default is inspect.Parameter.empty
                            else normalize(param.default)
                        ),
                    }
                    for param in inspect.signature(value).parameters.values()
                ],
            }
            if dataclasses.is_dataclass(value):
                result[target]["fields"] = [
                    field.name for field in dataclasses.fields(value)
                ]
        return result
    if operation == "service":
        service = resolve("datafog.services.text_service:TextService")(
            **case.get("constructor", {})
        )
        return getattr(service, case["method"])(**kwargs)
    if operation == "guardrail":
        guardrail = resolve("datafog:create_guardrail")(**case.get("constructor", {}))
        return getattr(guardrail, case["method"])(**kwargs)
    return resolve(case["target"])(**kwargs)


def observe(case):
    # Never send synthetic contract inputs to telemetry, even on opted-in hosts.
    with (
        patch.dict(os.environ, {"DATAFOG_NO_TELEMETRY": "1"}),
        warnings.catch_warnings(record=True) as caught,
    ):
        warnings.simplefilter("always")
        try:
            result = {"value": normalize(invoke(case))}
        except Exception as exc:  # noqa: BLE001 - exception behavior is oracle output
            result = {"error": {"type": type(exc).__name__, "message": str(exc)}}
    result["warnings"] = [
        {"type": item.category.__name__, "message": str(item.message)}
        for item in caught
    ]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    failures = []
    for case in fixture["cases"]:
        actual = observe(case)
        if actual != case["expected"]:
            failures.append(case["id"])
            print(json.dumps({"id": case["id"], "actual": actual}, indent=2))
    print(f"{len(fixture['cases']) - len(failures)}/{len(fixture['cases'])} matched")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
