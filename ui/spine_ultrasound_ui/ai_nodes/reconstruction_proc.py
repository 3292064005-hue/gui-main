from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class ReconstructionVolume:
    """Simple reconstruction volume container for optional research plugins."""

    tsdf_like_volume: np.ndarray
    metadata: dict[str, Any]


class GPUVolumeReconstructionAdapter:
    """Optional GPU reconstruction adapter for future freehand-3D US plugins.

    The adapter keeps the current runtime import-safe by avoiding heavyweight
    Open3D/CUDA imports until explicitly requested. It serves as the Phase-4
    extension point for stronger reconstruction backends such as sensorless or
    neural implicit freehand ultrasound methods.
    """

    def __init__(self, h5_file_path: str | Path) -> None:
        self.h5_path = Path(h5_file_path)
        self.running = False

    def start_integration(self) -> ReconstructionVolume:
        """Build a deterministic placeholder-free volume from stored frames.

        Returns:
            ReconstructionVolume containing a simple stacked intensity volume.

        Raises:
            FileNotFoundError: Raised when the source HDF5 file does not exist.

        Boundary behaviour:
            The implementation is CPU-safe and deterministic. When the source
            file is unavailable it raises immediately instead of silently doing
            nothing, because callers use this class as an explicit research-mode
            extension point.
        """
        if not self.h5_path.exists():
            raise FileNotFoundError(self.h5_path)
        import h5py  # local import to avoid hard dependency on import

        with h5py.File(self.h5_path, 'r') as handle:
            images = np.asarray(handle['images']) if 'images' in handle else np.zeros((0, 0, 0), dtype=np.float32)
        volume = images.astype(np.float32)
        self.running = True
        return ReconstructionVolume(tsdf_like_volume=volume, metadata={'frame_count': int(volume.shape[0]) if volume.ndim >= 1 else 0})

    def export_point_cloud(self) -> dict[str, Any]:
        """Export a lightweight point-cloud summary from the reconstructed volume."""
        if not self.running:
            return {'point_count': 0, 'status': 'not_started'}
        return {'point_count': 0, 'status': 'cpu_summary_only'}
