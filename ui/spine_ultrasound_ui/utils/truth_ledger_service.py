from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def _payload_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _build_hash_material(*, build_id: str, profile: Dict[str, Any], protocol_version: int, runtime_config: Dict[str, Any], robot_family_descriptor: Dict[str, Any], scan_plan_hash: str) -> Dict[str, Any]:
    return {
        "build_id": str(build_id),
        "profile": dict(profile),
        "protocol_version": int(protocol_version),
        "runtime_config_contract": dict(runtime_config.get("runtime_config_contract") or {}),
        "robot_family_descriptor": dict(robot_family_descriptor),
        "scan_plan_hash": str(scan_plan_hash),
        "software_version": str(runtime_config.get("software_version", "")),
    }


def build_repo_truth_ledger(
    *,
    session_id: str,
    session_dir: str,
    profile: Dict[str, Any],
    build_id: str,
    protocol_version: int,
    scan_plan_hash: str,
    runtime_config: Dict[str, Any],
    robot_family_descriptor: Dict[str, Any],
) -> Dict[str, Any]:
    contract = dict(runtime_config.get("runtime_config_contract") or {})
    build_hash_material = _build_hash_material(
        build_id=build_id,
        profile=profile,
        protocol_version=protocol_version,
        runtime_config=runtime_config,
        robot_family_descriptor=robot_family_descriptor,
        scan_plan_hash=scan_plan_hash,
    )
    ledger = {
        "ledger_kind": "repo_truth_ledger",
        "session_id": session_id,
        "session_dir": session_dir,
        "profile": dict(profile),
        "build_id": build_id,
        "build_hash_material": build_hash_material,
        "build_hash": _payload_hash(build_hash_material),
        "protocol_version": int(protocol_version),
        "scan_plan_hash": scan_plan_hash,
        "runtime_config": dict(runtime_config),
        "runtime_config_contract": contract,
        "runtime_config_digest": str(contract.get("digest", "")),
        "runtime_config_schema_version": str(contract.get("schema_version", "")),
        "robot_family_descriptor": dict(robot_family_descriptor),
        "sdk_model_switches": {
            "robot_model": str(robot_family_descriptor.get("robot_model", "")),
            "sdk_robot_class": str(robot_family_descriptor.get("sdk_robot_class", "")),
            "axis_count": int(robot_family_descriptor.get("axis_count", 0) or 0),
            "preferred_link": str(robot_family_descriptor.get("preferred_link", "")),
            "clinical_rt_mode": str(robot_family_descriptor.get("clinical_rt_mode", "")),
        },
        "verification_scope": {
            "repo_contract_parity": True,
            "protocol_sync": True,
            "architecture_fitness": True,
            "runtime_config_contract": bool(contract),
        },
    }
    ledger["ledger_hash"] = _payload_hash(ledger)
    return ledger


def build_live_truth_ledger(
    *,
    session_id: str,
    session_dir: str,
    build_id: str,
    profile: Dict[str, Any],
    robot_family_descriptor: Dict[str, Any],
) -> Dict[str, Any]:
    ledger = {
        "ledger_kind": "live_truth_ledger",
        "session_id": session_id,
        "session_dir": session_dir,
        "build_id": build_id,
        "profile": dict(profile),
        "robot_family_descriptor": dict(robot_family_descriptor),
        "status": "pending_live_validation",
        "evidence_status": "pending_artifact_materialization",
        "required_evidence": [
            "controller_log_summary",
            "phase_transition_trace",
            "rt_jitter_or_packet_loss_snapshot",
            "final_verdict_trace",
        ],
        "phase_transition_trace": {"available": False, "events": []},
        "controller_log_summary": {"available": False, "log_path": "", "last_transition": "", "last_event": ""},
        "rt_jitter_or_packet_loss_snapshot": {"available": False, "packet_loss_percent": None, "jitter_ms_p95": None, "rt_quality_gate_passed": None},
        "final_verdict_trace": {"available": False, "accepted": None, "authoritative": None, "reason": "", "source": ""},
        "latest_observation": {},
        "artifact_backfill": {"available": False, "sources": []},
    }
    ledger["ledger_hash"] = _payload_hash(ledger)
    return ledger


