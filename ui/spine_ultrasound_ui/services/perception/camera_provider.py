from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

import numpy as np

try:  # pragma: no cover - optional runtime dependency
    import cv2  # type: ignore
except Exception:  # pragma: no cover - cv2 is optional in test/runtime
    cv2 = None


@dataclass
class CapturedFrame:
    """Single guidance frame and its normalized metadata.

    Attributes:
        frame_id: Stable logical frame identifier.
        device_id: Source camera identifier.
        timestamp_ns: Capture timestamp in nanoseconds.
        frame_type: Camera stream mode such as ``rgb`` or ``rgbd``.
        resolution: Frame resolution mapping.
        intrinsics_hash: Hash of the intrinsics asset used for this frame.
        storage_ref: Logical or physical reference to the frame source.
        fresh: Whether the frame is fresh enough for guidance freeze.
        pixels: Normalized image matrix used by the perception pipeline.
        provider_mode: Source mode used to acquire the frame.
    """

    frame_id: str
    device_id: str
    timestamp_ns: int
    frame_type: str
    resolution: dict[str, int]
    intrinsics_hash: str
    storage_ref: str
    fresh: bool
    pixels: np.ndarray
    provider_mode: str

    def envelope(self) -> dict[str, Any]:
        """Return the JSON-serializable frame envelope consumed by artifacts.

        Returns:
            Serializable frame metadata without raw pixel buffers.
        """
        return {
            "frame_id": self.frame_id,
            "device_id": self.device_id,
            "timestamp_ns": int(self.timestamp_ns),
            "frame_type": self.frame_type,
            "resolution": dict(self.resolution),
            "intrinsics_hash": self.intrinsics_hash,
            "storage_ref": self.storage_ref,
            "fresh": bool(self.fresh),
            "provider_mode": self.provider_mode,
        }


