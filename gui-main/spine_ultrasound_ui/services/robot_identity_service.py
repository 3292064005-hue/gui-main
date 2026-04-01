from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class OfficialDhParameter:
    joint: int
    a_mm: float
    alpha_rad: float
    d_mm: float
    theta_rad: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RobotIdentity:
    robot_model: str
    label: str
    sdk_robot_class: str
    axis_count: int
    family_key: str = "xmate_6_collaborative"
    family_label: str = "xMate collaborative 6-axis"
    controller_series: str = "xCore"
    controller_version: str = "v2.1+"
    preferred_link: str = "wired_direct"
    rt_mode: str = "cartesianImpedance"
    supported_rt_modes: tuple[str, ...] = (
        "jointPosition",
        "cartesianPosition",
        "jointImpedance",
        "cartesianImpedance",
        "directTorque",
    )
    clinical_allowed_modes: tuple[str, ...] = (
        "MoveAbsJ",
        "MoveJ",
        "MoveL",
        "cartesianImpedance",
    )
    supports_xmate_model: bool = True
    supports_planner: bool = True
    supports_drag: bool = True
    supports_path_replay: bool = True
    requires_single_control_source: bool = True
    supported_nrt_profiles: tuple[str, ...] = ("go_home", "approach_prescan", "align_to_entry", "safe_retreat", "recovery_retreat", "post_scan_home")
    supported_rt_phases: tuple[str, ...] = ("idle", "seek_contact", "contact_stabilize", "scan_follow", "pause_hold", "controlled_retract", "fault_latched")
    cartesian_impedance_limits: tuple[float, ...] = (1500.0, 1500.0, 1500.0, 100.0, 100.0, 100.0)
    desired_wrench_limits: tuple[float, ...] = (60.0, 60.0, 60.0, 30.0, 30.0, 30.0)
    joint_filter_range_hz: tuple[float, float] = (1.0, 1000.0)
    rt_network_tolerance_range: tuple[int, int] = (0, 100)
    rt_network_tolerance_recommended: tuple[int, int] = (10, 20)
    official_dh_parameters: tuple[OfficialDhParameter, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["supported_rt_modes"] = list(self.supported_rt_modes)
        payload["clinical_allowed_modes"] = list(self.clinical_allowed_modes)
        payload["cartesian_impedance_limits"] = list(self.cartesian_impedance_limits)
        payload["desired_wrench_limits"] = list(self.desired_wrench_limits)
        payload["supported_nrt_profiles"] = list(self.supported_nrt_profiles)
        payload["supported_rt_phases"] = list(self.supported_rt_phases)
        payload["official_dh_parameters"] = [item.to_dict() for item in self.official_dh_parameters]
        return payload


_PI_2 = 1.57079632679


IDENTITIES: dict[str, RobotIdentity] = {
    "xmate3": RobotIdentity(
        robot_model="xmate3",
        label="xMate3",
        sdk_robot_class="xMateRobot",
        axis_count=6,
        family_key="xmate_6_collaborative",
        family_label="xMate collaborative 6-axis",
        official_dh_parameters=(
            OfficialDhParameter(1, 0.0, -_PI_2, 341.5),
            OfficialDhParameter(2, 394.0, 0.0, 0.0),
            OfficialDhParameter(3, 0.0, _PI_2, 0.0),
            OfficialDhParameter(4, 0.0, -_PI_2, 366.0),
            OfficialDhParameter(5, 0.0, _PI_2, 0.0),
            OfficialDhParameter(6, 0.0, 0.0, 250.3),
        ),
    ),
    "xmate7": RobotIdentity(
        robot_model="xmate7",
        label="xMate7",
        sdk_robot_class="xMateRobot",
        axis_count=6,
        family_key="xmate_6_collaborative",
        family_label="xMate collaborative 6-axis",
        official_dh_parameters=(
            OfficialDhParameter(1, 0.0, -_PI_2, 404.0),
            OfficialDhParameter(2, 437.5, 0.0, 0.0),
            OfficialDhParameter(3, 0.0, _PI_2, 0.0),
            OfficialDhParameter(4, 0.0, -_PI_2, 412.5),
            OfficialDhParameter(5, 0.0, _PI_2, 0.0),
            OfficialDhParameter(6, 0.0, 0.0, 275.5),
        ),
    ),
    "xmate_er3_pro": RobotIdentity(
        robot_model="xmate_er3_pro",
        label="xMateER3 Pro",
        sdk_robot_class="xMateErProRobot",
        axis_count=7,
        family_key="xmate_7_collaborative",
        family_label="xMate collaborative 7-axis",
        official_dh_parameters=(
            OfficialDhParameter(1, 0.0, -_PI_2, 341.5),
            OfficialDhParameter(2, 0.0, _PI_2, 0.0),
            OfficialDhParameter(3, 0.0, -_PI_2, 394.0),
            OfficialDhParameter(4, 0.0, _PI_2, 0.0),
            OfficialDhParameter(5, 0.0, -_PI_2, 366.0),
            OfficialDhParameter(6, 0.0, _PI_2, 0.0),
            OfficialDhParameter(7, 0.0, 0.0, 250.3),
        ),
    ),
    "xmate_er7_pro": RobotIdentity(
        robot_model="xmate_er7_pro",
        label="xMateER7 Pro",
        sdk_robot_class="xMateErProRobot",
        axis_count=7,
        family_key="xmate_7_collaborative",
        family_label="xMate collaborative 7-axis",
        official_dh_parameters=(
            OfficialDhParameter(1, 0.0, -_PI_2, 404.0),
            OfficialDhParameter(2, 0.0, _PI_2, 0.0),
            OfficialDhParameter(3, 0.0, -_PI_2, 437.5),
            OfficialDhParameter(4, 0.0, _PI_2, 0.0),
            OfficialDhParameter(5, 0.0, -_PI_2, 412.5),
            OfficialDhParameter(6, 0.0, _PI_2, 0.0),
            OfficialDhParameter(7, 0.0, 0.0, 275.5),
        ),
    ),
    "xmate_standard_6": RobotIdentity(
        robot_model="xmate_standard_6",
        label="Standard 6-axis",
        sdk_robot_class="StandardRobot",
        axis_count=6,
        family_key="standard_6_industrial",
        family_label="Standard industrial 6-axis",
        preferred_link="lan_switch",
        rt_mode="cartesianPosition",
        supported_rt_modes=("jointPosition", "cartesianPosition"),
        clinical_allowed_modes=("MoveAbsJ", "MoveJ", "MoveL", "cartesianPosition"),
        supports_xmate_model=False,
        supports_drag=False,
        supports_path_replay=False,
    ),
}


class RobotIdentityService:
    def __init__(self, default_model: str = "xmate3") -> None:
        self.default_model = default_model if default_model in IDENTITIES else "xmate3"

    def resolve(self, robot_model: str | None = None, sdk_robot_class: str | None = None, axis_count: int | None = None) -> RobotIdentity:
        normalized_model = (robot_model or "").strip().lower()
        if normalized_model in IDENTITIES:
            identity = IDENTITIES[normalized_model]
            if self._matches(identity, sdk_robot_class, axis_count):
                return identity
        if sdk_robot_class:
            for identity in IDENTITIES.values():
                if self._matches(identity, sdk_robot_class, axis_count):
                    return identity
        return IDENTITIES[self.default_model]


    def identities(self) -> dict[str, RobotIdentity]:
        return dict(IDENTITIES)

    def build_family_contract(self, robot_model: str | None = None, sdk_robot_class: str | None = None, axis_count: int | None = None) -> dict[str, Any]:
        identity = self.resolve(robot_model, sdk_robot_class, axis_count)
        return {
            "summary_state": "ready",
            "summary_label": "robot family resolved",
            "detail": "Capabilities are resolved from the frozen robot family matrix.",
            "family_key": identity.family_key,
            "family_label": identity.family_label,
            "robot_model": identity.robot_model,
            "sdk_robot_class": identity.sdk_robot_class,
            "axis_count": identity.axis_count,
            "clinical_rt_mode": identity.rt_mode,
            "supported_nrt_profiles": list(identity.supported_nrt_profiles),
            "supported_rt_phases": list(identity.supported_rt_phases),
            "supports_xmate_model": bool(identity.supports_xmate_model),
            "supports_planner": bool(identity.supports_planner),
            "supports_drag": bool(identity.supports_drag),
            "supports_path_replay": bool(identity.supports_path_replay),
            "requires_single_control_source": bool(identity.requires_single_control_source),
            "preferred_link": identity.preferred_link,
        }

    @staticmethod
    def _matches(identity: RobotIdentity, sdk_robot_class: str | None, axis_count: int | None) -> bool:
        if sdk_robot_class and identity.sdk_robot_class != sdk_robot_class:
            return False
        if axis_count and int(identity.axis_count) != int(axis_count):
            return False
        return True
