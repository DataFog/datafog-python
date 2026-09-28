"""Preview of the Core-native API planned for DataFog 5.0.

Names are the actual datafog_core objects: no legacy schema or strategy
translation is applied. Install ``datafog[rust]`` to use this module. Importing
``datafog`` or this namespace alone does not load the native extension.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datafog_core import DataFogConfigurationError as DataFogConfigurationError
    from datafog_core import DataFogFindingError as DataFogFindingError
    from datafog_core import DataFogInternalError as DataFogInternalError
    from datafog_core import DataFogKeyProviderError as DataFogKeyProviderError
    from datafog_core import FieldMapping as FieldMapping
    from datafog_core import Finding as Finding
    from datafog_core import PrivacyManager as PrivacyManager
    from datafog_core import Restoration as Restoration
    from datafog_core import RestoreResult as RestoreResult
    from datafog_core import StructuredFinding as StructuredFinding
    from datafog_core import StructuredRestoration as StructuredRestoration
    from datafog_core import StructuredRestoreResult as StructuredRestoreResult
    from datafog_core import StructuredScanResult as StructuredScanResult
    from datafog_core import StructuredTransformation as StructuredTransformation
    from datafog_core import StructuredTransformResult as StructuredTransformResult
    from datafog_core import TextRange as TextRange
    from datafog_core import Transformation as Transformation
    from datafog_core import TransformResult as TransformResult
    from datafog_core import discover_fields as discover_fields
    from datafog_core import scan as scan
    from datafog_core import scan_and_transform as scan_and_transform
    from datafog_core import (
        scan_and_transform_structured as scan_and_transform_structured,
    )
    from datafog_core import scan_structured as scan_structured
    from datafog_core import transform as transform
    from datafog_core import transform_structured as transform_structured

__all__ = [
    "DataFogConfigurationError",
    "DataFogFindingError",
    "DataFogInternalError",
    "DataFogKeyProviderError",
    "TextRange",
    "Finding",
    "Transformation",
    "TransformResult",
    "Restoration",
    "RestoreResult",
    "FieldMapping",
    "StructuredFinding",
    "StructuredScanResult",
    "StructuredTransformation",
    "StructuredTransformResult",
    "StructuredRestoration",
    "StructuredRestoreResult",
    "PrivacyManager",
    "scan",
    "transform",
    "scan_and_transform",
    "discover_fields",
    "scan_structured",
    "transform_structured",
    "scan_and_transform_structured",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        core = import_module("datafog_core")
    except ImportError as exc:
        raise ImportError(
            'datafog.v5 requires DataFog Core. Install with: pip install "datafog[rust]"'
        ) from exc
    value = getattr(core, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
