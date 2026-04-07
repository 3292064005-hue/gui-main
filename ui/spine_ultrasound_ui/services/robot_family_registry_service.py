from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.robot_identity_service import RobotIdentity, RobotIdentityService


@dataclass(frozen=True)
class RobotFamilyDescriptor:
    family_key: str
    family_label: str
    sdk_robot_class: str
    axis_count: int
    collaborative: bool
    clinical_rt_mode: str
    supports_xmate_model: bool
    supports_planner: bool
    supports_drag: bool
    supports_path_replay: bool
    supports_direct_torque: bool
    preferred_link: str
    requires_single_control_source: bool
    allowed_nrt_profiles: tuple[str, ...] = (
        "go_home",
        "approach_prescan",
        "align_to_entry",
        "safe_retreat",
        "recovery_retreat",
        "post_scan_home",
    )
    allowed_rt_phases: tuple[str, ...] = (
        "idle",
        "seek_contact",
        "scan_follow",
        "pause_hold",
        "controlled_retract",
        "fault_latched",
    )
    safe_defaults: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_nrt_profiles"] = list(self.allowed_nrt_profiles)
        payload["allowed_rt_phases"] = list(self.allowed_rt_phases)
        return payload


class RobotFamilyRegistryService:
    def __init__(self, identity_service: RobotIdentityService | None = None) -> None:
        self.identity_service = identity_service or RobotIdentityService()

    def resolve(self, config: RuntimeConfig | None = None, *, robot_model: str | None = None, sdk_robot_class: str | None = None, axis_count: int | None = None) -> RobotFamilyDescriptor:
        if config is not None:
            robot_model = config.robot_model
            sdk_robot_class = config.sdk_robot_class
            axis_count = config.axis_count
        identity = self.identity_service.resolve(robot_model, sdk_robot_class, axis_count)
        return self._from_identity(identity)

    def build_contract(self, config: RuntimeConfig | None = None, **kwargs: Any) -> dict[str, Any]:
        descriptor = self.resolve(config, **kwargs)
        return {
            "summary_state": "ready",
            "summary_label": "xMate3 family frozen",
            "detail": "Family capabilities are fixed to the xMateRobot-only clinical mainline.",
            "descriptor": descriptor.to_dict(),
        }

    def matrix(self) -> list[dict[str, Any]]:
        return [self._from_identity(self.identity_service.resolve()).to_dict()]

    def _from_identity(self, identity: RobotIdentity) -> RobotFamilyDescriptor:
        safe_defaults = {
            "preferred_link": identity.preferred_link,
            "clinical_rt_mode": identity.rt_mode,
            "rt_network_tolerance_recommended": list(identity.rt_network_tolerance_recommended),
            "cartesian_impedance_limits": list(identity.cartesian_impedance_limits),
            "desired_wrench_limits": list(identity.desired_wrench_limits),
        }
        return RobotFamilyDescriptor(
            family_key=identity.family_key,
            family_label=identity.family_label,
            sdk_robot_class=identity.sdk_robot_class,
            axis_count=identity.axis_count,
            collaborative=True,
            clinical_rt_mode=identity.rt_mode,
            supports_xmate_model=identity.supports_xmate_model,
            supports_planner=identity.supports_planner,
            supports_drag=identity.supports_drag,
            supports_path_replay=identity.supports_path_replay,
            supports_direct_torque=("directTorque" in set(identity.supported_rt_modes)),
            preferred_link=identity.preferred_link,
            requires_single_control_source=identity.requires_single_control_source,
            safe_defaults=safe_defaults,
        )
