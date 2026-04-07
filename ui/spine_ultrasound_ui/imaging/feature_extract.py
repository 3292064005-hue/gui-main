from __future__ import annotations

from typing import Any

import numpy as np


def run_feature_extract(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and "edge_energy" in data:
        edge_energy = np.asarray(data["edge_energy"], dtype=np.float32)
    else:
        edge_energy = np.asarray(data if data is not None else [], dtype=np.float32)
    if edge_energy.size == 0:
        return {"keypoints": [], "confidence": 0.0, "feature_count": 0}

    threshold = float(edge_energy.mean() + edge_energy.std())
    candidate_indices = np.argwhere(edge_energy >= threshold)
    if candidate_indices.size == 0:
        return {"keypoints": [], "confidence": 0.0, "feature_count": 0}

    ranked = sorted(
        (
            {
                "row": int(row),
                "col": int(col),
                "strength": round(float(edge_energy[row, col]), 6),
            }
            for row, col in candidate_indices
        ),
        key=lambda item: item["strength"],
        reverse=True,
    )
    top_keypoints = ranked[:64]
    max_strength = max((item["strength"] for item in top_keypoints), default=0.0)
    confidence = 0.0 if max_strength <= 0 else min(1.0, max_strength / (threshold + 1e-6))
    return {
        "keypoints": top_keypoints,
        "confidence": round(float(confidence), 6),
        "feature_count": len(top_keypoints),
    }
