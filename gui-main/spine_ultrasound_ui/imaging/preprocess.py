from __future__ import annotations

from typing import Any

import numpy as np


def _as_float_image(data: Any) -> np.ndarray:
    array = np.asarray(data if data is not None else [], dtype=np.float32)
    if array.size == 0:
        return np.zeros((1, 1), dtype=np.float32)
    if array.ndim == 3:
        array = array.mean(axis=2)
    return array



def run_preprocess(data: Any) -> dict[str, Any]:
    image = _as_float_image(data)
    min_value = float(image.min(initial=0.0))
    max_value = float(image.max(initial=0.0))
    normalized = image - min_value
    scale = max(max_value - min_value, 1.0)
    normalized /= scale
    gradient_y, gradient_x = np.gradient(normalized)
    edge_energy = np.sqrt(gradient_x ** 2 + gradient_y ** 2)
    return {
        "image": normalized.astype(np.float32),
        "edge_energy": edge_energy.astype(np.float32),
        "stats": {
            "shape": list(normalized.shape),
            "min": round(float(normalized.min(initial=0.0)), 6),
            "max": round(float(normalized.max(initial=0.0)), 6),
            "mean": round(float(normalized.mean()), 6),
            "std": round(float(normalized.std()), 6),
        },
    }
