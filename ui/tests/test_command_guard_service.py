from __future__ import annotations

from spine_ultrasound_ui.services.command_guard_service import CommandGuardService


class _Authority:
    def guard_command(self, command, payload, *, current_session_id, source):
        return {
            'allowed': True,
            'message': 'ok',
            'normalized_payload': dict(payload),
            'authority': {'summary_state': 'ready'},
        }


def test_live_profile_blocks_core_backend_when_runtime_doctor_is_blocked() -> None:
    service = CommandGuardService(
        control_authority=_Authority(),
        current_session_id=lambda: 'S1',
        deployment_profile_snapshot=lambda: {
            'name': 'research',
            'requires_live_sdk': True,
            'review_only': False,
            'allows_write_commands': True,
            'allowed_write_roles': ['operator'],
        },
        backend_mode_snapshot=lambda: 'core',
        control_plane_snapshot=lambda: {
            'runtime_doctor': {'summary_state': 'blocked', 'summary_label': '运行主线治理阻塞', 'detail': 'vendor boundary not live'},
            'blockers': [
                {'section': 'vendor_boundary', 'name': 'vendor_boundary_not_live', 'detail': 'not live'},
            ],
        },
    )

    normalized, reply = service.guard_write_command('start_scan', {'_command_context': {'role': 'operator'}})
    assert normalized['_command_context']['role'] == 'operator'
    assert reply is not None
    assert reply.ok is False
    assert reply.data['blocking_issue']['section'] == 'vendor_boundary'


def test_live_profile_allows_core_backend_when_runtime_doctor_has_no_blockers() -> None:
    service = CommandGuardService(
        control_authority=_Authority(),
        current_session_id=lambda: 'S1',
        deployment_profile_snapshot=lambda: {
            'name': 'research',
            'requires_live_sdk': True,
            'review_only': False,
            'allows_write_commands': True,
            'allowed_write_roles': ['operator'],
        },
        backend_mode_snapshot=lambda: 'core',
        control_plane_snapshot=lambda: {
            'runtime_doctor': {'summary_state': 'ready', 'summary_label': '运行主线已收敛', 'detail': 'ready'},
            'blockers': [],
        },
    )

    _normalized, reply = service.guard_write_command('start_scan', {'_command_context': {'role': 'operator'}})
    assert reply is None


def test_authoritative_write_capability_blocks_command_before_profile_fallback() -> None:
    service = CommandGuardService(
        control_authority=_Authority(),
        current_session_id=lambda: 'S1',
        deployment_profile_snapshot=lambda: {
            'name': 'research',
            'requires_live_sdk': True,
            'review_only': False,
            'allows_write_commands': True,
            'allowed_write_roles': ['operator'],
        },
        backend_mode_snapshot=lambda: 'core',
        control_plane_snapshot=lambda: {
            'authoritative_runtime_envelope': {
                'write_capabilities': {
                    'rt_motion_write': {'allowed': False, 'reason': 'live_takeover_ready_required', 'source_of_truth': 'cpp_robot_core'},
                },
            },
            'runtime_doctor': {'summary_state': 'ready', 'summary_label': '运行主线已收敛', 'detail': 'ready'},
            'blockers': [],
        },
    )

    _normalized, reply = service.guard_write_command('start_scan', {'_command_context': {'role': 'operator'}})
    assert reply is not None
    assert reply.ok is False
    assert reply.data['required_claim'] == 'rt_motion_write'
    assert reply.data['capability_state']['reason'] == 'live_takeover_ready_required'


def test_root_level_write_capabilities_are_honored() -> None:
    service = CommandGuardService(
        control_authority=_Authority(),
        current_session_id=lambda: 'S1',
        deployment_profile_snapshot=lambda: {
            'name': 'research',
            'requires_live_sdk': True,
            'review_only': False,
            'allows_write_commands': True,
            'allowed_write_roles': ['operator'],
        },
        backend_mode_snapshot=lambda: 'core',
        control_plane_snapshot=lambda: {
            'write_capabilities': {
                'rt_motion_write': {'allowed': False, 'reason': 'root_level_gate', 'source_of_truth': 'cpp_robot_core'},
            },
            'runtime_doctor': {'summary_state': 'ready', 'summary_label': '运行主线已收敛', 'detail': 'ready'},
            'blockers': [],
        },
    )

    _normalized, reply = service.guard_write_command('start_scan', {'_command_context': {'role': 'operator'}})
    assert reply is not None
    assert reply.ok is False
    assert reply.data['required_claim'] == 'rt_motion_write'
    assert reply.data['capability_state']['reason'] == 'root_level_gate'
