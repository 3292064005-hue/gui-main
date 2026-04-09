from __future__ import annotations

from typing import Any, Mapping

from spine_ultrasound_ui.core.telemetry_store import TelemetryStore
from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan, WorkflowArtifacts
from spine_ultrasound_ui.services.bridge_observability_service import BridgeObservabilityService
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.control_plane_snapshot_service import ControlPlaneSnapshotService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.runtime_verdict_kernel_service import RuntimeVerdictKernelService
from spine_ultrasound_ui.services.sdk_capability_service import SdkCapabilityService
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService
from spine_ultrasound_ui.services.session_governance_service import SessionGovernanceService


class GovernanceCoordinator:
    """Coordinate desktop governance snapshots without forcing every caller down the same heavy path.

    The desktop has three materially different refresh classes:
    1. full governance recompute after configuration or command-side changes;
    2. backend/link projection refresh;
    3. telemetry-only bridge observability refresh.

    This coordinator exposes explicit methods for those cases so the UI does not
    accidentally trigger scan-plan compilation or repeated session-artifact reads
    while merely repainting high-frequency status.
    """

    def __init__(
        self,
        *,
        sdk_service: SdkCapabilityService,
        config_service: ClinicalConfigService,
        runtime_service: SdkRuntimeAssetService,
        runtime_verdict_service: RuntimeVerdictKernelService,
        session_governance_service: SessionGovernanceService,
        bridge_observability_service: BridgeObservabilityService,
        deployment_profile_service: DeploymentProfileService,
        control_plane_snapshot_service: ControlPlaneSnapshotService,
    ) -> None:
        self.sdk_service = sdk_service
        self.config_service = config_service
        self.runtime_service = runtime_service
        self.runtime_verdict_service = runtime_verdict_service
        self.session_governance_service = session_governance_service
        self.bridge_observability_service = bridge_observability_service
        self.deployment_profile_service = deployment_profile_service
        self.control_plane_snapshot_service = control_plane_snapshot_service

    def refresh(
        self,
        *,
        backend,
        config: RuntimeConfig,
        telemetry: TelemetryStore,
        workflow_artifacts: WorkflowArtifacts,
        execution_scan_plan: ScanPlan | None,
        current_session_dir,
        force_sdk_assets: bool = False,
    ) -> dict[str, Any]:
        """Compatibility full-refresh entrypoint used by the desktop composition root."""
        return self.refresh_full(
            backend=backend,
            config=config,
            telemetry=telemetry,
            workflow_artifacts=workflow_artifacts,
            execution_scan_plan=execution_scan_plan,
            current_session_dir=current_session_dir,
            force_sdk_assets=force_sdk_assets,
        )

    def refresh_full(
        self,
        *,
        backend,
        config: RuntimeConfig,
        telemetry: TelemetryStore,
        workflow_artifacts: WorkflowArtifacts,
        execution_scan_plan: ScanPlan | None,
        current_session_dir,
        force_sdk_assets: bool = False,
    ) -> dict[str, Any]:
        """Perform the authoritative, command-side governance recompute.

        This path is appropriate after runtime configuration changes, command
        execution, explicit operator refresh requests, or workflow transitions
        that materially change the execution plan or backend state.
        """
        sdk_runtime = self.runtime_service.refresh(backend, config) if force_sdk_assets else self.runtime_service.snapshot.to_dict()
        config_report = self.config_service.build_report(config)
        model_report = self.runtime_verdict_service.resolve(
            backend,
            execution_scan_plan,
            config,
            refresh_runtime_verdict=True,
        )
        backend_link = self._refresh_backend_link(backend)
        bridge_observability = self.bridge_observability_service.build(telemetry, backend_link, workflow_artifacts)
        session_governance = self.session_governance_service.build(current_session_dir)
        sdk_alignment = self.sdk_service.build(config, telemetry.robot)
        deployment_profile = self.deployment_profile_service.build_snapshot(config)
        sdk_runtime = self._with_runtime_doctor(
            sdk_runtime=sdk_runtime,
            config=config,
            backend_link=backend_link,
            model_report=model_report,
            session_governance=session_governance,
        )
        control_plane_snapshot = self._build_control_plane_snapshot(
            backend_link=backend_link,
            bridge_observability=bridge_observability,
            config_report=config_report,
            sdk_alignment=sdk_alignment,
            model_report=model_report,
            deployment_profile=deployment_profile,
            session_governance=session_governance,
            runtime_doctor=dict(sdk_runtime.get("mainline_runtime_doctor", {})),
        )
        return {
            "sdk_runtime": sdk_runtime,
            "config_report": config_report,
            "model_report": model_report,
            "backend_link": backend_link,
            "bridge_observability": bridge_observability,
            "session_governance": session_governance,
            "sdk_alignment": sdk_alignment,
            "deployment_profile": deployment_profile,
            "control_plane_snapshot": control_plane_snapshot,
        }

    def refresh_bridge_projection(
        self,
        *,
        telemetry: TelemetryStore,
        workflow_artifacts: WorkflowArtifacts,
        snapshots: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Refresh only the telemetry-facing bridge observability projection.

        No runtime verdict compilation, session artifact reads, or SDK asset
        queries are performed here. This method is safe to use from high-frequency
        telemetry paths and status repaint loops.
        """
        backend_link = self._snapshot_dict(snapshots, "backend_link")
        bridge_observability = self.bridge_observability_service.build(telemetry, backend_link, workflow_artifacts)
        control_plane_snapshot = self._build_control_plane_snapshot_from_snapshots(
            snapshots,
            backend_link=backend_link,
            bridge_observability=bridge_observability,
        )
        return {
            "bridge_observability": bridge_observability,
            "control_plane_snapshot": control_plane_snapshot,
        }

    def refresh_backend_projection(
        self,
        *,
        backend,
        telemetry: TelemetryStore,
        workflow_artifacts: WorkflowArtifacts,
        snapshots: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Refresh backend-link and bridge-observability projections without recomputing model/session products."""
        backend_link = self._refresh_backend_link(backend)
        bridge_observability = self.bridge_observability_service.build(telemetry, backend_link, workflow_artifacts)
        control_plane_snapshot = self._build_control_plane_snapshot_from_snapshots(
            snapshots,
            backend_link=backend_link,
            bridge_observability=bridge_observability,
        )
        return {
            "backend_link": backend_link,
            "bridge_observability": bridge_observability,
            "control_plane_snapshot": control_plane_snapshot,
        }

    def refresh_session_governance_projection(
        self,
        *,
        current_session_dir,
        snapshots: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Refresh only session-governance-derived projections.

        The underlying ``SessionGovernanceService`` performs filesystem signature
        caching, so repeated explicit refreshes remain bounded even when an
        operator polls the same locked session.
        """
        session_governance = self.session_governance_service.build(current_session_dir)
        control_plane_snapshot = self._build_control_plane_snapshot_from_snapshots(
            snapshots,
            session_governance=session_governance,
        )
        return {
            "session_governance": session_governance,
            "control_plane_snapshot": control_plane_snapshot,
        }

    def _refresh_backend_link(self, backend: Any) -> dict[str, Any]:
        return backend.link_snapshot() if hasattr(backend, "link_snapshot") else {}

    def _with_runtime_doctor(
        self,
        *,
        sdk_runtime: dict[str, Any],
        config: RuntimeConfig,
        backend_link: dict[str, Any],
        model_report: dict[str, Any],
        session_governance: dict[str, Any],
    ) -> dict[str, Any]:
        runtime_doctor = dict(sdk_runtime.get("mainline_runtime_doctor", {}))
        if not runtime_doctor:
            return sdk_runtime
        inspected = self.runtime_service.mainline_doctor.inspect(
            config=config,
            sdk_runtime=sdk_runtime,
            backend_link=backend_link,
            model_report=model_report,
            session_governance=session_governance,
        )
        return {**sdk_runtime, "mainline_runtime_doctor": dict(inspected)}

    def _build_control_plane_snapshot_from_snapshots(
        self,
        snapshots: Mapping[str, Mapping[str, Any]],
        *,
        backend_link: dict[str, Any] | None = None,
        bridge_observability: dict[str, Any] | None = None,
        session_governance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sdk_runtime = self._snapshot_dict(snapshots, "sdk_runtime")
        return self._build_control_plane_snapshot(
            backend_link=backend_link if backend_link is not None else self._snapshot_dict(snapshots, "backend_link"),
            bridge_observability=bridge_observability if bridge_observability is not None else self._snapshot_dict(snapshots, "bridge_observability"),
            config_report=self._snapshot_dict(snapshots, "config_report"),
            sdk_alignment=self._snapshot_dict(snapshots, "sdk_alignment"),
            model_report=self._snapshot_dict(snapshots, "model_report"),
            deployment_profile=self._snapshot_dict(snapshots, "deployment_profile"),
            session_governance=session_governance if session_governance is not None else self._snapshot_dict(snapshots, "session_governance"),
            runtime_doctor=dict(sdk_runtime.get("mainline_runtime_doctor", {})),
        )

    def _build_control_plane_snapshot(
        self,
        *,
        backend_link: dict[str, Any],
        bridge_observability: dict[str, Any],
        config_report: dict[str, Any],
        sdk_alignment: dict[str, Any],
        model_report: dict[str, Any],
        deployment_profile: dict[str, Any],
        session_governance: dict[str, Any],
        runtime_doctor: dict[str, Any],
    ) -> dict[str, Any]:
        return self.control_plane_snapshot_service.build(
            backend_link=backend_link,
            control_authority=backend_link.get("control_plane", {}).get("control_authority", {}),
            bridge_observability=bridge_observability,
            config_report=config_report,
            sdk_alignment=sdk_alignment,
            model_report=model_report,
            deployment_profile=deployment_profile,
            session_governance=session_governance,
            evidence_seal=session_governance.get("evidence_seal", {}),
            release_mode=deployment_profile.get("name", "dev"),
            runtime_doctor=runtime_doctor,
        )

    @staticmethod
    def _snapshot_dict(snapshots: Mapping[str, Mapping[str, Any]], key: str) -> dict[str, Any]:
        return dict(snapshots.get(key, {}))

    @staticmethod
    def collect_startup_blockers(
        *,
        config_report: dict[str, Any],
        model_report: dict[str, Any],
        sdk_alignment: dict[str, Any],
        backend_link: dict[str, Any],
        bridge_observability: dict[str, Any],
        control_plane_snapshot: dict[str, Any],
    ) -> list[dict[str, str]]:
        blockers: list[dict[str, str]] = []
        backend_mode = str(backend_link.get("mode", ""))
        deployment_profile = dict(control_plane_snapshot.get("deployment_profile", {}))
        profile_name = str(deployment_profile.get("name", "dev") or "dev")
        allow_mock_startup_suppression = backend_mode == "mock" and profile_name in {"dev", "review"}
        for item in control_plane_snapshot.get("blockers", []) or []:
            payload = dict(item)
            payload.setdefault("section", "control_plane")
            section = str(payload.get("section", ""))
            name = str(payload.get("name", ""))
            if allow_mock_startup_suppression and section in {"environment", "runtime_doctor"}:
                if section != "runtime_doctor" or name in {"sdk_environment_blocked", "运行主线治理阻塞"}:
                    continue
            blockers.append(payload)
        return blockers
