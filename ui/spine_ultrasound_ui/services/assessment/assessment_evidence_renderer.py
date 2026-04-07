from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from spine_ultrasound_ui.utils import ensure_dir


class AssessmentEvidenceRenderer:
    """Render assessment evidence overlays for QA and report consumption."""

    def render(self, assessment_input: dict[str, Any], measurement: dict[str, Any], target: Path) -> Path:
        """Render an overlay image highlighting selected vertebra evidence.

        Args:
            assessment_input: Normalized assessment input payload.
            measurement: Detailed measurement payload.
            target: Output PNG path.

        Returns:
            Written overlay image path.

        Raises:
            ValueError: Raised when the target path has no PNG suffix.

        Boundary behaviour:
            Missing VPI previews degrade to a blank canvas with measurement text
            so the report pipeline remains deterministic.
        """
        if target.suffix.lower() != '.png':
            raise ValueError('assessment overlay target must be a PNG path')
        ensure_dir(target.parent)
        preview_path = Path(str(assessment_input.get('vpi_preview_path', '') or '')) if assessment_input.get('vpi_preview_path') else None
        if preview_path and preview_path.exists():
            image = Image.open(preview_path).convert('RGB')
        else:
            image = Image.fromarray(np.zeros((96, 192, 3), dtype=np.uint8), mode='RGB')
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for candidate_key, color in (('upper_end_vertebra_candidate', (255, 128, 0)), ('lower_end_vertebra_candidate', (0, 255, 160))):
            candidate = dict(measurement.get(candidate_key, {}))
            position = dict(candidate.get('position_mm', {}))
            x_mm = float(position.get('x', 0.0) or 0.0)
            y_mm = float(position.get('y', 0.0) or 0.0)
            x_px = int(np.clip(round((x_mm + 120.0) / 240.0 * max(1, width - 1)), 0, width - 1))
            y_px = int(np.clip(round(y_mm / max(1.0, float(measurement.get('fit_diagnostics', {}).get('point_count', 1))) * max(1, height - 1)), 0, height - 1))
            draw.ellipse((x_px - 4, y_px - 4, x_px + 4, y_px + 4), outline=color, width=2)
        draw.text((8, 8), f"{measurement.get('measurement_source', 'measurement')} angle={measurement.get('angle_deg', 0.0):.2f}°", fill=(255, 255, 255))
        image.save(target)
        return target
