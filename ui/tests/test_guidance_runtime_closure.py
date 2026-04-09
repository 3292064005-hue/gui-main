from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.core.plan_service import LocalizationPipeline
from spine_ultrasound_ui.core.workflow_state_machine import WorkflowContext, WorkflowStateMachine
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.device_readiness import build_device_readiness
from spine_ultrasound_ui.services.localization_strategies import FallbackRegistrationStrategy
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.perception import GuidanceRuntimeService


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _device_roster() -> dict:
    return {
        "robot": {"online": True, "fresh": True, "fact_source": "test"},
        "camera": {"online": True, "fresh": True, "fact_source": "test"},
        "ultrasound": {"online": True, "fresh": True, "fact_source": "test"},
        "pressure": {"online": True, "fresh": True, "fact_source": "test"},
    }


def _make_guidance_frame(path: Path, *, center_offset_px: int) -> None:
    height, width = 120, 160
    pixels = np.zeros((height, width), dtype=np.float32)
    center = width // 2 + center_offset_px
    pixels[16:108, max(0, center - 8):min(width, center + 8)] = 0.95
    np.save(path, pixels)


def test_guidance_runtime_reads_filesystem_frames(tmp_path: Path) -> None:
    frames_dir = tmp_path / 'frames'
    frames_dir.mkdir()
    _make_guidance_frame(frames_dir / 'frame01.npy', center_offset_px=-6)
    _make_guidance_frame(frames_dir / 'frame02.npy', center_offset_px=0)
    _make_guidance_frame(frames_dir / 'frame03.npy', center_offset_px=4)

    config = RuntimeConfig(
        camera_guidance_input_mode='filesystem',
        camera_guidance_source_path=str(frames_dir),
        camera_guidance_frame_count=3,
    )
    result = GuidanceRuntimeService().build(
        experiment_id='EXP-FS',
        config=config,
        device_roster={
            'robot': {'online': True, 'fresh': True},
            'camera': {'online': True, 'fresh': True},
            'ultrasound': {'online': True, 'fresh': True},
            'pressure': {'online': True, 'fresh': True},
        },
        source_type='camera_only',
        source_label='camera_backed_registration',
    )
    assert result.source_frame_set['provider_mode'] == 'filesystem'
    assert result.source_frame_set['frame_count'] == 3
    assert result.localization_readiness['status'] == 'READY_FOR_FREEZE'
    assert result.patient_registration['camera_frame_refs']
    assert result.patient_registration['camera_observations']['provider_mode'] == 'filesystem'




def test_localization_pipeline_preserves_runtime_device_fact_surface() -> None:
    config = RuntimeConfig()
    pipeline = LocalizationPipeline()
    class _Exp:
        exp_id = 'EXP-FACTS'
    result = pipeline.run(
        _Exp(),
        config,
        device_roster={
            'robot': {'online': True, 'fresh': True, 'fact_source': 'telemetry'},
            'camera': {'online': True, 'fresh': True, 'fact_source': 'telemetry'},
            'ultrasound': {'online': False, 'fresh': False, 'fact_source': 'telemetry'},
            'pressure': {'online': False, 'fresh': False, 'fact_source': 'telemetry'},
        },
    )
    device_gate = result.localization_readiness['device_gate']
    assert device_gate['robot_online'] is True
    assert device_gate['camera_online'] is True
    assert device_gate['ultrasound_online'] is False
    assert device_gate['pressure_online'] is False
    assert device_gate['robot_fact_source'] == 'telemetry'
    assert device_gate['pressure_fact_source'] == 'telemetry'


def test_localization_pipeline_falls_back_when_camera_provider_fails(tmp_path: Path) -> None:
    config = RuntimeConfig(
        camera_guidance_input_mode='filesystem',
        camera_guidance_source_path=str(tmp_path / 'missing_frames'),
    )
    pipeline = LocalizationPipeline()
    class _Exp:
        exp_id = 'EXP-MISSING'
    result = pipeline.run(_Exp(), config, device_roster=_device_roster())
    assert result.status.state == 'REVIEW_REQUIRED'
    assert result.localization_readiness['status'] == 'READY_WITH_REVIEW'
    assert '其余策略失败' in result.status.detail



