#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import PySide6  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - repository gate fallback
    import types

    class _DummySignal:
        def __init__(self, *args, **kwargs):
            self._slots = []

        def connect(self, slot):
            self._slots.append(slot)

        def disconnect(self, slot=None):
            if slot is None:
                self._slots.clear()
                return
            self._slots = [item for item in self._slots if item is not slot]

        def emit(self, *args, **kwargs):
            for slot in list(self._slots):
                slot(*args, **kwargs)

    class _DummyQObject:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyQTimer:
        def __init__(self, *args, **kwargs):
            self.timeout = _DummySignal()
            self._active = False

        def start(self, *args, **kwargs):
            self._active = True

        def stop(self):
            self._active = False

        def isActive(self):
            return self._active

    class _DummyPixmap:
        def __init__(self, *args, **kwargs):
            pass

        def fill(self, *args, **kwargs):
            return None

    class _DummyColor:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyPainter:
        Antialiasing = 1

        def __init__(self, *args, **kwargs):
            pass

        def setRenderHint(self, *args, **kwargs):
            return None

        def setPen(self, *args, **kwargs):
            return None

        def setBrush(self, *args, **kwargs):
            return None

        def drawLine(self, *args, **kwargs):
            return None

        def drawRoundedRect(self, *args, **kwargs):
            return None

        def drawText(self, *args, **kwargs):
            return None

        def drawEllipse(self, *args, **kwargs):
            return None

        def end(self):
            return None

    pyside6 = types.ModuleType('PySide6')
    qtcore = types.ModuleType('PySide6.QtCore')
    qtgui = types.ModuleType('PySide6.QtGui')
    qtcore.QObject = _DummyQObject
    qtcore.QTimer = _DummyQTimer
    qtcore.Signal = _DummySignal
    qtgui.QPixmap = _DummyPixmap
    qtgui.QColor = _DummyColor
    qtgui.QPainter = _DummyPainter
    sys.modules['PySide6'] = pyside6
    sys.modules['PySide6.QtCore'] = qtcore
    sys.modules['PySide6.QtGui'] = qtgui

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.api_bridge_backend import ApiBridgeBackend
from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService
from spine_ultrasound_ui.services.backend_base import BackendBase
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.robot_core_client import RobotCoreClientBackend
import spine_ultrasound_ui.services.robot_core_client as robot_core_client_module


class _AuthorityBackend(BackendBase):
    def resolve_authoritative_runtime_envelope(self) -> dict:
        return {
            'authority_source': 'unit-test',
            'control_authority': {
                'summary_state': 'ready',
                'owner': {'actor_id': 'runtime', 'workspace': 'runtime', 'role': 'runtime', 'session_id': ''},
            },
            'runtime_config_applied': {'pressure_target': 8.0},
            'final_verdict': {'accepted': True, 'source': 'cpp_robot_core'},
        }

    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict:
        return {'accepted': True, 'source': 'cpp_robot_core', 'read_only': bool(read_only)}


def _sample_authoritative_envelope(authority_source: str) -> dict:
    return {
        'summary_state': 'ready',
        'summary_label': '运行时权威快照可用',
        'detail': 'runtime-owned',
        'authority_source': authority_source,
        'protocol_version': 1,
        'control_authority': {
            'summary_state': 'ready',
            'summary_label': '控制权已收口',
            'detail': 'runtime-owned',
            'owner': {'actor_id': 'runtime', 'workspace': 'runtime', 'role': 'runtime', 'session_id': ''},
            'active_lease': {'lease_id': 'runtime', 'actor_id': 'runtime', 'workspace': 'runtime', 'role': 'runtime', 'session_id': '', 'expires_in_s': 0},
            'owner_provenance': {'source': authority_source},
            'workspace_binding': 'runtime',
            'session_binding': '',
            'blockers': [],
            'warnings': [],
        },
        'runtime_config_applied': {'pressure_target': 8.0},
        'desired_runtime_config': {'pressure_target': 8.0},
        'session_freeze': {},
        'plan_digest': {},
        'write_capabilities': {},
        'final_verdict': {'accepted': True, 'source': 'cpp_robot_core'},
        'authoritative_runtime_envelope_present': True,
        'envelope_origin': 'direct_authoritative_runtime_envelope',
        'synthesized': False,
    }


