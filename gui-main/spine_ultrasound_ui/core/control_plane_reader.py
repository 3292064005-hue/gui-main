from __future__ import annotations

from typing import Any, Callable

from spine_ultrasound_ui.core.governance_coordinator import GovernanceCoordinator
from spine_ultrasound_ui.core.ui_projection_service import UiProjectionService
from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan, WorkflowArtifacts


class ControlPlaneReader:
    """Single projection entrypoint for governance refresh and UI payload assembly."""

    def __init__(
        self,
        governance: GovernanceCoordinator,
        ui_projection: UiProjectionService,
        persistence_snapshot_getter: Callable[[], dict[str, Any]],
    ) -> None:
        self.governance = governance
        self.ui_projection = ui_projection
        self._get_persistence_snapshot = persistence_snapshot_getter
        self._snapshots: dict[str, dict[str, Any]] = {
            "sdk_runtime": {},
            "config_report": {},
            "model_report": {},
            "backend_link": {},
            "bridge_observability": {},
            "session_governance": {},
            "deployment_profile": {},
            "control_plane_snapshot": {},
            "sdk_alignment": {},
        }

    @property
    def snapshots(self) -> dict[str, dict[str, Any]]:
        return {key: dict(value) for key, value in self._snapshots.items()}

    def refresh(
        self,
        *,
        backend,
        config: RuntimeConfig,
        telemetry,
        workflow_artifacts: WorkflowArtifacts,
        execution_scan_plan: ScanPlan | None,
        current_session_dir,
        force_sdk_assets: bool = False,
    ) -> dict[str, dict[str, Any]]:
        refreshed = self.governance.refresh(
            backend=backend,
            config=config,
            telemetry=telemetry,
            workflow_artifacts=workflow_artifacts,
            execution_scan_plan=execution_scan_plan,
            current_session_dir=current_session_dir,
            force_sdk_assets=force_sdk_assets,
        )
        self._snapshots.update({key: dict(value) for key, value in refreshed.items()})
        return self.snapshots

    def collect_startup_blockers(self) -> list[dict[str, str]]:
        return self.governance.collect_startup_blockers(
            config_report=self._snapshots.get("config_report", {}),
            model_report=self._snapshots.get("model_report", {}),
            sdk_alignment=self._snapshots.get("sdk_alignment", {}),
            backend_link=self._snapshots.get("backend_link", {}),
            bridge_observability=self._snapshots.get("bridge_observability", {}),
            control_plane_snapshot=self._snapshots.get("control_plane_snapshot", {}),
        )

    def build_status_payload(
        self,
        *,
        telemetry,
        config: RuntimeConfig,
        workflow_artifacts: WorkflowArtifacts,
        current_experiment,
    ) -> dict[str, Any]:
        return self.ui_projection.build_status_payload(
            telemetry=telemetry,
            config=config,
            workflow_artifacts=workflow_artifacts,
            current_experiment=current_experiment,
            persistence=self._get_persistence_snapshot(),
            sdk_runtime=self._snapshots.get("sdk_runtime", {}),
            model_report=self._snapshots.get("model_report", {}),
            config_report=self._snapshots.get("config_report", {}),
            backend_link=self._snapshots.get("backend_link", {}),
            bridge_observability=self._snapshots.get("bridge_observability", {}),
            session_governance=self._snapshots.get("session_governance", {}),
            deployment_profile=self._snapshots.get("deployment_profile", {}),
            control_plane_snapshot=self._snapshots.get("control_plane_snapshot", {}),
        )

    def build_governance_payload(
        self,
        *,
        telemetry,
        config: RuntimeConfig,
        workflow_artifacts: WorkflowArtifacts,
        current_experiment,
    ) -> dict[str, Any]:
        payload = self.build_status_payload(
            telemetry=telemetry,
            config=config,
            workflow_artifacts=workflow_artifacts,
            current_experiment=current_experiment,
        )
        return self.ui_projection.build_governance_payload(status_payload=payload)
