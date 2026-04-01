from __future__ import annotations

import hashlib
import json
from typing import Any

from spine_ultrasound_ui.models import ScanPlan, ScanSegment
from spine_ultrasound_ui.services.planning.plan_validator import PlanValidator
from spine_ultrasound_ui.utils import now_ns


class RescanPatchPlanner:
    version = "rescan_patch_planner_v2"

    def __init__(self, validator: PlanValidator | None = None) -> None:
        self.validator = validator or PlanValidator()

    def build(
        self,
        base_plan: ScanPlan,
        low_quality_segments: list[int],
        *,
        quality_target: float,
        low_quality_windows: list[dict[str, int]] | None = None,
        hotspot_windows: list[dict[str, Any]] | None = None,
    ) -> ScanPlan:
        selected: list[ScanSegment] = []
        window_map: dict[int, tuple[int, int]] = {}
        for window in (low_quality_windows or []) + [
            {
                "segment_id": item.get("segment_id", 0),
                "start_index": item.get("start_index", 0),
                "end_index": item.get("end_index", item.get("start_index", 0) + 2),
            }
            for item in (hotspot_windows or [])
        ]:
            segment_id = int(window.get("segment_id", 0) or 0)
            if segment_id <= 0:
                continue
            start_idx = max(0, int(window.get("start_index", 0) or 0))
            end_idx = max(start_idx + 1, int(window.get("end_index", start_idx + 1) or (start_idx + 1)))
            window_map[segment_id] = (start_idx, end_idx)
        selected_set = set(low_quality_segments) | set(window_map)
        for segment in base_plan.segments:
            if segment.segment_id not in selected_set:
                continue
            waypoints = list(segment.waypoints)
            if segment.segment_id in window_map:
                start_idx, end_idx = window_map[segment.segment_id]
                waypoints = waypoints[start_idx:end_idx]
            patch_segment = ScanSegment(
                segment_id=segment.segment_id,
                waypoints=waypoints,
                target_pressure=segment.target_pressure,
                scan_direction=segment.scan_direction,
                needs_resample=True,
                estimated_duration_ms=max(1, int(segment.estimated_duration_ms * max(len(waypoints), 1) / max(len(segment.waypoints), 1))),
                requires_contact_probe=True,
                segment_priority=segment.segment_priority,
                rescan_origin_segment=segment.segment_id,
                quality_target=max(quality_target, segment.quality_target),
                coverage_target=segment.coverage_target,
            )
            patch_segment.segment_hash = hashlib.sha256(json.dumps(patch_segment.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            selected.append(patch_segment)
        patch = ScanPlan(
            session_id=base_plan.session_id,
            plan_id=f"{base_plan.plan_id}_RESCAN",
            approach_pose=base_plan.approach_pose,
            retreat_pose=base_plan.retreat_pose,
            segments=selected,
            planner_version=self.version,
            registration_hash=base_plan.registration_hash,
            plan_kind="rescan_patch",
            created_ts_ns=now_ns(),
        )
        patch.validation_summary = self.validator.validate(patch)
        return patch
