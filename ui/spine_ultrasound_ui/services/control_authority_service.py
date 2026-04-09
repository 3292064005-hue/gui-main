from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Iterable

from spine_ultrasound_ui.services.role_matrix import RoleMatrix
from spine_ultrasound_ui.services.runtime_command_catalog import command_capability_claim
from spine_ultrasound_ui.utils import now_ns, now_text


DEFAULT_ACTOR_ID = "implicit-operator"
DEFAULT_WORKSPACE = "desktop"
DEFAULT_ROLE = "operator"
DEFAULT_PROFILE = "dev"
DEFAULT_INTENT = "runtime_command"
ROLE_PRIORITY = {
    "service": 100,
    "operator": 80,
    "qa": 60,
    "researcher": 50,
    "review": 10,
}


@dataclass
class ControlLease:
    """Canonical single-owner control lease.

    The lease now carries explicit capability claims so write surfaces can
    reason about *what* the current owner is allowed to do, not only *who* the
    owner is.
    """

    lease_id: str
    actor_id: str
    role: str
    workspace: str
    session_id: str = ""
    intent_reason: str = ""
    deployment_profile: str = DEFAULT_PROFILE
    acquired_ts_ns: int = 0
    refreshed_ts_ns: int = 0
    expires_ts_ns: int = 0
    source: str = "headless"
    granted_claims: list[str] = field(default_factory=list)

    def to_dict(self, *, now_ts_ns: int | None = None) -> dict[str, Any]:
        current_ts_ns = int(now_ts_ns or now_ns())
        expires_in_s = max(0.0, (self.expires_ts_ns - current_ts_ns) / 1_000_000_000)
        return {
            "lease_id": self.lease_id,
            "actor_id": self.actor_id,
            "role": self.role,
            "workspace": self.workspace,
            "session_id": self.session_id,
            "intent_reason": self.intent_reason,
            "deployment_profile": self.deployment_profile,
            "acquired_ts_ns": self.acquired_ts_ns,
            "refreshed_ts_ns": self.refreshed_ts_ns,
            "expires_ts_ns": self.expires_ts_ns,
            "expires_in_s": round(expires_in_s, 3),
            "source": self.source,
            "granted_claims": list(self.granted_claims),
        }


