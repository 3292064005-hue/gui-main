from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .file_utils import ensure_dir
from .runtime_fingerprint import payload_hash, short_hash
from .time_utils import now_text, now_ns

if TYPE_CHECKING:  # pragma: no cover
    from .image_utils import generate_demo_pixmap

__all__ = ["ensure_dir", "now_text", "now_ns", "generate_demo_pixmap", "payload_hash", "short_hash"]


def __getattr__(name: str) -> Any:
    if name != "generate_demo_pixmap":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(".image_utils", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
