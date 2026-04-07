from pathlib import Path
import json

from spine_ultrasound_ui.services.pressure_analysis_service import PressureAnalysisService


def test_pressure_analysis_reports_admittance_metrics(tmp_path: Path):
    session = tmp_path / "s1"
    (session / "meta").mkdir(parents=True)
    (session / "raw" / "pressure").mkdir(parents=True)
    manifest = {
        "session_id": "s1",
        "config_snapshot": {"pressure_target": 8.0, "pressure_lower": 6.0, "pressure_upper": 12.0},
        "safety_thresholds": {"stale_telemetry_ms": 250},
    }
    (session / "meta" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rows = [
        {"seq": 1, "source_ts_ns": 1_000_000, "data": {"pressure_current": 8.5, "desired_force_n": 8.0, "force_source": "pressure", "estimated_normal_force_n": 8.3, "admittance_saturated": False, "orientation_trim_saturated": False}},
        {"seq": 2, "source_ts_ns": 3_000_000, "data": {"pressure_current": 7.8, "desired_force_n": 8.0, "force_source": "fused", "estimated_normal_force_n": 7.9, "admittance_saturated": True, "orientation_trim_saturated": True}},
    ]
    (session / "raw" / "pressure" / "samples.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    analysis = PressureAnalysisService().build_report(session)
    summary = analysis["summary"]
    assert "force_tracking_rmse" in summary
    assert summary["saturation_ratio"] > 0.0
    assert summary["source_switch_count"] == 1
