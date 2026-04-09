"""Repository-owned MONAI Label skeleton for offline annotation workflows.

This package is intentionally import-safe without MONAI Label installed. It
provides repository-local configuration, manifest generation, and lightweight
server-task facades used by tests and offline dataset tooling.
"""

from .app import SpineUltrasoundMonaiLabelSkeleton
from .config import MonaiLabelAppConfig
from .server_app import SpineUltrasoundMonaiLabelServerApp

__all__ = [
    "MonaiLabelAppConfig",
    "SpineUltrasoundMonaiLabelSkeleton",
    "SpineUltrasoundMonaiLabelServerApp",
]
