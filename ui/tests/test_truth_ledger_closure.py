import json
from pathlib import Path

from spine_ultrasound_ui.utils.truth_ledger_service import build_live_truth_ledger, build_repo_truth_ledger, refresh_live_truth_ledger_from_artifacts


def test_repo_truth_ledger_uses_real_build_hash() -> None:
    ledger = build_repo_truth_ledger(
        session_id='S',
        session_dir='/tmp/S',
        profile={'name': 'mainline'},
        build_id='build-123',
        protocol_version=3,
        scan_plan_hash='plan-hash',
        runtime_config={'software_version': '0.1', 'runtime_config_contract': {'digest': 'abc', 'schema_version': 'v1'}},
        robot_family_descriptor={'robot_model': 'xmate3', 'sdk_robot_class': 'xMateRobot', 'axis_count': 6, 'preferred_link': 'wired_direct', 'clinical_rt_mode': 'cartesianImpedance'},
    )
    assert ledger['build_hash'] != ledger['build_id']
    assert len(str(ledger['build_hash'])) == 64


def test_live_truth_ledger_refresh_backfills_artifacts(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'export').mkdir(parents=True)
    (session_dir / 'derived/session').mkdir(parents=True)
    base = build_live_truth_ledger(
        session_id='S',
        session_dir=str(session_dir),
        build_id='build-123',
        profile={'name': 'mainline'},
        robot_family_descriptor={'robot_model': 'xmate3'},
    )
    (session_dir / 'export' / 'release_gate_decision.json').write_text(json.dumps({'allowed': True, 'authoritative': True, 'reason': 'ok'}), encoding='utf-8')
    (session_dir / 'derived' / 'session' / 'control_plane_snapshot.json').write_text(json.dumps({'phase_history': [{'state': 'SCANNING'}], 'rt_metrics': {'packet_loss_percent': 0.0, 'jitter_ms_p95': 0.1, 'rt_quality_gate_passed': True}}), encoding='utf-8')
    (session_dir / 'export' / 'release_evidence_pack.json').write_text(json.dumps({'controller_log_summary': {'log_path': 'controller.log', 'last_transition': 'SCAN', 'last_event': 'ok'}}), encoding='utf-8')

    refreshed = refresh_live_truth_ledger_from_artifacts(session_dir, existing=base)
    assert refreshed['status'] == 'live_validation_materialized'
    assert refreshed['phase_transition_trace']['available'] is True
    assert refreshed['controller_log_summary']['available'] is True
    assert refreshed['rt_jitter_or_packet_loss_snapshot']['available'] is True
    assert refreshed['final_verdict_trace']['available'] is True
