from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.headless_adapter_components import HeadlessAdapterSettings, build_host_services, build_runtime_transport
from spine_ultrasound_ui.services.headless_adapter_products_surface import HeadlessAdapterProductsSurface
from spine_ultrasound_ui.services.headless_adapter_surface import HeadlessAdapterSurface
from spine_ultrasound_ui.services.headless_authority_query_service import HeadlessAuthorityQueryService
from spine_ultrasound_ui.services.headless_command_service import HeadlessCommandService
from spine_ultrasound_ui.services.headless_loop_driver import HeadlessLoopDriver
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope, is_write_command


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
        self.authority_query_service = HeadlessAuthorityQueryService(
            dispatch_command=lambda command, payload: self.command_service._dispatch.dispatch(command, payload),
            authoritative_contract_service=self.control_plane_aggregator.authoritative_contract_service,
            runtime_config_provider=lambda: dict(self.runtime_config_snapshot_data),
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
        return self.authority_query_service.resolve_authoritative_runtime_envelope()
    def resolve_control_authority(self) -> dict[str, Any]:
        """Return the canonical control-authority snapshot for read consumers."""
        return self.authority_query_service.resolve_control_authority()
    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict[str, Any]:
        """Resolve the canonical runtime-owned final verdict surface."""
        return self.authority_query_service.resolve_final_verdict(plan=plan, config=config, read_only=read_only)
    def query_final_verdict_snapshot(self) -> dict[str, Any]:
        """Compatibility wrapper for the read-only final-verdict API."""
        return self.authority_query_service.query_final_verdict_snapshot()
    def recent_commands(self) -> dict[str, Any]:
        return self.command_service.recent_commands()

    def _readonly_rejection(self, operation: str) -> dict[str, Any]:
        """Return a stable failure envelope for headless write attempts.

        Args:
            operation: Command or façade method name that attempted to mutate
                runtime/control state.

        Returns:
            Serialized reply envelope shape used by the rest of the adapter.

        Boundary behavior:
            Headless is a permanent read-only evidence and review surface. It may
            query runtime authority/verdict/session products, but it must not
            initiate robot writes, lease mutations, or runtime-config writes.
        """
        return {
            "ok": False,
            "message": "headless adapter is a read-only evidence surface; use the desktop operator console for write-control transitions",
            "request_id": "",
            "protocol_version": 1,
            "data": {"operation": operation, "read_only_surface": "headless_adapter"},
        }

    def command(self, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if is_write_command(name):
            return self._readonly_rejection(name)
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
        del payload
        return self._readonly_rejection("acquire_control_lease")

    def renew_control_lease(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        del payload
        return self._readonly_rejection("renew_control_lease")

    def release_control_lease(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        del payload
        return self._readonly_rejection("release_control_lease")

    def set_runtime_config(self, config_payload: dict[str, Any]) -> dict[str, Any]:
        del config_payload
        return self._readonly_rejection("set_runtime_config")
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

