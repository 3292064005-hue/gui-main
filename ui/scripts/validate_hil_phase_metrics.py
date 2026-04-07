#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f'{path} must contain a top-level JSON object')
    return data


def _require_number(obj: dict[str, Any], key: str) -> float:
    value = obj.get(key)
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f'missing or non-finite numeric field: {key}')
    return float(value)


def validate_metrics(runtime_cfg: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    phase_contract = evidence.get('rt_phase_contract') or runtime_cfg.get('rt_phase_contract')
    if not isinstance(phase_contract, dict):
        raise ValueError('runtime config must expose rt_phase_contract')

    seek_cfg = phase_contract.get('seek_contact', {})
    scan_cfg = phase_contract.get('scan_follow', {})
    retract_cfg = phase_contract.get('controlled_retract', {})

    seek = evidence.get('seek_contact', {})
    scan = evidence.get('scan_follow', {})
    pause = evidence.get('pause_hold', {})
    retract = evidence.get('controlled_retract', {})
    if not all(isinstance(section, dict) for section in (seek, scan, pause, retract)):
        raise ValueError('evidence file must contain seek_contact/scan_follow/pause_hold/controlled_retract objects')

    seek_time_ms = _require_number(seek, 'contact_establish_time_ms')
    seek_overshoot_n = _require_number(seek, 'peak_force_overshoot_n')
    seek_travel_mm = _require_number(seek, 'max_seek_travel_mm')
    if seek_time_ms > max(100.0, 4.0 * _require_number(retract_cfg, 'retract_timeout_ms')):
        failures.append(f'seek_contact.contact_establish_time_ms too high: {seek_time_ms}')
    if seek_overshoot_n > max(1.0, _require_number(seek_cfg, 'contact_force_tolerance_n') * 2.0):
        failures.append(f'seek_contact.peak_force_overshoot_n too high: {seek_overshoot_n}')
    if seek_travel_mm > _require_number(seek_cfg, 'seek_contact_max_travel_mm'):
        failures.append(f'seek_contact.max_seek_travel_mm exceeds contract: {seek_travel_mm}')

    scan_force_rms = _require_number(scan, 'normal_force_rms_error_n')
    scan_speed_rms = _require_number(scan, 'tangent_speed_rms_mm_s')
    scan_trim_rms = _require_number(scan, 'pose_trim_rms_deg')
    if scan_force_rms > max(0.5, _require_number(scan_cfg, 'scan_force_tolerance_n')):
        failures.append(f'scan_follow.normal_force_rms_error_n too high: {scan_force_rms}')
    if scan_speed_rms > _require_number(scan_cfg, 'scan_tangent_speed_max_mm_s'):
        failures.append(f'scan_follow.tangent_speed_rms_mm_s exceeds max: {scan_speed_rms}')
    if scan_trim_rms > _require_number(phase_contract.get('common', {}), 'rt_max_pose_trim_deg'):
        failures.append(f'scan_follow.pose_trim_rms_deg exceeds max trim: {scan_trim_rms}')

    pause_drift_30 = _require_number(pause, 'drift_mm_30s')
    pause_drift_60 = _require_number(pause, 'drift_mm_60s')
    if pause_drift_30 > _require_number(phase_contract.get('pause_hold', {}), 'pause_hold_position_guard_mm'):
        failures.append(f'pause_hold.drift_mm_30s exceeds guard: {pause_drift_30}')
    if pause_drift_60 > _require_number(phase_contract.get('pause_hold', {}), 'pause_hold_position_guard_mm') * 1.5:
        failures.append(f'pause_hold.drift_mm_60s exceeds extended guard: {pause_drift_60}')

    retract_release_ms = _require_number(retract, 'release_detection_time_ms')
    retract_total_ms = _require_number(retract, 'total_retract_time_ms')
    retract_faulted = bool(retract.get('timeout_faulted', False))
    if retract_release_ms > _require_number(retract_cfg, 'retract_timeout_ms'):
        failures.append(f'controlled_retract.release_detection_time_ms exceeds timeout: {retract_release_ms}')
    if retract_total_ms > _require_number(retract_cfg, 'retract_timeout_ms') * 1.2:
        failures.append(f'controlled_retract.total_retract_time_ms exceeds limit: {retract_total_ms}')
    if retract_faulted:
        failures.append('controlled_retract.timeout_faulted reported true')

    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate captured HIL RT phase metrics against the active RT contract.')
    parser.add_argument('--runtime-config', required=True, help='JSON file captured from get_sdk_runtime_config')
    parser.add_argument('--evidence', required=True, help='JSON file with measured RT phase metrics')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_cfg = _load_json(Path(args.runtime_config))
    evidence = _load_json(Path(args.evidence))
    try:
        failures = validate_metrics(runtime_cfg, evidence)
    except ValueError as exc:
        print(f'[hil-phase-gate][ERROR] {exc}', file=sys.stderr)
        return 2
    if failures:
        print('[hil-phase-gate] validation failed:')
        for item in failures:
            print(f'  - {item}')
        return 1
    print('[hil-phase-gate] validation passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
