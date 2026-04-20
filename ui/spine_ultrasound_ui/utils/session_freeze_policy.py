from __future__ import annotations

from typing import Any, Dict

EXECUTION_CRITICAL_FREEZE_FIELDS = (
    "device_roster",
    "safety_thresholds",
    "device_health_snapshot",
)

EVIDENCE_ONLY_FREEZE_FIELDS = (
    "software_version",
    "build_id",
    "force_sensor_provider",
    "protocol_version",
)

DEFAULT_STRICT_RUNTIME_FREEZE_GATE = "enforce"


def normalize_strict_runtime_freeze_gate(value: str | None) -> str:
    normalized = str(value or DEFAULT_STRICT_RUNTIME_FREEZE_GATE).strip().lower()
    if normalized in {"off", "warn", "enforce"}:
        return normalized
    return DEFAULT_STRICT_RUNTIME_FREEZE_GATE


def build_session_freeze_policy(
    strict_runtime_freeze_gate: str | None,
    *,
    recheck_on_start_procedure: bool = True,
) -> Dict[str, Any]:
    return {
        "strict_runtime_freeze_gate": normalize_strict_runtime_freeze_gate(strict_runtime_freeze_gate),
        "execution_critical_fields": list(EXECUTION_CRITICAL_FREEZE_FIELDS),
        "evidence_only_fields": list(EVIDENCE_ONLY_FREEZE_FIELDS),
        "recheck_on_start_procedure": bool(recheck_on_start_procedure),
    }
