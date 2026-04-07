from __future__ import annotations

"""Internal composition root for AppController dependencies."""

from dataclasses import dataclass
from pathlib import Path

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.plan_service import PlanService
from spine_ultrasound_ui.core.postprocess_service import PostprocessService
from spine_ultrasound_ui.core.runtime_persistence_service import RuntimePersistenceService
from spine_ultrasound_ui.core.session_facade import SessionFacade
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.core.telemetry_store import TelemetryStore
from spine_ultrasound_ui.core.ui_projection_service import UiProjectionService
from spine_ultrasound_ui.core.view_state_factory import ViewStateFactory
from spine_ultrasound_ui.services.bridge_observability_service import BridgeObservabilityService
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.config_service import ConfigService
from spine_ultrasound_ui.services.control_plane_snapshot_service import ControlPlaneSnapshotService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.perception import GuidanceReviewService
from spine_ultrasound_ui.services.runtime_verdict_kernel_service import RuntimeVerdictKernelService
from spine_ultrasound_ui.services.sdk_capability_service import SdkCapabilityService
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService
from spine_ultrasound_ui.services.session_governance_service import SessionGovernanceService


@dataclass(frozen=True)
class AppControllerComposition:
    """Materialized dependency bundle for ``AppController``."""

    config_service: ConfigService
    persistence: RuntimePersistenceService
    telemetry: TelemetryStore
    experiment_manager: ExperimentManager
    session_service: SessionService
    plan_service: PlanService
    postprocess_service: PostprocessService
    guidance_review_service: GuidanceReviewService
    sdk_service: SdkCapabilityService
    config_profile_service: ClinicalConfigService
    sdk_runtime_service: SdkRuntimeAssetService
    runtime_verdict_service: RuntimeVerdictKernelService
    session_governance_service: SessionGovernanceService
    bridge_observability_service: BridgeObservabilityService
    deployment_profile_service: DeploymentProfileService
    control_plane_snapshot_service: ControlPlaneSnapshotService
    view_factory: ViewStateFactory
    session_facade: SessionFacade
    ui_projection: UiProjectionService


def build_app_controller_composition(*, exp_root: Path, runtime_config_path: Path, runtime_dir: Path) -> AppControllerComposition:
    """Construct AppController collaborators without exposing build details.

    Args:
        exp_root: Experiment storage root used by runtime/session services.
        runtime_config_path: Canonical runtime configuration JSON path.
        runtime_dir: Runtime working directory containing preferences and cache files.

    Returns:
        Fully materialized dependency bundle consumed by ``AppController``.
    """
    config_service = ConfigService()
    persistence = RuntimePersistenceService(
        config_service=config_service,
        runtime_config_path=runtime_config_path,
        ui_prefs_path=runtime_dir / "ui_preferences.json",
        session_meta_path=runtime_dir / "session_meta.json",
    )
    telemetry = TelemetryStore()
    experiment_manager = ExperimentManager(exp_root)
    session_service = SessionService(experiment_manager)
    plan_service = PlanService()
    postprocess_service = PostprocessService(experiment_manager)
    guidance_review_service = GuidanceReviewService()
    sdk_service = SdkCapabilityService()
    config_profile_service = ClinicalConfigService()
    sdk_runtime_service = SdkRuntimeAssetService()
    runtime_verdict_service = RuntimeVerdictKernelService()
    session_governance_service = SessionGovernanceService()
    bridge_observability_service = BridgeObservabilityService()
    deployment_profile_service = DeploymentProfileService()
    control_plane_snapshot_service = ControlPlaneSnapshotService()
    view_factory = ViewStateFactory(sdk_service=sdk_service)
    session_facade = SessionFacade(session_service, experiment_manager)
    ui_projection = UiProjectionService(view_factory)
    return AppControllerComposition(
        config_service=config_service,
        persistence=persistence,
        telemetry=telemetry,
        experiment_manager=experiment_manager,
        session_service=session_service,
        plan_service=plan_service,
        postprocess_service=postprocess_service,
        guidance_review_service=guidance_review_service,
        sdk_service=sdk_service,
        config_profile_service=config_profile_service,
        sdk_runtime_service=sdk_runtime_service,
        runtime_verdict_service=runtime_verdict_service,
        session_governance_service=session_governance_service,
        bridge_observability_service=bridge_observability_service,
        deployment_profile_service=deployment_profile_service,
        control_plane_snapshot_service=control_plane_snapshot_service,
        view_factory=view_factory,
        session_facade=session_facade,
        ui_projection=ui_projection,
    )
