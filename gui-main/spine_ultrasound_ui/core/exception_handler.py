"""
Unified Exception Handler for Spine Ultrasound Platform
Provides centralized error handling, classification, and user feedback.
"""

import logging
import traceback
from enum import Enum
from typing import Callable, Any, Optional
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    NETWORK = "network"
    HARDWARE = "hardware"
    LOGIC = "logic"
    CONFIG = "config"
    USER = "user"
    SYSTEM = "system"


class AppException(Exception):
    """Base exception for application errors"""

    def __init__(self, message: str, category: ErrorCategory, severity: ErrorSeverity,
                 user_message: Optional[str] = None, recovery_action: Optional[str] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.user_message = user_message or message
        self.recovery_action = recovery_action


class ExceptionHandler(QObject):
    error_occurred = Signal(str, str, str)  # message, severity, recovery_action

    def __init__(self):
        super().__init__()
        self.error_counts = {}
        self.max_retries = 3

    def handle_exception(self, exc: Exception, context: str = "") -> None:
        """Central exception handling method"""
        if isinstance(exc, AppException):
            self._handle_app_exception(exc, context)
        else:
            self._handle_unexpected_exception(exc, context)

    def wrap_function(self, func: Callable, context: str = "", retries: int = 0) -> Callable:
        """Decorator to wrap functions with exception handling"""
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.handle_exception(e, f"{context}.{func.__name__}")
                if retries > 0 and self._should_retry(e):
                    for attempt in range(retries):
                        try:
                            logger.info(f"Retrying {func.__name__} (attempt {attempt + 1})")
                            return func(*args, **kwargs)
                        except Exception as retry_exc:
                            self.handle_exception(retry_exc, f"{context}.{func.__name__} (retry {attempt + 1})")
                raise
        return wrapper

    def _handle_app_exception(self, exc: AppException, context: str) -> None:
        """Handle known application exceptions"""
        logger.log(self._severity_to_level(exc.severity),
                   f"{exc.category.value}: {str(exc)} (context: {context})")

        # Track error counts for monitoring
        key = f"{exc.category.value}:{exc.severity.value}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

        # Emit signal for UI feedback
        self.error_occurred.emit(exc.user_message, exc.severity.value, exc.recovery_action or "")

        # Show user dialog for critical errors
        if exc.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            self._show_error_dialog(exc)

    def _handle_unexpected_exception(self, exc: Exception, context: str) -> None:
        """Handle unexpected exceptions"""
        logger.error(f"Unexpected error in {context}: {exc}", exc_info=True)

        app_exc = AppException(
            str(exc),
            ErrorCategory.SYSTEM,
            ErrorSeverity.ERROR,
            f"系统错误: {str(exc)}",
            "请重启应用程序或联系技术支持"
        )
        self._handle_app_exception(app_exc, context)

    def _should_retry(self, exc: Exception) -> bool:
        """Determine if an exception should trigger retry"""
        if isinstance(exc, AppException):
            return exc.category in [ErrorCategory.NETWORK, ErrorCategory.HARDWARE]
        return isinstance(exc, (ConnectionError, TimeoutError, OSError))

    def _severity_to_level(self, severity: ErrorSeverity) -> int:
        """Convert severity to logging level"""
        mapping = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }
        return mapping[severity]

    def _show_error_dialog(self, exc: AppException) -> None:
        """Show error dialog to user"""
        from PySide6.QtWidgets import QApplication
        if QApplication.instance():
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical if exc.severity == ErrorSeverity.CRITICAL else QMessageBox.Warning)
            msg_box.setWindowTitle("错误" if exc.severity == ErrorSeverity.ERROR else "严重错误")
            msg_box.setText(exc.user_message)
            if exc.recovery_action:
                msg_box.setInformativeText(f"建议操作: {exc.recovery_action}")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()

    def get_error_stats(self) -> dict:
        """Get error statistics for monitoring"""
        return self.error_counts.copy()


# Global exception handler instance
global_exception_handler = ExceptionHandler()