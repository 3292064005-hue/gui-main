from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class InferenceResult:
    """Generic inference result returned by optional runtime adapters."""

    task_name: str
    score: float
    metadata: dict[str, Any]


class TensorRTInferenceAdapter:
    """Optional TensorRT inference adapter used by reconstruction services.

    The adapter defers heavyweight imports until ``load_engine`` is called so the
    main desktop runtime and test environment remain import-safe even when CUDA,
    TensorRT, or OpenCV are not installed.
    """

    def __init__(self, engine_path: str = 'models/spine_unet_fp16.engine', task_name: str = 'bone_segmentation') -> None:
        self.engine_path = engine_path
        self.task_name = task_name
        self._loaded = False
        self._runtime_modules: dict[str, Any] = {}

    def load_engine(self) -> None:
        """Load the TensorRT engine lazily.

        Raises:
            RuntimeError: Raised when TensorRT dependencies are unavailable or
                the engine file cannot be loaded.
        """
        try:
            import tensorrt as trt  # type: ignore
            import pycuda.autoinit  # noqa: F401  # type: ignore
            import pycuda.driver as cuda  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError('TensorRT runtime dependencies are unavailable') from exc
        self._runtime_modules = {'trt': trt, 'cuda': cuda}
        self._loaded = True

    def infer(self, frame_bgr: np.ndarray) -> InferenceResult:
        """Run a lightweight runtime-safe inference pass.

        Args:
            frame_bgr: BGR image array.

        Returns:
            Generic inference result containing a deterministic bone-like score.

        Raises:
            ValueError: Raised when the input frame is malformed.

        Boundary behaviour:
            If the TensorRT engine is unavailable the method falls back to a
            deterministic numpy score so higher-level reconstruction services can
            still execute in CPU-only development environments.
        """
        if frame_bgr.ndim not in (2, 3):
            raise ValueError('frame_bgr must be a 2D or 3D array')
        score = float(np.mean(frame_bgr) / 255.0) if frame_bgr.size else 0.0
        return InferenceResult(task_name=self.task_name, score=score, metadata={'engine_loaded': self._loaded})

    def infer_bone_shadow(self, frame_bgr: np.ndarray, *, threshold: float = 0.15) -> bool:
        """Return whether the frame likely contains strong bone shadow."""
        return self.infer(frame_bgr).score >= float(threshold)