class CameraProvider:
    """Acquire guidance frames from filesystem, webcam, or deterministic synthetic input.

    The provider gives the guidance pipeline access to actual image tensors when
    they are available. It also preserves a deterministic synthetic mode for
    tests and offline development.
    """

    def collect_frames(
        self,
        *,
        experiment_id: str,
        config: Any,
        calibration_bundle: dict[str, Any],
        source_type: str,
    ) -> list[CapturedFrame]:
        """Collect frames for guidance analysis.

        Args:
            experiment_id: Experiment identifier used to namespace frames.
            config: Runtime configuration containing provider settings.
            calibration_bundle: Frozen calibration bundle bound to the capture.
            source_type: Guidance source mode.

        Returns:
            Ordered captured frames.

        Raises:
            RuntimeError: If the selected provider cannot produce frames.
            ValueError: If provider configuration is malformed.
        """
        mode = str(getattr(config, 'camera_guidance_input_mode', 'synthetic') or 'synthetic').lower()
        if source_type == 'fallback_simulated':
            mode = 'synthetic'
        if mode == 'filesystem':
            return self._collect_filesystem_frames(experiment_id=experiment_id, config=config, calibration_bundle=calibration_bundle)
        if mode in {'opencv_camera', 'webcam', 'live'}:
            return self._collect_webcam_frames(experiment_id=experiment_id, config=config, calibration_bundle=calibration_bundle)
        if mode == 'synthetic':
            return self._collect_synthetic_frames(experiment_id=experiment_id, config=config, calibration_bundle=calibration_bundle, source_type=source_type)
        raise ValueError(f'unsupported camera guidance input mode: {mode}')

    @staticmethod
    def provider_status(*, frames: list[CapturedFrame], requested_mode: str) -> dict[str, Any]:
        """Return a normalized provider health summary.

        Args:
            frames: Frames produced by the provider.
            requested_mode: Provider mode requested by configuration.

        Returns:
            Provider status mapping used by readiness and audit layers.
        """
        provider_mode = frames[0].provider_mode if frames else requested_mode
        return {
            'requested_mode': requested_mode,
            'provider_mode': provider_mode,
            'frame_count': len(frames),
            'available': bool(frames),
            'fresh': all(bool(frame.fresh) for frame in frames) if frames else False,
        }

    def _collect_filesystem_frames(self, *, experiment_id: str, config: Any, calibration_bundle: dict[str, Any]) -> list[CapturedFrame]:
        source_path = Path(str(getattr(config, 'camera_guidance_source_path', '') or '')).expanduser()
        if not source_path.exists():
            raise RuntimeError(f'camera guidance source path not found: {source_path}')
        frame_limit = max(1, int(getattr(config, 'camera_guidance_frame_count', 3) or 3))
        if source_path.is_file():
            candidates = [source_path]
        else:
            patterns = [
                str(getattr(config, 'camera_guidance_file_glob', '*.npy') or '*.npy'),
                '*.npz', '*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tif', '*.tiff',
            ]
            seen: set[Path] = set()
            candidates = []
            for pattern in patterns:
                for item in sorted(source_path.glob(pattern)):
                    if item not in seen:
                        seen.add(item)
                        candidates.append(item)
        if not candidates:
            raise RuntimeError(f'no guidance frames found under {source_path}')
        frames: list[CapturedFrame] = []
        for index, file_path in enumerate(candidates[:frame_limit], start=1):
            pixels = self._load_pixels(file_path)
            frame = self._make_frame(
                experiment_id=experiment_id,
                calibration_bundle=calibration_bundle,
                storage_ref=str(file_path),
                pixels=pixels,
                provider_mode='filesystem',
                index=index,
            )
            frames.append(frame)
        return frames

    def _collect_webcam_frames(self, *, experiment_id: str, config: Any, calibration_bundle: dict[str, Any]) -> list[CapturedFrame]:
        if cv2 is None:
            raise RuntimeError('opencv-python-headless is required for webcam guidance input mode')
        device_index = int(getattr(config, 'camera_capture_device_index', 0) or 0)
        frame_limit = max(1, int(getattr(config, 'camera_guidance_frame_count', 3) or 3))
        timeout_ms = max(100, int(getattr(config, 'camera_capture_timeout_ms', 500) or 500))
        capture = cv2.VideoCapture(device_index)
        if not capture.isOpened():
            raise RuntimeError(f'unable to open camera device {device_index}')
        frames: list[CapturedFrame] = []
        deadline = time.monotonic() + timeout_ms / 1000.0
        try:
            index = 0
            while index < frame_limit and time.monotonic() < deadline:
                ok, image = capture.read()
                if not ok or image is None:
                    continue
                index += 1
                pixels = self._normalize_pixels(image)
                frame = self._make_frame(
                    experiment_id=experiment_id,
                    calibration_bundle=calibration_bundle,
                    storage_ref=f'camera://device/{device_index}/frame-{index:03d}',
                    pixels=pixels,
                    provider_mode='opencv_camera',
                    index=index,
                )
                frames.append(frame)
        finally:
            capture.release()
        if len(frames) < frame_limit:
            raise RuntimeError(f'camera device {device_index} produced only {len(frames)} of {frame_limit} requested frames before timeout')
        return frames

    def _collect_synthetic_frames(self, *, experiment_id: str, config: Any, calibration_bundle: dict[str, Any], source_type: str) -> list[CapturedFrame]:
        frame_limit = max(1, int(getattr(config, 'camera_guidance_frame_count', 3) or 3))
        width = int(calibration_bundle.get('camera_intrinsics', {}).get('resolution', {}).get('width', 640) or 640)
        height = int(calibration_bundle.get('camera_intrinsics', {}).get('resolution', {}).get('height', 480) or 480)
        frames: list[CapturedFrame] = []
        seed = abs(hash((experiment_id, source_type))) % 9973
        offset_px = int((seed % max(width // 6, 1)) - max(width // 12, 1))
        for index in range(1, frame_limit + 1):
            pixels = np.zeros((height, width), dtype=np.float32)
            center_x = width // 2 + offset_px + (index - 2) * max(width // 100, 1)
            half_band = max(width // 16, 8)
            x0 = max(0, center_x - half_band)
            x1 = min(width, center_x + half_band)
            y0 = max(0, height // 8)
            y1 = min(height, height - height // 10)
            pixels[y0:y1, x0:x1] = 0.92
            pixels[y0:y1, max(0, x0 - 3):x0] = 0.4
            pixels[y0:y1, x1:min(width, x1 + 3)] = 0.4
            gradient = np.linspace(0.08, 0.18, height, dtype=np.float32)[:, None]
            pixels = np.clip(pixels + gradient, 0.0, 1.0)
            frame = self._make_frame(
                experiment_id=experiment_id,
                calibration_bundle=calibration_bundle,
                storage_ref=f'synthetic://{experiment_id}/{source_type}/frame-{index:03d}',
                pixels=pixels,
                provider_mode='synthetic',
                index=index,
            )
            frames.append(frame)
        return frames

    def _make_frame(
        self,
        *,
        experiment_id: str,
        calibration_bundle: dict[str, Any],
        storage_ref: str,
        pixels: np.ndarray,
        provider_mode: str,
        index: int,
    ) -> CapturedFrame:
        pixels = self._normalize_pixels(pixels)
        height, width = pixels.shape[:2]
        device_id = str(calibration_bundle.get('camera_device_id', 'rgbd_back_camera'))
        intrinsics_hash = str(calibration_bundle.get('camera_intrinsics_hash', ''))
        frame_type = str(calibration_bundle.get('camera_intrinsics', {}).get('frame_type', 'rgbd'))
        return CapturedFrame(
            frame_id=f'{experiment_id}-{provider_mode}-{index:03d}',
            device_id=device_id,
            timestamp_ns=time.time_ns() + index,
            frame_type=frame_type,
            resolution={'width': int(width), 'height': int(height)},
            intrinsics_hash=intrinsics_hash,
            storage_ref=storage_ref,
            fresh=True,
            pixels=pixels,
            provider_mode=provider_mode,
        )

    def _load_pixels(self, file_path: Path) -> np.ndarray:
        suffix = file_path.suffix.lower()
        if suffix == '.npy':
            array = np.load(file_path)
            return self._normalize_pixels(array)
        if suffix == '.npz':
            archive = np.load(file_path)
            if not archive.files:
                raise RuntimeError(f'npz guidance source contains no arrays: {file_path}')
            return self._normalize_pixels(archive[archive.files[0]])
        if suffix in {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}:
            if cv2 is None:
                raise RuntimeError('opencv-python-headless is required for image guidance input mode')
            image = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
            if image is None:
                raise RuntimeError(f'failed to read guidance frame: {file_path}')
            return self._normalize_pixels(image)
        raise RuntimeError(f'unsupported guidance frame format: {file_path.suffix}')

    @staticmethod
    def _normalize_pixels(image: np.ndarray) -> np.ndarray:
        array = np.asarray(image)
        if array.ndim == 3:
            if array.shape[2] >= 3:
                array = array[..., :3].mean(axis=2)
            else:
                array = array[..., 0]
        if array.ndim != 2:
            raise RuntimeError(f'guidance frame must be 2-D after normalization, got shape {array.shape}')
        array = array.astype(np.float32)
        max_value = float(array.max()) if array.size else 0.0
        min_value = float(array.min()) if array.size else 0.0
        if max_value > min_value:
            array = (array - min_value) / (max_value - min_value)
        elif max_value > 0.0:
            array = array / max_value
        return np.clip(array, 0.0, 1.0)
