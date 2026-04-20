from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping
import zipfile

from spine_ultrasound_ui.services.robot_identity_service import RobotIdentityService


@dataclass(frozen=True)
class LiveEvidenceBundleInspection:
    valid: bool
    reason: str
    bundle_path: str
    bundle_kind: str
    members: tuple[str, ...]
    runtime_identity_ok: bool
    readiness_ok: bool
    metrics_ok: bool
    readiness_summary_state: str = ''
    readiness_verification_boundary: str = ''
    readiness_evidence_tier: str = ''
    readiness_live_runtime_ready: bool = False
    readiness_live_runtime_verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            'valid': self.valid,
            'reason': self.reason,
            'bundle_path': self.bundle_path,
            'bundle_kind': self.bundle_kind,
            'members': list(self.members),
            'runtime_identity_ok': self.runtime_identity_ok,
            'readiness_ok': self.readiness_ok,
            'metrics_ok': self.metrics_ok,
            'readiness_summary_state': self.readiness_summary_state,
            'readiness_verification_boundary': self.readiness_verification_boundary,
            'readiness_evidence_tier': self.readiness_evidence_tier,
            'readiness_live_runtime_ready': self.readiness_live_runtime_ready,
            'readiness_live_runtime_verified': self.readiness_live_runtime_verified,
        }


