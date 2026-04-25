from pathlib import Path

from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


def test_headless_adapter_surface_delegates_to_split_services() -> None:
    text = Path('spine_ultrasound_ui/services/headless_adapter_surface.py').read_text(encoding='utf-8')
    assert 'HeadlessControlPlaneStatusService' in text
    assert 'HeadlessEventSurfaceService' in text
    assert 'HeadlessFrameSurfaceService' in text



def test_headless_adapter_rejects_write_side_channels() -> None:
    adapter = HeadlessAdapter(
        mode='mock',
        command_host='127.0.0.1',
        command_port=5656,
        telemetry_host='127.0.0.1',
        telemetry_port=5657,
    )
    for operation in ('connect_robot', 'acquire_control_lease', 'renew_control_lease', 'release_control_lease', 'set_runtime_config'):
        if operation == 'connect_robot':
            reply = adapter.command(operation, {})
        elif operation == 'set_runtime_config':
            reply = adapter.set_runtime_config({'pressure_target': 9.0})
        else:
            reply = getattr(adapter, operation)({'actor_id': 'api'})
        assert reply['ok'] is False
        assert reply['data']['read_only_surface'] == 'headless_adapter'
