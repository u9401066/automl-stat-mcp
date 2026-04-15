"""Shared helpers for safe local path resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


class UnsafePathError(ValueError):
    """Raised when a requested local path escapes the allowed roots."""


def _normalize_roots(allowed_roots: Iterable[str | Path]) -> list[Path]:
    roots = [Path(root).resolve(strict=False) for root in allowed_roots]
    if not roots:
        raise UnsafePathError("No allowed roots configured")
    return roots


def resolve_safe_path(
    path: str,
    *,
    base_root: str | Path | None = None,
    allowed_roots: Iterable[str | Path] | None = None,
) -> Path:
    """Resolve a path and ensure it stays within allowed roots."""
    if not path or not path.strip():
        raise UnsafePathError("Path is empty")

    base = Path(base_root).resolve(strict=False) if base_root is not None else None
    candidate = Path(path.strip())

    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
    else:
        if base is None:
            raise UnsafePathError("Relative paths require a base root")
        resolved = (base / candidate).resolve(strict=False)

    roots = _normalize_roots(allowed_roots or ([base] if base is not None else []))
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue

    allowed_display = ", ".join(str(root) for root in roots)
    raise UnsafePathError(f"Path '{path}' resolves outside allowed roots: {allowed_display}")