def test_approve_localization_review_unblocks_path_generation(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.localization_result = FallbackRegistrationStrategy().run(controller.session_service.current_experiment, controller.config, device_roster=_device_roster())
    controller.workflow_artifacts.localization = controller.localization_result.status
    controller.workflow_artifacts.localization_review_required = True
    controller.workflow_artifacts.localization_source_type = 'fallback_simulated'

    controller.approve_localization_review(operator_id='clinician_a')

    assert controller.localization_result is not None
    assert controller.localization_result.status.ready is True
    assert controller.workflow_artifacts.localization_review_approved is True
    controller.generate_path()
    assert controller.preview_scan_plan is not None



def test_device_readiness_uses_localization_gate_consistency() -> None:
    readiness = build_device_readiness(
        config=RuntimeConfig(),
        device_roster={
            'robot': {'online': True, 'fresh': True},
            'camera': {'online': True, 'fresh': True},
            'ultrasound': {'online': True, 'fresh': True},
            'pressure': {'online': True, 'fresh': True},
        },
        protocol_version=1,
        calibration_bundle={
            'release_state': 'approved',
            'bundle_hash': 'bundle',
            'camera_intrinsics_hash': 'intr',
            'camera_to_base_hash': 'ext',
            'probe_tcp_hash': 'tcp',
            'support_frame_hash': 'support',
            'temporal_sync_hash': 'sync',
            'residual_metrics': {'temporal_sync_jitter_ms': 1.0},
        },
        guidance_algorithm_registry={
            'camera_preprocess': {'plugin_id': 'cp', 'plugin_version': '1'},
            'spine_midline_estimation': {'plugin_id': 'sm', 'plugin_version': '1'},
            'registration_build': {'plugin_id': 'rb', 'plugin_version': '1'},
            'registration_validate': {'plugin_id': 'rv', 'plugin_version': '1'},
        },
        source_frame_set={
            'frame_count': 3,
            'frame_envelopes': [{'frame_id': 'f1'}, {'frame_id': 'f2'}, {'frame_id': 'f3'}],
            'fresh': True,
            'provider_mode': 'filesystem',
            'source_frame_set_hash': 'sfs',
        },
        localization_readiness={
            'device_gate': {'camera_online': False, 'robot_online': True, 'pressure_online': True, 'frame_count': 3, 'frame_fresh': True},
            'calibration_gate': {'camera_intrinsics_valid': True, 'camera_to_base_valid': True, 'probe_tcp_valid': True, 'temporal_sync_valid': True, 'temporal_sync_jitter_ms': 1.0},
            'freeze_gate': {'source_frame_set_hash': 'sfs'},
        },
    )
    assert readiness['localization_gate_consistent'] is False
    assert readiness['ready_to_lock'] is False


def test_generate_path_blocks_until_review_approved(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.localization_result = FallbackRegistrationStrategy().run(controller.session_service.current_experiment, controller.config, device_roster=_device_roster())
    controller.workflow_artifacts.localization = controller.localization_result.status
    controller.workflow_artifacts.localization_review_required = True
    controller.workflow_artifacts.localization_review_approved = False
    controller.generate_path()
    assert controller.preview_scan_plan is None


def test_device_readiness_requires_review_approval_and_frame_envelopes() -> None:
    readiness = build_device_readiness(
        config=RuntimeConfig(),
        device_roster={
            'robot': {'online': True, 'fresh': True},
            'camera': {'online': True, 'fresh': True},
            'ultrasound': {'online': True, 'fresh': True},
            'pressure': {'online': True, 'fresh': True},
        },
        protocol_version=1,
        calibration_bundle={
            'release_state': 'approved',
            'bundle_hash': 'bundle',
            'camera_intrinsics_hash': 'intr',
            'camera_to_base_hash': 'ext',
            'probe_tcp_hash': 'tcp',
            'support_frame_hash': 'support',
            'temporal_sync_hash': 'sync',
            'residual_metrics': {'temporal_sync_jitter_ms': 1.0},
        },
        guidance_algorithm_registry={
            'camera_preprocess': {'plugin_id': 'cp', 'plugin_version': '1'},
            'spine_midline_estimation': {'plugin_id': 'sm', 'plugin_version': '1'},
            'registration_build': {'plugin_id': 'rb', 'plugin_version': '1'},
            'registration_validate': {'plugin_id': 'rv', 'plugin_version': '1'},
        },
        source_frame_set={
            'frame_count': 2,
            'frame_envelopes': [{'frame_id': 'f1'}],
            'fresh': True,
            'provider_mode': 'filesystem',
            'source_frame_set_hash': 'sfs',
        },
        localization_readiness={
            'status': 'READY_WITH_REVIEW',
            'review_required': True,
            'review_approval': {'approved': False, 'operator_id': '', 'reason': ''},
            'device_gate': {'camera_online': True, 'robot_online': True, 'ultrasound_online': True, 'pressure_online': True, 'frame_count': 2, 'frame_fresh': True},
            'calibration_gate': {'camera_intrinsics_valid': True, 'camera_to_base_valid': True, 'probe_tcp_valid': True, 'temporal_sync_valid': True, 'temporal_sync_jitter_ms': 1.0},
            'freeze_gate': {'source_frame_set_hash': 'sfs', 'freeze_ready': False, 'review_approved': False},
        },
    )
    assert readiness['localization_inputs_available'] is False
    assert readiness['ready_to_lock'] is False


def test_workflow_recommends_review_approval_before_path_generation() -> None:
    workflow = WorkflowStateMachine()
    from spine_ultrasound_ui.models import SystemState
    actions = workflow.permission_matrix(
        WorkflowContext(
            core_state=SystemState.BOOT,
            has_experiment=True,
            localization_ready=True,
            localization_review_required=True,
            localization_review_approved=False,
        )
    )
    assert actions['approve_localization_review']['enabled'] is False
    # AUTO_READY context should enable approval and block path generation.
    actions = workflow.permission_matrix(
        WorkflowContext(
            core_state=SystemState.AUTO_READY,
            has_experiment=True,
            localization_ready=True,
            localization_review_required=True,
            localization_review_approved=False,
        )
    )
    assert actions['approve_localization_review']['enabled'] is True
    assert actions['generate_path']['enabled'] is False
