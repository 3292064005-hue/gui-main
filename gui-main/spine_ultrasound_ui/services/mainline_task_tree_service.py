
from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig


class MainlineTaskTreeService:
    """Build a BehaviorTree-style clinical mainline contract.

    This is not a realtime controller. It is a high-level task graph describing
    what the orchestration shell expects to happen around the official SDK
    runtime. The leaf actions are intentionally asynchronous/task-oriented and
    should be executed through cpp_robot_core rather than in Python.
    """

    _ORDER = [
        'ensure_connected',
        'ensure_powered',
        'ensure_auto_mode',
        'ensure_control_lease',
        'ensure_doctor_ready',
        'ensure_session_locked',
        'ensure_plan_validated',
        'configure_rt_mainline',
        'approach_prescan',
        'approach_entry',
        'seek_contact',
        'contact_hold',
        'scan_follow',
        'controlled_retract',
        'seal_evidence',
        'export_artifacts',
    ]

    def build(
        self,
        *,
        config: RuntimeConfig,
        sdk_runtime: dict[str, Any] | None = None,
        backend_link: dict[str, Any] | None = None,
        model_report: dict[str, Any] | None = None,
        session_governance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sdk_runtime = dict(sdk_runtime or {})
        backend_link = dict(backend_link or {})
        model_report = dict(model_report or {})
        session_governance = dict(session_governance or {})

        control = dict(sdk_runtime.get('control_governance_contract', {}))
        clinical = dict(sdk_runtime.get('clinical_mainline_contract', {}))
        release_contract = dict(sdk_runtime.get('release_contract', {}))
        executor = dict(sdk_runtime.get('mainline_executor_contract', {}))
        dual = dict(sdk_runtime.get('dual_state_machine_contract', {}))
        environment = dict(sdk_runtime.get('environment_doctor', {}))
        hardware_lifecycle = dict(sdk_runtime.get('hardware_lifecycle_contract', {}))
        rt_kernel = dict(sdk_runtime.get('rt_kernel_contract', {}))
        session_freeze = dict(sdk_runtime.get('session_freeze', {}))
        session_drift = dict(sdk_runtime.get('session_drift_contract', {}))
        final_verdict = dict(model_report.get('final_verdict', {}))
        if not final_verdict:
            final_verdict = dict(release_contract.get('final_verdict', {}))
        ownership = dict(backend_link.get('control_plane', {})).get('control_authority', {}) or {}

        runtime_state = str(control.get('current_execution_state') or dual.get('runtime_state') or 'BOOT')
        clinical_task_state = str(dual.get('clinical_task_state') or 'boot')
        if not clinical_task_state or clinical_task_state == 'boot':
            clinical_task_state = self._clinical_state_from_runtime(runtime_state)

        doctor_ready = str(environment.get('summary_state', 'ready')) != 'blocked' and str(hardware_lifecycle.get('summary_state', 'ready')) != 'blocked' and str(rt_kernel.get('summary_state', 'ready')) != 'blocked'
        checks = {
            'ensure_connected': bool(control.get('controller_online', False)),
            'ensure_powered': bool(control.get('powered', False)),
            'ensure_auto_mode': bool(control.get('automatic_mode', False)),
            'ensure_control_lease': str(ownership.get('summary_state', 'ready')) != 'blocked',
            'ensure_doctor_ready': doctor_ready,
            'ensure_session_locked': bool(session_freeze.get('session_locked', False)) and not bool(session_drift.get('drifts', [])),
            'ensure_plan_validated': runtime_state in {'PATH_VALIDATED', 'APPROACHING', 'CONTACT_SEEKING', 'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD', 'RETREATING', 'SCAN_COMPLETE'},
            'configure_rt_mainline': bool(control.get('rt_ready', False)) or (runtime_state in {'CONTACT_SEEKING', 'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD'}),
            'approach_prescan': runtime_state in {'APPROACHING', 'CONTACT_SEEKING', 'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD', 'RETREATING', 'SCAN_COMPLETE'},
            'approach_entry': runtime_state in {'APPROACHING', 'CONTACT_SEEKING', 'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD', 'RETREATING', 'SCAN_COMPLETE'},
            'seek_contact': runtime_state in {'CONTACT_SEEKING', 'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD', 'RETREATING', 'SCAN_COMPLETE'},
            'contact_hold': runtime_state in {'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD', 'RETREATING', 'SCAN_COMPLETE'},
            'scan_follow': runtime_state in {'SCANNING', 'PAUSED_HOLD', 'RETREATING', 'SCAN_COMPLETE'},
            'controlled_retract': runtime_state in {'RETREATING', 'SCAN_COMPLETE'},
            'seal_evidence': bool(release_contract.get('session_locked', False)) and runtime_state in {'SCAN_COMPLETE', 'RETREATING'},
            'export_artifacts': bool(release_contract.get('session_locked', False)) and runtime_state == 'SCAN_COMPLETE',
        }

        def _node(name: str, label: str, detail: str, *, async_action: bool = True, kind: str = 'action', section: str = 'mainline') -> dict[str, Any]:
            passed = checks.get(name, False)
            status = 'success' if passed else ('running' if self._is_current_node(name, runtime_state) else 'idle')
            if name == 'configure_rt_mainline' and environment.get('summary_state') == 'blocked':
                status = 'running' if not passed else status
            if name == 'ensure_session_locked' and session_governance.get('summary_state') == 'blocked':
                status = 'failure'
            if name == 'ensure_plan_validated' and final_verdict and not bool(final_verdict.get('accepted', False)):
                status = 'failure'
            return {
                'name': name,
                'label': label,
                'kind': kind,
                'section': section,
                'async_action': async_action,
                'status': status,
                'detail': detail,
            }

        nodes = [
            _node('ensure_connected', 'EnsureConnected', '连接链路与控制器就绪。', async_action=False, kind='condition', section='startup'),
            _node('ensure_powered', 'EnsurePowered', '机器人已上电。', async_action=False, kind='condition', section='startup'),
            _node('ensure_auto_mode', 'EnsureAutoMode', '机器人处于自动模式。', async_action=False, kind='condition', section='startup'),
            _node('ensure_control_lease', 'EnsureControlLease', '确认唯一控制源与 lease 已收敛。', async_action=False, kind='condition', section='startup'),
            _node('ensure_doctor_ready', 'EnsureDoctorReady', 'Environment/Hardware/RT kernel 医生检查通过。', async_action=False, kind='condition', section='startup'),
            _node('ensure_session_locked', 'EnsureSessionLocked', '会话冻结、生效配置与 plan hash 已绑定。', async_action=False, kind='condition', section='startup'),
            _node('ensure_plan_validated', 'EnsurePlanValidated', '官方/运行时最终裁决已通过。', async_action=False, kind='condition', section='startup'),
            _node('configure_rt_mainline', 'ConfigureRtMainline', '配置 RT 主线、阻抗、滤波、碰撞与软限位。', section='startup'),
            _node('approach_prescan', 'ApproachPrescan', 'NRT 接近预扫位。', section='nrt'),
            _node('approach_entry', 'ApproachEntry', 'NRT 进入扫描入口位。', section='nrt'),
            _node('seek_contact', 'SeekContact', 'RT 低速寻触进入接触带。', section='rt'),
            _node('contact_hold', 'ContactHold', 'RT 接触保持与稳定窗口确认。', section='rt'),
            _node('scan_follow', 'ScanFollow', 'RT 沿 path frame 扫查并维持接触。', section='rt'),
            _node('controlled_retract', 'ControlledRetract', 'RT/NRT 受控退让与抬离。', section='recovery'),
            _node('seal_evidence', 'SealEvidence', '冻结 controller evidence、session seal 与导出产物。', section='release'),
            _node('export_artifacts', 'ExportArtifacts', '生成 export/replay/report 等产物。', section='release'),
        ]

        blockers: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        def add(target: list[dict[str, Any]], name: str, detail: str, section: str) -> None:
            target.append({'name': name, 'detail': detail, 'section': section})

        if ownership.get('summary_state') == 'blocked':
            add(blockers, 'control_authority_conflict', str(ownership.get('detail', '控制权冲突')), 'startup')
        if session_drift.get('drifts'):
            add(blockers, 'session_freeze_drift', str(session_drift.get('detail', 'session freeze drift detected')), 'startup')
        backend_mode = str(backend_link.get('mode', ''))
        if environment.get('summary_state') == 'blocked' and backend_mode not in {'mock', 'inproc'}:
            add(blockers, 'environment_blocked', str(environment.get('detail', 'SDK 环境阻塞')), 'startup')
        elif environment.get('summary_state') in {'blocked', 'warning', 'degraded'}:
            add(warnings, 'environment_not_live', str(environment.get('detail', 'SDK 环境尚未进入 live 接管')), 'startup')
        if final_verdict and not bool(final_verdict.get('accepted', False)):
            add(blockers, 'final_verdict_rejected', str(final_verdict.get('reason', 'final verdict rejected')), 'startup')
        if not bool(executor.get('task_tree_aligned', True)):
            add(blockers, 'executor_task_tree_misaligned', 'executor 合同与任务树阶段不一致。', 'governance')
        if dict(executor.get('rt_executor', {})).get('summary_state') in {'warning', 'degraded'}:
            add(warnings, 'rt_executor_degraded', str(dict(executor.get('rt_executor', {})).get('detail', 'RT executor degraded')), 'rt')
        if dict(executor.get('nrt_executor', {})).get('summary_state') in {'warning', 'degraded'}:
            add(warnings, 'nrt_executor_degraded', str(dict(executor.get('nrt_executor', {})).get('detail', 'NRT executor degraded')), 'nrt')
        if not bool(session_freeze.get('session_locked', False)):
            add(warnings, 'session_not_locked', '会话尚未冻结；正式扫描前必须锁定。', 'startup')
        if ownership.get('summary_state') in {'warning', 'degraded'}:
            add(warnings, 'control_authority_degraded', str(ownership.get('detail', '控制权租约降级')), 'startup')

        summary_state = 'ready'
        if blockers:
            summary_state = 'blocked'
        elif warnings:
            summary_state = 'warning'

        next_action = self._first_pending(nodes)
        sections = self._summarize_sections(nodes)
        return {
            'summary_state': summary_state,
            'summary_label': {'ready': '临床主线任务树已对齐', 'warning': '临床主线任务树存在告警', 'blocked': '临床主线任务树阻塞'}[summary_state],
            'detail': '高层任务树仅负责编排，不替代官方 SDK RT/NRT 执行内核。',
            'runtime_state': runtime_state,
            'clinical_task_state': clinical_task_state,
            'expected_rt_mode': str(clinical.get('clinical_mainline_mode') or config.rt_mode),
            'nodes': nodes,
            'sections': sections,
            'blockers': blockers,
            'warnings': warnings,
            'next_action': next_action,
            'halt_behavior': 'pause_hold_or_controlled_retract',
            'async_policy': 'tree_nodes_are_non_blocking__execution_delegated_to_cpp_core',
            'tree_format': 'behavior_tree_async_contract_v2',
            'xml_outline': self._xml_outline(nodes),
        }

    def _clinical_state_from_runtime(self, runtime_state: str) -> str:
        mapping = {
            'BOOT': 'boot',
            'DISCONNECTED': 'boot',
            'CONNECTED': 'startup',
            'POWERED': 'startup',
            'AUTO_READY': 'startup',
            'SESSION_LOCKED': 'session_locked',
            'PATH_VALIDATED': 'plan_validated',
            'APPROACHING': 'approaching',
            'CONTACT_SEEKING': 'seek_contact',
            'CONTACT_STABLE': 'contact_stable',
            'SCANNING': 'scan_follow',
            'PAUSED_HOLD': 'paused',
            'RETREATING': 'controlled_retract',
            'SCAN_COMPLETE': 'completed',
            'FAULT': 'fault',
            'ESTOP': 'estop',
        }
        return mapping.get(runtime_state, 'boot')

    def _is_current_node(self, name: str, runtime_state: str) -> bool:
        mapping = {
            'configure_rt_mainline': {'AUTO_READY', 'SESSION_LOCKED', 'PATH_VALIDATED'},
            'approach_prescan': {'APPROACHING'},
            'approach_entry': {'APPROACHING'},
            'seek_contact': {'CONTACT_SEEKING'},
            'contact_hold': {'CONTACT_STABLE', 'PAUSED_HOLD'},
            'scan_follow': {'SCANNING'},
            'controlled_retract': {'RETREATING'},
            'seal_evidence': {'SCAN_COMPLETE'},
        }
        return runtime_state in mapping.get(name, set())

    def _first_pending(self, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        for node in nodes:
            if node['status'] in {'idle', 'running', 'failure'}:
                return {'name': node['name'], 'label': node['label'], 'status': node['status'], 'section': node['section']}
        return {'name': 'done', 'label': 'MainlineComplete', 'status': 'success', 'section': 'release'}

    def _summarize_sections(self, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        sections: dict[str, Any] = {}
        for section_name in ['startup', 'nrt', 'rt', 'recovery', 'release']:
            items = [node for node in nodes if node['section'] == section_name]
            state = 'ready'
            if any(node['status'] == 'failure' for node in items):
                state = 'blocked'
            elif any(node['status'] in {'idle', 'running'} for node in items):
                state = 'warning'
            sections[section_name] = {
                'summary_state': state,
                'summary_label': section_name,
                'nodes': items,
            }
        return sections

    def _xml_outline(self, nodes: list[dict[str, Any]]) -> str:
        lines = ["<BehaviorTree ID=\"ClinicalMainline\">", "  <Sequence name=\"startup_and_scan\">"]
        for node in nodes:
            tag = 'Condition' if node.get('kind') == 'condition' else 'Action'
            lines.append(f"    <{tag} ID=\"{node['label']}\" name=\"{node['name']}\" section=\"{node['section']}\" />")
        lines.append("  </Sequence>")
        lines.append("</BehaviorTree>")
        return '\n'.join(lines)
