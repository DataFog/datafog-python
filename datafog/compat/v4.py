"""Legacy scan/redact facade, preserving the 4.x Python result schema.

The result classes retain their original engine identity. This namespace does
not include the deprecated detect/process shims.
"""

from ..engine import Entity, RedactResult, ScanResult
from ..engine import redact as _redact_entities
from ..engine import scan as _scan
from ..engine import scan_and_redact as _scan_and_redact

__all__ = ["Entity", "ScanResult", "RedactResult", "scan", "redact"]

_REDACT_PRESETS = {
    "default": "token",
    "llm": "token",
    "mask": "mask",
    "hash": "hash",
    "replace": "pseudonymize",
    "pseudonymize": "pseudonymize",
}


def scan(
    text: str,
    engine: str = "regex",
    entity_types: list[str] | None = None,
    locales: list[str] | None = None,
    allowlist: list[str] | None = None,
    allowlist_patterns: list[str] | None = None,
    *,
    backend: str = "python",
) -> ScanResult:
    """
    Scan with the legacy result schema; Rust detection is opt-in.

    Defaults to the lightweight regex engine so the core install works without
    optional dependency fallback warnings.

    ``allowlist`` exempts exact entity texts (your own support address, doc
    placeholders); ``allowlist_patterns`` exempts entities whose full text
    matches a regex (e.g. ``^\\d{10}$`` so unix timestamps stop matching as
    phone numbers).
    """
    return _scan(
        text=text,
        engine=engine,
        entity_types=entity_types,
        locales=locales,
        allowlist=allowlist,
        allowlist_patterns=allowlist_patterns,
        backend=backend,
    )


def redact(
    text: str,
    entities: list[Entity] | None = None,
    engine: str = "regex",
    entity_types: list[str] | None = None,
    strategy: str = "token",
    preset: str | None = None,
    locales: list[str] | None = None,
    allowlist: list[str] | None = None,
    allowlist_patterns: list[str] | None = None,
    *,
    backend: str = "python",
) -> RedactResult:
    """
    Redact with legacy strategies and result schema.

    If entities are provided, redact those spans. Otherwise, scan text first
    using the selected engine and redact the detected entities. ``allowlist``
    and ``allowlist_patterns`` exempt findings from redaction (exact text and
    full-text regex match respectively); they apply to the scan path and are
    rejected when explicit ``entities`` are supplied.
    """
    if backend not in ("python", "rust"):
        raise ValueError("backend must be one of: python, rust")

    if preset is not None:
        try:
            strategy = _REDACT_PRESETS[preset]
        except KeyError as exc:
            allowed = ", ".join(sorted(_REDACT_PRESETS))
            raise ValueError(f"preset must be one of: {allowed}") from exc

    if entities is not None:
        if allowlist or allowlist_patterns:
            raise ValueError(
                "allowlist/allowlist_patterns cannot be combined with explicit "
                "entities; filter the entities before calling redact"
            )
        return _redact_entities(text=text, entities=entities, strategy=strategy)

    return _scan_and_redact(
        text=text,
        engine=engine,
        entity_types=entity_types,
        strategy=strategy,
        locales=locales,
        allowlist=allowlist,
        allowlist_patterns=allowlist_patterns,
        backend=backend,
    )
