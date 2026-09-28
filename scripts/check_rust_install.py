"""Smoke-test installed 4.9 bridge wheels with python -I, outside checkout imports."""

import importlib.metadata
import sys


def main():
    assert sys.flags.isolated, "Run with python -I"

    import datafog_core

    import datafog
    from datafog import v5
    from datafog.compat import v4

    assert importlib.metadata.version("datafog-core").startswith("0.4.")
    assert datafog_core.capabilities()["contract_version"] == 1
    assert v4.Entity is datafog.Entity
    assert v5.Finding is datafog_core.Finding
    text = "👋 Contact alice@example.com"
    legacy = datafog.scan(text, backend="rust")
    assert isinstance(legacy, datafog.ScanResult)
    assert legacy.entities[0].text == "alice@example.com"
    assert (
        text[legacy.entities[0].start : legacy.entities[0].end] == "alice@example.com"
    )
    assert datafog.redact(text, backend="rust").redacted_text == "👋 Contact [EMAIL_1]"
    native = v5.scan(text)
    assert isinstance(native[0], datafog_core.Finding)
    assert (
        v5.scan_and_transform(
            text, {"transform": {"default": {"strategy": "redact"}}}
        ).text
        == "👋 Contact [EMAIL]"
    )
    print(
        "Installed wheel: compatibility facade, Rust backend and native preview passed"
    )


if __name__ == "__main__":
    main()
