from __future__ import annotations

from typing import Any


def runtime_scan_plan_payload(plan: Any | None) -> dict[str, Any] | None:
    """Return the canonical runtime contract payload for a scan plan.

    The runtime contract requires a stable `plan_hash`, but the application-side
    ScanPlan dataclass intentionally keeps hashes as derived values instead of
    serializing them by default. This helper materializes the contract shape
    once so Desktop, API, and headless flows all send the same payload.
    """
    if plan is None:
        return None
    if hasattr(plan, 'to_dict'):
        payload = dict(plan.to_dict())
        plan_hash = getattr(plan, 'plan_hash', None)
        if callable(plan_hash):
            try:
                payload.setdefault('plan_hash', str(plan_hash()))
            except Exception:
                pass
        return payload
    payload = dict(plan or {})
    if 'plan_hash' not in payload and 'scan_plan_hash' in payload:
        payload['plan_hash'] = payload['scan_plan_hash']
    return payload
