"""Translate installed Core capabilities into native text scan configuration."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def _locale_key(value: str) -> str:
    return value.strip(" \t\n\r\v\f").translate(_ASCII_LOWER)


def _invalid(detail: str) -> RuntimeError:
    return RuntimeError(f"Incompatible datafog-core capabilities: {detail}")


def _labels(value: Any, field: str) -> set[str]:
    if not isinstance(value, list) or any(
        not isinstance(label, str) or not label for label in value
    ):
        raise _invalid(f"{field} must be a list of entity labels")
    return set(value)


@lru_cache(maxsize=4)
def _read_capabilities(capabilities: Any) -> tuple[set[str], dict, dict]:
    """Snapshot one installed build; replacing its reader invalidates the cache.

    The private snapshot never escapes into native scan configuration. Failed
    capability reads or validation are not cached by lru_cache.
    """
    payload = deepcopy(capabilities())
    if not isinstance(payload, dict):
        raise _invalid("capabilities() must return a dictionary")
    version = payload.get("contract_version")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        raise _invalid(f"unsupported contract_version {version!r}; expected 1")
    supported = _labels(payload.get("supported_entities"), "supported_entities")
    defaults = _labels(payload.get("default_entities"), "default_entities")
    if not defaults <= supported:
        raise _invalid("default_entities contains unsupported labels")
    advertised_locales = payload.get("locales")
    metadata = payload.get("entities")
    if not isinstance(advertised_locales, dict) or not isinstance(metadata, dict):
        raise _invalid("locales and entities must be dictionaries")

    return supported, _locale_lookup(advertised_locales, supported), metadata


def _locale_lookup(advertised_locales: dict, supported: set[str]) -> dict[str, str]:
    locale_lookup: dict[str, str] = {}
    for locale, details in advertised_locales.items():
        if not isinstance(locale, str) or not _locale_key(locale):
            raise _invalid("locale identifiers must be nonempty strings")
        if (
            not isinstance(details, dict)
            or not _labels(
                details.get("enabled_entities"), f"locales[{locale!r}].enabled_entities"
            )
            <= supported
        ):
            raise _invalid(f"invalid locale metadata for {locale!r}")
        locale_lookup[_locale_key(locale)] = locale

    return locale_lookup


def _resolve_locale(value: Any, locale_lookup: dict[str, str]) -> str:
    if not isinstance(value, str) or _locale_key(value) not in locale_lookup:
        raise ValueError(f"Unsupported locale for the Rust backend: {value!r}")
    return value


def _requested_locales(locales: Any, lookup: dict[str, str]) -> set[str]:
    if isinstance(locales, str):
        locales = [locales]
    if locales is not None and (
        not isinstance(locales, (list, tuple))
        or any(not isinstance(locale, str) for locale in locales)
    ):
        raise ValueError("locales must be a list of locale identifiers")
    return {_resolve_locale(locale, lookup) for locale in locales or []}


def _activation_config(label: str, metadata: dict) -> dict:
    details = metadata.get(label)
    if not isinstance(details, dict):
        raise _invalid(f"missing entity metadata for {label!r}")
    scopes = details.get("scopes")
    if not isinstance(scopes, list) or any(
        not isinstance(scope, str) for scope in scopes
    ):
        raise _invalid(f"invalid scopes for {label!r}")
    if "text" not in scopes:
        raise ValueError(
            f"Entity {label!r} is not available for Rust text scanning "
            "(structured-only entity)"
        )
    activation = details.get("activation")
    if not isinstance(activation, dict):
        raise _invalid(f"missing activation metadata for {label!r}")
    kind = activation.get("kind")
    if kind == "default":
        return {}
    if kind not in {"locale", "config"}:
        raise _invalid(f"unsupported activation kind {kind!r} for {label!r}")
    config = activation.get("scan_config")
    if not isinstance(config, dict) or not config:
        raise _invalid(f"missing scan_config for {label!r}")
    if kind == "locale" and "locale" not in config:
        raise _invalid(f"missing activation locale for {label!r}")
    return deepcopy(config)


def scan_configs(core: Any, requested: set[str], locales: Any) -> list[dict]:
    """Build a union of singular-locale scans without duplicating inventories."""
    capabilities = getattr(core, "capabilities", None)
    if not callable(capabilities):
        raise _invalid(
            "contract version 1 is required; install a compatible Core 0.4.x"
        )
    supported, lookup, metadata = _read_capabilities(capabilities)
    selected_locales = _requested_locales(locales, lookup)
    common: dict[str, Any] = {}
    for label in sorted(requested & supported):
        config = _activation_config(label, metadata)
        for key, value in config.items():
            if key == "locale":
                selected_locales.add(_resolve_locale(value, lookup))
            elif key in common and common[key] != value:
                raise _invalid(f"conflicting activation values for {key!r}")
            else:
                common[key] = value
    if not selected_locales:
        return [common]
    return [
        deepcopy(dict(common, locale=locale)) for locale in sorted(selected_locales)
    ]