class LiveEvidenceBundleService:
    """Validate archived real-controller evidence bundles.

    Live-controller validation is closed only by the archived bundle itself.
    The caller may not substitute a directory tree, nor may it splice an
    external readiness manifest into the proof chain. The bundle must contain
    the frozen mainline identity, an archived runtime readiness manifest, and
    measured RT phase metrics that satisfy the active runtime contract.
    """

    REQUIRED_BUNDLE_FILES = (
        'runtime_config.json',
        'rt_phase_metrics.json',
        'runtime_readiness_manifest.json',
    )
    REQUIRED_PHASE_SECTIONS = (
        'seek_contact',
        'scan_follow',
        'pause_hold',
        'controlled_retract',
    )

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

    def inspect(
        self,
        bundle_path: str,
        *,
        readiness_manifest: Mapping[str, Any] | None = None,
        sdk_binding_requested: bool,
        model_binding_requested: bool,
    ) -> LiveEvidenceBundleInspection:
        bundle = str(bundle_path or '').strip()
        if not bundle:
            return LiveEvidenceBundleInspection(False, 'no live evidence bundle supplied', '', 'missing', (), False, False, False)
        if not (sdk_binding_requested and model_binding_requested):
            return LiveEvidenceBundleInspection(False, 'live evidence requires both SDK and xMate model bindings', bundle, 'rejected', (), False, False, False)
        if isinstance(readiness_manifest, Mapping) and readiness_manifest:
            return LiveEvidenceBundleInspection(False, 'external readiness manifest is forbidden when validating a live evidence bundle; embed runtime_readiness_manifest.json inside the archived bundle', bundle, 'rejected', (), False, False, False)
        path = Path(bundle)
        if not path.is_absolute():
            path = (self.root_dir / path).resolve()
        if not path.exists():
            return LiveEvidenceBundleInspection(False, f'live evidence bundle does not exist: {path}', str(path), 'missing', (), False, False, False)

        try:
            files = self._read_bundle(path)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            return LiveEvidenceBundleInspection(False, f'failed to read live evidence bundle: {exc}', str(path), 'invalid', (), False, False, False)

        members = tuple(sorted(k for k in files if not k.startswith('_')))
        missing = [name for name in self.REQUIRED_BUNDLE_FILES if name not in files]
        if missing:
            return LiveEvidenceBundleInspection(False, f'live evidence bundle missing required files: {", ".join(missing)}', str(path), files['_kind'], members, False, False, False)

        runtime_cfg = self._load_json_dict(files['runtime_config.json'], 'runtime_config.json')
        metrics = self._load_json_dict(files['rt_phase_metrics.json'], 'rt_phase_metrics.json')
        readiness_snapshot = self._load_json_dict(files['runtime_readiness_manifest.json'], 'runtime_readiness_manifest.json')
        runtime_ok, runtime_reason = self._validate_runtime_identity(runtime_cfg)
        readiness_ok, readiness_reason = self._validate_readiness(readiness_snapshot)
        readiness_verification = dict((readiness_snapshot or {}).get('verification') or {})
        metrics_ok, metrics_reason = self._validate_metrics(runtime_cfg, metrics)
        common = dict(
            readiness_summary_state=str(readiness_snapshot.get('summary_state', '')),
            readiness_verification_boundary=str(readiness_verification.get('verification_boundary', '')),
            readiness_evidence_tier=str(readiness_verification.get('evidence_tier', '')),
            readiness_live_runtime_ready=bool(readiness_verification.get('live_runtime_ready', False)),
            readiness_live_runtime_verified=bool(readiness_verification.get('live_runtime_verified', False)),
        )
        if not runtime_ok:
            return LiveEvidenceBundleInspection(False, runtime_reason, str(path), files['_kind'], members, False, readiness_ok, metrics_ok, **common)
        if not readiness_ok:
            return LiveEvidenceBundleInspection(False, readiness_reason, str(path), files['_kind'], members, True, False, metrics_ok, **common)
        if not metrics_ok:
            return LiveEvidenceBundleInspection(False, metrics_reason, str(path), files['_kind'], members, True, True, False, **common)
        return LiveEvidenceBundleInspection(True, 'live evidence bundle passed archived structural, readiness, and RT metric checks', str(path), files['_kind'], members, True, True, True, **common)

    def _read_bundle(self, path: Path) -> dict[str, str]:
        if path.is_dir():
            raise ValueError(f'{path} is a directory; only archived .zip bundles are accepted for live evidence validation')
        if path.suffix.lower() != '.zip' or not zipfile.is_zipfile(path):
            raise ValueError(f'{path} is not a zip archive')
        data = {'_kind': 'zip'}
        with zipfile.ZipFile(path, 'r') as zf:
            for member in zf.namelist():
                if member.endswith('/'):
                    continue
                name = Path(member).name
                if name.endswith('.json'):
                    data[name] = zf.read(member).decode('utf-8')
        return data

    @staticmethod
    def _load_json_dict(raw: str, source_name: str) -> dict[str, Any]:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f'{source_name} must contain a top-level JSON object')
        return data

    @staticmethod
    def _validate_runtime_identity(runtime_cfg: Mapping[str, Any]) -> tuple[bool, str]:
        try:
            identity = RobotIdentityService().resolve(
                str(runtime_cfg.get('robot_model') or ''),
                str(runtime_cfg.get('sdk_robot_class') or ''),
                int(runtime_cfg.get('axis_count', 0) or 0),
            )
        except Exception as exc:
            return False, f'runtime_config.json identity mismatch: {exc}'
        if str(runtime_cfg.get('preferred_link') or '') != identity.preferred_link:
            return False, f"runtime_config.json identity mismatch: expected preferred_link={identity.preferred_link!r}, got {runtime_cfg.get('preferred_link')!r}"
        rt_mode = str(runtime_cfg.get('rt_mode') or runtime_cfg.get('clinical_mainline_mode') or '')
        if rt_mode != identity.rt_mode:
            return False, f'runtime_config.json mainline mode mismatch: expected {identity.rt_mode}, got {rt_mode!r}'
        if not isinstance(runtime_cfg.get('rt_phase_contract'), Mapping):
            return False, 'runtime_config.json must include rt_phase_contract for measured HIL checks'
        return True, ''

    @staticmethod
    def _validate_readiness(readiness_manifest: Mapping[str, Any]) -> tuple[bool, str]:
        verification = dict((readiness_manifest or {}).get('verification') or {})
        if not verification:
            return False, 'runtime_readiness_manifest.json missing verification section'
        if not bool(verification.get('live_runtime_ready', False)):
            return False, 'runtime_readiness_manifest.json does not prove live runtime readiness'
        boundary = str(verification.get('verification_boundary', ''))
        if boundary != 'live_runtime_unverified':
            return False, f'unexpected verification boundary for archived live evidence: {boundary!r}'
        return True, ''

    @staticmethod
    def _require_number(obj: Mapping[str, Any], key: str) -> float:
        value = obj.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f'missing or non-finite numeric field: {key}')
        return float(value)

    def _validate_metrics(self, runtime_cfg: Mapping[str, Any], evidence: Mapping[str, Any]) -> tuple[bool, str]:
        phase_contract = evidence.get('rt_phase_contract') or runtime_cfg.get('rt_phase_contract')
        if not isinstance(phase_contract, Mapping):
            return False, 'runtime config must expose rt_phase_contract'
        for name in self.REQUIRED_PHASE_SECTIONS:
            if not isinstance(evidence.get(name), Mapping):
                return False, f'rt_phase_metrics.json missing section: {name}'

        seek_cfg = dict(phase_contract.get('seek_contact', {}))
        scan_cfg = dict(phase_contract.get('scan_follow', {}))
        retract_cfg = dict(phase_contract.get('controlled_retract', {}))
        common_cfg = dict(phase_contract.get('common', {}))
        pause_cfg = dict(phase_contract.get('pause_hold', {}))
        seek = dict(evidence.get('seek_contact', {}))
        scan = dict(evidence.get('scan_follow', {}))
        pause = dict(evidence.get('pause_hold', {}))
        retract = dict(evidence.get('controlled_retract', {}))
        try:
            seek_time_ms = self._require_number(seek, 'contact_establish_time_ms')
            seek_overshoot_n = self._require_number(seek, 'peak_force_overshoot_n')
            seek_travel_mm = self._require_number(seek, 'max_seek_travel_mm')
            if seek_time_ms > max(100.0, 4.0 * self._require_number(retract_cfg, 'retract_timeout_ms')):
                return False, f'seek_contact.contact_establish_time_ms too high: {seek_time_ms}'
            if seek_overshoot_n > max(1.0, self._require_number(seek_cfg, 'contact_force_tolerance_n') * 2.0):
                return False, f'seek_contact.peak_force_overshoot_n too high: {seek_overshoot_n}'
            if seek_travel_mm > self._require_number(seek_cfg, 'seek_contact_max_travel_mm'):
                return False, f'seek_contact.max_seek_travel_mm exceeds contract: {seek_travel_mm}'

            scan_force_rms = self._require_number(scan, 'normal_force_rms_error_n')
            scan_speed_rms = self._require_number(scan, 'tangent_speed_rms_mm_s')
            scan_trim_rms = self._require_number(scan, 'pose_trim_rms_deg')
            if scan_force_rms > max(0.5, self._require_number(scan_cfg, 'scan_force_tolerance_n')):
                return False, f'scan_follow.normal_force_rms_error_n too high: {scan_force_rms}'
            if scan_speed_rms > self._require_number(scan_cfg, 'scan_tangent_speed_max_mm_s'):
                return False, f'scan_follow.tangent_speed_rms_mm_s exceeds max: {scan_speed_rms}'
            if scan_trim_rms > self._require_number(common_cfg, 'rt_max_pose_trim_deg'):
                return False, f'scan_follow.pose_trim_rms_deg exceeds max trim: {scan_trim_rms}'

            pause_drift_30 = self._require_number(pause, 'drift_mm_30s')
            pause_drift_60 = self._require_number(pause, 'drift_mm_60s')
            if pause_drift_30 > self._require_number(pause_cfg, 'pause_hold_position_guard_mm'):
                return False, f'pause_hold.drift_mm_30s exceeds guard: {pause_drift_30}'
            if pause_drift_60 > self._require_number(pause_cfg, 'pause_hold_position_guard_mm') * 1.5:
                return False, f'pause_hold.drift_mm_60s exceeds extended guard: {pause_drift_60}'

            retract_release_ms = self._require_number(retract, 'release_detection_time_ms')
            retract_total_ms = self._require_number(retract, 'total_retract_time_ms')
            if retract_release_ms > self._require_number(retract_cfg, 'retract_timeout_ms'):
                return False, f'controlled_retract.release_detection_time_ms exceeds timeout: {retract_release_ms}'
            if retract_total_ms > self._require_number(retract_cfg, 'retract_timeout_ms') * 1.2:
                return False, f'controlled_retract.total_retract_time_ms exceeds limit: {retract_total_ms}'
            if bool(retract.get('timeout_faulted', False)):
                return False, 'controlled_retract.timeout_faulted reported true'
        except ValueError as exc:
            return False, str(exc)
        return True, ''
