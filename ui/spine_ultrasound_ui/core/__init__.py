from __future__ import annotations

"""Core package compatibility surface with lazy AppController loading."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from .app_controller import AppController

__all__ = ["AppController"]


def __getattr__(name: str) -> Any:
    if name != "AppController":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(".app_controller", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
