from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.xmate_profile import build_control_authority_snapshot, load_xmate_profile
from spine_ultrasound_ui.utils import now_text


def build_device_readiness(
    *,
    config: RuntimeConfig,
    device_roster: dict[str, Any],
    protocol_version: int,
    read_only_mode: bool = False,
    calibration_bundle: dict[str, Any] | None = None,
    guidance_algorithm_registry: dict[str, Any] | None = None,
    source_frame_set: dict[str, Any] | None = None,
    localization_readiness: dict[str, Any] | None = None,
    storage_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build the device-level readiness contract used before session lock.

    Args:
        config: Active runtime configuration.
        device_roster: Current device roster or health snapshot.
        protocol_version: UI/core protocol version.
        read_only_mode: Whether the runtime is in read-only observation mode.
        calibration_bundle: Optional calibration bundle bound to guidance.
        guidance_algorithm_registry: Optional guidance pipeline registry.
        source_frame_set: Optional source frame set available before lock.
        localization_readiness: Optional guidance readiness verdict.
        storage_dir: Optional path that must be writable for session artifacts.

    Returns:
        Device-level readiness facts. This payload intentionally stops short of
        localization or guidance freeze eligibility; those are reported by the
        dedicated ``localization_readiness`` artifact.
    """
    roster = dict(device_roster)
    profile = load_xmate_profile()
    calibration_bundle = dict(calibration_bundle or {})
    guidance_algorithm_registry = dict(guidance_algorithm_registry or {})
    source_frame_set = dict(source_frame_set or {})
    localization_readiness = dict(localization_readiness or {})

    def _is_ready(name: str) -> bool:
        item = dict(roster.get(name, {}))
        return bool(item.get("online", item.get("connected", False))) and bool(item.get("fresh", True))

    def _is_storage_ready(target: str | Path | None) -> bool:
        if target is None:
            return True
        path = Path(target)
        parent = path if path.exists() and path.is_dir() else path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            probe = parent / ".write_probe.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except Exception:
            return False

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
    frame_count = int(source_frame_set.get("frame_count", 0) or 0)
    frame_envelopes = list(source_frame_set.get("frame_envelopes", []) or [])
    readiness_device_gate = dict(localization_readiness.get("device_gate", {}))
    readiness_calibration_gate = dict(localization_readiness.get("calibration_gate", {}))
    freeze_gate = dict(localization_readiness.get("freeze_gate", {}))
    source_frame_set_hash = str(source_frame_set.get("source_frame_set_hash", ""))
    localization_inputs_available = bool(
        camera_ready
        and pressure_ready
        and (
            (
                frame_count > 0
                and source_frame_set_hash
                and bool(source_frame_set.get("fresh", False))
                and len(frame_envelopes) == frame_count
                and all(str(item.get("frame_id", "")) for item in frame_envelopes)
            )
            if source_frame_set
            else True
        )
    )
    calibration_bundle_available = bool(
        (
            calibration_bundle.get("release_state") == "approved"
            and calibration_bundle.get("bundle_hash")
            and calibration_bundle.get("camera_intrinsics_hash")
            and calibration_bundle.get("camera_to_base_hash")
            and calibration_bundle.get("probe_tcp_hash")
            and calibration_bundle.get("support_frame_hash")
            and calibration_bundle.get("temporal_sync_hash")
        ) if calibration_bundle else True
    )
    required_guidance_plugins = {"camera_preprocess", "spine_midline_estimation", "registration_build", "registration_validate"}
    guidance_pipeline_available = bool(
        (
            required_guidance_plugins.issubset(set(guidance_algorithm_registry))
            and all(
                str(dict(guidance_algorithm_registry.get(name, {})).get("plugin_id", ""))
                and str(dict(guidance_algorithm_registry.get(name, {})).get("plugin_version", ""))
                for name in required_guidance_plugins
            )
        )
        if guidance_algorithm_registry else True
    )
    measured_jitter_ms = float(calibration_bundle.get("residual_metrics", {}).get("temporal_sync_jitter_ms", 0.0) or 0.0)
    readiness_jitter_ms = float(readiness_calibration_gate.get("temporal_sync_jitter_ms", measured_jitter_ms) or measured_jitter_ms)
    time_sync_ok = bool(
        (
            calibration_bundle.get("temporal_sync_hash")
            and readiness_calibration_gate.get("temporal_sync_valid", True)
            and readiness_jitter_ms <= 10.0
        ) if calibration_bundle else True
    )
    storage_ready = _is_storage_ready(storage_dir)
    localization_gate_consistent = bool(
        not localization_readiness
        or (
            bool(readiness_device_gate.get("camera_online", True)) == camera_ready
            and bool(readiness_device_gate.get("robot_online", True)) == robot_ready
            and bool(readiness_device_gate.get("pressure_online", True)) == pressure_ready
            and bool(readiness_device_gate.get("ultrasound_online", True)) == ultrasound_ready
            and int(readiness_device_gate.get("frame_count", frame_count) or frame_count) == frame_count
            and bool(readiness_device_gate.get("frame_fresh", source_frame_set.get("fresh", False))) == bool(source_frame_set.get("fresh", False))
            and bool(readiness_calibration_gate.get("camera_intrinsics_valid", True)) == bool(calibration_bundle.get("camera_intrinsics_hash"))
            and bool(readiness_calibration_gate.get("camera_to_base_valid", True)) == bool(calibration_bundle.get("camera_to_base_hash"))
            and bool(readiness_calibration_gate.get("probe_tcp_valid", True)) == bool(calibration_bundle.get("probe_tcp_hash"))
        )
    )
    review_required = bool(localization_readiness.get("review_required", False))
    review_approved = bool(dict(localization_readiness.get("review_approval", {})).get("approved", False))
    freeze_gate_consistent = bool(
        not localization_readiness
        or (
            bool(freeze_gate.get("source_frame_set_hash", source_frame_set_hash)) == bool(source_frame_set_hash)
            and bool(freeze_gate.get("freeze_ready", False)) == (str(localization_readiness.get("status", "BLOCKED")) == "READY_FOR_FREEZE")
            and (not review_required or review_approved == bool(freeze_gate.get("review_approved", review_approved)))
        )
    )
    return {
        "generated_at": now_text(),
        "robot_ready": robot_ready,
        "camera_ready": camera_ready,
        "ultrasound_ready": ultrasound_ready,
        "force_provider_ready": pressure_ready,
        "storage_ready": storage_ready,
        "config_valid": config_valid,
        "protocol_match": protocol_version == 1,
        "software_version": config.software_version,
        "build_id": config.build_id,
        "time_sync_ok": time_sync_ok,
        "ready_to_lock": all([
            robot_ready,
            camera_ready,
            pressure_ready,
            storage_ready,
            config_valid,
            protocol_version == 1,
            network_link_ok,
            single_control_source_ok,
            rt_control_ready,
            localization_inputs_available,
            calibration_bundle_available,
            guidance_pipeline_available,
            time_sync_ok,
            localization_gate_consistent,
            freeze_gate_consistent,
            (not review_required or review_approved),
        ]),
        "network_link_ok": network_link_ok,
        "single_control_source_ok": single_control_source_ok,
        "rt_control_ready": rt_control_ready,
        "localization_inputs_available": localization_inputs_available,
        "calibration_bundle_available": calibration_bundle_available,
        "guidance_pipeline_available": guidance_pipeline_available,
        "localization_gate_consistent": localization_gate_consistent,
        "freeze_gate_consistent": freeze_gate_consistent,
        "control_authority": build_control_authority_snapshot(read_only_mode=read_only_mode),
        "robot_profile": profile.to_dict(),
        "rt_contract": {
            "network_tolerance_percent": int(getattr(config, "rt_network_tolerance_percent", profile.rt_network_tolerance_percent)),
            "fc_frame_type": getattr(config, "fc_frame_type", profile.fc_frame_type),
            "cartesian_impedance": list(getattr(config, "cartesian_impedance", profile.cartesian_impedance)),
        },
        "guidance_inputs": {
            "frame_count": frame_count,
            "source_frame_set_hash": str(source_frame_set.get("source_frame_set_hash", "")),
            "provider_mode": str(source_frame_set.get("provider_mode", "")),
            "frame_envelope_count": len(frame_envelopes),
            "review_required": review_required,
            "review_approved": review_approved,
        },
        "calibration_bundle_hash": str(calibration_bundle.get("bundle_hash", "")),
        "guidance_registry_count": len(guidance_algorithm_registry),
    }
