from __future__ import annotations

import json

import jsonschema
from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.contracts import schema_catalog, validate_payload_against_schema
from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_schema_catalog_includes_guidance_contracts() -> None:
    catalog = schema_catalog()
    for name in [
        "localization_readiness.schema.json",
        "calibration_bundle.schema.json",
        "registration_candidate.schema.json",
        "manual_adjustment.schema.json",
        "localization_freeze.schema.json",
        "camera_frame_envelope.schema.json",
        "source_frame_set.schema.json",
        "back_roi.schema.json",
        "midline_polyline.schema.json",
        "landmarks.schema.json",
        "body_surface.schema.json",
        "guidance_targets.schema.json",
        "localization_replay_index.schema.json",
    ]:
        assert name in catalog


def test_locked_session_materializes_guidance_bundle(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_procedure()

    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    manifest = json.loads((session_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))
    registration = json.loads((session_dir / "meta" / "patient_registration.json").read_text(encoding="utf-8"))
    readiness = json.loads((session_dir / "meta" / "localization_readiness.json").read_text(encoding="utf-8"))
    calibration = json.loads((session_dir / "meta" / "calibration_bundle.json").read_text(encoding="utf-8"))
    freeze = json.loads((session_dir / "meta" / "localization_freeze.json").read_text(encoding="utf-8"))
    source_frame_set = json.loads((session_dir / "derived" / "sync" / "source_frame_set.json").read_text(encoding="utf-8"))
    replay = json.loads((session_dir / "replay" / "localization_replay_index.json").read_text(encoding="utf-8"))

    assert registration["role"] == "guidance_only"
    assert registration["guidance_mode"] == "pre_scan_guidance"
    assert manifest["guidance_mode"] == "guidance_only"
    assert manifest["guidance_version"] == "camera_guidance_v1"
    assert readiness["status"] == "READY_FOR_FREEZE"
    assert calibration["release_state"] == "approved"
    assert freeze["freeze_verdict"] == "accepted"
    assert source_frame_set["frame_count"] == 3
    assert replay["registration_hash"] == registration["registration_hash"]
    for artifact in [
        "localization_readiness",
        "calibration_bundle",
        "localization_freeze",
        "manual_adjustment",
        "source_frame_set",
        "localization_replay_index",
        "registration_candidate",
        "back_roi",
        "midline_polyline",
        "landmarks",
        "body_surface",
        "guidance_targets",
    ]:
        assert artifact in manifest["artifact_registry"]


from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.session_lock_service import SessionLockService
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan, ScanWaypoint


def test_locked_session_uses_canonical_guidance_hashes(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_procedure()

    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    manifest = json.loads((session_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))
    registration = json.loads((session_dir / "meta" / "patient_registration.json").read_text(encoding="utf-8"))
    calibration = json.loads((session_dir / "meta" / "calibration_bundle.json").read_text(encoding="utf-8"))
    source_frame_set = json.loads((session_dir / "derived" / "sync" / "source_frame_set.json").read_text(encoding="utf-8"))
    freeze = json.loads((session_dir / "meta" / "localization_freeze.json").read_text(encoding="utf-8"))

    assert manifest["patient_registration_hash"] == registration["registration_hash"]
    assert manifest["calibration_bundle_hash"] == calibration["bundle_hash"]
    assert manifest["source_frame_set_hash"] == source_frame_set["source_frame_set_hash"]
    assert manifest["localization_freeze_hash"] == freeze["freeze_hash"]
    assert registration["processing_step_refs"] == [
        step["step_id"] for step in manifest["guidance_processing_steps"]
    ]


def test_guidance_lock_rejects_review_required_bundle(tmp_path: Path) -> None:
    manager = ExperimentManager(Path(tmp_path))
    service = SessionLockService(manager)
    runtime = RuntimeConfig()
    exp = manager.create(runtime.to_dict())
    preview = ScanPlan(
        session_id="",
        plan_id="PLAN_PREVIEW",
        approach_pose=ScanWaypoint(0, 0, 0, 0, 0, 0),
        retreat_pose=ScanWaypoint(0, 0, 0, 0, 0, 0),
        segments=[],
    )
    try:
        service.lock(
            exp_id=exp["exp_id"],
            config=runtime,
            device_roster={},
            preview_plan=preview,
            protocol_version=1,
            patient_registration={
                "role": "guidance_only",
                "registration_hash": "reg-hash",
                "freeze_ready": False,
            },
            localization_readiness={
                "status": "READY_WITH_REVIEW",
                "freeze_gate": {"freeze_ready": False},
            },
            calibration_bundle={"bundle_hash": "bundle-hash"},
            source_frame_set={"source_frame_set_hash": "sfs-hash"},
            patient_registration_hash="reg-hash",
            safety_thresholds={},
            device_health_snapshot={},
            force_control_hash="",
            robot_profile_hash="",
        )
    except RuntimeError as exc:
        assert "not eligible" in str(exc)
    else:
        raise AssertionError("review-required guidance bundle should be rejected")


def test_session_service_guidance_only_lock_requires_canonical_localization_result(tmp_path: Path) -> None:
    manager = ExperimentManager(Path(tmp_path))
    session_service = SessionService(manager)
    runtime = RuntimeConfig()
    session_service.create_experiment(runtime, note="compat-guidance-lock")
    preview = ScanPlan(
        session_id="",
        plan_id="PLAN_COMPAT",
        approach_pose=ScanWaypoint(0, 0, 0, 0, 0, 0),
        retreat_pose=ScanWaypoint(0, 0, 0, 0, 0, 0),
        segments=[],
    )
    session_service.save_preview_plan(preview)
    registration = {
        "role": "guidance_only",
        "guidance_mode": "pre_scan_guidance",
        "registration_id": "REG_COMPAT",
        "registration_hash": "reg-compat-hash",
        "camera_device_id": "camera-0",
    }

    try:
        session_service.ensure_locked(
            runtime,
            {},
            preview,
            protocol_version=1,
            safety_thresholds={},
            device_health_snapshot={},
            patient_registration=registration,
            localization_result=None,
            control_authority={},
        )
    except RuntimeError as exc:
        assert 'canonical localization_result' in str(exc)
    else:
        raise AssertionError('guidance-only session lock should reject non-canonical compatibility freeze synthesis')


def test_source_frame_set_schema_accepts_device_fact_sources(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_procedure()

    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    payload = json.loads((session_dir / "derived" / "sync" / "source_frame_set.json").read_text(encoding="utf-8"))
    validate_payload_against_schema(schema_name='source_frame_set.schema.json', payload=payload)
    assert set(payload['device_fact_sources']) == {'camera', 'robot', 'ultrasound', 'pressure'}


def test_localization_strategy_requires_authoritative_device_roster() -> None:
    class _Exp:
        exp_id = 'EXP-STRICT-ROSTER'

    from spine_ultrasound_ui.services.localization_strategies import FallbackRegistrationStrategy

    try:
        FallbackRegistrationStrategy().run(_Exp(), RuntimeConfig())
    except ValueError as exc:
        assert 'device_roster' in str(exc)
    else:
        raise AssertionError('localization without authoritative device roster should fail')


def test_source_frame_set_schema_requires_device_fact_sources() -> None:
    payload = {
        'schema_version': '1.0',
        'camera_device_id': 'camera-0',
        'frame_refs': ['frame-1'],
        'frame_envelopes': [{
            'storage_ref': 'frame-1',
            'provider_mode': 'synthetic',
            'captured_at': '2026-04-09T00:00:00Z',
            'fresh': True,
            'roi_center_y_mm': 0.0,
            'confidence': 0.8,
            'frame_size_px': {'width': 640, 'height': 480},
        }],
        'frame_count': 1,
        'fresh': True,
        'provider_mode': 'synthetic',
        'requested_mode': 'synthetic',
        'source_frame_set_hash': 'hash',
    }
    try:
        validate_payload_against_schema(schema_name='source_frame_set.schema.json', payload=payload)
    except ValueError as exc:
        assert 'device_fact_sources' in str(exc)
    else:
        raise AssertionError('source_frame_set payload without device_fact_sources should violate schema')


def test_locked_session_guidance_artifacts_match_declared_schemas(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_procedure()

    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    catalog = schema_catalog()

    artifacts = {
        'registration_candidate': json.loads((session_dir / 'derived' / 'guidance' / 'registration_candidate.json').read_text(encoding='utf-8')),
        'back_roi': json.loads((session_dir / 'derived' / 'guidance' / 'back_roi.json').read_text(encoding='utf-8')),
        'midline_polyline': json.loads((session_dir / 'derived' / 'guidance' / 'midline_polyline.json').read_text(encoding='utf-8')),
        'landmarks': json.loads((session_dir / 'derived' / 'guidance' / 'landmarks.json').read_text(encoding='utf-8')),
        'body_surface': json.loads((session_dir / 'derived' / 'guidance' / 'body_surface.json').read_text(encoding='utf-8')),
        'guidance_targets': json.loads((session_dir / 'derived' / 'guidance' / 'guidance_targets.json').read_text(encoding='utf-8')),
    }
    for artifact_name, payload in artifacts.items():
        schema_name = f'{artifact_name}.schema.json'
        jsonschema.Draft202012Validator(catalog[schema_name]).validate(payload)


def test_register_artifact_rejects_schema_invalid_canonical_payload(tmp_path: Path) -> None:
    manager = ExperimentManager(Path(tmp_path))
    runtime = RuntimeConfig()
    exp = manager.create(runtime.to_dict())
    preview = ScanPlan(
        session_id="",
        plan_id="PLAN_REGISTER_INVALID",
        approach_pose=ScanWaypoint(0, 0, 0, 0, 0, 0),
        retreat_pose=ScanWaypoint(0, 0, 0, 0, 0, 0),
        segments=[],
    )
    locked = manager.lock_session(
        exp_id=exp["exp_id"],
        config_snapshot=runtime.to_dict(),
        device_roster={},
        software_version=runtime.software_version,
        build_id=runtime.build_id,
        scan_plan=preview,
    )
    session_dir = Path(locked["session_dir"])
    artifact_path = session_dir / 'derived' / 'sync' / 'source_frame_set.json'
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text('{}', encoding='utf-8')

    try:
        manager.register_artifact(
            session_dir,
            'source_frame_set',
            {
                'artifact_type': 'source_frame_set',
                'path': 'derived/sync/source_frame_set.json',
                'producer': 'test',
                'schema': 'source_frame_set.schema.json',
            },
        )
    except RuntimeError as exc:
        assert 'schema validation failed' in str(exc)
    else:
        raise AssertionError('register_artifact should reject schema-invalid canonical artifacts')
