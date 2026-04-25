from __future__ import annotations

from typing import Any, Callable

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.services.scan_plan_contract import runtime_scan_plan_payload


class HeadlessAuthorityQueryService:
    """Resolve authoritative runtime-owned read surfaces for the headless adapter.

    The headless adapter remains permanently read-only. This helper centralizes
    the authoritative envelope and final-verdict query logic so the adapter does
    not mix dispatch orchestration with session/product concerns.
    """

    def __init__(
        self,
        *,
        dispatch_command: Callable[[str, dict[str, Any]], ReplyEnvelope],
        authoritative_contract_service: Any,
        runtime_config_provider: Callable[[], dict[str, Any]],
    ) -> None:
        self._dispatch_command = dispatch_command
        self._authoritative_contract_service = authoritative_contract_service
        self._runtime_config_provider = runtime_config_provider

    def resolve_authoritative_runtime_envelope(self) -> dict[str, Any]:
        desired_config = RuntimeConfig.from_dict(self._runtime_config_provider() or {})
        try:
            reply = self._dispatch_command('get_authoritative_runtime_envelope', {'reason': 'authoritative_query'})
        except (RuntimeError, ValueError, TypeError):
            reply = ReplyEnvelope(ok=False, message='authoritative query failed', data={})
        if not bool(getattr(reply, 'ok', False)):
            return self._authoritative_contract_service.build_unavailable_authoritative_runtime_envelope(
                authority_source='headless_adapter',
                detail=str(getattr(reply, 'message', '') or 'authoritative query failed'),
                desired_runtime_config=desired_config,
                envelope_origin='headless_dispatch_failed',
            )
        envelope_payload = dict(getattr(reply, 'data', {}) or {})
        envelope = self._authoritative_contract_service.normalize_authoritative_runtime_envelope(
            envelope_payload,
            authority_source='headless_adapter',
            desired_runtime_config=desired_config,
            allow_direct_payload=True,
        )
        if envelope:
            return envelope
        return self._authoritative_contract_service.build_unavailable_authoritative_runtime_envelope(
            authority_source='headless_adapter',
            detail='runtime did not publish an authoritative runtime envelope',
            desired_runtime_config=desired_config,
            envelope_origin='headless_dispatch_missing_envelope',
        )

    def resolve_control_authority(self) -> dict[str, Any]:
        return dict(self.resolve_authoritative_runtime_envelope().get('control_authority', {}))

    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict[str, Any]:
        if read_only:
            command = 'query_final_verdict'
            payload: dict[str, Any] = {}
        else:
            active_config = config if config is not None else RuntimeConfig.from_dict(self._runtime_config_provider() or {})
            command = 'validate_scan_plan'
            payload = {
                'scan_plan': runtime_scan_plan_payload(plan),
                'config_snapshot': active_config.to_dict(),
            }
        try:
            reply = self._dispatch_command(command, payload)
        except (RuntimeError, ValueError, TypeError):
            return {}
        if not bool(getattr(reply, 'ok', False)):
            return {}
        verdict = self._authoritative_contract_service.extract_final_verdict(dict(getattr(reply, 'data', {}) or {}))
        if verdict:
            return verdict
        if read_only:
            authoritative_envelope = self.resolve_authoritative_runtime_envelope()
            return self._authoritative_contract_service.extract_final_verdict(authoritative_envelope)
        return self.resolve_final_verdict(read_only=True)

    def query_final_verdict_snapshot(self) -> dict[str, Any]:
        return self.resolve_final_verdict(read_only=True)
