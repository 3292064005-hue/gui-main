from __future__ import annotations

from typing import Any

import numpy as np

from spine_ultrasound_ui.imaging.feature_extract import run_feature_extract


def run_reconstruction(data: Any) -> dict[str, Any]:
    feature_result = run_feature_extract(data)
    keypoints = feature_result["keypoints"]
    if not keypoints:
        return {"curve": [], "mesh": None, "confidence": 0.0}

    ordered = sorted(keypoints, key=lambda item: (item["row"], item["col"]))
    curve = [{"x": item["col"], "y": item["row"], "strength": item["strength"]} for item in ordered]
    points = np.asarray([[item["x"], item["y"]] for item in curve], dtype=np.float32)
    centroid = points.mean(axis=0)
    bounds = {
        "min_x": float(points[:, 0].min()),
        "max_x": float(points[:, 0].max()),
        "min_y": float(points[:, 1].min()),
        "max_y": float(points[:, 1].max()),
    }
    return {
        "curve": curve,
        "mesh": {
            "point_count": int(points.shape[0]),
            "centroid": {"x": float(centroid[0]), "y": float(centroid[1])},
            "bounds": bounds,
        },
        "confidence": feature_result["confidence"],
    }
