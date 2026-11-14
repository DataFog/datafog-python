"""Native detection API, re-exported from the installed ``datafog-core``.

``datafog`` selects the native engine by default, so most callers never need
this module. Import it to reach the native schema directly: byte and code-point
ranges, transformation records, provider-backed tokenization, structured scans,
the embedded model, and ``capabilities()``.

The names are re-exports, not a second implementation. Importing ``datafog``
alone does not load them.

Experimental: this module may change outside the deprecation policy until 5.0.
"""

from __future__ import annotations

import importlib
import importlib.metadata
from typing import Any

_MODULE = "datafog_core"

__all__ = [
    "EmbeddedCnnDetector",
    "Finding",
    "ModelScanResult",
    "capabilities",
    "contract_version",
    "scan",
    "scan_and_transform",
    "scan_structured",
    "transform",
    "transform_structured",
    "version",
]


def _core() -> Any:
    try:
        return importlib.import_module(_MODULE)
    except ImportError as exc:  # pragma: no cover - base install always has it
        raise ImportError(
            "datafog.native requires datafog-core. Install with: "
            'pip install "datafog==4.10.0"'
        ) from exc


def __getattr__(name: str) -> Any:
    if name in __all__:
        return getattr(_core(), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def version() -> str:
    """Installed Core version, for bug reports and reproducibility locks."""
    return importlib.metadata.version("datafog-core")


def contract_version() -> int:
    """Capability contract the installed Core speaks. Currently 1."""
    return int(_core().capabilities()["contract_version"])
