from __future__ import annotations

"""Demo scoliosis-assessment adapter.

This module remains available for lightweight imaging tests and preview-only
workflows. Authoritative Cobb measurements for locked sessions are produced by
``spine_ultrasound_ui.services.assessment`` and written to
``derived/assessment/*``.
"""

from math import atan2, degrees
from typing import Any

import numpy as np

from spine_ultrasound_ui.imaging.reconstruction import run_reconstruction


def run_assessment(data: Any) -> dict[str, Any]:
    """Build a lightweight demo Cobb-like assessment from demo reconstruction.

    Args:
        data: Raw image or preprocessed payload accepted by
            :func:`spine_ultrasound_ui.imaging.reconstruction.run_reconstruction`.

    Returns:
        Structured demo assessment payload suitable for unit tests and preview
        pages.

    Raises:
        ValueError: Propagated from demo reconstruction when the input payload is
            malformed.

    Boundary behaviour:
        The returned ``cobb_angle`` is a preview-only geometric proxy and must
        not be treated as the authoritative clinical measurement for a session.
    """
    reconstruction = run_reconstruction(data)
    curve = reconstruction["curve"]
    if len(curve) < 2:
        return {"cobb_angle": 0.0, "confidence": 0.0, "curve_length": 0.0, "point_count": 0, "mode": "demo_adapter"}

    points = np.asarray([[point["x"], point["y"]] for point in curve], dtype=np.float32)
    deltas = np.diff(points, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    curve_length = float(lengths.sum())
    start = points[0]
    end = points[-1]
    vector = end - start
    cobb_angle = float(degrees(atan2(vector[1], vector[0])))
    confidence = float(min(1.0, reconstruction["confidence"] * min(1.0, curve_length / 100.0)))
    return {
        "cobb_angle": round(cobb_angle, 4),
        "confidence": round(confidence, 6),
        "curve_length": round(curve_length, 4),
        "point_count": int(points.shape[0]),
        "mode": "demo_adapter",
    }


def load_assessment_view_model(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize authoritative or demo assessment payloads for UI previews.

    Args:
        payload: Either an authoritative ``assessment_summary`` /
            ``cobb_measurement`` artifact or the demo assessment payload
            returned by :func:`run_assessment`.

    Returns:
        Preview-friendly assessment view model.

    Raises:
        No exceptions are raised.
    """
    if "cobb_angle_deg" in payload or "angle_deg" in payload:
        return {
            "mode": "authoritative",
            "cobb_angle": float(payload.get("cobb_angle_deg", payload.get("angle_deg", 0.0)) or 0.0),
            "confidence": float(payload.get("confidence", 0.0) or 0.0),
            "requires_manual_review": bool(payload.get("requires_manual_review", False)),
        }
    return {
        "mode": str(payload.get("mode", "demo_adapter") or "demo_adapter"),
        "cobb_angle": float(payload.get("cobb_angle", 0.0) or 0.0),
        "confidence": float(payload.get("confidence", 0.0) or 0.0),
        "requires_manual_review": bool(payload.get("requires_manual_review", False)),
    }
