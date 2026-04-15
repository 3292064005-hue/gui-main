from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig


class HeadlessControlPlaneStatusService:
    """Assemble the authoritative headless control-plane status payload."""

    def __init__(self, adapter) -> None:
        self.adapter = adapter

    def build(self) -> dict[str, Any]:
        adapter = self.adapter
        status = adapter.status()
        health = adapter.health()
        schema = adapter.schema()
        runtime_config = adapter.runtime_config()
        topics = adapter.topic_catalog()
        recent_commands = adapter.recent_commands().get('recent_commands', [])
        control_authority = adapter.control_authority_status()
        session_governance = {
            'summary_state': 'idle',
            'summary_label': '未锁定会话',
            'detail': 'no_active_session',
            'session_locked': False,
            'session_id': adapter._current_session_id,
        }
        evidence_seal: dict[str, Any] = {}
        if adapter._current_session_dir is not None:
            session_governance = {
                'summary_state': 'ready',
                'summary_label': '会话已锁定',
                'detail': str(adapter._current_session_dir),
                'session_locked': True,
                'session_id': adapter._current_session_id,
            }
            try:
                evidence_seal = adapter.current_evidence_seal()
            except (FileNotFoundError, OSError, RuntimeError, ValueError):
                evidence_seal = {}
        summary = adapter.control_plane_aggregator.build(
            local_config=RuntimeConfig.from_dict(
                dict(runtime_config.get('runtime_config', {})) or adapter.runtime_config_snapshot_data or RuntimeConfig().to_dict()
            ),
            runtime_config=runtime_config,
            schema=schema,
            status=status,
            health=health,
            topic_catalog=topics,
            recent_commands=recent_commands,
            control_authority=control_authority,
            session_governance=session_governance,
            evidence_seal=evidence_seal,
            authoritative_runtime_envelope=adapter.resolve_authoritative_runtime_envelope() if hasattr(adapter, 'resolve_authoritative_runtime_envelope') else None,
        )
        return {
            **summary,
            'status': status,
            'health': health,
            'schema': schema,
            'runtime_config': runtime_config,
            'topics': topics,
            'recent_commands': {'recent_commands': recent_commands},
            'control_authority': control_authority,
            'control_plane_snapshot': summary.get('control_plane_snapshot', {}),
        }
