"""Dependency-free retirement notices for optional legacy functionality."""

import warnings

#: Final release on which retired optional surfaces still work.
LAST_SUPPORTED = "4.10.0"


class LegacySurfaceWarning(FutureWarning):
    """An optional DataFog surface scheduled for removal in 5.0."""


def warn_legacy_surface(surface: str) -> None:
    """Warn at the caller's public API boundary, before optional imports."""
    warnings.warn(
        f"DataFog {surface} support is deprecated in 4.9 and will be removed in 5.0. "
        f'Last supported version is {LAST_SUPPORTED}. Pin it with: pip install "datafog=={LAST_SUPPORTED}". '
        "See docs/retirement.rst.",
        LegacySurfaceWarning,
        stacklevel=3,
    )
