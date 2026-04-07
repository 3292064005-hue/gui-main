from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import now_text


class CalibrationBundleService:
    """Build the frozen calibration bundle used by guidance-only registration.

    The camera guidance subsystem is not an execution authority, but its outputs
    must still be traceable to a single calibration bundle before a session can
    be frozen. This service loads the external calibration configuration and
    normalizes it into a stable JSON contract with per-asset hashes.

    Args:
        config_path: Optional explicit path to the calibration YAML. When not
            supplied, the repository default ``configs/calibration.yaml`` is
            used.

    Raises:
        ValueError: Raised when required calibration structures are malformed.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or Path(__file__).resolve().parents[3] / "configs" / "calibration.yaml"

    def build_bundle(self, *, config: RuntimeConfig, camera_device_id: str = "rgbd_back_camera") -> dict[str, Any]:
        """Return the normalized calibration bundle.

        Args:
            config: Active runtime configuration used to bind the probe TCP.
            camera_device_id: Logical camera identifier participating in
                guidance.

        Returns:
            A JSON-serializable calibration bundle with per-asset hashes and a
            stable bundle hash.

        Raises:
            ValueError: Raised when required matrices or scalar values are not
                present or have invalid shapes.
        """
        raw = self._load_yaml()
        camera = dict(raw.get("camera_guidance", {}))
        temporal = dict(raw.get("temporal_calibration", {}))
        spatial = dict(raw.get("spatial_calibration", {}))
        support = dict(raw.get("support_frame_calibration", {}))

        intrinsics = self._build_camera_intrinsics(camera_device_id=camera_device_id, camera=camera, spatial=spatial)
        camera_to_base = self._build_camera_to_base(camera_device_id=camera_device_id, camera=camera)
        probe_tcp = self._build_probe_tcp(config=config, spatial=spatial)
        support_frame = self._build_support_frame(support)
        temporal_sync = self._build_temporal_sync(temporal=temporal, camera_device_id=camera_device_id)

        bundle = {
            "schema_version": "1.0",
            "bundle_id": f"guidance_bundle::{camera_device_id}",
            "generated_at": now_text(),
            "release_state": "approved",
            "bundle_role": "guidance_only",
            "camera_device_id": camera_device_id,
            "camera_intrinsics": intrinsics,
            "camera_to_base": camera_to_base,
            "probe_tcp": probe_tcp,
            "support_frame": support_frame,
            "temporal_sync": temporal_sync,
            "camera_intrinsics_hash": intrinsics["hash"],
            "camera_to_base_hash": camera_to_base["hash"],
            "probe_tcp_hash": probe_tcp["hash"],
            "support_frame_hash": support_frame["hash"],
            "temporal_sync_hash": temporal_sync["hash"],
            "valid_for_devices": {
                "camera_device_id": camera_device_id,
                "robot_model": config.robot_model,
                "sdk_robot_class": config.sdk_robot_class,
            },
            "residual_metrics": {
                "camera_to_base_rms_mm": float(camera_to_base.get("residual_rms_mm", 0.0)),
                "probe_tcp_rms_mm": float(probe_tcp.get("residual_rms_mm", 0.0)),
                "temporal_sync_jitter_ms": float(temporal_sync.get("estimated_jitter_ms", 0.0)),
            },
        }
        bundle["bundle_hash"] = self._stable_hash({
            "camera_intrinsics_hash": bundle["camera_intrinsics_hash"],
            "camera_to_base_hash": bundle["camera_to_base_hash"],
            "probe_tcp_hash": bundle["probe_tcp_hash"],
            "support_frame_hash": bundle["support_frame_hash"],
            "temporal_sync_hash": bundle["temporal_sync_hash"],
            "bundle_role": bundle["bundle_role"],
            "valid_for_devices": bundle["valid_for_devices"],
        })
        return bundle

    def _load_yaml(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise ValueError(f"calibration config not found: {self.config_path}")
        loaded = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError("calibration config root must be a mapping")
        return loaded

    def _build_camera_intrinsics(self, *, camera_device_id: str, camera: dict[str, Any], spatial: dict[str, Any]) -> dict[str, Any]:
        intrinsics = dict(camera.get("intrinsics", {}))
        resolution = dict(camera.get("resolution", {}))
        fx = float(intrinsics.get("fx", 0.0) or 0.0)
        fy = float(intrinsics.get("fy", 0.0) or 0.0)
        cx = float(intrinsics.get("cx", 0.0) or 0.0)
        cy = float(intrinsics.get("cy", 0.0) or 0.0)
        width = int(resolution.get("width", 0) or 0)
        height = int(resolution.get("height", 0) or 0)
        if min(fx, fy) <= 0.0 or min(width, height) <= 0:
            raise ValueError("camera intrinsics and resolution must be positive")
        payload = {
            "device_id": camera_device_id,
            "frame_type": str(camera.get("frame_type", "rgbd")),
            "resolution": {"width": width, "height": height},
            "distortion_model": str(intrinsics.get("distortion_model", "plumb_bob")),
            "coefficients": [float(value) for value in list(intrinsics.get("distortion_coefficients", []))],
            "matrix": {"fx": fx, "fy": fy, "cx": cx, "cy": cy},
            "mm_per_pixel_x": float(spatial.get("mm_per_pixel_x", 0.15) or 0.15),
            "mm_per_pixel_y": float(spatial.get("mm_per_pixel_y", 0.15) or 0.15),
            "qualification_basis": str(camera.get("qualification_basis", "guidance_release")),
        }
        payload["hash"] = self._stable_hash(payload)
        return payload

    def _build_camera_to_base(self, *, camera_device_id: str, camera: dict[str, Any]) -> dict[str, Any]:
        extrinsics = dict(camera.get("camera_to_base", {}))
        translation = [float(value) for value in list(extrinsics.get("translation_m", []))]
        rotation = [float(value) for value in list(extrinsics.get("rotation_rpy_deg", []))]
        if len(translation) != 3 or len(rotation) != 3:
            raise ValueError("camera_to_base requires 3 translation and 3 rotation values")
        payload = {
            "device_id": camera_device_id,
            "mount_id": str(extrinsics.get("mount_id", "guidance_back_mount")),
            "translation_m": translation,
            "rotation_rpy_deg": rotation,
            "residual_rms_mm": float(extrinsics.get("residual_rms_mm", 0.0) or 0.0),
            "source": str(extrinsics.get("source", "released_guidance_mount")),
        }
        payload["hash"] = self._stable_hash(payload)
        return payload

    def _build_probe_tcp(self, *, config: RuntimeConfig, spatial: dict[str, Any]) -> dict[str, Any]:
        matrix = [float(value) for value in list(config.tcp_frame_matrix)]
        if len(matrix) != 16:
            raise ValueError("runtime TCP frame matrix must contain 16 elements")
        calibration_matrix = self._normalize_matrix_4x4(spatial.get("T_probe", []), field_name="spatial_calibration.T_probe")
        payload = {
            "tool_name": config.tool_name,
            "tcp_name": config.tcp_name,
            "tcp_frame_matrix_mm": matrix,
            "calibration_probe_matrix": calibration_matrix,
            "load_com_mm": [float(value) for value in list(config.load_com_mm)],
            "load_inertia": [float(value) for value in list(config.load_inertia)],
            "residual_rms_mm": float(spatial.get("probe_tcp_residual_rms_mm", 0.0) or 0.0),
            "source": "runtime_config_and_calibration_yaml",
        }
        payload["hash"] = self._stable_hash(payload)
        return payload

    def _build_support_frame(self, support: dict[str, Any]) -> dict[str, Any]:
        translation = [float(value) for value in list(support.get("translation_m", []))]
        rotation = [float(value) for value in list(support.get("rotation_rpy_deg", []))]
        bounds = dict(support.get("bounds_m", {}))
        if len(translation) != 3 or len(rotation) != 3:
            raise ValueError("support_frame_calibration requires 3 translation and 3 rotation values")
        payload = {
            "frame_id": str(support.get("frame_id", "patient_support")),
            "translation_m": translation,
            "rotation_rpy_deg": rotation,
            "bounds_m": {
                "length": float(bounds.get("length", 0.0) or 0.0),
                "width": float(bounds.get("width", 0.0) or 0.0),
                "height": float(bounds.get("height", 0.0) or 0.0),
            },
            "source": str(support.get("source", "released_support_frame")),
        }
        payload["hash"] = self._stable_hash(payload)
        return payload

    def _build_temporal_sync(self, *, temporal: dict[str, Any], camera_device_id: str) -> dict[str, Any]:
        payload = {
            "camera_device_id": camera_device_id,
            "camera_latency_ms": float(temporal.get("dt_camera_latency_ms", 0.0) or 0.0),
            "estimated_jitter_ms": float(temporal.get("estimated_jitter_ms", 0.0) or 0.0),
            "sync_method": str(temporal.get("sync_method", "cross_correlation")),
            "source": str(temporal.get("source", "released_temporal_sync")),
        }
        payload["hash"] = self._stable_hash(payload)
        return payload

    @staticmethod
    def _normalize_matrix_4x4(value: Any, *, field_name: str) -> list[list[float]]:
        matrix = [[float(cell) for cell in list(row)] for row in list(value)]
        if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
            raise ValueError(f"{field_name} must be a 4x4 matrix")
        return matrix

    @staticmethod
    def _stable_hash(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
