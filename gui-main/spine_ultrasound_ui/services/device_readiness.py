from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.xmate_profile import build_control_authority_snapshot, load_xmate_profile
from spine_ultrasound_ui.utils import now_text


def build_device_readiness(*, config: RuntimeConfig, device_roster: dict[str, Any], protocol_version: int, read_only_mode: bool = False) -> dict[str, Any]:
    roster = dict(device_roster)
    profile = load_xmate_profile()

    def _is_ready(name: str) -> bool:
        item = dict(roster.get(name, {}))
        return bool(item.get("online", item.get("connected", False))) and bool(item.get("fresh", True))

    robot_ready = _is_ready("robot")
    camera_ready = _is_ready("camera")
    ultrasound_ready = _is_ready("ultrasound")
    pressure_ready = _is_ready("pressure")
    network_link_ok = bool(getattr(config, "preferred_link", profile.preferred_link) == profile.preferred_link)
    single_control_source_ok = bool(getattr(config, "requires_single_control_source", True)) and not read_only_mode
    rt_control_ready = bool(
        getattr(config, "rt_mode", profile.rt_mode) == profile.rt_mode
        and int(getattr(config, "axis_count", profile.axis_count)) == profile.axis_count
        and int(getattr(config, "rt_network_tolerance_percent", profile.rt_network_tolerance_percent)) == profile.rt_network_tolerance_percent
    )
    config_valid = bool(
        config.tool_name
        and config.tcp_name
        and config.load_kg > 0.0
        and getattr(config, "robot_model", profile.robot_model) == profile.robot_model
        and int(getattr(config, "axis_count", profile.axis_count)) == profile.axis_count
        and getattr(config, "sdk_robot_class", profile.sdk_robot_class) == profile.sdk_robot_class
    )
    return {
        "generated_at": now_text(),
        "robot_ready": robot_ready,
        "camera_ready": camera_ready,
        "ultrasound_ready": ultrasound_ready,
        "force_provider_ready": pressure_ready,
        "storage_ready": True,
        "config_valid": config_valid,
        "protocol_match": protocol_version == 1,
        "software_version": config.software_version,
        "build_id": config.build_id,
        "time_sync_ok": True,
        "network_link_ok": network_link_ok,
        "single_control_source_ok": single_control_source_ok,
        "rt_control_ready": rt_control_ready,
        "control_authority": build_control_authority_snapshot(read_only_mode=read_only_mode),
        "robot_profile": profile.to_dict(),
        "rt_contract": {
            "network_tolerance_percent": int(getattr(config, "rt_network_tolerance_percent", profile.rt_network_tolerance_percent)),
            "fc_frame_type": getattr(config, "fc_frame_type", profile.fc_frame_type),
            "cartesian_impedance": list(getattr(config, "cartesian_impedance", profile.cartesian_impedance)),
        },
        "ready_to_lock": all([
            robot_ready,
            camera_ready,
            ultrasound_ready,
            pressure_ready,
            network_link_ok,
            single_control_source_ok,
            rt_control_ready,
            config_valid,
        ]),
    }
