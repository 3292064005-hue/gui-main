from __future__ import annotations

"""Public service compatibility surface with lazy imports.

This package intentionally avoids importing heavyweight backend implementations
at module import time. Doing so prevents package-level circular imports from
turning into silent ``None`` fallbacks while keeping the historical public names
available to existing callers.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .backend_base import BackendBase

if TYPE_CHECKING:  # pragma: no cover
    from .api_bridge_backend import ApiBridgeBackend
    from .mock_backend import MockBackend
    from .robot_core_client import RobotCoreClientBackend

__all__ = ["BackendBase", "MockBackend", "RobotCoreClientBackend", "ApiBridgeBackend"]

_LAZY_EXPORTS = {
    "ApiBridgeBackend": (".api_bridge_backend", "ApiBridgeBackend"),
    "MockBackend": (".mock_backend", "MockBackend"),
    "RobotCoreClientBackend": (".robot_core_client", "RobotCoreClientBackend"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
