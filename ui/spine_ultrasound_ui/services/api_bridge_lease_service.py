from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from spine_ultrasound_ui.services.api_bridge_backend_helpers import build_command_headers, remember_backend_error
from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception

if TYPE_CHECKING:  # pragma: no cover
    from spine_ultrasound_ui.services.api_bridge_backend import ApiBridgeBackend


class ApiBridgeLeaseService:
    """Own API-side control-lease acquisition and refresh.

    The service keeps lease lifecycle logic out of ``ApiBridgeBackend`` so the
    backend can remain a stable façade while lease ownership evolves
    independently.
    """

    def __init__(self, host: 'ApiBridgeBackend') -> None:
        self._host = host

    def ensure_control_lease(self, *, force: bool = False) -> None:
        """Acquire or refresh the API-side control lease.

        Args:
            force: When ``True`` reacquire even if a cached lease id exists.

        Returns:
            None.

        Raises:
            No exceptions are propagated. Failures are normalized into the
            backend error window and log stream.
        """
        if self._host._lease_id and not force:
            return
        try:
            response = self._host._client.post(
                "/api/v1/control-lease/acquire",
                json={
                    "actor_id": self._host._actor_id,
                    "role": self._host._role,
                    "workspace": self._host._workspace,
                    "intent_reason": "desktop_control_plane",
                    "source": "api_bridge_backend",
                },
                headers=build_command_headers(
                    intent="acquire-control-lease",
                    actor_id=self._host._actor_id,
                    workspace=self._host._workspace,
                    role=self._host._role,
                    include_lease=False,
                ),
            )
            response.raise_for_status()
            body = response.json() if response.content else {}
            lease = dict(body.get("lease", {}))
            authoritative = self._host._authoritative_service.build(
                authority_source="api_bridge",
                control_authority=body,
                runtime_config_applied=self._host._runtime_config_cache,
                desired_runtime_config=self._host.config,
                final_verdict=self._host._last_final_verdict,
                detail="headless API control lease snapshot",
            )
            with self._host._lock:
                self._host._control_authority_cache = dict(authoritative.get("control_authority", {}))
                self._host._authoritative_envelope = authoritative
                self._host._lease_id = str(lease.get("lease_id", "") or self._host._lease_id)
            self._host._projection_cache.update_partition("control_authority", authoritative.get("control_authority", {}))
            self._host._projection_cache.update_partition("authoritative_runtime_envelope", authoritative)
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(exc, context="control-lease")
            remember_backend_error(self._host._last_errors, f"control-lease: {normalized.error_type}: {normalized.message}")
            self._host._log("WARN", f"控制权租约获取失败：{normalized.error_type}: {normalized.message}")
