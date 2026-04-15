from __future__ import annotations

"""Final-verdict resolution for the direct core backend."""

from typing import Any, Callable

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService
from spine_ultrasound_ui.services.backend_errors import BackendOperationError
from spine_ultrasound_ui.services.scan_plan_contract import runtime_scan_plan_payload


class RobotCoreVerdictService:
    """Resolve authoritative final verdicts through the direct core backend."""

    def __init__(
        self,
        *,
        send_command: Callable[..., Any],
        authoritative_service: BackendAuthoritativeContractService,
        current_config: Callable[[], RuntimeConfig],
        read_cached_contracts: Callable[[], tuple[dict[str, Any], dict[str, Any], dict[str, Any]]],
    ) -> None:
        self._send_command = send_command
        self._authoritative_service = authoritative_service
        self._current_config = current_config
        self._read_cached_contracts = read_cached_contracts

    def _raise_if_reply_failed(self, reply: Any, *, command: str) -> None:
        """Raise a typed backend error when the runtime rejected the request.

        Args:
            reply: Compatibility reply envelope returned by ``send_command``.
            command: Runtime command name used for diagnostics.

        Raises:
            BackendOperationError: Raised when the reply envelope is not OK.

        Boundary behaviour:
            This service must not fall back to cached verdicts when the current
            query/compile request failed, because stale cache data is not an
            authoritative answer for the in-flight request.
        """
        if bool(getattr(reply, 'ok', False)):
            return
        data = dict(getattr(reply, 'data', {}) or {})
        raise BackendOperationError(
            str(getattr(reply, 'message', '') or f'{command} failed'),
            error_type=str(data.get('error_type', 'runtime_rejected')),
            http_status=int(data.get('http_status', 409)),
            retryable=bool(data.get('retryable', False)),
            data=data,
        )

    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict[str, Any]:
        """Resolve the authoritative runtime final verdict.

        Args:
            plan: Optional scan plan used for compile-time evaluation.
            config: Optional runtime config override used for compile-time evaluation.
            read_only: When ``True``, query the current runtime snapshot only.

        Returns:
            Final-verdict dictionary.

        Raises:
            BackendOperationError: Raised when the runtime rejects the current
                query/compile request.

        Boundary behaviour:
            Successful replies may still be completed from cached authoritative
            snapshots when the inline verdict is omitted. Failed replies never
            fall back to cached verdicts.
        """
        if read_only:
            reply = self._send_command("query_final_verdict", {})
            self._raise_if_reply_failed(reply, command="query_final_verdict")
            verdict = self._authoritative_service.extract_final_verdict(reply.data)
            if verdict:
                return verdict
            cached_verdict, cached_envelope, _cached_control_plane = self._read_cached_contracts()
            return cached_verdict or self._authoritative_service.extract_final_verdict(cached_envelope)

        active_config = config if config is not None else self._current_config()
        compile_payload = {
            "scan_plan": runtime_scan_plan_payload(plan),
            "config_snapshot": active_config.to_dict(),
        }
        reply = self._send_command("validate_scan_plan", compile_payload)
        self._raise_if_reply_failed(reply, command="validate_scan_plan")
        verdict = self._authoritative_service.extract_final_verdict(reply.data)
        if verdict:
            return verdict
        return self.resolve_final_verdict(read_only=True)
