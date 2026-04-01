from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.mock_backend import MockBackend


def test_runtime_verdict_service_prefers_runtime_contract(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path / 'backend')
    controller = AppController(tmp_path / 'app', backend)
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    report = controller.model_report
    assert report['authority_source'] == 'cpp_robot_core'
    assert report['verdict_kind'] == 'final'
    assert report['final_verdict']['advisory_only'] is False
    assert report['final_verdict']['source'] == 'cpp_robot_core'


def test_session_intelligence_materializes_governance_snapshots(tmp_path: Path) -> None:
    exp_manager = ExperimentManager(tmp_path / 'exp')
    session_service = SessionService(exp_manager)
    record = session_service.create_experiment(RuntimeConfig(), note='wave-def')
    from spine_ultrasound_ui.core.plan_service import PlanService
    plan_service = PlanService()
    localization = plan_service.run_localization(record, RuntimeConfig())
    preview, _ = plan_service.build_preview_plan(record, localization, RuntimeConfig())
    execution = plan_service.build_execution_plan(preview, config=RuntimeConfig())
    locked = session_service.ensure_locked(
        RuntimeConfig(),
        {},
        execution,
        protocol_version=1,
        safety_thresholds={'stale_telemetry_ms': 250},
        device_health_snapshot={},
        patient_registration=localization.patient_registration,
        control_authority={'owner': {'actor_id': 'tester'}},
    )
    session_service.save_summary({'control_plane_snapshot': {'summary_state': 'ready'}, 'control_authority': {'owner': {'actor_id': 'tester'}}, 'bridge_observability': {'summary_state': 'ready'}})
    session_dir = locked.session_dir
    control_plane = json.loads((session_dir / 'derived' / 'session' / 'control_plane_snapshot.json').read_text(encoding='utf-8'))
    authority = json.loads((session_dir / 'derived' / 'session' / 'control_authority_snapshot.json').read_text(encoding='utf-8'))
    bridge = json.loads((session_dir / 'derived' / 'events' / 'bridge_observability_report.json').read_text(encoding='utf-8'))
    seal = json.loads((session_dir / 'meta' / 'session_evidence_seal.json').read_text(encoding='utf-8'))
    manifest = json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8'))
    assert control_plane['summary_state'] in {'ready', 'degraded', 'blocked', 'warning'}
    assert authority['session_id'] == manifest['session_id']
    assert bridge['session_id'] == manifest['session_id']
    assert seal['seal_digest']
    assert manifest['artifact_registry']['control_plane_snapshot']['path'] == 'derived/session/control_plane_snapshot.json'
    assert manifest['artifact_registry']['session_evidence_seal']['path'] == 'meta/session_evidence_seal.json'


def test_deployment_profile_smoke_matrix() -> None:
    clinical = DeploymentProfileService({'SPINE_DEPLOYMENT_PROFILE': 'clinical'}).build_snapshot()
    review = DeploymentProfileService({'SPINE_DEPLOYMENT_PROFILE': 'review'}).build_snapshot()
    assert clinical['requires_api_token'] is True
    assert clinical['seal_strength'] == 'strict'
    assert review['review_only'] is True
    assert review['allows_write_commands'] is False
