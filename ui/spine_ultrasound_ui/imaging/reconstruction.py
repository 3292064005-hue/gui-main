from __future__ import annotations

"""Demo reconstruction adapter.

This module remains available for lightweight imaging tests and UI previews, but
it is no longer the authoritative postprocess reconstruction path. Authoritative
session reconstruction artifacts are now produced under
``spine_ultrasound_ui.services.reconstruction``.
"""

from typing import Any

import numpy as np

from spine_ultrasound_ui.imaging.feature_extract import run_feature_extract


def run_reconstruction(data: Any) -> dict[str, Any]:
    """Build a lightweight demo reconstruction result from imaging features.

    Args:
        data: Raw image or preprocessed payload accepted by
            :func:`spine_ultrasound_ui.imaging.feature_extract.run_feature_extract`.

    Returns:
        Structured demo payload containing a 2D curve and bounding mesh summary.

    Raises:
        ValueError: Propagated from the feature extractor when the input payload
            is malformed.

    Boundary behaviour:
        This function intentionally stays local to the imaging demo surface. It
        does not read or write session artifacts and should not be used as the
        authoritative clinical reconstruction path.
    """
    feature_result = run_feature_extract(data)
    keypoints = feature_result["keypoints"]
    if not keypoints:
        return {"curve": [], "mesh": None, "confidence": 0.0, "mode": "demo_adapter"}

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
        "mode": "demo_adapter",
    }


def load_reconstruction_view_model(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize authoritative or demo reconstruction payloads for UI previews.

    Args:
        payload: Either an authoritative ``spine_curve`` artifact or the demo
            reconstruction payload returned by :func:`run_reconstruction`.

    Returns:
        Preview-friendly view-model dictionary.

    Raises:
        No exceptions are raised.
    """
    if "points" in payload:
        points = [dict(item) for item in payload.get("points", []) if isinstance(item, dict)]
        return {
            "mode": "authoritative",
            "curve": [{"x": point.get("x_mm", 0.0), "y": point.get("y_mm", 0.0), "strength": point.get("quality_score", 0.0)} for point in points],
            "mesh": dict(payload.get("fit", {})),
            "confidence": float(payload.get("confidence", 0.0) or 0.0),
        }
    return {
        "mode": str(payload.get("mode", "demo_adapter") or "demo_adapter"),
        "curve": list(payload.get("curve", [])),
        "mesh": payload.get("mesh"),
        "confidence": float(payload.get("confidence", 0.0) or 0.0),
    }
