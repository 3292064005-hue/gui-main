from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.headless_adapter_components import HeadlessAdapterSettings, build_host_services, build_runtime_transport
from spine_ultrasound_ui.services.headless_adapter_products_surface import HeadlessAdapterProductsSurface
from spine_ultrasound_ui.services.headless_adapter_surface import HeadlessAdapterSurface
from spine_ultrasound_ui.services.headless_command_service import HeadlessCommandService
from spine_ultrasound_ui.services.headless_loop_driver import HeadlessLoopDriver
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.services.scan_plan_contract import runtime_scan_plan_payload


class HeadlessAdapter(HeadlessAdapterProductsSurface):
    """Stable headless control-plane façade with an explicit, inspectable method surface."""
    def __init__(self, mode: str, command_host: str, command_port: int, telemetry_host: str, telemetry_port: int):
        self.settings = HeadlessAdapterSettings.from_runtime(
            mode=mode,
            command_host=command_host,
            command_port=command_port,
            telemetry_host=telemetry_host,
            telemetry_port=telemetry_port,
        )
        self.mode = self.settings.mode
        self.command_host = self.settings.command_host
        self.command_port = self.settings.command_port
        self.telemetry_host = self.settings.telemetry_host
        self.telemetry_port = self.settings.telemetry_port
        self.runtime, self.ssl_context = build_runtime_transport(self.settings)
        self.read_only_mode = self.settings.read_only_mode
        self._loop_driver = HeadlessLoopDriver()
        self._stop = self._loop_driver.stop_event
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.phase = 0.0

        build_host_services(self)
        self.command_service = HeadlessCommandService(
            mode=self.mode,
            runtime=self.runtime,
            ssl_context=self.ssl_context,
            command_host=self.command_host,
            command_port=self.command_port,
            control_authority=self.control_authority,
            current_session_id=lambda: self._current_session_id,
            prepare_session_tracking=self.session_context.prepare_session_tracking,
            clear_current_session=self.session_context.clear_current_session,
            remember_recent_command=self._remember_recent_command_hook,
            record_command_journal=self.session_context.record_command_journal,
            store_runtime_messages=self._store_messages,
            deployment_profile_snapshot=lambda: self.deployment_profile_service.build_snapshot(RuntimeConfig.from_dict(self.runtime_config_snapshot_data or {})),
            control_plane_snapshot=lambda: dict(self.control_plane_status().get("control_plane_snapshot", {})),
        )
        self.surface = HeadlessAdapterSurface(self)

    @property
    def _current_session_dir(self) -> Path | None:
        return self.session_context.current_session_dir

    @property
    def _current_session_id(self) -> str:
        return self.session_context.current_session_id
    def start(self) -> None:
        target = self.surface.mock_loop if self.mode == 'mock' else self.surface.core_loop
        self._loop_driver.start(target)
        self._thread = getattr(self._loop_driver, '_thread', None)
    def stop(self) -> None:
        self._loop_driver.stop(join_timeout=1.5)
        self._thread = None
        self.event_bus.close()
    def status(self) -> dict[str, Any]:
        return self.runtime_introspection.status()
    def health(self) -> dict[str, Any]:
        return self.runtime_introspection.health()
    def schema(self) -> dict[str, Any]:
        return self.runtime_introspection.schema()
    def topic_catalog(self) -> dict[str, Any]:
        return self.runtime_introspection.topic_catalog()
    def role_catalog(self) -> dict[str, Any]:
        return self.runtime_introspection.role_catalog()
    def command_policy_catalog(self) -> dict[str, Any]:
        return self.runtime_introspection.command_policy_catalog()
    def control_authority_status(self) -> dict[str, Any]:
        return self.runtime_introspection.control_authority_status()
    def resolve_authoritative_runtime_envelope(self) -> dict[str, Any]:
        """Return the canonical runtime-owned authoritative envelope or an explicit unavailable payload."""
        desired_config = RuntimeConfig.from_dict(self.runtime_config_snapshot_data or {})
        try:
            reply = self.command_service._dispatch.dispatch('get_authoritative_runtime_envelope', {'reason': 'authoritative_query'})
        except (RuntimeError, ValueError, TypeError):
            reply = ReplyEnvelope(ok=False, message='authoritative query failed', data={})
        if not bool(getattr(reply, 'ok', False)):
            return self.control_plane_aggregator.authoritative_contract_service.build_unavailable_authoritative_runtime_envelope(
                authority_source='headless_adapter',
                detail=str(getattr(reply, 'message', '') or 'authoritative query failed'),
                desired_runtime_config=desired_config,
                envelope_origin='headless_dispatch_failed',
            )
        envelope_payload = dict(getattr(reply, 'data', {}) or {})
        envelope = self.control_plane_aggregator.authoritative_contract_service.normalize_authoritative_runtime_envelope(
            envelope_payload,
            authority_source='headless_adapter',
            desired_runtime_config=desired_config,
            allow_direct_payload=True,
        )
        if envelope:
            return envelope
        return self.control_plane_aggregator.authoritative_contract_service.build_unavailable_authoritative_runtime_envelope(
            authority_source='headless_adapter',
            detail='runtime did not publish an authoritative runtime envelope',
            desired_runtime_config=desired_config,
            envelope_origin='headless_dispatch_missing_envelope',
        )
    def resolve_control_authority(self) -> dict[str, Any]:
        """Return the canonical control-authority snapshot for read consumers."""
        envelope = self.resolve_authoritative_runtime_envelope()
        return dict(envelope.get('control_authority', {}))
    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict[str, Any]:
        """Resolve the canonical runtime-owned final verdict surface."""
        if read_only:
            command = 'query_final_verdict'
            payload: dict[str, Any] = {}
        else:
            command = 'validate_scan_plan'
            active_config = config if config is not None else RuntimeConfig.from_dict(self.runtime_config_snapshot_data or {})
            payload = {
                'scan_plan': runtime_scan_plan_payload(plan),
                'config_snapshot': active_config.to_dict(),
            }
        try:
            reply = self.command_service._dispatch.dispatch(command, payload)
        except (RuntimeError, ValueError, TypeError):
            return {}
        if not bool(getattr(reply, 'ok', False)):
            return {}
        verdict = self.control_plane_aggregator.authoritative_contract_service.extract_final_verdict(dict(getattr(reply, 'data', {}) or {}))
        if verdict:
            return verdict
        if read_only:
            authoritative_envelope = self.resolve_authoritative_runtime_envelope()
            return self.control_plane_aggregator.authoritative_contract_service.extract_final_verdict(authoritative_envelope)
        return self.resolve_final_verdict(read_only=True)
    def query_final_verdict_snapshot(self) -> dict[str, Any]:
        """Compatibility wrapper for the read-only final-verdict API."""
        return self.resolve_final_verdict(read_only=True)
    def recent_commands(self) -> dict[str, Any]:
        return self.command_service.recent_commands()
    def command(self, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.command_service.command(name, payload)
    def snapshot(self, topics: set[str] | None = None) -> list[dict[str, Any]]:
        return self.surface.snapshot(topics)
    def control_plane_status(self) -> dict[str, Any]:
        return self.surface.control_plane_status()
    def replay_events(
        self,
        *,
        topics: set[str] | None = None,
        session_id: str | None = None,
        since_ts_ns: int | None = None,
        until_ts_ns: int | None = None,
        delivery: str | None = None,
        category: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        return self.surface.replay_events(
            topics=topics,
            session_id=session_id,
            since_ts_ns=since_ts_ns,
            until_ts_ns=until_ts_ns,
            delivery=delivery,
            category=category,
            limit=limit,
            cursor=cursor,
            page_size=page_size,
        )
    def event_bus_stats(self) -> dict[str, Any]:
        return self.event_bus.stats()
    def event_dead_letters(self) -> dict[str, Any]:
        return self.event_bus.dead_letters()
    def event_delivery_audit(self) -> dict[str, Any]:
        return self.event_bus.delivery_audit()
    def subscribe(self, topics: set[str] | None = None, *, include_snapshot: bool = True, categories: set[str] | None = None, deliveries: set[str] | None = None):
        return self.surface.subscribe(topics, include_snapshot=include_snapshot, categories=categories, deliveries=deliveries)
    def unsubscribe(self, subscription) -> None:
        self.surface.unsubscribe(subscription)
    def iter_events(self, topics: set[str] | None = None):
        return self.surface.iter_events(topics)
    def camera_frame(self) -> str:
        return self.surface.camera_frame()
    def ultrasound_frame(self) -> str:
        return self.surface.ultrasound_frame()
    def acquire_control_lease(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = dict(payload or {})
        profile = self.deployment_profile_service.build_snapshot(RuntimeConfig.from_dict(self.runtime_config_snapshot_data or {})).get('name', 'dev')
        return self.control_authority.acquire(
            actor_id=str(data.get('actor_id', '')),
            role=str(data.get('role', 'operator')),
            workspace=str(data.get('workspace', 'desktop')),
            session_id=str(data.get('session_id', self._current_session_id)),
            intent_reason=str(data.get('intent_reason', '')),
            deployment_profile=str(data.get('profile', profile)),
            ttl_s=int(data.get('ttl_s', self.control_authority.lease_ttl_s) or self.control_authority.lease_ttl_s),
            source=str(data.get('source', 'api')),
            preempt=bool(data.get('preempt', False)),
            preempt_reason=str(data.get('preempt_reason', '')),
            requested_claims=data.get('requested_claims') or data.get('claims'),
        )
    def renew_control_lease(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = dict(payload or {})
        return self.control_authority.renew(
            lease_id=str(data.get('lease_id', '')),
            actor_id=str(data.get('actor_id', '')) or None,
            ttl_s=int(data.get('ttl_s', self.control_authority.lease_ttl_s) or self.control_authority.lease_ttl_s),
        )
    def release_control_lease(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = dict(payload or {})
        return self.control_authority.release(
            lease_id=str(data.get('lease_id', '')) or None,
            actor_id=str(data.get('actor_id', '')) or None,
            reason=str(data.get('reason', '')),
        )
    def set_runtime_config(self, config_payload: dict[str, Any]) -> dict[str, Any]:
        self.runtime_config_snapshot_data = dict(config_payload or {})
        if self.runtime is not None:
            self.runtime.update_runtime_config(RuntimeConfig.from_dict(self.runtime_config_snapshot_data))
            self._store_messages(self.runtime.telemetry_snapshot())
        return {'runtime_config': dict(self.runtime_config_snapshot_data), 'backend_mode': self.mode}
    def runtime_config(self) -> dict[str, Any]:
        return {'runtime_config': dict(self.runtime_config_snapshot_data), 'backend_mode': self.mode}
    def _remember_recent_command_hook(self, command: str, payload: dict[str, Any], reply: ReplyEnvelope) -> None:
        return None
    def _store_messages(self, messages) -> None:
        self.surface.store_messages(messages)
    def _resolve_session_dir(self) -> Path | None:
        return self.session_context.resolve_session_dir(self.runtime.session_dir if self.runtime is not None else None)
    def _read_json(self, path: Path) -> dict[str, Any]:
        return self.session_context.read_json(path)
    def _read_json_if_exists(self, path: Path) -> dict[str, Any]:
        return self.session_context.read_json_if_exists(path)
    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        return self.session_context.read_jsonl(path)
    def _read_manifest_if_available(self, session_dir: Path | None = None) -> dict[str, Any]:
        return self.session_context.read_manifest_if_available(session_dir or self._resolve_session_dir())
    def _derive_recovery_state(self, core: dict[str, Any]) -> str:
        return self.session_context.derive_recovery_state(core)

