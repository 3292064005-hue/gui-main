from __future__ import annotations

import base64
from typing import Any

from PySide6.QtGui import QPixmap


def build_command_headers(
    *,
    intent: str,
    actor_id: str,
    workspace: str,
    role: str,
    session_id: str = "",
    lease_id: str = "",
    include_lease: bool = True,
) -> dict[str, str]:
    """Build canonical HTTP command headers for API bridge requests."""
    headers = {
        "x-spine-role": str(role),
        "x-spine-actor": str(actor_id),
        "x-spine-workspace": str(workspace),
        "x-spine-intent": intent,
    }
    if session_id:
        headers["x-spine-session-id"] = str(session_id)
    if include_lease and lease_id:
        headers["x-spine-lease-id"] = str(lease_id)
    return headers


def decode_pixmap_payload(encoded: str) -> QPixmap | None:
    """Decode a base64 PNG payload into a ``QPixmap`` when possible."""
    try:
        payload = base64.b64decode(encoded)
    except Exception:
        return None
    pixmap = QPixmap()
    if hasattr(pixmap, "loadFromData"):
        ok = pixmap.loadFromData(payload, "PNG")
        return pixmap if ok else None
    return pixmap


def remember_backend_error(error_window, message: str) -> None:
    """Append a normalized error string into the backend error deque."""
    text = str(message).strip()
    if text:
        error_window.append(text)
