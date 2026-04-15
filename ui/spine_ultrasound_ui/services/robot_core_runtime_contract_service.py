from __future__ import annotations

"""Direct-core authoritative contract normalization helpers."""

import ssl
from typing import Any, Callable

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService
from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception
from spine_ultrasound_ui.services.core_transport import send_tls_command
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


class RobotCoreRuntimeContractService:
    """Capture and refresh authoritative runtime envelopes for the core backend."""

    def __init__(self, *, authoritative_service: BackendAuthoritativeContractService) -> None:
        self._authoritative_service = authoritative_service

    def capture_reply_contracts(self, reply: ReplyEnvelope, *, desired_runtime_config: RuntimeConfig) -> tuple[dict[str, Any], dict[str, Any]]:
        """Extract authoritative envelope and final verdict from a runtime reply."""
        verdict = self._authoritative_service.extract_final_verdict(reply.data)
        envelope = self._authoritative_service.normalize_authoritative_runtime_envelope(
            reply.data,
            authority_source="cpp_robot_core",
            desired_runtime_config=desired_runtime_config,
            allow_direct_payload=True,
        )
        return envelope, verdict

    def refresh_authoritative_runtime_snapshot(
        self,
        *,
        command_host: str,
        command_port: int,
        ssl_context: ssl.SSLContext,
        desired_runtime_config: RuntimeConfig,
        reason: str,
        remember_recent_command: Callable[[str, ReplyEnvelope], Any],
        log: Callable[[str, str], None],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Request a fresh authoritative envelope from the direct core runtime.

        Returns:
            Tuple of ``(authoritative_envelope, final_verdict)``. Empty
            dictionaries are returned on transport failures.
        """
        try:
            reply = send_tls_command(
                command_host,
                command_port,
                ssl_context,
                "get_authoritative_runtime_envelope",
                {"reason": reason},
            )
        except (OSError, TimeoutError, ConnectionError, ssl.SSLError, ValueError, TypeError, RuntimeError) as exc:
            normalized = normalize_backend_exception(exc, context="authoritative-refresh")
            log("WARN", f"权威快照刷新失败：{normalized.error_type}: {normalized.message}")
            return {}, {}
        remember_recent_command("get_authoritative_runtime_envelope", reply)
        envelope = self._authoritative_service.normalize_authoritative_runtime_envelope(
            reply.data,
            authority_source="cpp_robot_core",
            desired_runtime_config=desired_runtime_config,
            allow_direct_payload=True,
        )
        if not envelope:
            log("WARN", "直接核心运行时未发布 authoritative runtime envelope；返回显式 unavailable surface。")
            return (
                self._authoritative_service.build_unavailable_authoritative_runtime_envelope(
                    authority_source="cpp_robot_core",
                    detail="direct core runtime did not publish an authoritative runtime envelope",
                    desired_runtime_config=desired_runtime_config,
                    envelope_origin="direct_core_missing_envelope",
                ),
                {},
            )
        verdict = self._authoritative_service.extract_final_verdict(envelope)
        return envelope, verdict
