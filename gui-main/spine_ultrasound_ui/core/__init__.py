try:
    from .app_controller import AppController
except Exception:  # pragma: no cover - PySide6 may be unavailable during headless tests
    AppController = None

__all__ = ["AppController"]
