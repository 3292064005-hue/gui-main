from __future__ import annotations

from spine_ultrasound_ui.services.control_plane_snapshot_service import ControlPlaneSnapshotService
from spine_ultrasound_ui.services.runtime_governance_projection_service import RuntimeGovernanceProjectionService


def test_projection_prefers_authoritative_runtime_envelope_over_raw_control_plane() -> None:
    service = RuntimeGovernanceProjectionService()
    projection = service.build_projection(
        backend_link={
            'control_plane': {
                'control_authority': {'summary_state': 'blocked', 'detail': 'stale-non-authoritative'},
                'authoritative_runtime_envelope': {
                    'authority_source': 'cpp_robot_core',
                    'control_authority': {
                        'summary_state': 'ready',
                        'summary_label': '控制权已锁定',
                        'detail': 'runtime owner',
                        'owner': {'actor_id': 'runtime', 'workspace': 'core', 'role': 'runtime', 'session_id': 'S1'},
                    },
                    'final_verdict': {
                        'accepted': True,
                        'reason': 'validated',
                        'policy_state': 'ready',
                        'source': 'cpp_robot_core',
                    },
                },
            },
        },
        model_report={'final_verdict': {'accepted': False, 'reason': 'stale-view-only'}},
    )
    assert projection['control_authority']['summary_state'] == 'ready'
    assert projection['final_verdict']['accepted'] is True
    assert projection['final_verdict']['source'] == 'cpp_robot_core'
    assert projection['authoritative_runtime_envelope']['control_authority']['owner']['actor_id'] == 'runtime'


def test_projection_does_not_allow_snapshot_authoritative_runtime_envelope_to_override_direct_runtime_truth() -> None:
    service = RuntimeGovernanceProjectionService()
    projection = service.build_projection(
        backend_link={
            'authoritative_runtime_envelope': {
                'authority_source': 'cpp_robot_core',
                'control_authority': {
                    'summary_state': 'ready',
                    'summary_label': '控制权已锁定',
                    'detail': 'runtime owner',
                    'owner': {'actor_id': 'runtime', 'workspace': 'core', 'role': 'runtime', 'session_id': 'S1'},
                },
                'final_verdict': {
                    'accepted': True,
                    'reason': 'validated',
                    'policy_state': 'ready',
                    'source': 'cpp_robot_core',
                },
            },
        },
        control_plane_snapshot={
            'authoritative_runtime_envelope': {
                'authority_source': 'snapshot',
                'control_authority': {
                    'summary_state': 'blocked',
                    'summary_label': '快照阻塞',
                    'detail': 'stale snapshot conflict',
                    'owner': {'actor_id': 'snapshot', 'workspace': 'ui', 'role': 'projection', 'session_id': 'OLD'},
                },
                'final_verdict': {
                    'accepted': False,
                    'reason': 'stale snapshot',
                    'policy_state': 'blocked',
                    'source': 'snapshot',
                },
            },
        },
    )
    assert projection['authoritative_runtime_envelope']['authority_source'] == 'cpp_robot_core'
    assert projection['control_authority']['summary_state'] == 'ready'
    assert projection['final_verdict']['accepted'] is True
    assert projection['final_verdict']['source'] == 'cpp_robot_core'


def test_projection_prefers_release_contract_over_model_report_when_runtime_envelope_missing() -> None:
    service = RuntimeGovernanceProjectionService()
    projection = service.build_projection(
        backend_link={'control_plane': {'control_authority': {'summary_state': 'ready', 'detail': 'lease ok'}}},
        model_report={'final_verdict': {'accepted': False, 'reason': 'stale-view-only'}},
        sdk_runtime={'release_contract': {'final_verdict': {'accepted': True, 'reason': 'release-ready', 'policy_state': 'ready', 'source': 'cpp_robot_core'}}},
    )
    assert projection['final_verdict']['accepted'] is True
    assert projection['final_verdict']['reason'] == 'release-ready'


def test_projection_uses_model_report_only_as_last_fallback() -> None:
    service = RuntimeGovernanceProjectionService()
    projection = service.build_projection(
        backend_link={'control_plane': {'control_authority': {'summary_state': 'ready', 'detail': 'lease ok'}}},
        model_report={'final_verdict': {'accepted': False, 'reason': 'force band violated', 'source': 'model_report'}},
    )
    assert projection['final_verdict']['accepted'] is False
    assert projection['final_verdict']['source'] == 'model_report'


def test_control_plane_snapshot_ignores_non_authoritative_control_authority_override() -> None:
    service = ControlPlaneSnapshotService()
    snapshot = service.build(
        backend_link={
            'control_plane': {
                'authoritative_runtime_envelope': {
                    'authority_source': 'cpp_robot_core',
                    'control_authority': {
                        'summary_state': 'ready',
                        'summary_label': '控制权已锁定',
                        'detail': 'runtime owner',
                        'owner': {'actor_id': 'runtime', 'workspace': 'core', 'role': 'runtime', 'session_id': 'S1'},
                    },
                },
            },
        },
        control_authority={'summary_state': 'blocked', 'detail': 'non-authoritative injection'},
    )
    assert snapshot['ownership_state']['summary_state'] == 'ready'
    assert any(item['name'] == 'non_authoritative_control_authority_ignored' for item in snapshot['warnings'])


def test_projection_does_not_allow_nested_authoritative_projection_to_override_direct_runtime_truth() -> None:
    service = RuntimeGovernanceProjectionService()
    projection = service.build_projection(
        backend_link={
            'control_plane': {
                'authoritative_runtime_envelope': {
                    'authority_source': 'cpp_robot_core',
                    'control_authority': {
                        'summary_state': 'ready',
                        'summary_label': '控制权已锁定',
                        'detail': 'runtime owner',
                        'owner': {'actor_id': 'runtime', 'workspace': 'core', 'role': 'runtime', 'session_id': 'S1'},
                    },
                    'final_verdict': {
                        'accepted': True,
                        'reason': 'validated',
                        'policy_state': 'ready',
                        'source': 'cpp_robot_core',
                    },
                },
            },
        },
        control_plane_snapshot={
            'authoritative_projection': {
                'authority_source': 'stale_projection',
                'control_authority': {
                    'summary_state': 'blocked',
                    'summary_label': '旧投影阻塞',
                    'detail': 'stale conflict',
                    'owner': {'actor_id': 'stale', 'workspace': 'ui', 'role': 'projection', 'session_id': 'OLD'},
                },
                'final_verdict': {
                    'accepted': False,
                    'reason': 'stale projection',
                    'policy_state': 'blocked',
                    'source': 'stale_projection',
                },
                'authoritative_runtime_envelope': {
                    'authority_source': 'stale_projection',
                    'control_authority': {
                        'summary_state': 'blocked',
                        'detail': 'stale envelope',
                    },
                    'final_verdict': {
                        'accepted': False,
                        'reason': 'stale envelope',
                        'policy_state': 'blocked',
                        'source': 'stale_projection',
                    },
                },
            },
        },
    )
    assert projection['authoritative_runtime_envelope']['authority_source'] == 'cpp_robot_core'
    assert projection['control_authority']['summary_state'] == 'ready'
    assert projection['final_verdict']['accepted'] is True
    assert projection['final_verdict']['source'] == 'cpp_robot_core'
