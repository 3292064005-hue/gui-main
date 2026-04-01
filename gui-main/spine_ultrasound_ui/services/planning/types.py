from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from spine_ultrasound_ui.models import CapabilityStatus


@dataclass
class LocalizationResult:
    status: CapabilityStatus
    roi_center_y: float = 0.0
    segment_count: int = 0
    patient_registration: dict[str, Any] = field(default_factory=dict)
    registration_version: str = "camera_backed_registration_v2"
    confidence: float = 0.0

    def registration_hash(self) -> str:
        payload = json.dumps(self.patient_registration, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest() if payload else ""


def hash_payload(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest() if blob else ""
