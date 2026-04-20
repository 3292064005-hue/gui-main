from __future__ import annotations

"""Utility package public surface.

Only light, non-GUI helpers may be imported eagerly. Qt-backed helpers are kept
lazy so headless services and repository scripts can import this package without
requiring PySide6.
"""

from typing import TYPE_CHECKING, Any

from .file_utils import ensure_dir
from .runtime_fingerprint import payload_hash, short_hash
from .time_utils import now_text, now_ns

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .image_utils import generate_demo_pixmap as generate_demo_pixmap

__all__ = ["ensure_dir", "now_text", "now_ns", "generate_demo_pixmap", "payload_hash", "short_hash"]


def __getattr__(name: str) -> Any:
    if name == "generate_demo_pixmap":
        from .image_utils import generate_demo_pixmap

        return generate_demo_pixmap
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
