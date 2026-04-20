from __future__ import annotations

"""Runtime-owned control-authority proxy for the headless control plane.

This service deliberately does *not* own any lease state. It forwards lease
mutations to the runtime, snapshots runtime-published authority envelopes, and
only injects normalized command context for write/plan-compile requests.
Python/headless layers remain requesters and projections; the C++ runtime is the
single source of truth for control ownership.
"""

from dataclasses import dataclass
from typing import Any, Callable

from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.services.runtime_command_catalog import command_capability_claim


@dataclass(frozen=True)
class RuntimeAuthorityProxySettings:
    strict_mode: bool
    auto_issue_implicit_lease: bool
    lease_ttl_s: int


class RuntimeAuthorityProxyService:
    """Proxy runtime-owned control authority into the Python/headless surface.

    Args:
        dispatch: Callable used to dispatch canonical runtime commands.
        deployment_profile_snapshot: Callable returning the active deployment profile.
        current_session_id: Callable returning the active session id.
        strict_mode: Whether strict authority is requested by deployment policy.
        auto_issue_implicit_lease: Whether the runtime may auto-issue a first lease.
        lease_ttl_s: Preferred lease TTL advertised to UI/API callers.

    Boundary behavior:
        - This service never becomes the owner of a lease.
        - ``guard_command`` only normalizes command context; final acceptance or
          rejection is decided by the runtime.
        - Snapshot failures are surfaced as degraded runtime-owned authority
          payloads instead of fabricating local lease state.
    """

    def __init__(
        self,
        *,
        dispatch: Callable[[str, dict[str, Any]], ReplyEnvelope],
        deployment_profile_snapshot: Callable[[], dict[str, Any]],
        current_session_id: Callable[[], str],
        strict_mode: bool,
        auto_issue_implicit_lease: bool,
        lease_ttl_s: int = 180,
    ) -> None:
        self._dispatch = dispatch
        self._deployment_profile_snapshot = deployment_profile_snapshot
        self._current_session_id = current_session_id
        self.strict_mode = bool(strict_mode)
        self.auto_issue_implicit_lease = bool(auto_issue_implicit_lease)
        self.lease_ttl_s = max(30, int(lease_ttl_s))

    def acquire(self, **kwargs: Any) -> dict[str, Any]:
        payload = self._lease_payload(kwargs)
        reply = self._dispatch_reply("acquire_control_lease", payload)
        return self._flatten_lease_reply(reply, fallback_label="控制权租约获取失败")

    def renew(self, **kwargs: Any) -> dict[str, Any]:
        payload = self._lease_payload(kwargs)
        reply = self._dispatch_reply("renew_control_lease", payload)
        return self._flatten_lease_reply(reply, fallback_label="控制权租约续租失败")

    def release(self, **kwargs: Any) -> dict[str, Any]:
        payload = self._lease_payload(kwargs)
        reply = self._dispatch_reply("release_control_lease", payload)
        return self._flatten_lease_reply(reply, fallback_label="控制权租约释放失败")

    def bind_session(self, session_id: str) -> None:
        del session_id

    def clear_session_binding(self) -> None:
        return None

    def guard_command(
        self,
        command: str,
        payload: dict[str, Any] | None,
        *,
        current_session_id: str = "",
        source: str = "headless",
        require_lease: bool = True,
    ) -> dict[str, Any]:
        normalized_payload = dict(payload or {})
        context = dict(normalized_payload.get("_command_context", {}))
        profile = self._deployment_profile_snapshot() if callable(self._deployment_profile_snapshot) else {}
        required_claim = str(command_capability_claim(command) or "").strip()
        current_authority = self.snapshot(required_claim=required_claim)
        normalized_payload["_command_context"] = {
            **context,
            "actor_id": str(context.get("actor_id") or "implicit-operator"),
            "role": str(context.get("role") or "operator").strip().lower() or "operator",
            "workspace": str(context.get("workspace") or "desktop").strip().lower() or "desktop",
            "profile": str(context.get("profile") or context.get("deployment_profile") or profile.get("name") or "dev").strip().lower() or "dev",
            "intent_reason": str(context.get("intent_reason") or command),
            "session_id": str(context.get("session_id") or normalized_payload.get("session_id") or current_session_id or self._current_session_id() or ""),
            "lease_id": str(context.get("lease_id") or ""),
            "source": str(context.get("source") or source),
            "required_claim": required_claim,
            "lease_required": bool(require_lease),
            "auto_issue_implicit_lease": self.auto_issue_implicit_lease,
        }
        return {
            "allowed": True,
            "message": "runtime authority pending validation",
            "normalized_payload": normalized_payload,
            "authority": current_authority,
        }

    def snapshot(self, *, required_claim: str = "") -> dict[str, Any]:
        reply = self._dispatch_reply("get_authoritative_runtime_envelope", {"reason": "control_authority_snapshot"})
        if reply.ok:
            payload = dict(reply.data or {})
            authority = dict(payload.get("control_authority") or {})
            if authority:
                if required_claim and "required_claim" not in authority:
                    authority = {**authority, "required_claim": required_claim}
                return authority
        detail = str(reply.message or "runtime authoritative envelope unavailable")
        return {
            "summary_state": "degraded" if not self.strict_mode else "blocked",
            "summary_label": "运行时控制权快照不可用",
            "detail": detail,
            "strict_mode": self.strict_mode,
            "auto_issue_implicit_lease": self.auto_issue_implicit_lease,
            "lease_ttl_s": self.lease_ttl_s,
            "required_claim": required_claim,
            "owner": {},
            "active_lease": {},
            "owner_provenance": {"source": "cpp_robot_core"},
            "workspace_binding": "",
            "session_binding": "",
            "conflict_reason": detail,
            "blockers": [],
            "warnings": [{"name": "runtime_authority_unavailable", "detail": detail}],
        }

    def _dispatch_reply(self, command: str, payload: dict[str, Any]) -> ReplyEnvelope:
        try:
            return self._dispatch(command, payload)
        except Exception as exc:  # pragma: no cover - defensive transport compatibility
            return ReplyEnvelope(ok=False, message=str(exc), data={})

    def _lease_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = self._deployment_profile_snapshot() if callable(self._deployment_profile_snapshot) else {}
        return {
            "actor_id": str(payload.get("actor_id") or "implicit-operator"),
            "role": str(payload.get("role") or "operator").strip().lower() or "operator",
            "workspace": str(payload.get("workspace") or "desktop").strip().lower() or "desktop",
            "session_id": str(payload.get("session_id") or self._current_session_id() or ""),
            "intent_reason": str(payload.get("intent_reason") or "runtime_control_authority"),
            "profile": str(payload.get("profile") or payload.get("deployment_profile") or profile.get("name") or "dev").strip().lower() or "dev",
            "ttl_s": int(payload.get("ttl_s") or self.lease_ttl_s),
            "source": str(payload.get("source") or "headless_api"),
            "lease_id": str(payload.get("lease_id") or ""),
            "preempt": bool(payload.get("preempt", False)),
            "preempt_reason": str(payload.get("preempt_reason") or ""),
            "requested_claims": list(payload.get("requested_claims") or payload.get("claims") or []),
            "reason": str(payload.get("reason") or ""),
        }

    @staticmethod
    def _flatten_lease_reply(reply: ReplyEnvelope, *, fallback_label: str) -> dict[str, Any]:
        data = dict(reply.data or {})
        flattened = {
            "ok": bool(reply.ok),
            "summary_state": str(data.get("summary_state") or ("ready" if reply.ok else "blocked")),
            "summary_label": str(data.get("summary_label") or fallback_label),
            "detail": str(data.get("detail") or reply.message or ""),
        }
        for key in ("lease", "active_lease", "control_authority", "conflict_reason", "owner", "warnings", "blockers"):
            if key in data:
                flattened[key] = data[key]
        return flattened
