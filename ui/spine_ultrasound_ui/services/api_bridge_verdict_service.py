from __future__ import annotations

from typing import TYPE_CHECKING, Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.backend_errors import BackendOperationError
from spine_ultrasound_ui.services.scan_plan_contract import runtime_scan_plan_payload

if TYPE_CHECKING:  # pragma: no cover
    from spine_ultrasound_ui.services.api_bridge_backend import ApiBridgeBackend


class ApiBridgeVerdictService:
    """Resolve final-verdict reads/compiles through a canonical backend entrypoint."""

    def __init__(self, host: 'ApiBridgeBackend') -> None:
        self._host = host

    def _raise_if_reply_failed(self, reply: Any, *, command: str) -> None:
        """Raise a typed runtime error when the command reply is not OK.

        Args:
            reply: Compatibility reply envelope returned by ``send_command``.
            command: Runtime command name used for diagnostics.

        Returns:
            None.

        Raises:
            BackendOperationError: When the runtime rejected the command or the
                transport layer returned an error envelope.

        Boundary behaviour:
            The method preserves reply metadata rather than silently falling back
            to cached verdicts, because cached verdicts are not authoritative for
            the current compile/query attempt.
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

    def resolve_final_verdict(
        self,
        plan: Any = None,
        config: RuntimeConfig | None = None,
        *,
        read_only: bool,
    ) -> dict[str, Any]:
        """Return the authoritative final verdict.

        Args:
            plan: Optional scan plan for compile-time validation.
            config: Optional runtime configuration snapshot.
            read_only: When ``True`` query the read-only final-verdict snapshot;
                otherwise request runtime compilation for the supplied plan.

        Returns:
            Final verdict payload when available, otherwise an empty dictionary.

        Raises:
            BackendOperationError: Raised when the underlying command failed.

        Boundary behaviour:
            Failed read/compile attempts do not fall back to cached verdicts,
            because stale cache data must not be presented as authoritative for
            the current request. Successful replies may still be completed from
            the current authoritative envelope/control-plane cache when the reply
            omits an inline final-verdict payload.
        """
        if read_only:
            reply = self._host.send_command(
                "query_final_verdict",
                {},
                context={"include_lease": False, "intent_reason": "query_final_verdict"},
            )
            self._raise_if_reply_failed(reply, command="query_final_verdict")
            verdict = self._host._authoritative_service.extract_final_verdict(reply.data)
            if verdict:
                return verdict
            authoritative_envelope = self._host.resolve_authoritative_runtime_envelope()
            return self._host._authoritative_service.extract_final_verdict(authoritative_envelope)

        reply = self._host.send_command(
            "validate_scan_plan",
            {
                "scan_plan": runtime_scan_plan_payload(plan),
                "config_snapshot": config.to_dict() if config is not None else self._host.config.to_dict(),
            },
            context={"include_lease": False, "intent_reason": "validate_scan_plan"},
        )
        self._raise_if_reply_failed(reply, command="validate_scan_plan")
        verdict = self._host._authoritative_service.extract_final_verdict(reply.data)
        if verdict:
            return verdict
        return self.resolve_final_verdict(read_only=True)
