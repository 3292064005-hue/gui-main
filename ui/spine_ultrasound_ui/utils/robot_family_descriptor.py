from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.robot_identity_service import RobotIdentityService


def build_robot_family_descriptor(config: RuntimeConfig) -> dict[str, Any]:
    identity = RobotIdentityService().resolve(config.robot_model, config.sdk_robot_class, config.axis_count)
    return {
        "family_key": identity.family_key,
        "family_label": identity.family_label,
        "robot_model": identity.robot_model,
        "sdk_robot_class": identity.sdk_robot_class,
        "axis_count": identity.axis_count,
        "preferred_link": config.preferred_link or identity.preferred_link,
        "clinical_rt_mode": config.rt_mode or identity.rt_mode,
        "requires_single_control_source": bool(config.requires_single_control_source),
        "supports_xmate_model": bool(identity.supports_xmate_model),
        "supports_planner": bool(identity.supports_planner),
        "supports_drag": bool(identity.supports_drag),
        "supports_path_replay": bool(identity.supports_path_replay),
        "supported_nrt_profiles": list(identity.supported_nrt_profiles),
        "supported_rt_phases": list(identity.supported_rt_phases),
    }


def build_profile_snapshot(config: RuntimeConfig) -> dict[str, Any]:
    descriptor = build_robot_family_descriptor(config)
    return {
        "name": f"{descriptor['family_key']}::{descriptor['clinical_rt_mode']}",
        "family_key": descriptor["family_key"],
        "robot_model": descriptor["robot_model"],
        "sdk_robot_class": descriptor["sdk_robot_class"],
        "axis_count": descriptor["axis_count"],
        "preferred_link": descriptor["preferred_link"],
        "clinical_rt_mode": descriptor["clinical_rt_mode"],
    }
