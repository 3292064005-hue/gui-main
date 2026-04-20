from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from spine_ultrasound_ui.services.api_bridge_backend_helpers import build_command_headers, remember_backend_error
from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception

if TYPE_CHECKING:  # pragma: no cover
    from spine_ultrasound_ui.services.api_bridge_backend import ApiBridgeBackend


class ApiBridgeLeaseService:
    """Proxy runtime-owned control-lease lifecycle for ``ApiBridgeBackend``.

    The backend never becomes the authority owner. This helper keeps HTTP lease
    acquisition/renew/release calls out of the façade while preserving the
    runtime-published control-authority snapshot as the only source of truth.
    """

    def __init__(self, host: 'ApiBridgeBackend') -> None:
        self._host = host

    def ensure_control_lease(self, *, force: bool = False) -> None:
        """Acquire a runtime-owned lease when the backend lacks a cached id."""
        if self._host._lease_id and not force:
            return
        self.acquire_control_lease(force=force)

    def acquire_control_lease(self, *, force: bool = False) -> dict[str, object]:
        """Request a new control lease snapshot from the headless API."""
        if self._host._lease_id and not force:
            return dict(self._host._control_authority_cache)
        payload = {
            "actor_id": self._host._actor_id,
            "role": self._host._role,
            "workspace": self._host._workspace,
            "intent_reason": "desktop_control_plane",
            "source": "api_bridge_backend",
        }
        return self._post_lease_command(
            "/api/v1/control-lease/acquire",
            payload=payload,
            intent="acquire-control-lease",
            error_context="control-lease",
            success_detail="headless API control lease snapshot",
        )

    def renew_control_lease(self, *, ttl_s: int | None = None) -> dict[str, object]:
        """Refresh the currently cached control lease through the API surface."""
        payload = {
            "lease_id": self._host._lease_id,
            "actor_id": self._host._actor_id,
        }
        if ttl_s is not None:
            payload["ttl_s"] = int(ttl_s)
        return self._post_lease_command(
            "/api/v1/control-lease/renew",
            payload=payload,
            intent="renew-control-lease",
            error_context="control-lease-renew",
            success_detail="headless API control lease refresh snapshot",
        )

    def release_control_lease(self, *, reason: str = "") -> dict[str, object]:
        """Release the currently cached control lease through the API surface."""
        payload = {
            "lease_id": self._host._lease_id,
            "actor_id": self._host._actor_id,
            "reason": str(reason),
        }
        authority = self._post_lease_command(
            "/api/v1/control-lease/release",
            payload=payload,
            intent="release-control-lease",
            error_context="control-lease-release",
            success_detail="headless API control lease release snapshot",
        )
        with self._host._lock:
            self._host._lease_id = ""
        return authority

    def _post_lease_command(
        self,
        path: str,
        *,
        payload: dict[str, object],
        intent: str,
        error_context: str,
        success_detail: str,
    ) -> dict[str, object]:
        try:
            response = self._host._client.post(
                path,
                json=payload,
                headers=build_command_headers(
                    intent=intent,
                    actor_id=self._host._actor_id,
                    workspace=self._host._workspace,
                    role=self._host._role,
                    include_lease=False,
                ),
            )
            response.raise_for_status()
            body = response.json() if response.content else {}
            lease = dict(body.get("lease", {}))
            control_authority = dict(body.get("control_authority") or {})
            if not control_authority and lease:
                control_authority = {
                    "summary_state": str(body.get("summary_state") or "ready"),
                    "summary_label": str(body.get("summary_label") or "控制权租约已更新"),
                    "detail": str(body.get("detail") or success_detail),
                    "owner": {
                        "actor_id": str(lease.get("actor_id", "")),
                        "workspace": str(lease.get("workspace", "")),
                        "role": str(lease.get("role", "")),
                        "session_id": str(lease.get("session_id", "")),
                    },
                    "active_lease": lease,
                    "owner_provenance": {"source": "cpp_robot_core"},
                    "workspace_binding": str(lease.get("workspace", "")),
                    "session_binding": str(lease.get("session_id", "")),
                    "blockers": list(body.get("blockers", [])) if isinstance(body.get("blockers"), list) else [],
                    "warnings": list(body.get("warnings", [])) if isinstance(body.get("warnings"), list) else [],
                }
            authoritative = self._host._authoritative_service.build(
                authority_source="api_bridge",
                control_authority=control_authority,
                runtime_config_applied=self._host._runtime_config_cache,
                desired_runtime_config=self._host.config,
                final_verdict=self._host._last_final_verdict,
                detail=success_detail,
            )
            with self._host._lock:
                self._host._control_authority_cache = dict(authoritative.get("control_authority", {}))
                self._host._authoritative_envelope = authoritative
                if lease:
                    self._host._lease_id = str(lease.get("lease_id", "") or self._host._lease_id)
            self._host._projection_cache.update_partition("control_authority", authoritative.get("control_authority", {}))
            self._host._projection_cache.update_partition("authoritative_runtime_envelope", authoritative)
            return dict(authoritative.get("control_authority", {}))
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(exc, context=error_context)
            remember_backend_error(self._host._last_errors, f"{error_context}: {normalized.error_type}: {normalized.message}")
            self._host._log("WARN", f"{error_context}: {normalized.error_type}: {normalized.message}")
            return {}
