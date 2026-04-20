from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig

from spine_ultrasound_ui.services.backend_control_plane_service import BackendControlPlaneService
from spine_ultrasound_ui.services.command_state_policy import CommandStatePolicyService
from spine_ultrasound_ui.services.control_authority_service import ControlAuthorityService
from spine_ultrasound_ui.services.runtime_authority_proxy_service import RuntimeAuthorityProxyService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.event_bus import EventBus
from spine_ultrasound_ui.services.headless_control_plane_aggregator import HeadlessControlPlaneAggregator
from spine_ultrasound_ui.services.headless_runtime_introspection import HeadlessRuntimeIntrospection
from spine_ultrasound_ui.services.headless_session_context import HeadlessSessionContext
from spine_ultrasound_ui.services.headless_session_products_reader import HeadlessSessionProductsReader
from spine_ultrasound_ui.services.headless_telemetry_cache import HeadlessTelemetryCache
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime
from spine_ultrasound_ui.services.protobuf_transport import create_client_ssl_context
from spine_ultrasound_ui.services.role_matrix import RoleMatrix
from spine_ultrasound_ui.services.session_dir_watcher import SessionDirWatcher
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService
from spine_ultrasound_ui.services.topic_registry import TopicRegistry
from spine_ultrasound_ui.services.runtime_mode_policy import resolve_runtime_mode


@dataclass(frozen=True)
class HeadlessAdapterSettings:
    mode: str
    command_host: str
    command_port: int
    telemetry_host: str
    telemetry_port: int
    read_only_mode: bool
    strict_control_authority: bool
    implicit_control_lease: bool
    deployment_profile: str
    backend_resolution_source: str
    allowed_backend_modes: tuple[str, ...]

    @classmethod
    def from_runtime(cls, *, mode: str | None, command_host: str, command_port: int, telemetry_host: str, telemetry_port: int) -> "HeadlessAdapterSettings":
        """Resolve headless adapter settings with deployment-profile validation."""
        decision = resolve_runtime_mode(explicit_mode=mode, surface="headless")
        return cls(
            mode=decision.mode,
            command_host=command_host,
            command_port=command_port,
            telemetry_host=telemetry_host,
            telemetry_port=telemetry_port,
            read_only_mode=(os.getenv("SPINE_READ_ONLY_MODE", "0").lower() in {"1", "true", "yes", "on"}) or decision.review_only,
            strict_control_authority=os.getenv("SPINE_STRICT_CONTROL_AUTHORITY", "0").lower() in {"1", "true", "yes", "on"},
            implicit_control_lease=os.getenv("SPINE_IMPLICIT_CONTROL_LEASE", "1").lower() not in {"0", "false", "no", "off"},
            deployment_profile=decision.profile_name,
            backend_resolution_source=decision.resolution_source,
            allowed_backend_modes=decision.allowed_modes,
        )


def build_runtime_transport(settings: HeadlessAdapterSettings) -> tuple[MockCoreRuntime | None, Any | None]:
    runtime = MockCoreRuntime() if settings.mode == "mock" else None
    ssl_context = create_client_ssl_context() if settings.mode == "core" else None
    return runtime, ssl_context


def build_host_services(host: Any) -> None:
    host.telemetry_cache = HeadlessTelemetryCache(host._lock)
    host.latest_by_topic = host.telemetry_cache.latest_by_topic
    host.role_matrix = RoleMatrix()
    host.event_bus = EventBus()
    host.topic_registry = TopicRegistry(host.role_matrix)
    host.command_policy_service = CommandStatePolicyService(host.role_matrix)
    host.session_watcher = SessionDirWatcher()
    host.integrity_service = SessionIntegrityService()
    host.backend_control_plane_service = BackendControlPlaneService()
    host.deployment_profile_service = DeploymentProfileService()
    host.control_plane_aggregator = HeadlessControlPlaneAggregator(
        host.backend_control_plane_service,
        host.deployment_profile_service,
    )
    host.session_intelligence = SessionIntelligenceService()
    host.evidence_seal_service = SessionEvidenceSealService()
    if host.settings.mode == "core":
        host.control_authority = RuntimeAuthorityProxyService(
            dispatch=lambda command, payload: host.command_service._dispatch.dispatch(command, payload),
            deployment_profile_snapshot=lambda: host.deployment_profile_service.build_snapshot(RuntimeConfig.from_dict(host.runtime_config_snapshot_data or {})),
            current_session_id=lambda: host._current_session_id,
            strict_mode=host.settings.strict_control_authority,
            auto_issue_implicit_lease=host.settings.implicit_control_lease,
        )
    else:
        host.control_authority = ControlAuthorityService(
            strict_mode=host.settings.strict_control_authority,
            auto_issue_implicit_lease=host.settings.implicit_control_lease,
        )
    host.runtime_config_snapshot_data = {}
    host.session_context = HeadlessSessionContext()
    host.runtime_introspection = HeadlessRuntimeIntrospection(host)
    host.session_products = HeadlessSessionProductsReader(
        telemetry_cache=host.telemetry_cache,
        resolve_session_dir=host._resolve_session_dir,
        current_session_id=lambda: host._current_session_id,
        manifest_reader=host._read_manifest_if_available,
        json_reader=host._read_json,
        json_if_exists_reader=host._read_json_if_exists,
        jsonl_reader=host._read_jsonl,
        status_reader=host.runtime_introspection.status,
        derive_recovery_state=host._derive_recovery_state,
        command_policy_catalog=host.command_policy_catalog,
        integrity_service=host.integrity_service,
        session_intelligence=host.session_intelligence,
        evidence_seal_service=host.evidence_seal_service,
    )