class ControlAuthorityService:
    """Single write-source lease with explicit capability-claim governance.

    All mutations are linearized behind an internal re-entrant lock so that
    lease acquire/renew/release, session binding, command guarding, and claim
    escalation observe a consistent ownership snapshot.
    """

    def __init__(
        self,
        *,
        lease_ttl_s: int = 180,
        auto_issue_implicit_lease: bool = True,
        strict_mode: bool = False,
        role_matrix: RoleMatrix | None = None,
    ) -> None:
        self.lease_ttl_s = max(30, int(lease_ttl_s))
        self.auto_issue_implicit_lease = bool(auto_issue_implicit_lease)
        self.strict_mode = bool(strict_mode)
        self._role_matrix = role_matrix or RoleMatrix()
        self._active_lease: ControlLease | None = None
        self._events: list[dict[str, Any]] = []
        self._last_conflict_reason = ""
        self._lock = RLock()

    def acquire(
        self,
        *,
        actor_id: str,
        role: str,
        workspace: str,
        session_id: str = "",
        intent_reason: str = "",
        deployment_profile: str = DEFAULT_PROFILE,
        ttl_s: int | None = None,
        source: str = "api",
        preempt: bool = False,
        preempt_reason: str = "",
        requested_claims: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Acquire or refresh the active control lease.

        Args:
            actor_id: Logical issuer identity.
            role: Role used for conflict resolution.
            workspace: Issuer workspace name.
            session_id: Optional bound session identifier.
            intent_reason: Human-readable lease purpose.
            deployment_profile: Deployment profile provenance.
            ttl_s: Optional lease TTL override.
            source: Surface that issued the request.
            preempt: Whether preemption is explicitly requested.
            preempt_reason: User-facing rationale for a preemption attempt.
            requested_claims: Capability claims requested for the lease.

        Returns:
            Lease acquisition result with a normalized authority snapshot.

        Raises:
            No exceptions are raised.

        Boundary behavior:
            Conflicting owners are rejected unless preemption is explicitly
            requested and the caller outranks the active lease owner. Unknown or
            unauthorized capability claims are rejected before the lease is
            granted.
        """
        with self._lock:
            actor = self._normalize_actor(actor_id)
            normalized_role = self._normalize_role(role)
            normalized_workspace = self._normalize_workspace(workspace)
            normalized_profile = self._normalize_profile(deployment_profile)
            normalized_claims = self._normalize_claims(requested_claims)
            unauthorized = [claim for claim in normalized_claims if not self._role_matrix.can_claim(normalized_role, claim)]
            if unauthorized:
                detail = f"角色 {normalized_role} 无权申请 capability claims: {', '.join(unauthorized)}"
                self._record_event_unlocked("lease_claim_rejected", actor, normalized_workspace, normalized_role, session_id, detail)
                return {
                    "ok": False,
                    "summary_state": "blocked",
                    "summary_label": "控制权 claim 被拒绝",
                    "detail": detail,
                    "conflict_reason": detail,
                }
            ttl = max(30, int(ttl_s or self.lease_ttl_s))
            now_ts = now_ns()
            active = self._get_active_lease_unlocked(now_ts)
            same_owner = active is not None and self._same_owner(active, actor, normalized_workspace, normalized_role)
            if active and not same_owner:
                if preempt and self._can_preempt(active, actor, normalized_role):
                    detail = (
                        f"{actor}@{normalized_workspace}/{normalized_role} 抢占 "
                        f"{active.actor_id}@{active.workspace}/{active.role}: {preempt_reason or 'explicit_preempt'}"
                    )
                    self._record_event_unlocked("lease_preempted", actor, normalized_workspace, normalized_role, session_id, detail)
                else:
                    detail = self._conflict_detail(active, actor, normalized_workspace, normalized_role)
                    self._last_conflict_reason = detail
                    self._record_event_unlocked("lease_conflict", actor, normalized_workspace, normalized_role, session_id, detail)
                    return {
                        "ok": False,
                        "summary_state": "blocked",
                        "summary_label": "控制权冲突",
                        "detail": detail,
                        "conflict_reason": detail,
                        "active_lease": active.to_dict(now_ts_ns=now_ts),
                    }
            merged_claims = list(normalized_claims)
            if same_owner and active is not None:
                merged_claims = sorted(set(active.granted_claims) | set(normalized_claims))
            lease_id = active.lease_id if same_owner and active is not None else self._make_lease_id(actor, normalized_workspace, normalized_role, session_id)
            self._active_lease = ControlLease(
                lease_id=lease_id,
                actor_id=actor,
                role=normalized_role,
                workspace=normalized_workspace,
                session_id=str(session_id or (active.session_id if active else "")),
                intent_reason=str(intent_reason or (active.intent_reason if active else "")),
                deployment_profile=normalized_profile,
                acquired_ts_ns=active.acquired_ts_ns if same_owner and active is not None else now_ts,
                refreshed_ts_ns=now_ts,
                expires_ts_ns=now_ts + ttl * 1_000_000_000,
                source=source,
                granted_claims=merged_claims,
            )
            self._last_conflict_reason = ""
            event_name = "lease_acquired" if not same_owner else "lease_refreshed"
            self._record_event_unlocked(event_name, actor, normalized_workspace, normalized_role, session_id, self._active_lease.lease_id)
            return {
                "ok": True,
                "summary_state": "ready",
                "summary_label": "控制权已授予",
                "detail": f"lease={self._active_lease.lease_id}",
                "lease": self._active_lease.to_dict(now_ts_ns=now_ts),
            }

    def renew(self, *, lease_id: str, actor_id: str | None = None, ttl_s: int | None = None) -> dict[str, Any]:
        """Renew the currently active lease.

        Args:
            lease_id: Lease identifier expected by the caller.
            actor_id: Optional actor identity assertion.
            ttl_s: Optional TTL override.

        Returns:
            Renewal result. Rejected renewals always include the current active
            lease snapshot when one exists.
        """
        with self._lock:
            now_ts = now_ns()
            active = self._get_active_lease_unlocked(now_ts)
            if active is None:
                return {
                    "ok": False,
                    "summary_state": "blocked",
                    "summary_label": "续租失败",
                    "detail": "no_active_lease",
                }
            if lease_id != active.lease_id:
                return {
                    "ok": False,
                    "summary_state": "blocked",
                    "summary_label": "续租失败",
                    "detail": f"lease_id 不匹配，active={active.lease_id}",
                    "active_lease": active.to_dict(now_ts_ns=now_ts),
                }
            if actor_id and self._normalize_actor(actor_id) != active.actor_id:
                return {
                    "ok": False,
                    "summary_state": "blocked",
                    "summary_label": "续租失败",
                    "detail": f"actor_id 不匹配，active={active.actor_id}",
                    "active_lease": active.to_dict(now_ts_ns=now_ts),
                }
            ttl = max(30, int(ttl_s or self.lease_ttl_s))
            active.refreshed_ts_ns = now_ts
            active.expires_ts_ns = now_ts + ttl * 1_000_000_000
            self._record_event_unlocked("lease_renewed", active.actor_id, active.workspace, active.role, active.session_id, active.lease_id)
            return {
                "ok": True,
                "summary_state": "ready",
                "summary_label": "控制权已续租",
                "detail": active.lease_id,
                "lease": active.to_dict(now_ts_ns=now_ts),
            }

    def release(self, *, lease_id: str | None = None, actor_id: str | None = None, reason: str = "") -> dict[str, Any]:
        """Release the active control lease if the caller matches ownership."""
        with self._lock:
            now_ts = now_ns()
            active = self._get_active_lease_unlocked(now_ts)
            if active is None:
                return {
                    "ok": True,
                    "summary_state": "ready",
                    "summary_label": "当前无控制权租约",
                    "detail": "no_active_lease",
                }
            actor = self._normalize_actor(actor_id) if actor_id else ""
            if lease_id and lease_id != active.lease_id:
                return {
                    "ok": False,
                    "summary_state": "blocked",
                    "summary_label": "租约释放被拒绝",
                    "detail": f"lease_id 不匹配，active={active.lease_id}",
                    "active_lease": active.to_dict(now_ts_ns=now_ts),
                }
            if actor and actor != active.actor_id:
                return {
                    "ok": False,
                    "summary_state": "blocked",
                    "summary_label": "租约释放被拒绝",
                    "detail": f"actor_id 不匹配，active={active.actor_id}",
                    "active_lease": active.to_dict(now_ts_ns=now_ts),
                }
            self._record_event_unlocked("lease_released", active.actor_id, active.workspace, active.role, active.session_id, reason or active.lease_id)
            self._active_lease = None
            self._last_conflict_reason = ""
            return {
                "ok": True,
                "summary_state": "ready",
                "summary_label": "控制权已释放",
                "detail": reason or "released",
            }

    def bind_session(self, session_id: str) -> None:
        """Bind the active lease to a session identifier.

        Boundary behavior:
            No-op when no active lease exists.
        """
        with self._lock:
            if self._active_lease is None:
                return
            self._active_lease.session_id = str(session_id)
            self._active_lease.refreshed_ts_ns = now_ns()
            self._record_event_unlocked(
                "lease_bound_session",
                self._active_lease.actor_id,
                self._active_lease.workspace,
                self._active_lease.role,
                session_id,
                self._active_lease.lease_id,
            )

    def clear_session_binding(self) -> None:
        """Clear the active session binding if a lease exists."""
        with self._lock:
            if self._active_lease is None:
                return
            self._active_lease.session_id = ""
            self._active_lease.refreshed_ts_ns = now_ns()

    def guard_command(
        self,
        command: str,
        payload: dict[str, Any] | None,
        *,
        current_session_id: str = "",
        source: str = "api",
        require_lease: bool = True,
    ) -> dict[str, Any]:
        """Validate command ownership, capability claims, and inject context.

        Args:
            command: Canonical runtime command name.
            payload: Original command payload.
            current_session_id: Active runtime session id if available.
            source: Issuing surface identifier.

        Returns:
            Authorization result containing the normalized payload and an
            authority snapshot.

        Boundary behavior:
            When ``require_lease`` is ``True`` and implicit lease issuance is
            enabled, an empty ownership state can be upgraded into an active
            lease before the command is evaluated. If a command only needs a
            capability contract check (for example a read-contract command that
            still carries a scoped capability claim), callers may pass
            ``require_lease=False`` to validate claims without mutating runtime
            ownership.
        """
        with self._lock:
            normalized_payload = dict(payload or {})
            context = self._extract_context(normalized_payload)
            actor = self._normalize_actor(str(context.get("actor_id", DEFAULT_ACTOR_ID)))
            role = self._normalize_role(str(context.get("role", DEFAULT_ROLE)))
            workspace = self._normalize_workspace(str(context.get("workspace", DEFAULT_WORKSPACE)))
            deployment_profile = self._normalize_profile(
                str(context.get("profile") or context.get("deployment_profile") or normalized_payload.get("profile") or DEFAULT_PROFILE)
            )
            intent = str(context.get("intent") or normalized_payload.get("intent") or DEFAULT_INTENT).strip() or DEFAULT_INTENT
            intent_reason = str(context.get("intent_reason", normalized_payload.get("intent_reason", intent)))
            requested_session_id = str(context.get("session_id") or normalized_payload.get("session_id") or current_session_id or "")
            requested_lease_id = str(context.get("lease_id", "")).strip()
            requested_claims = self._normalize_claims(
                context.get("requested_claims")
                or context.get("claims")
                or normalized_payload.get("requested_claims")
                or normalized_payload.get("claims")
            )
            required_claim = str(command_capability_claim(command)).strip()

            if required_claim and not self._role_matrix.can_claim(role, required_claim):
                detail = f"角色 {role} 无权获取 {required_claim}，命令 {command} 被拒绝"
                self._last_conflict_reason = detail
                self._record_event_unlocked("claim_guard_rejected", actor, workspace, role, requested_session_id, detail)
                return {
                    "allowed": False,
                    "message": detail,
                    "normalized_payload": normalized_payload,
                    "authority": self._snapshot_unlocked(required_claim=required_claim),
                }
            unauthorized_requested = [claim for claim in requested_claims if not self._role_matrix.can_claim(role, claim)]
            if unauthorized_requested:
                detail = f"角色 {role} 无权请求 claims: {', '.join(unauthorized_requested)}"
                self._last_conflict_reason = detail
                self._record_event_unlocked("claim_guard_rejected", actor, workspace, role, requested_session_id, detail)
                return {
                    "allowed": False,
                    "message": detail,
                    "normalized_payload": normalized_payload,
                    "authority": self._snapshot_unlocked(required_claim=required_claim),
                }

            if not require_lease:
                granted_claims = set(requested_claims)
                if required_claim:
                    granted_claims.add(required_claim)
                normalized_payload["_command_context"] = {
                    **context,
                    "actor_id": actor,
                    "role": role,
                    "workspace": workspace,
                    "profile": deployment_profile,
                    "intent": intent,
                    "intent_reason": intent_reason,
                    "session_id": requested_session_id,
                    "lease_id": requested_lease_id,
                    "required_claim": required_claim,
                    "granted_claims": sorted(granted_claims),
                    "source": source,
                    "lease_required": False,
                }
                return {
                    "allowed": True,
                    "message": "capability guard passed",
                    "normalized_payload": normalized_payload,
                    "authority": self._snapshot_unlocked(required_claim=required_claim),
                }

            active = self._get_active_lease_unlocked()
            if active is None and (requested_lease_id or self.auto_issue_implicit_lease or not self.strict_mode):
                bootstrap_claims = set(requested_claims)
                if required_claim:
                    bootstrap_claims.add(required_claim)
                acquire_result = self.acquire(
                    actor_id=actor,
                    role=role,
                    workspace=workspace,
                    session_id=requested_session_id,
                    intent_reason=intent_reason or f"implicit:{command}",
                    deployment_profile=deployment_profile,
                    source=source,
                    requested_claims=sorted(bootstrap_claims),
                )
                if not acquire_result.get("ok", False):
                    return {
                        "allowed": False,
                        "message": str(acquire_result.get("detail", "控制权冲突")),
                        "normalized_payload": normalized_payload,
                        "authority": self._snapshot_unlocked(required_claim=required_claim),
                    }
                active = self._get_active_lease_unlocked()
            elif active is None:
                return {
                    "allowed": False,
                    "message": "当前命令要求显式控制权租约。",
                    "normalized_payload": normalized_payload,
                    "authority": self._snapshot_unlocked(required_claim=required_claim),
                }

            assert active is not None
            if requested_lease_id and requested_lease_id != active.lease_id:
                return {
                    "allowed": False,
                    "message": f"lease_id 不匹配，active={active.lease_id}",
                    "normalized_payload": normalized_payload,
                    "authority": self._snapshot_unlocked(required_claim=required_claim),
                }
            if not self._same_owner(active, actor, workspace, role):
                detail = self._conflict_detail(active, actor, workspace, role)
                self._last_conflict_reason = detail
                return {
                    "allowed": False,
                    "message": detail,
                    "normalized_payload": normalized_payload,
                    "authority": self._snapshot_unlocked(required_claim=required_claim),
                }
            if active.session_id and requested_session_id and active.session_id != requested_session_id:
                detail = f"session 绑定冲突，active={active.session_id}, requested={requested_session_id}"
                self._last_conflict_reason = detail
                return {
                    "allowed": False,
                    "message": detail,
                    "normalized_payload": normalized_payload,
                    "authority": self._snapshot_unlocked(required_claim=required_claim),
                }

            granted_claims = set(active.granted_claims)
            before_claims = set(granted_claims)
            granted_claims.update(requested_claims)
            if required_claim:
                granted_claims.add(required_claim)
            active.granted_claims = sorted(granted_claims)
            if granted_claims != before_claims and required_claim:
                self._record_event_unlocked("claim_granted", active.actor_id, active.workspace, active.role, active.session_id, required_claim)

            active.refreshed_ts_ns = now_ns()
            active.expires_ts_ns = active.refreshed_ts_ns + self.lease_ttl_s * 1_000_000_000
            active.deployment_profile = deployment_profile
            if requested_session_id:
                active.session_id = requested_session_id
            normalized_payload["_command_context"] = {
                "actor_id": active.actor_id,
                "role": active.role,
                "workspace": active.workspace,
                "lease_id": active.lease_id,
                "session_id": active.session_id or requested_session_id,
                "intent": intent,
                "intent_reason": intent_reason,
                "profile": deployment_profile,
                "required_claim": required_claim,
                "granted_claims": list(active.granted_claims),
                "command_uid": self._make_command_uid(command, active.actor_id, active.lease_id),
                "source": source,
                "issued_at": now_text(),
            }
            self._last_conflict_reason = ""
            return {
                "allowed": True,
                "message": "ok",
                "normalized_payload": normalized_payload,
                "authority": self._snapshot_unlocked(required_claim=required_claim),
            }

    def snapshot(self) -> dict[str, Any]:
        """Return an atomic control-authority snapshot."""
        with self._lock:
            return self._snapshot_unlocked()

    def _snapshot_unlocked(self, *, required_claim: str = "") -> dict[str, Any]:
        now_ts = now_ns()
        active = self._get_active_lease_unlocked(now_ts)
        events = [dict(item) for item in self._events[-10:]]
        if active is None:
            summary_state = "ready" if not self.strict_mode else "degraded"
            summary_label = "未持有控制权" if not self.strict_mode else "缺少显式控制权"
            detail = self._last_conflict_reason or "no_active_lease"
            return {
                "summary_state": summary_state,
                "summary_label": summary_label,
                "detail": detail,
                "strict_mode": self.strict_mode,
                "auto_issue_implicit_lease": self.auto_issue_implicit_lease,
                "lease_ttl_s": self.lease_ttl_s,
                "required_claim": required_claim,
                "available_claims_for_default_role": sorted(self._role_matrix.allowed_capability_claims(DEFAULT_ROLE)),
                "has_owner": False,
                "conflict_reason": self._last_conflict_reason,
                "active_lease": {},
                "owner_provenance": {},
                "granted_claims": [],
                "claim_bindings": {},
                "events": events,
            }
        return {
            "summary_state": "ready",
            "summary_label": "控制权已锁定",
            "detail": f"{active.actor_id}@{active.workspace}/{active.role}",
            "strict_mode": self.strict_mode,
            "auto_issue_implicit_lease": self.auto_issue_implicit_lease,
            "lease_ttl_s": self.lease_ttl_s,
            "required_claim": required_claim,
            "available_claims_for_role": sorted(self._role_matrix.allowed_capability_claims(active.role)),
            "has_owner": True,
            "conflict_reason": self._last_conflict_reason,
            "owner": {
                "actor_id": active.actor_id,
                "workspace": active.workspace,
                "role": active.role,
                "session_id": active.session_id,
            },
            "owner_provenance": {
                "source": active.source,
                "intent_reason": active.intent_reason,
                "deployment_profile": active.deployment_profile,
            },
            "workspace_binding": active.workspace,
            "session_binding": active.session_id,
            "active_lease": active.to_dict(now_ts_ns=now_ts),
            "granted_claims": list(active.granted_claims),
            "claim_bindings": {claim: {"lease_id": active.lease_id, "session_id": active.session_id, "owner": active.actor_id} for claim in active.granted_claims},
            "events": events,
        }

    def _get_active_lease(self, now_ts_ns: int | None = None) -> ControlLease | None:
        with self._lock:
            return self._get_active_lease_unlocked(now_ts_ns)

    def _get_active_lease_unlocked(self, now_ts_ns: int | None = None) -> ControlLease | None:
        active = self._active_lease
        if active is None:
            return None
        current_ts = int(now_ts_ns or now_ns())
        if active.expires_ts_ns <= current_ts:
            self._record_event_unlocked("lease_expired", active.actor_id, active.workspace, active.role, active.session_id, active.lease_id)
            self._active_lease = None
            return None
        return active

    @staticmethod
    def _extract_context(payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("_command_context")
        if isinstance(context, dict):
            return dict(context)
        control = payload.get("control")
        if isinstance(control, dict):
            return dict(control)
        return {}

    @staticmethod
    def _same_owner(active: ControlLease, actor_id: str, workspace: str, role: str) -> bool:
        return active.actor_id == actor_id and active.workspace == workspace and active.role == role

    @staticmethod
    def _normalize_actor(actor_id: str) -> str:
        cleaned = str(actor_id or "").strip()
        return cleaned or DEFAULT_ACTOR_ID

    @staticmethod
    def _normalize_workspace(workspace: str) -> str:
        cleaned = str(workspace or "").strip().lower()
        return cleaned or DEFAULT_WORKSPACE

    @staticmethod
    def _normalize_role(role: str) -> str:
        cleaned = str(role or "").strip().lower()
        return cleaned or DEFAULT_ROLE

    @staticmethod
    def _normalize_profile(profile: str) -> str:
        cleaned = str(profile or "").strip().lower()
        return cleaned or DEFAULT_PROFILE

    @staticmethod
    def _normalize_claims(raw_claims: Any) -> list[str]:
        if raw_claims is None:
            return []
        if isinstance(raw_claims, str):
            claims = [item.strip() for item in raw_claims.split(",") if item.strip()]
            return sorted(set(claims))
        if isinstance(raw_claims, Iterable):
            claims = [str(item).strip() for item in raw_claims if str(item).strip()]
            return sorted(set(claims))
        return []

    def _make_lease_id(self, actor_id: str, workspace: str, role: str, session_id: str) -> str:
        raw = json.dumps({
            "actor_id": actor_id,
            "workspace": workspace,
            "role": role,
            "session_id": session_id,
            "ts_ns": now_ns(),
        }, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def _make_command_uid(self, command: str, actor_id: str, lease_id: str) -> str:
        raw = json.dumps({"command": command, "actor_id": actor_id, "lease_id": lease_id, "ts_ns": now_ns()}, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    @staticmethod
    def _can_preempt(active: ControlLease, actor_id: str, role: str) -> bool:
        del actor_id
        return ROLE_PRIORITY.get(role, 0) > ROLE_PRIORITY.get(active.role, 0)

    @staticmethod
    def _conflict_detail(active: ControlLease, actor_id: str, workspace: str, role: str) -> str:
        return (
            f"控制权已被 {active.actor_id}@{active.workspace}/{active.role} 持有，"
            f"当前请求为 {actor_id}@{workspace}/{role}"
        )

    def _record_event_unlocked(self, event: str, actor_id: str, workspace: str, role: str, session_id: str, detail: str) -> None:
        self._events.append({
            "event": event,
            "ts_ns": now_ns(),
            "actor_id": actor_id,
            "workspace": workspace,
            "role": role,
            "session_id": session_id,
            "detail": detail,
        })
        if len(self._events) > 64:
            self._events = self._events[-64:]
