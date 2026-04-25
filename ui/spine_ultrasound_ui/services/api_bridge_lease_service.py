from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from spine_ultrasound_ui.services.api_bridge_backend import ApiBridgeBackend


class ApiBridgeLeaseService:
    """Read-only compatibility shim for ``ApiBridgeBackend`` lease methods.

    The headless HTTP API is an evidence/state surface only. Desktop callers may
    still ask the bridge for lease information through historical helper names,
    but those calls must not mutate runtime control ownership. This service
    therefore returns the currently published runtime control-authority snapshot
    and never sends acquire/renew/release traffic over HTTP.
    """

    def __init__(self, host: 'ApiBridgeBackend') -> None:
        self._host = host

    def ensure_control_lease(self, *, force: bool = False) -> None:
        """Keep a compatibility hook without mutating lease state."""
        if force:
            self._host._log("INFO", "API bridge is read-only; forced lease refresh request ignored.")
        else:
            self._host._log("INFO", "API bridge is read-only; control lease acquisition suppressed.")

    def acquire_control_lease(self, *, force: bool = False) -> dict[str, object]:
        """Return the current runtime-published control-authority snapshot."""
        return self._read_only_control_authority(
            "API bridge is read-only; acquire_control_lease is a compatibility shim and returns the current runtime-published control_authority snapshot."
        )

    def renew_control_lease(self, *, ttl_s: int | None = None) -> dict[str, object]:
        """Return the current runtime-published control-authority snapshot."""
        _ = ttl_s
        return self._read_only_control_authority(
            "API bridge is read-only; renew_control_lease is a compatibility shim and returns the current runtime-published control_authority snapshot."
        )

    def release_control_lease(self, *, reason: str = "") -> dict[str, object]:
        """Return the current runtime-published control-authority snapshot."""
        _ = reason
        return self._read_only_control_authority(
            "API bridge is read-only; release_control_lease is a compatibility shim and returns the current runtime-published control_authority snapshot."
        )

    def _read_only_control_authority(self, detail: str) -> dict[str, object]:
        authoritative = self._host.resolve_authoritative_runtime_envelope()
        control_authority = dict(authoritative.get("control_authority", {}))
        if control_authority:
            return control_authority
        unavailable = self._host._authoritative_service.build_unavailable_authoritative_runtime_envelope(
            authority_source="api_bridge",
            detail=detail,
            desired_runtime_config=self._host.config,
            envelope_origin="api_bridge_read_only_lease_shim",
        )
        return dict(unavailable.get("control_authority", {}))
