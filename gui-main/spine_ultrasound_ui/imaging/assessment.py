from __future__ import annotations

from typing import Any

import numpy as np

from spine_ultrasound_ui.imaging.reconstruction import run_reconstruction


def run_assessment(data: Any) -> dict[str, Any]:
    reconstruction = run_reconstruction(data)
    curve = reconstruction["curve"]
    if len(curve) < 2:
        return {"cobb_angle": 0.0, "confidence": 0.0, "curve_length": 0.0}

    points = np.asarray([[point["x"], point["y"]] for point in curve], dtype=np.float32)
    deltas = np.diff(points, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    curve_length = float(lengths.sum())
    start = points[0]
    end = points[-1]
    vector = end - start
    cobb_angle = float(np.degrees(np.arctan2(vector[1], vector[0])))
    confidence = float(min(1.0, reconstruction["confidence"] * min(1.0, curve_length / 100.0)))
    return {
        "cobb_angle": round(cobb_angle, 4),
        "confidence": round(confidence, 6),
        "curve_length": round(curve_length, 4),
        "point_count": int(points.shape[0]),
    }
