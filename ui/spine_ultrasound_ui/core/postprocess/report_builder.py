from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.utils import now_text


def build_session_report(service, session_dir: Path) -> Path:
    manifest = service.exp_manager.load_manifest(session_dir)
    summary = service._read_json(session_dir / "export" / "summary.json")
    quality_timeline = service._read_json(session_dir / "derived/quality/quality_timeline.json")
    replay_index = service._read_json(session_dir / "replay/replay_index.json")
    alarms = service._read_json(session_dir / "derived/alarms/alarm_timeline.json")
    sync_index = service._read_json(session_dir / "derived/sync/frame_sync_index.json")
    pressure_timeline = service._read_json(session_dir / "derived/pressure/pressure_sensor_timeline.json")
    ultrasound_metrics = service._read_json(session_dir / "derived/ultrasound/ultrasound_frame_metrics.json")
    pressure_analysis = service._read_json(session_dir / "export/pressure_analysis.json")
    ultrasound_analysis = service._read_json(session_dir / "export/ultrasound_analysis.json")
    reconstruction_summary = service._read_json(session_dir / "derived" / "reconstruction" / "reconstruction_summary.json")
    assessment_summary = service._read_json(session_dir / "derived" / "assessment" / "assessment_summary.json")
    cobb_resolution = service.authoritative_artifact_reader.read_cobb_measurement(session_dir)
    cobb_measurement = dict(cobb_resolution.get("effective_payload", {}))
    uca_measurement = service._read_json(session_dir / "derived" / "assessment" / "uca_measurement.json")
    assessment_agreement = service._read_json(session_dir / "derived" / "assessment" / "assessment_agreement.json")
    journal_entries = service._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
    annotations = service._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
    payload = {
        "generated_at": now_text(),
        "experiment_id": manifest["experiment_id"],
        "session_id": manifest["session_id"],
        "session_overview": {"core_state": summary.get("core_state", "UNKNOWN"), "software_version": manifest.get("software_version", ""), "build_id": manifest.get("build_id", ""), "force_sensor_provider": manifest.get("force_sensor_provider", ""), "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""), "sdk_robot_class": manifest.get("robot_profile", {}).get("sdk_robot_class", ""), "axis_count": manifest.get("robot_profile", {}).get("axis_count", 0)},
        "workflow_trace": {**summary.get("workflow", {}), "patient_registration": manifest.get("patient_registration", {}), "scan_protocol": manifest.get("scan_protocol", {})},
        "safety_summary": {**summary.get("safety", {}), "alarms": alarms.get("summary", {}), "safety_thresholds": manifest.get("safety_thresholds", {}), "contact_force_policy": manifest.get("robot_profile", {}).get("clinical_scan_contract", {}).get("contact_force_policy", {})},
        "recording": summary.get("recording", {}),
        "quality_summary": {**quality_timeline.get("summary", {}), "annotation_count": len(annotations), "usable_sync_ratio": sync_index.get("summary", {}).get("usable_ratio", 0.0)},
        "ultrasound_summary": {**ultrasound_metrics.get("summary", {}), "analysis": ultrasound_analysis.get("summary", {})},
        "pressure_summary": {**pressure_timeline.get("summary", {}), "analysis": pressure_analysis.get("summary", {})},
        "operator_actions": {"command_count": len(journal_entries), "latest_command": journal_entries[-1].get("data", {}).get("command", "") if journal_entries else "", "annotation_count": len(annotations)},
        "closure": {"runtime_profile": reconstruction_summary.get("runtime_profile", assessment_summary.get("runtime_profile", "weighted_runtime")), "profile_release_state": reconstruction_summary.get("profile_release_state", assessment_summary.get("profile_release_state", "research_validated")), "closure_mode": reconstruction_summary.get("closure_mode", assessment_summary.get("closure_mode", "runtime_optional")), "profile_config_path": reconstruction_summary.get("profile_config_path", assessment_summary.get("profile_config_path", "")), "profile_load_error": reconstruction_summary.get("profile_load_error", assessment_summary.get("profile_load_error", "")), "closure_verdict": assessment_summary.get("closure_verdict", reconstruction_summary.get("closure_verdict", "blocked")), "provenance_purity": assessment_summary.get("provenance_purity", reconstruction_summary.get("provenance_purity", "blocked")), "source_contamination_flags": assessment_summary.get("source_contamination_flags", reconstruction_summary.get("source_contamination_flags", [])), "hard_blockers": assessment_summary.get("hard_blockers", reconstruction_summary.get("hard_blockers", [])), "soft_review_reasons": assessment_summary.get("soft_review_reasons", reconstruction_summary.get("soft_review_reasons", []))},
        "reconstruction_summary": reconstruction_summary,
        "assessment_summary": assessment_summary,
        "cobb_measurement": cobb_measurement,
        "uca_measurement": uca_measurement,
        "assessment_agreement": assessment_agreement,
        "devices": {**manifest.get("device_health_snapshot", {}), "device_readiness": manifest.get("device_readiness", {}), "robot_profile": manifest.get("robot_profile", {})},
        "outputs": manifest.get("artifact_registry", {}),
        "replay": {"camera_frames": replay_index.get("streams", {}).get("camera", {}).get("frame_count", 0), "ultrasound_frames": replay_index.get("streams", {}).get("ultrasound", {}).get("frame_count", 0), "synced_frames": sync_index.get("summary", {}).get("frame_count", 0), "timeline_points": len(replay_index.get("timeline", [])), "pressure_samples": pressure_timeline.get("summary", {}).get("sample_count", 0), "ultrasound_metric_frames": ultrasound_metrics.get("summary", {}).get("frame_count", 0)},
        "algorithm_versions": {plugin.stage: plugin.plugin_version for plugin in service.plugins.all_plugins()},
        "open_issues": [],
    }
    return service.exp_manager.save_json_artifact(session_dir, "export/session_report.json", payload)


def build_session_compare(service, session_dir: Path) -> Path:
    payload = service.analytics.compare_session(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "export/session_compare.json", payload)


def build_session_trends(service, session_dir: Path) -> Path:
    payload = service.analytics.trend_summary(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "export/session_trends.json", payload)


def build_diagnostics_pack(service, session_dir: Path) -> Path:
    payload = service.diagnostics_service.build(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "export/diagnostics_pack.json", payload)


def build_qa_pack(service, session_dir: Path) -> Path:
    payload = service.qa_pack_service.build(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "export/qa_pack.json", payload)