def refresh_live_truth_ledger_from_artifacts(session_dir: Path, existing: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base = dict(existing or {})
    meta = session_dir / "meta"
    export = session_dir / "export"
    derived = session_dir / "derived"

    def _read(rel: str) -> Dict[str, Any]:
        path = session_dir / rel
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    release_gate = _read("export/release_gate_decision.json")
    control_plane = _read("derived/session/control_plane_snapshot.json")
    release_evidence = _read("export/release_evidence_pack.json")
    alarm_timeline = _read("derived/alarms/alarm_timeline.json")
    evidence_sources: list[str] = []

    phase_events = list(control_plane.get("phase_history", []) or release_evidence.get("phase_history", []) or [])
    if phase_events:
        evidence_sources.append("phase_history")
    controller_log = dict(release_evidence.get("controller_log_summary", {}) or {})
    if controller_log.get("log_path") or controller_log.get("last_event"):
        evidence_sources.append("controller_log_summary")
    rt_metrics = dict(release_evidence.get("rt_metrics", {}) or control_plane.get("rt_metrics", {}) or {})
    if rt_metrics:
        evidence_sources.append("rt_metrics")
    final_verdict = dict(release_gate.get("final_verdict_trace", {}) or {})
    if not final_verdict and release_gate:
        final_verdict = {
            "accepted": bool(release_gate.get("allowed", False)),
            "authoritative": bool(release_gate.get("authoritative", False)),
            "reason": str(release_gate.get("reason", "")),
            "source": "release_gate_decision",
        }
    if final_verdict:
        evidence_sources.append("final_verdict")

    ledger = build_live_truth_ledger(
        session_id=str(base.get("session_id", session_dir.name)),
        session_dir=str(base.get("session_dir", session_dir)),
        build_id=str(base.get("build_id", "")),
        profile=dict(base.get("profile", {})),
        robot_family_descriptor=dict(base.get("robot_family_descriptor", {})),
    )
    ledger.update({k: v for k, v in base.items() if k not in {"ledger_hash"}})
    ledger["phase_transition_trace"] = {
        "available": bool(phase_events),
        "events": phase_events,
    }
    latest_alarm = (alarm_timeline.get("events") or [{}])[-1] if alarm_timeline.get("events") else {}
    ledger["controller_log_summary"] = {
        "available": bool(controller_log),
        "log_path": str(controller_log.get("log_path", "")),
        "last_transition": str(controller_log.get("last_transition", "")),
        "last_event": str(controller_log.get("last_event", latest_alarm.get("message", ""))),
    }
    ledger["rt_jitter_or_packet_loss_snapshot"] = {
        "available": bool(rt_metrics),
        "packet_loss_percent": rt_metrics.get("packet_loss_percent"),
        "jitter_ms_p95": rt_metrics.get("jitter_ms_p95"),
        "rt_quality_gate_passed": rt_metrics.get("rt_quality_gate_passed"),
    }
    ledger["final_verdict_trace"] = {
        "available": bool(final_verdict),
        "accepted": final_verdict.get("accepted"),
        "authoritative": final_verdict.get("authoritative"),
        "reason": str(final_verdict.get("reason", "")),
        "source": str(final_verdict.get("source", "")),
    }
    ledger["artifact_backfill"] = {
        "available": bool(evidence_sources),
        "sources": evidence_sources,
    }
    all_available = all(bool(dict(ledger.get(name, {})).get("available", False)) for name in ledger.get("required_evidence", []))
    ledger["evidence_status"] = "artifact_backfilled" if evidence_sources else "pending_artifact_materialization"
    ledger["status"] = "live_validation_materialized" if all_available else "pending_live_validation"
    ledger["latest_observation"] = {
        "release_gate_path": str(export / "release_gate_decision.json") if release_gate else "",
        "control_plane_snapshot_path": str(derived / "session" / "control_plane_snapshot.json") if control_plane else "",
        "release_evidence_pack_path": str(export / "release_evidence_pack.json") if release_evidence else "",
    }
    ledger["ledger_hash"] = _payload_hash({k: v for k, v in ledger.items() if k != "ledger_hash"})
    return ledger
