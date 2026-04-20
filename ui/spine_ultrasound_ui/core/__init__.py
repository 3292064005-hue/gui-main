from __future__ import annotations

"""Core package public surface.

This package must stay import-safe in headless/script environments where the
Qt desktop stack is intentionally absent. Heavy GUI objects are therefore
loaded lazily via ``__getattr__`` instead of being imported at module import
time.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - static typing only
    from .app_controller import AppController as AppController

__all__ = ["AppController"]


def __getattr__(name: str) -> Any:
    if name == "AppController":
        from .app_controller import AppController

        return AppController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
