from __future__ import annotations


def operator_display_name(value: str | None) -> str | None:
    """Return the privacy-safe operator label used by the public API."""

    if not value:
        return value
    return "wgs-scanner" if value == "wgs-intake-scanner" else value
