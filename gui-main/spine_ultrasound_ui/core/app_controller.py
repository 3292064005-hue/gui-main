from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.core.alarm_manager import AlarmManager
from spine_ultrasound_ui.core.app_controller_composition import build_app_controller_composition
from spine_ultrasound_ui.core.app_controller_config_mixin import AppControllerConfigMixin
from spine_ultrasound_ui.core.app_controller_runtime_mixin import AppControllerRuntimeMixin
from spine_ultrasound_ui.core.app_runtime_bridge import AppRuntimeBridge
from spine_ultrasound_ui.core.command_orchestrator import CommandOrchestrator
from spine_ultrasound_ui.core.control_plane_reader import ControlPlaneReader
from spine_ultrasound_ui.core.governance_coordinator import GovernanceCoordinator
from spine_ultrasound_ui.models import ExperimentRecord, ScanPlan, WorkflowArtifacts
from spine_ultrasound_ui.services.backend_base import BackendBase
from spine_ultrasound_ui.utils import ensure_dir


class AppController(AppControllerConfigMixin, AppControllerRuntimeMixin, QObject):
    """Desktop application façade with a stable external API.

    Internally the controller now acts primarily as a composition root and UI
    façade while delegating orchestration, persistence, governance refresh, and
    session artifact handling to dedicated collaborators.
    """

    status_updated = Signal(dict)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)
    experiments_updated = Signal(list)
    system_state_changed = Signal(str)
    alarm_raised = Signal(str)

    def __init__(self, root_dir: Path, backend: BackendBase):
        """Construct the controller and wire the internal composition.

        Args:
            root_dir: Workspace root directory.
            backend: Runtime backend implementation.

        Raises:
            OSError: If workspace/runtime directories cannot be created.
        """
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.exp_root = ensure_dir(self.root_dir / "experiments")
        self.runtime_dir = ensure_dir(self.root_dir / "runtime")
        self.backend = backend
        self.runtime_config_path = self.runtime_dir / "runtime_config.json"

        composition = build_app_controller_composition(
            exp_root=self.exp_root,
            runtime_config_path=self.runtime_config_path,
            runtime_dir=self.runtime_dir,
        )
        self.config_service = composition.config_service
        self.persistence = composition.persistence
        self.config = self.persistence.load_initial_config()
        self.telemetry = composition.telemetry
        self.telemetry.metrics.pressure_target = self.config.pressure_target
        self.workflow_artifacts = WorkflowArtifacts()
        self.exp_manager = composition.experiment_manager
        self.session_service = composition.session_service
        self.plan_service = composition.plan_service
        self.postprocess_service = composition.postprocess_service
        self.sdk_service = composition.sdk_service
        self.config_profile_service = composition.config_profile_service
        self.sdk_runtime_service = composition.sdk_runtime_service
        self.runtime_verdict_service = composition.runtime_verdict_service
        self.session_governance_service = composition.session_governance_service
        self.bridge_observability_service = composition.bridge_observability_service
        self.deployment_profile_service = composition.deployment_profile_service
        self.control_plane_snapshot_service = composition.control_plane_snapshot_service
        self.execution_scan_plan: Optional[ScanPlan] = None
        self.view_factory = composition.view_factory
        self.command_orchestrator = CommandOrchestrator(self.backend, self.session_service)
        self.governance = GovernanceCoordinator(
            sdk_service=self.sdk_service,
            config_service=self.config_profile_service,
            runtime_service=self.sdk_runtime_service,
            runtime_verdict_service=self.runtime_verdict_service,
            session_governance_service=self.session_governance_service,
            bridge_observability_service=self.bridge_observability_service,
            deployment_profile_service=self.deployment_profile_service,
            control_plane_snapshot_service=self.control_plane_snapshot_service,
        )
        self.session_facade = composition.session_facade
        self.ui_projection = composition.ui_projection
        self.control_plane_reader = ControlPlaneReader(self.governance, self.ui_projection, self.get_persistence_snapshot)
        self.runtime_bridge = AppRuntimeBridge(self)
        snapshots = self.control_plane_reader.refresh(
            backend=self.backend,
            config=self.config,
            telemetry=self.telemetry,
            workflow_artifacts=self.workflow_artifacts,
            execution_scan_plan=self.execution_scan_plan,
            current_session_dir=self.session_service.current_session_dir,
            force_sdk_assets=True,
        )
        self.sdk_runtime_snapshot = dict(snapshots["sdk_runtime"])
        self.model_report = dict(snapshots["model_report"])
        self.config_report = dict(snapshots["config_report"])
        self.session_governance_snapshot = dict(snapshots["session_governance"])
        self.backend_link_snapshot = dict(snapshots["backend_link"])
        self.bridge_observability_snapshot = dict(snapshots["bridge_observability"])
        self.deployment_profile_snapshot = dict(snapshots["deployment_profile"])
        self.control_plane_snapshot = dict(snapshots["control_plane_snapshot"])
        self.alarm_manager = AlarmManager()
        self.experiments: list[ExperimentRecord] = []
        self.localization_result = None
        self.preview_scan_plan: Optional[ScanPlan] = None
        self._connect_backend()
        self._connect_exception_handler()