def main() -> int:
    issues: list[str] = []
    service = BackendAuthoritativeContractService()

    base_backend = _AuthorityBackend()
    if base_backend.resolve_control_authority().get('owner', {}).get('actor_id') != 'runtime':
        issues.append('BackendBase.resolve_control_authority no longer derives authority from canonical envelope')
    if base_backend.query_final_verdict_snapshot().get('accepted') is not True:
        issues.append('BackendBase.query_final_verdict_snapshot no longer delegates to canonical verdict surface')

    with tempfile.TemporaryDirectory(prefix='authority-parity-') as tmpdir:
        root = Path(tmpdir)

        mock_backend = MockBackend(root)
        mock_envelope = mock_backend.resolve_authoritative_runtime_envelope()
        if not mock_envelope.get('authoritative_runtime_envelope_present'):
            issues.append('MockBackend canonical envelope is not marked as runtime-published')
        if mock_backend.resolve_control_authority().get('owner', {}).get('actor_id') != mock_envelope.get('control_authority', {}).get('owner', {}).get('actor_id'):
            issues.append('MockBackend control-authority surface diverges from canonical envelope')
        if mock_backend.query_final_verdict_snapshot() != mock_envelope.get('final_verdict', {}):
            issues.append('MockBackend final-verdict surface diverges from canonical envelope')
        mock_link_snapshot = mock_backend.link_snapshot()
        if mock_link_snapshot.get('control_authority', {}).get('owner', {}).get('actor_id') != mock_envelope.get('control_authority', {}).get('owner', {}).get('actor_id'):
            issues.append('MockBackend link_snapshot top-level control_authority must stay canonical')

        headless = HeadlessAdapter('mock', '127.0.0.1', 5656, '127.0.0.1', 5657)
        headless_envelope = headless.resolve_authoritative_runtime_envelope()
        if not headless_envelope.get('authoritative_runtime_envelope_present'):
            issues.append('HeadlessAdapter canonical envelope is not runtime-published in mock mode')
        if headless.query_final_verdict_snapshot().get('accepted') is not False:
            issues.append('HeadlessAdapter query_final_verdict_snapshot did not return runtime-owned verdict snapshot')
        original_dispatch = headless.command_service._dispatch.dispatch
        headless.command_service._dispatch.dispatch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('boom'))
        unavailable = headless.resolve_authoritative_runtime_envelope()
        headless.command_service._dispatch.dispatch = original_dispatch
        if unavailable.get('control_authority'):
            issues.append('HeadlessAdapter fabricated control-authority facts when runtime envelope query failed')
        if unavailable.get('synthesized'):
            issues.append('HeadlessAdapter unavailable authority envelope is incorrectly marked synthesized')

        robot_core_client_module.create_client_ssl_context = lambda cert_path=None: object()  # type: ignore[assignment]
        core = RobotCoreClientBackend(root)
        core._authoritative_envelope = _sample_authoritative_envelope('cpp_robot_core')
        if core.resolve_control_authority().get('owner', {}).get('actor_id') != 'runtime':
            issues.append('RobotCoreClientBackend control-authority no longer comes from canonical envelope cache')
        core_link_snapshot = core.link_snapshot()
        if core_link_snapshot.get('control_authority', {}).get('owner', {}).get('actor_id') != 'runtime':
            issues.append('RobotCoreClientBackend link_snapshot top-level control_authority must stay canonical')
        core._authoritative_envelope = {}
        core._refresh_authoritative_runtime_snapshot = lambda **kwargs: None  # type: ignore[assignment]
        core._last_final_verdict = {'accepted': True, 'source': 'projection'}
        if core.resolve_authoritative_runtime_envelope() != {}:
            issues.append('RobotCoreClientBackend resolve_authoritative_runtime_envelope should stay empty without runtime-published cache')
        core_link_snapshot_without_authority = core.link_snapshot()
        if core_link_snapshot_without_authority.get('authoritative_runtime_envelope'):
            issues.append('RobotCoreClientBackend link_snapshot authoritative_runtime_envelope must stay empty without runtime-published cache')
        if core_link_snapshot_without_authority.get('final_verdict'):
            issues.append('RobotCoreClientBackend link_snapshot top-level final_verdict must stay empty without runtime-published cache')
        if core_link_snapshot_without_authority.get('projected_final_verdict', {}).get('source') != 'projection':
            issues.append('RobotCoreClientBackend link_snapshot projected_final_verdict must preserve non-authoritative projection state')

        api = ApiBridgeBackend(root)
        api._authoritative_envelope = _sample_authoritative_envelope('api_bridge')
        if api.resolve_control_authority().get('owner', {}).get('actor_id') != 'runtime':
            issues.append('ApiBridgeBackend control-authority no longer comes from canonical envelope cache')
        api._authoritative_envelope = {}
        api._control_plane_cache = {
            'control_authority': {'summary_state': 'ready', 'summary_label': 'projected'},
            'final_verdict': {'accepted': True, 'source': 'projection'},
        }
        unavailable_api = api.resolve_authoritative_runtime_envelope()
        if unavailable_api.get('control_authority'):
            issues.append('ApiBridgeBackend fabricated control-authority facts from control-plane fallback')
        if unavailable_api.get('synthesized'):
            issues.append('ApiBridgeBackend unavailable authority envelope is incorrectly marked synthesized')
        link_snapshot = api.link_snapshot()
        if link_snapshot.get('control_authority'):
            issues.append('ApiBridgeBackend link_snapshot top-level control_authority must stay empty when no authoritative envelope exists')
        if link_snapshot.get('final_verdict'):
            issues.append('ApiBridgeBackend link_snapshot top-level final_verdict must stay empty when no authoritative envelope exists')
        if link_snapshot.get('projected_control_authority', {}).get('summary_label') != 'projected':
            issues.append('ApiBridgeBackend link_snapshot projected_control_authority must preserve control-plane projection')
        if link_snapshot.get('projected_final_verdict', {}).get('source') != 'projection':
            issues.append('ApiBridgeBackend link_snapshot projected_final_verdict must preserve control-plane projection')
        api._client.close()

        direct_payload = {
            'authority_source': 'cpp_robot_core',
            'control_authority': {'summary_state': 'ready', 'owner': {'actor_id': 'runtime', 'workspace': 'runtime', 'role': 'runtime', 'session_id': ''}},
            'runtime_config_applied': {'pressure_target': 8.0},
            'final_verdict': {'accepted': True, 'source': 'cpp_robot_core'},
        }
        normalized = service.normalize_authoritative_runtime_envelope(
            direct_payload,
            authority_source='cpp_robot_core',
            desired_runtime_config=RuntimeConfig(),
            allow_direct_payload=True,
        )
        if not normalized.get('authoritative_runtime_envelope_present'):
            issues.append('BackendAuthoritativeContractService strict authority normalization rejected direct runtime envelope payloads')
        synthetic = service.normalize_authoritative_runtime_envelope(
            {'control_plane': {'control_authority': {'summary_state': 'ready'}}},
            authority_source='unit-test',
            desired_runtime_config=RuntimeConfig(),
            allow_direct_payload=False,
        )
        if synthetic:
            issues.append('BackendAuthoritativeContractService strict authority normalization accepted synthesized control-plane fallback payloads')

    if issues:
        for issue in issues:
            print(f'[FAIL] {issue}')
        return 1

    print('[PASS] canonical backend authority surface behavior stays aligned across base/api/core/mock/headless backends')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
