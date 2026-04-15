#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping


REQUIRED_PHASE_SECTIONS = ("seek_contact", "scan_follow", "pause_hold", "controlled_retract")


def _require_number(obj: Mapping[str, Any], key: str, path: str) -> float:
    value = obj.get(key)
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{path}.{key} missing or non-finite numeric field")
    return float(value)


def validate_metrics(runtime_cfg: Mapping[str, Any], evidence: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    phase_contract = evidence.get("rt_phase_contract") or runtime_cfg.get("rt_phase_contract")
    if not isinstance(phase_contract, Mapping):
        return ["runtime config must expose rt_phase_contract"]

    for name in REQUIRED_PHASE_SECTIONS:
        if not isinstance(evidence.get(name), Mapping):
            failures.append(f"rt phase metrics evidence missing section: {name}")
    if failures:
        return failures

    seek_cfg = dict(phase_contract.get("seek_contact", {}))
    scan_cfg = dict(phase_contract.get("scan_follow", {}))
    pause_cfg = dict(phase_contract.get("pause_hold", {}))
    retract_cfg = dict(phase_contract.get("controlled_retract", {}))
    common_cfg = dict(phase_contract.get("common", {}))

    seek = dict(evidence.get("seek_contact", {}))
    scan = dict(evidence.get("scan_follow", {}))
    pause = dict(evidence.get("pause_hold", {}))
    retract = dict(evidence.get("controlled_retract", {}))

    try:
        seek_time_ms = _require_number(seek, "contact_establish_time_ms", "seek_contact")
        seek_overshoot_n = _require_number(seek, "peak_force_overshoot_n", "seek_contact")
        seek_travel_mm = _require_number(seek, "max_seek_travel_mm", "seek_contact")
        retract_timeout_ms = _require_number(retract_cfg, "retract_timeout_ms", "rt_phase_contract.controlled_retract")
        if seek_time_ms > max(100.0, 4.0 * retract_timeout_ms):
            failures.append(f"seek_contact.contact_establish_time_ms too high: {seek_time_ms}")
        if seek_overshoot_n > max(1.0, _require_number(seek_cfg, "contact_force_tolerance_n", "rt_phase_contract.seek_contact") * 2.0):
            failures.append(f"seek_contact.peak_force_overshoot_n too high: {seek_overshoot_n}")
        if seek_travel_mm > _require_number(seek_cfg, "seek_contact_max_travel_mm", "rt_phase_contract.seek_contact"):
            failures.append(f"seek_contact.max_seek_travel_mm exceeds contract: {seek_travel_mm}")

        scan_force_rms = _require_number(scan, "normal_force_rms_error_n", "scan_follow")
        scan_speed_rms = _require_number(scan, "tangent_speed_rms_mm_s", "scan_follow")
        scan_trim_rms = _require_number(scan, "pose_trim_rms_deg", "scan_follow")
        if scan_force_rms > max(0.5, _require_number(scan_cfg, "scan_force_tolerance_n", "rt_phase_contract.scan_follow")):
            failures.append(f"scan_follow.normal_force_rms_error_n too high: {scan_force_rms}")
        if scan_speed_rms > _require_number(scan_cfg, "scan_tangent_speed_max_mm_s", "rt_phase_contract.scan_follow"):
            failures.append(f"scan_follow.tangent_speed_rms_mm_s exceeds max: {scan_speed_rms}")
        if scan_trim_rms > _require_number(common_cfg, "rt_max_pose_trim_deg", "rt_phase_contract.common"):
            failures.append(f"scan_follow.pose_trim_rms_deg exceeds max trim: {scan_trim_rms}")

        pause_drift_30 = _require_number(pause, "drift_mm_30s", "pause_hold")
        pause_drift_60 = _require_number(pause, "drift_mm_60s", "pause_hold")
        pause_guard_mm = _require_number(pause_cfg, "pause_hold_position_guard_mm", "rt_phase_contract.pause_hold")
        if pause_drift_30 > pause_guard_mm:
            failures.append(f"pause_hold.drift_mm_30s exceeds guard: {pause_drift_30}")
        if pause_drift_60 > pause_guard_mm * 1.5:
            failures.append(f"pause_hold.drift_mm_60s exceeds extended guard: {pause_drift_60}")

        retract_release_ms = _require_number(retract, "release_detection_time_ms", "controlled_retract")
        retract_total_ms = _require_number(retract, "total_retract_time_ms", "controlled_retract")
        if retract_release_ms > retract_timeout_ms:
            failures.append(f"controlled_retract.release_detection_time_ms exceeds timeout: {retract_release_ms}")
        if retract_total_ms > retract_timeout_ms * 1.2:
            failures.append(f"controlled_retract.total_retract_time_ms exceeds limit: {retract_total_ms}")
        if bool(retract.get("timeout_faulted", False)):
            failures.append("controlled_retract.timeout_faulted reported true")
    except ValueError as exc:
        failures.append(str(exc))

    return failures


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate exported HIL RT phase metric evidence.")
    parser.add_argument("--runtime-config", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)

    failures = validate_metrics(_load_json(args.runtime_config), _load_json(args.evidence))
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("HIL phase metrics validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
