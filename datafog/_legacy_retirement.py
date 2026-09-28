"""Dependency-free retirement notices for optional legacy functionality."""

import warnings


class LegacySurfaceWarning(FutureWarning):
    """An optional DataFog surface scheduled for removal in 5.0."""


def warn_legacy_surface(surface: str) -> None:
    """Warn at the caller's public API boundary, before optional imports."""
    warnings.warn(
        f"DataFog {surface} support is deprecated in 4.9 and will be removed in 5.0. "
        "Remain on the final 4.x release if you need continued support.",
        LegacySurfaceWarning,
        stacklevel=3,
    )
