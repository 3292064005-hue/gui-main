from __future__ import annotations

import json
import socket
import ssl
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class BackendOperationError(Exception):
    """Typed backend/runtime failure with stable compatibility metadata."""

    message: str
    error_type: str = "backend_error"
    http_status: int = 502
    retryable: bool = False
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)


class InvalidPayloadError(BackendOperationError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_type="invalid_payload", http_status=400, retryable=False, data=dict(kwargs))


class LeaseConflictError(BackendOperationError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_type="lease_conflict", http_status=409, retryable=False, data=dict(kwargs))


class ProfilePolicyError(BackendOperationError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_type="profile_policy", http_status=403, retryable=False, data=dict(kwargs))


class SchemaMismatchError(BackendOperationError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_type="schema_mismatch", http_status=422, retryable=False, data=dict(kwargs))


class RuntimeRejectedError(BackendOperationError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_type="runtime_rejected", http_status=409, retryable=False, data=dict(kwargs))


class TransportError(BackendOperationError):
    def __init__(self, message: str, *, http_status: int = 503, **kwargs: Any) -> None:
        super().__init__(message, error_type="transport_error", http_status=http_status, retryable=True, data=dict(kwargs))


class TransportTimeoutError(TransportError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, http_status=504, **kwargs)
        self.error_type = "transport_timeout"


class DependencyFailureError(BackendOperationError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_type="dependency_failure", http_status=503, retryable=True, data=dict(kwargs))


class ConfigurationError(BackendOperationError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_type="configuration_error", http_status=500, retryable=False, data=dict(kwargs))


class ResourceCleanupError(BackendOperationError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_type="resource_cleanup", http_status=500, retryable=False, data=dict(kwargs))


def _message(exc: BaseException) -> str:
    return str(exc).strip() or exc.__class__.__name__


def normalize_backend_exception(exc: Exception, *, command: str = "", context: str = "") -> BackendOperationError:
    """Normalize transport/runtime failures into a stable typed error surface."""
    if isinstance(exc, BackendOperationError):
        return exc

    text = _message(exc)
    lower = text.lower()
    extra: dict[str, Any] = {}
    if command:
        extra["command"] = command
    if context:
        extra["context"] = context

    if isinstance(exc, httpx.HTTPStatusError):
        status_code = int(exc.response.status_code)
        extra["http_status"] = status_code
        if status_code == 409 or "lease" in lower or "control" in lower:
            return LeaseConflictError(text, **extra)
        if status_code in {401, 403}:
            return ProfilePolicyError(text, **extra)
        if status_code in {400, 422}:
            return InvalidPayloadError(text, **extra)
        if status_code >= 500:
            return DependencyFailureError(text, **extra)
        return RuntimeRejectedError(text, **extra)

    if isinstance(exc, (httpx.TimeoutException, socket.timeout, TimeoutError)):
        return TransportTimeoutError(text, **extra)

    if isinstance(exc, (httpx.ConnectError, httpx.NetworkError, httpx.ProtocolError, ssl.SSLError, ConnectionError, OSError)):
        return TransportError(text, **extra)

    if isinstance(exc, json.JSONDecodeError):
        return SchemaMismatchError(text, **extra)

    if isinstance(exc, TypeError):
        return InvalidPayloadError(text, **extra)

    if isinstance(exc, ValueError):
        if "protocol" in lower or "schema" in lower or "payload" in lower or "json" in lower or "frame" in lower:
            return SchemaMismatchError(text, **extra)
        return InvalidPayloadError(text, **extra)

    if isinstance(exc, RuntimeError):
        if "transport" in lower or "network" in lower or "socket" in lower or "timeout" in lower or "tls" in lower:
            return TransportError(text, **extra)
        if "lease" in lower or "control权" in text or "控制权" in text or "conflict" in lower:
            return LeaseConflictError(text, **extra)
        if "policy" in lower or "forbidden" in lower or "profile" in lower or "authority" in lower:
            return ProfilePolicyError(text, **extra)
        if "cleanup" in lower or "close" in lower or context == "shutdown":
            return ResourceCleanupError(text, **extra)
        if "schema" in lower or "protocol" in lower:
            return SchemaMismatchError(text, **extra)
        return RuntimeRejectedError(text, **extra)

    if context == "shutdown":
        return ResourceCleanupError(text, **extra)
    return DependencyFailureError(text, **extra)
