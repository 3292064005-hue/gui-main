from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan, SystemState
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract
from spine_ultrasound_ui.utils.runtime_fingerprint import payload_hash


class MockRuntimeContractSurfaceMixin:
        def _runtime_alignment_payload(self) -> dict[str, Any]:
            return {
                "sdk_family": "ROKAE xCore SDK (C++)",
                "robot_model": self.config.robot_model,
                "sdk_robot_class": self.config.sdk_robot_class,
                "axis_count": self.config.axis_count,
                "remote_ip": self.config.remote_ip,
                "local_ip": self.config.local_ip,
                "preferred_link": self.config.preferred_link,
                "rt_mode": self.config.rt_mode,
                "single_control_source": self.config.requires_single_control_source,
                "source": "mock_runtime_contract",
                "sdk_available": False,
                "sdk_binding_mode": "contract_only",
                "control_source_exclusive": bool(self.config.requires_single_control_source),
                "network_healthy": bool(self.controller_online),
                "motion_channel_ready": bool(self.controller_online and self.powered),
                "state_channel_ready": bool(self.controller_online),
                "aux_channel_ready": bool(self.controller_online),
                "nominal_rt_loop_hz": 1000,
            }

        def _xmate_model_summary_payload(self) -> dict[str, Any]:
            profile = self.model_service.profile
            return {
                "robot_model": profile.robot_model,
                "sdk_robot_class": profile.sdk_robot_class,
                "axis_count": profile.axis_count,
                "dh_parameters": [item.to_dict() for item in profile.dh_parameters],
                "supported_rt_modes": list(profile.supported_rt_modes),
                "clinical_mainline_mode": profile.rt_mode,
                "approximate": True,
                "source": "python_profile_contract",
                "duplication_policy": "desktop_advisory_only__official_fk_ik_jacobian_torque_stay_in_cpp_runtime",
            }

        def _identity_payload(self) -> dict[str, Any]:
            identity = self.identity_service.resolve(self.config.robot_model, self.config.sdk_robot_class, self.config.axis_count)
            return identity.to_dict()

        def _robot_family_contract_payload(self) -> dict[str, Any]:
            return self.family_registry.build_contract(self.config)

        def _vendor_boundary_contract_payload(self) -> dict[str, Any]:
            return {
                "summary_state": "warning" if not self.controller_online else "ready",
                "summary_label": "vendor boundary contract" if not self.controller_online else "vendor boundary attached",
                "detail": "Mock runtime keeps a narrow vendor boundary and does not claim direct live SDK ownership.",
                "binding_mode": "contract_only",
                "runtime_source": "mock_runtime_contract",
                "runtime_source_semantics": "contract_replay_only",
                "single_control_source_required": bool(self.config.requires_single_control_source),
                "control_source_exclusive": bool(self.config.requires_single_control_source),
                "fixed_period_enforced": True,
                "active_rt_phase": self._mainline_executor_contract_payload().get("rt_executor", {}).get("phase", "idle"),
                "active_nrt_profile": self._hardware_lifecycle_contract_payload().get("active_nrt_profile", ""),
            }

        def _clinical_mainline_contract_payload(self) -> dict[str, Any]:
            identity = self.identity_service.resolve(self.config.robot_model, self.config.sdk_robot_class, self.config.axis_count)
            return {
                "robot_model": identity.robot_model,
                "clinical_mainline_mode": identity.rt_mode,
                "required_sequence": ["connect_robot", "power_on", "set_auto_mode", "lock_session", "load_scan_plan", "start_procedure", "safe_retreat"],
                "runtime_owned_phase_sequence": ["approach_prescan", "seek_contact", "contact_hold", "scan_follow", "controlled_retract"],
                "single_control_source_required": identity.requires_single_control_source,
                "preferred_link": identity.preferred_link,
                "rt_loop_hz": 1000,
                "cartesian_impedance_limits": list(identity.cartesian_impedance_limits),
                "desired_wrench_limits": list(identity.desired_wrench_limits),
            }

        def _runtime_profile_payload(self) -> dict[str, Any]:
            return {
                "robot_model": self.config.robot_model,
                "sdk_robot_class": self.config.sdk_robot_class,
                "axis_count": int(self.config.axis_count),
                "remote_ip": self.config.remote_ip,
                "local_ip": self.config.local_ip,
                "preferred_link": self.config.preferred_link,
                "rt_mode": self.config.rt_mode,
                "rt_network_tolerance_percent": int(self.config.rt_network_tolerance_percent),
                "joint_filter_hz": float(self.config.joint_filter_hz),
                "cart_filter_hz": float(self.config.cart_filter_hz),
                "torque_filter_hz": float(self.config.torque_filter_hz),
                "collision_detection_enabled": bool(self.config.collision_detection_enabled),
                "soft_limit_enabled": bool(self.config.soft_limit_enabled),
                "tool_name": self.config.tool_name,
                "tcp_name": self.config.tcp_name,
                "load_kg": float(self.config.load_kg),
                "cartesian_impedance": list(self.config.cartesian_impedance),
                "desired_wrench_n": list(self.config.desired_wrench_n),
            }

        def _executor_profile_payload(self) -> dict[str, Any]:
            executor = self._mainline_executor_contract_payload()
            return {
                "nrt_templates": [item.get("name", "") for item in executor.get("nrt_executor", {}).get("templates", [])],
                "rt_nominal_loop_hz": int(executor.get("rt_executor", {}).get("nominal_loop_hz", 1000) or 1000),
                "rt_monitors": {
                    "reference_limiter": bool(executor.get("rt_executor", {}).get("reference_limiter_enabled", False)),
                    "freshness_guard": bool(executor.get("rt_executor", {}).get("freshness_guard_enabled", False)),
                    "jitter_monitor": bool(executor.get("rt_executor", {}).get("jitter_monitor_enabled", False)),
                    "contact_band_monitor": bool(executor.get("rt_executor", {}).get("contact_band_monitor_enabled", False)),
                },
            }

        def _hardware_lifecycle_contract_payload(self) -> dict[str, Any]:
            lifecycle_state = 'boot'
            if self.controller_online:
                lifecycle_state = 'connected'
            if self.controller_online and self.powered:
                lifecycle_state = 'powered'
            if self.controller_online and self.powered and self.operate_mode == 'AUTO':
                lifecycle_state = 'auto_ready'
            if self.execution_state in {SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD}:
                lifecycle_state = 'rt_active'
            elif self.execution_state in {SystemState.PATH_VALIDATED, SystemState.APPROACHING, SystemState.RETREATING, SystemState.SCAN_COMPLETE}:
                lifecycle_state = 'nrt_ready'
            state_channel_ready = bool(self.controller_online)
            motion_channel_ready = bool(self.controller_online and self.powered)
            aux_channel_ready = bool(self.controller_online)
            live_takeover = bool(self.controller_online and self.powered and self.operate_mode == 'AUTO')
            return {
                'summary_state': 'warning' if not live_takeover else 'ready',
                'summary_label': 'hardware lifecycle ready' if live_takeover else 'hardware lifecycle contract only',
                'detail': 'Mock runtime exposes hardware-layer lifecycle and channel readiness without claiming live SDK control.',
                'runtime_source': 'mock_runtime_contract',
                'sdk_binding_mode': 'contract_only',
                'lifecycle_state': lifecycle_state,
                'controller_manager_model': 'hardware_layer__read_update_write',
                'transport_ready': bool(self.controller_online),
                'motion_channel_ready': motion_channel_ready,
                'state_channel_ready': state_channel_ready,
                'aux_channel_ready': aux_channel_ready,
                'network_healthy': bool(self.controller_online),
                'control_source_exclusive': bool(self.config.requires_single_control_source),
                'active_nrt_profile': 'safe_retreat' if self.execution_state == SystemState.RETREATING else ('approach_prescan' if self.execution_state == SystemState.APPROACHING else ''),
                'active_rt_phase': 'scan_follow' if self.execution_state == SystemState.SCANNING else ('pause_hold' if self.execution_state == SystemState.PAUSED_HOLD else ('contact_hold' if self.execution_state == SystemState.CONTACT_STABLE else ('seek_contact' if self.execution_state == SystemState.CONTACT_SEEKING else 'idle'))),
                'command_sequence': int(self.frame_id),
                'live_takeover_ready': live_takeover,
                'single_control_source_required': bool(self.config.requires_single_control_source),
            }

        def _rt_kernel_contract_payload(self) -> dict[str, Any]:
            executor = self._mainline_executor_contract_payload()
            rt_executor = dict(executor.get('rt_executor', {}))
            jitter_budget_ms = round(max(0.25, 1000.0 / float(rt_executor.get('nominal_loop_hz', 1000) or 1000) * 0.2), 3)
            freshness_budget_ms = int(self.config.pressure_stale_ms)
            return {
                'summary_state': 'warning' if not self.controller_online else 'ready',
                'summary_label': 'rt kernel wrapped by official sdk lifecycle' if self.controller_online else 'rt kernel contract only',
                'detail': 'RT kernel follows read/update/write staging and keeps limiter/guard semantics outside the official controller.',
                'runtime_source': 'mock_runtime_contract',
                'nominal_loop_hz': int(rt_executor.get('nominal_loop_hz', 1000) or 1000),
                'read_update_write': ['read_state', 'update_phase_policy', 'write_command'],
                'phase': str(rt_executor.get('phase', 'idle')),
                'monitors': {
                    'reference_limiter': bool(rt_executor.get('reference_limiter_enabled', False)),
                    'freshness_guard': bool(rt_executor.get('freshness_guard_enabled', False)),
                    'jitter_monitor': bool(rt_executor.get('jitter_monitor_enabled', False)),
                    'contact_band_monitor': bool(rt_executor.get('contact_band_monitor_enabled', False)),
                    'network_guard': True,
                },
                'jitter_budget_ms': jitter_budget_ms,
                'current_period_ms': round(1000.0 / float(rt_executor.get('nominal_loop_hz', 1000) or 1000), 3),
                'freshness_budget_ms': freshness_budget_ms,
                'reference_limits': {
                    'max_cart_step_mm': 2.5,
                    'max_force_delta_n': 1.0,
                },
                'fixed_period_enforced': True,
                'network_healthy': bool(self.controller_online),
                'overrun_count': 0 if self.rt_jitter_ok else 1,
                'max_cycle_ms': round(1.0 if self.rt_jitter_ok else 1.6, 3),
                'last_wake_jitter_ms': round(0.05 if self.rt_jitter_ok else 0.45, 3),
                'rt_quality_gate_passed': bool(self.rt_jitter_ok),
                'last_sensor_decision': 'fresh' if self.pressure_fresh and self.robot_state_fresh else ('stale' if self.controller_online else 'unavailable'),
                'sample_count': 3,
                'loop_samples': [
                    {'execution_ms': round(0.94 if self.rt_jitter_ok else 1.05, 3), 'wake_jitter_ms': round(0.03 if self.rt_jitter_ok else 0.08, 3), 'overrun': False},
                    {'execution_ms': round(0.98 if self.rt_jitter_ok else 1.32, 3), 'wake_jitter_ms': round(0.04 if self.rt_jitter_ok else 0.42, 3), 'overrun': bool(not self.rt_jitter_ok)},
                    {'execution_ms': round(1.0 if self.rt_jitter_ok else 1.41, 3), 'wake_jitter_ms': round(0.05 if self.rt_jitter_ok else 0.46, 3), 'overrun': bool(not self.rt_jitter_ok)},
                ],
                'degraded_without_sdk': True,
            }

        def _session_drift_contract_payload(self) -> dict[str, Any]:
            runtime_profile_hash = payload_hash(self._runtime_profile_payload())
            sdk_boundary = build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm)
            sdk_boundary_hash = str(sdk_boundary.get('contract_hash', '')) or payload_hash(sdk_boundary)
            executor_hash = payload_hash(self._executor_profile_payload())
            drifts: list[dict[str, Any]] = []
            if self.session_id:
                if self.locked_runtime_config_hash and self.locked_runtime_config_hash != runtime_profile_hash:
                    drifts.append({'name': 'runtime_profile_hash', 'detail': 'runtime config drifted after session lock'})
                if self.locked_sdk_boundary_hash and self.locked_sdk_boundary_hash != sdk_boundary_hash:
                    drifts.append({'name': 'sdk_boundary_hash', 'detail': 'sdk boundary/unit contract drifted after session lock'})
                if self.locked_executor_hash and self.locked_executor_hash != executor_hash:
                    drifts.append({'name': 'executor_profile_hash', 'detail': 'executor profile drifted after session lock'})
                if self.locked_scan_plan_hash and self.plan_hash and self.locked_scan_plan_hash != self.plan_hash:
                    drifts.append({'name': 'plan_hash', 'detail': 'locked plan hash does not match active plan hash'})
            summary_state = 'ready' if not drifts else 'blocked'
            return {
                'summary_state': summary_state,
                'summary_label': 'hard freeze consistent' if summary_state == 'ready' else 'hard freeze drift detected',
                'detail': 'Session hard freeze watches runtime profile, SDK boundary contract, executor profile, and plan hash.',
                'session_locked': bool(self.session_id),
                'locked_runtime_config_hash': self.locked_runtime_config_hash,
                'active_runtime_config_hash': runtime_profile_hash,
                'locked_sdk_boundary_hash': self.locked_sdk_boundary_hash,
                'active_sdk_boundary_hash': sdk_boundary_hash,
                'locked_executor_hash': self.locked_executor_hash,
                'active_executor_hash': executor_hash,
                'locked_scan_plan_hash': self.locked_scan_plan_hash,
                'active_plan_hash': self.plan_hash,
                'drifts': drifts,
            }

        def _session_freeze_payload(self) -> dict[str, Any]:
            runtime_profile_hash = payload_hash(self._runtime_profile_payload())
            sdk_boundary = build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm)
            executor_hash = payload_hash(self._executor_profile_payload())
            return {
                "session_locked": bool(self.session_id),
                "session_id": self.session_id,
                "session_dir": str(self.session_dir) if self.session_dir else "",
                "locked_at_ns": int(self.session_locked_ts_ns),
                "plan_hash": self.plan_hash,
                "active_segment": int(self.active_segment),
                "tool_name": self.config.tool_name,
                "tcp_name": self.config.tcp_name,
                "load_kg": self.config.load_kg,
                "rt_mode": self.config.rt_mode,
                "cartesian_impedance": list(self.config.cartesian_impedance),
                "desired_wrench_n": list(self.config.desired_wrench_n),
                "freeze_version": "hard_freeze_v2",
                "runtime_profile_hash": runtime_profile_hash,
                "sdk_boundary_hash": str(sdk_boundary.get('contract_hash', '')),
                "executor_profile_hash": executor_hash,
            }

        def _authoritative_runtime_envelope_payload(self) -> dict[str, Any]:
            authority_state = 'ready' if self.controller_online else 'degraded'
            authority_label = 'mock runtime authority ready' if authority_state == 'ready' else 'mock runtime authority degraded'
            if self.last_final_verdict:
                final_verdict = dict(self.last_final_verdict)
            else:
                final_verdict = {
                    'summary_state': 'idle',
                    'summary_label': '运行时前检',
                    'detail': 'no final verdict compiled',
                    'final_verdict': {
                        'accepted': False,
                        'reason': 'no final verdict compiled',
                        'policy_state': 'idle',
                        'source': 'cpp_robot_core',
                        'advisory_only': False,
                    },
                    'plan_metrics': {'plan_id': getattr(self.scan_plan, 'plan_id', '') if hasattr(self.scan_plan, 'plan_id') else '', 'plan_hash': self.plan_hash},
                    'authority_source': 'cpp_robot_core',
                    'warnings': [],
                    'blockers': [],
                }
            return {
                'summary_state': authority_state,
                'summary_label': authority_label,
                'detail': 'mock runtime contract-replay authority surface',
                'authority_source': 'mock_runtime_contract',
                'authority_semantics': 'contract_replay_only',
                'control_authority': {
                    'summary_state': authority_state,
                    'summary_label': authority_label,
                    'detail': 'mock runtime owns the in-process contract-replay state surface',
                    'owner': {
                        'actor_id': 'mock-runtime',
                        'workspace': 'runtime',
                        'role': 'runtime',
                        'session_id': self.session_id,
                    },
                    'active_lease': {
                        'lease_id': 'mock-runtime-authority',
                        'actor_id': 'mock-runtime',
                        'workspace': 'runtime',
                        'role': 'runtime',
                        'session_id': self.session_id,
                        'expires_in_s': 0,
                        'source': 'mock_runtime_contract',
                    },
                    'owner_provenance': {'source': 'mock_runtime_contract'},
                    'workspace_binding': 'runtime',
                    'session_binding': self.session_id,
                    'blockers': [],
                    'warnings': [],
                },
                'runtime_config_applied': self._sdk_runtime_config_payload(),
                'session_freeze': self._session_freeze_payload(),
                'final_verdict': final_verdict,
                'plan_digest': {
                    'plan_id': str(final_verdict.get('plan_metrics', {}).get('plan_id', '')),
                    'plan_hash': str(final_verdict.get('plan_metrics', {}).get('plan_hash', self.plan_hash)),
                    'active_segment': int(self.active_segment),
                    'session_id': self.session_id,
                },
                'protocol_version': 1,
            }

        def _control_governance_contract_payload(self) -> dict[str, Any]:
            session_locked = bool(self.session_id)
            drift_contract = self._session_drift_contract_payload()
            runtime_binding_valid = session_locked and not drift_contract.get('drifts')
            return {
                "single_control_source_required": bool(self.config.requires_single_control_source),
                "control_authority_expected_source": "cpp_robot_core",
                "write_surface": "core_runtime_only",
                "current_execution_state": self.execution_state.value,
                "controller_online": bool(self.controller_online),
                "powered": bool(self.powered),
                "automatic_mode": self.operate_mode == "AUTO",
                "session_binding_valid": runtime_binding_valid,
                "runtime_config_bound": session_locked,
                "session_id": self.session_id,
                "active_plan_hash": self.plan_hash,
                "locked_scan_plan_hash": self.locked_scan_plan_hash,
                "tool_ready": bool(self.tool_ready),
                "tcp_ready": bool(self.tcp_ready),
                "load_ready": bool(self.load_ready),
                "rt_ready": bool(self.controller_online and self.powered and self.operate_mode == "AUTO" and self.config.rt_mode == "cartesianImpedance"),
                "nrt_ready": bool(self.controller_online and self.powered),
                "lifecycle_state": self._hardware_lifecycle_contract_payload().get('lifecycle_state', 'boot'),
                "detail": "single control source contract requires session freeze + AUTO + powered + contract-aligned rt mode + no hard-freeze drift",
            }

        def _controller_evidence_payload(self) -> dict[str, Any]:
            rt_kernel = self._rt_kernel_contract_payload()
            return {
                "runtime_source": "mock_runtime_contract",
                "last_event": self.last_event,
                "last_controller_log": self.last_controller_log,
                "controller_log_tail": list(self.controller_logs[-6:]),
                "rl_status": dict(self.rl_status),
                "drag_state": dict(self.drag_state),
                "registers": {"segment": int(self.active_segment), "frame": int(self.frame_id), "command_sequence": int(self.frame_id)},
                "pending_alarm_count": len(self.pending_alarms),
                "fault_code": self.fault_code,
                "last_nrt_profile": 'safe_retreat' if self.execution_state == SystemState.RETREATING else ('approach_prescan' if self.execution_state == SystemState.APPROACHING else ''),
                "last_rt_phase": str(rt_kernel.get('phase', 'idle')),
                "reason_chain": [
                    item for item in [
                        self.last_event or '',
                        self.recovery_reason or '',
                        self.last_recovery_action or '',
                        self.fault_code or '',
                    ] if item
                ],
            }

        def _dual_state_machine_contract_payload(self) -> dict[str, Any]:
            runtime_state = self.execution_state.value
            clinical_task_state = {
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
                'PAUSED_HOLD': 'paused_hold',
                'RETREATING': 'controlled_retract',
                'SCAN_COMPLETE': 'completed',
                'FAULT': 'fault',
                'ESTOP': 'estop',
            }.get(runtime_state, 'boot')
            aligned = True
            detail = '执行状态机与临床任务状态机已通过映射规则对齐。'
            if runtime_state == 'SCANNING' and clinical_task_state != 'scan_follow':
                aligned = False
                detail = 'SCANNING 必须映射到 scan_follow。'
            execution_permissions = {
                'allow_nrt': runtime_state in {'AUTO_READY', 'SESSION_LOCKED', 'PATH_VALIDATED', 'SCAN_COMPLETE'},
                'allow_rt_seek': runtime_state in {'PATH_VALIDATED', 'APPROACHING', 'CONTACT_SEEKING'},
                'allow_rt_scan': runtime_state in {'CONTACT_STABLE', 'SCANNING', 'PAUSED_HOLD'},
                'allow_retract': runtime_state not in {'BOOT', 'DISCONNECTED', 'ESTOP'},
            }
            return {
                'summary_state': 'ready' if aligned else 'blocked',
                'summary_label': '双层状态机已对齐' if aligned else '双层状态机冲突',
                'detail': detail,
                'runtime_state': runtime_state,
                'clinical_task_state': clinical_task_state,
                'execution_and_clinical_aligned': aligned,
                'execution_permissions': execution_permissions,
            }

        def _mainline_executor_contract_payload(self) -> dict[str, Any]:
            runtime_state = self.execution_state.value
            rt_phase = {
                'APPROACHING': 'idle',
                'CONTACT_SEEKING': 'seek_contact',
                'CONTACT_STABLE': 'contact_hold',
                'SCANNING': 'scan_follow',
                'PAUSED_HOLD': 'pause_hold',
                'RETREATING': 'controlled_retract',
            }.get(runtime_state, 'idle')
            nrt_templates = [
                {'name': 'go_home', 'sdk_delegate': 'MoveAbsJ', 'blocking': True, 'preconditions': ['connected', 'powered']},
                {'name': 'approach_prescan', 'sdk_delegate': 'MoveL', 'blocking': True, 'preconditions': ['session_locked', 'plan_validated', 'auto_mode']},
                {'name': 'approach_entry', 'sdk_delegate': 'MoveL', 'blocking': True, 'preconditions': ['session_locked', 'plan_validated', 'auto_mode']},
                {'name': 'safe_retreat', 'sdk_delegate': 'MoveL', 'blocking': True, 'preconditions': ['connected', 'powered']},
            ]
            rt_executor = {
                'summary_state': 'warning' if not self.controller_online else 'ready',
                'detail': 'RT executor wraps official cartesianImpedance mainline and keeps limiter/guard semantics in the runtime shell.',
                'phase': rt_phase,
                'phase_group': 'scan' if rt_phase in {'contact_hold', 'scan_follow', 'pause_hold'} else ('recovery' if rt_phase == 'controlled_retract' else ('contact' if rt_phase == 'seek_contact' else 'idle')),
                'nominal_loop_hz': 1000,
                'reference_limiter_enabled': True,
                'freshness_guard_enabled': True,
                'jitter_monitor_enabled': True,
                'contact_band_monitor_enabled': True,
                'network_guard_enabled': True,
                'fixed_period_enforced': True,
                'network_healthy': bool(self.controller_online),
                'overrun_count': 0 if self.rt_jitter_ok else 1,
                'last_sensor_decision': 'fresh' if self.pressure_fresh and self.robot_state_fresh else ('stale' if self.controller_online else 'unavailable'),
                'max_cycle_ms': round(1.0 if self.rt_jitter_ok else 1.6, 3),
                'last_wake_jitter_ms': round(0.05 if self.rt_jitter_ok else 0.45, 3),
                'rt_quality_gate_passed': bool(self.rt_jitter_ok),
                'delegation_policy': 'official_sdk_rt_loop_only',
            }
            nrt_executor = {
                'summary_state': 'warning' if not self.controller_online else 'ready',
                'detail': 'NRT executor only submits templated MoveAbsJ/MoveL intents and delegates planning to the official SDK.',
                'templates': nrt_templates,
                'last_blocking_template': 'approach_prescan' if runtime_state == 'APPROACHING' else ('safe_retreat' if runtime_state == 'RETREATING' else ''),
                'requires_move_reset': True,
                'requires_single_control_source': bool(self.config.requires_single_control_source),
                'last_result': 'accepted' if self.controller_online and self.powered and self.operate_mode == 'AUTO' else 'contract_only',
                'delegation_policy': 'official_sdk_nrt_only',
            }
            task_tree_aligned = not (runtime_state == 'SCANNING' and rt_phase != 'scan_follow')
            return {
                'summary_state': 'ready' if task_tree_aligned else 'blocked',
                'summary_label': '主线执行器已对齐' if task_tree_aligned else '主线执行器未对齐',
                'detail': 'NRT/RT executor 合同描述的是意图、阶段与监测器，不替代官方控制器。',
                'task_tree_aligned': task_tree_aligned,
                'nrt_executor': nrt_executor,
                'rt_executor': rt_executor,
            }

        def _mainline_task_tree_payload(self) -> dict[str, Any]:
            return dict(self.mainline_task_tree.build(
                config=self.config,
                sdk_runtime={
                    'control_governance_contract': self._control_governance_contract_payload(),
                    'clinical_mainline_contract': self._clinical_mainline_contract_payload(),
                    'release_contract': self._release_contract_payload(),
                    'mainline_executor_contract': self._mainline_executor_contract_payload(),
                    'dual_state_machine_contract': self._dual_state_machine_contract_payload(),
                    'environment_doctor': {'summary_state': 'warning', 'summary_label': 'mock environment', 'detail': 'mock runtime; live SDK not attached'},
                    'hardware_lifecycle_contract': self._hardware_lifecycle_contract_payload(),
                    'rt_kernel_contract': self._rt_kernel_contract_payload(),
                    'session_freeze': self._session_freeze_payload(),
                    'session_drift_contract': self._session_drift_contract_payload(),
                    'safety_recovery_contract': self._safety_recovery_contract_payload(),
                },
                backend_link={},
                model_report={'final_verdict': dict(self.last_final_verdict.get('final_verdict', {}))},
                session_governance={'summary_state': 'ready' if self.session_id else 'warning'},
            ))

        def _capability_contract_payload(self) -> dict[str, Any]:
            robot_snapshot = {"operate_mode": self.operate_mode, "powered": self.powered}
            return dict(self.capability_service.build(self.config, robot_snapshot))

        def _model_authority_contract_payload(self) -> dict[str, Any]:
            identity = self.identity_service.resolve(self.config.robot_model, self.config.sdk_robot_class, self.config.axis_count)
            family = self.family_registry.resolve(self.config)
            return {
                "authoritative_kernel": "cpp_robot_core",
                "runtime_source": "mock_runtime_contract",
                "family_key": family.family_key,
                "family_label": family.family_label,
                "robot_model": identity.robot_model,
                "sdk_robot_class": identity.sdk_robot_class,
                "planner_supported": bool(identity.supports_planner),
                "xmate_model_supported": bool(identity.supports_xmate_model),
                "authoritative_precheck": False,
                "authoritative_runtime": False,
                "approximate_advisory_allowed": True,
                "planner_primitives": ["JointMotionGenerator", "CartMotionGenerator", "FollowPosition"],
                "model_methods": ["robot.model()", "getCartPose", "getJointPos", "jacobian", "getTorque"],
                "warnings": [
                    {"name": "model_authority", "detail": "mock runtime does not execute vendored C++ xMateModel / Planner"}
                ],
            }

        def _safety_recovery_contract_payload(self) -> dict[str, Any]:
            recovery_state = self._recovery_state()
            summary_state = 'ready'
            summary_label = 'safety/recovery kernel'
            if recovery_state in {'ControlledRetract', 'Holding'}:
                summary_state = 'warning'
                summary_label = 'safety/recovery active'
            elif recovery_state == 'EstopLatched':
                summary_state = 'blocked'
                summary_label = 'safety/recovery latched'
            return {
                "summary_state": summary_state,
                "summary_label": summary_label,
                "detail": "Mock runtime exposes frozen safety/recovery policy layers without claiming live controller authority.",
                "policy_layers": ["L0_hard_block", "L1_runtime_guard", "L2_auto_recovery", "L3_evidence_ack"],
                "supported_actions": ["pause_hold", "controlled_retract", "retry_wait_stable", "retry_ready", "estop_latched"],
                "pause_resume_enabled": True,
                "safe_retreat_enabled": True,
                "operator_ack_required_for_fault_latched": True,
                "runtime_guard_enforced": True,
                "recovery_state": recovery_state,
                "collision_behavior": self.config.collision_behavior,
                "resume_force_band_n": self.force_control["resume_force_band_n"],
                "warning_z_force_n": self.force_control["warning_z_force_n"],
                "max_z_force_n": self.force_control["max_z_force_n"],
                "sensor_timeout_ms": self.force_control["sensor_timeout_ms"],
                "stale_telemetry_ms": self.force_control["stale_telemetry_ms"],
                "emergency_retract_mm": self.force_control["emergency_retract_mm"],
            }

        def _recovery_contract_payload(self) -> dict[str, Any]:
            return dict(self._safety_recovery_contract_payload())

        def _sdk_runtime_config_payload(self) -> dict[str, Any]:
            return {
                "robot_model": self.config.robot_model,
                "sdk_robot_class": self.config.sdk_robot_class,
                "remote_ip": self.config.remote_ip,
                "local_ip": self.config.local_ip,
                "axis_count": self.config.axis_count,
                "rt_network_tolerance_percent": self.config.rt_network_tolerance_percent,
                "joint_filter_hz": self.config.joint_filter_hz,
                "cart_filter_hz": self.config.cart_filter_hz,
                "torque_filter_hz": self.config.torque_filter_hz,
                "cartesian_impedance": list(self.config.cartesian_impedance),
                "desired_wrench_n": list(self.config.desired_wrench_n),
                "fc_frame_type": self.config.fc_frame_type,
                "fc_frame_matrix": list(self.config.fc_frame_matrix),
                "tcp_frame_matrix": list(self.config.tcp_frame_matrix),
                "load_com_mm": list(self.config.load_com_mm),
                "load_inertia": list(self.config.load_inertia),
                "rt_stale_state_timeout_ms": self.config.rt_stale_state_timeout_ms,
                "rt_phase_transition_debounce_cycles": self.config.rt_phase_transition_debounce_cycles,
                "rt_max_cart_step_mm": self.config.rt_max_cart_step_mm,
                "contact_force_target_n": self.config.contact_force_target_n,
                "scan_force_target_n": self.config.scan_force_target_n,
                "retract_timeout_ms": self.config.retract_timeout_ms,
                "rt_phase_contract": self.config.build_rt_phase_contract(),
                "sdk_boundary_units": build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm),
            }

        def _release_contract_payload(self) -> dict[str, Any]:
            safety = self._safety_status()
            drift_contract = self._session_drift_contract_payload()
            hardware = self._hardware_lifecycle_contract_payload()
            freeze_consistent = bool(self.session_id) and bool(self.session_dir) and self.tool_ready and self.tcp_ready and self.load_ready and not drift_contract.get('drifts')
            final_verdict = dict(self.last_final_verdict.get("final_verdict", {}))
            blockers = list(self.last_final_verdict.get("blockers", []))
            warnings = list(self.last_final_verdict.get("warnings", []))
            if drift_contract.get('drifts'):
                blockers.append({'name': 'hard_freeze_drift', 'detail': 'session hard freeze drift detected'})
            if hardware.get('summary_state') in {'warning', 'degraded'}:
                warnings.append({'name': 'hardware_lifecycle_not_live', 'detail': str(hardware.get('detail', 'hardware lifecycle not live'))})
            release_allowed = bool(final_verdict.get("accepted")) and freeze_consistent and not safety.get("active_interlocks")
            return {
                "summary_state": 'ready' if release_allowed else ('blocked' if blockers or safety.get('active_interlocks') else 'warning'),
                "session_locked": bool(self.session_id),
                "session_freeze_consistent": freeze_consistent,
                "locked_scan_plan_hash": self.locked_scan_plan_hash,
                "active_plan_hash": self.plan_hash,
                "runtime_source": "mock_runtime_contract",
                "compile_ready": bool(final_verdict.get("accepted")) and freeze_consistent,
                "ready_for_approach": bool(final_verdict.get("accepted")) and freeze_consistent and self.execution_state == SystemState.PATH_VALIDATED,
                "ready_for_scan": bool(final_verdict.get("accepted")) and freeze_consistent and self.execution_state == SystemState.CONTACT_STABLE,
                "release_recommendation": "allow" if release_allowed else "block",
                "active_interlocks": list(safety.get("active_interlocks", [])),
                "final_verdict": final_verdict,
                "blockers": blockers,
                "warnings": warnings,
                "active_injections": sorted(self.injected_faults),
                'hardware_lifecycle': {'summary_state': hardware.get('summary_state', 'unknown'), 'lifecycle_state': hardware.get('lifecycle_state', 'boot')},
                'hard_freeze': {'summary_state': drift_contract.get('summary_state', 'unknown'), 'drift_count': len(drift_contract.get('drifts', []))},
            }

        def _deployment_contract_payload(self) -> dict[str, Any]:
            identity = self.identity_service.resolve(self.config.robot_model, self.config.sdk_robot_class, self.config.axis_count)
            profile = self.deployment_profiles.build_snapshot(self.config)
            return {
                "runtime_source": "mock_runtime_contract",
                "vendored_sdk_required": True,
                "vendored_sdk_detected": False,
                "xmate_model_detected": False,
                "preferred_link": identity.preferred_link,
                "single_control_source_required": identity.requires_single_control_source,
                "required_host_dependencies": ["cmake", "g++/clang++", "openssl headers", "Eigen headers (or vendored SDK external/Eigen)"],
                "required_runtime_materials": ["configs/tls/runtime/*", "vendored librokae include/lib/external"],
                "bringup_sequence": ["doctor_runtime.py", "generate_dev_tls_cert.sh", "start_real.sh", "run.py --backend core"],
                "systemd_units": ["spine-cpp-core.service", "spine-python-api.service", "spine-ultrasound.target"],
                "summary_state": "warning",
                "summary_label": "mock deployment contract",
                "detail": "Mock runtime advertises the frozen deployment profile matrix without claiming live bring-up.",
                **profile,
            }

        def _fault_injection_contract_payload(self) -> dict[str, Any]:
            catalog = [
                {"name": "pressure_stale", "effect": "forces stale telemetry watchdog and estop path", "phase_scope": ["CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"], "recoverable": False},
                {"name": "rt_jitter_high", "effect": "marks RT jitter interlock active", "phase_scope": ["CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"], "recoverable": True},
                {"name": "overpressure", "effect": "forces pressure above upper bound and pause/retreat logic", "phase_scope": ["CONTACT_STABLE", "SCANNING"], "recoverable": True},
                {"name": "collision_event", "effect": "injects recoverable collision alarm and retreat", "phase_scope": ["APPROACHING", "CONTACT_SEEKING", "SCANNING"], "recoverable": True},
                {"name": "start_procedure_phase_fault", "effect": "forces runtime-owned recovery during start_procedure(scan)", "phase_scope": ["PATH_VALIDATED", "APPROACHING", "CONTACT_SEEKING"], "recoverable": True},
                {"name": "plan_hash_mismatch", "effect": "breaks locked plan hash consistency", "phase_scope": ["SESSION_LOCKED", "PATH_VALIDATED"], "recoverable": True},
                {"name": "estop_latch", "effect": "forces ESTOP latched state", "phase_scope": ["*"], "recoverable": False},
            ]
            return {
                "runtime_source": "mock_runtime_contract",
                "enabled": True,
                "simulation_only": True,
                "active_injections": sorted(self.injected_faults),
                "catalog": catalog,
            }

        def compile_scan_plan_verdict(self, plan_payload: dict[str, Any] | None, config_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
            config = RuntimeConfig.from_dict(dict(config_snapshot or self.config.to_dict()))
            plan = None
            plan_error = ""
            if plan_payload:
                try:
                    plan = ScanPlan.from_dict(dict(plan_payload))
                except Exception:
                    plan = None
                    plan_error = "scan plan parse failed"
                if not plan_error:
                    plan_error = self._validate_scan_plan(dict(plan_payload))
            advisory = self.model_service.build_report(plan, config)
            capability = self.capability_service.build(config, {"operate_mode": self.operate_mode, "powered": self.powered})
            baseline = self.clinical_config_service.build_report(config)
            blockers = list(advisory.get('blockers', [])) + list(capability.get('blockers', [])) + list(baseline.get('blockers', []))
            warnings = list(advisory.get('warnings', [])) + list(capability.get('warnings', [])) + list(baseline.get('warnings', []))
            if plan_error:
                blockers.append({"name": "scan_plan", "severity": "blocker", "detail": plan_error})
            if self.locked_scan_plan_hash and plan is not None and getattr(plan, 'plan_hash', '') and self.locked_scan_plan_hash != plan.plan_hash:
                blockers.append({"name": "session_freeze", "severity": "blocker", "detail": "plan_hash does not match locked session freeze"})
            summary_state = 'blocked' if blockers else ('warning' if warnings else 'ready')
            accepted = summary_state != 'blocked'
            evidence_id = f"mock-verdict:{plan.plan_id if plan is not None else 'none'}:{self.session_id or 'unlocked'}"
            detail = str(advisory.get('detail', '')) if accepted else str(blockers[0].get('detail', 'compile blocked'))
            verdict = {
                'summary_state': summary_state,
                'summary_label': {
                    'ready': '模型前检通过',
                    'warning': '模型前检告警',
                    'blocked': '模型前检阻塞',
                    'idle': '未生成路径',
                }.get(summary_state, '运行时前检'),
                'detail': detail,
                'warnings': warnings,
                'blockers': blockers,
                'authority_source': 'cpp_robot_core',
                'verdict_kind': 'final',
                'approximate': False,
                'model_contract': dict(advisory.get('model_contract', {})),
                'plan_metrics': dict(advisory.get('plan_metrics', {})),
                'execution_selection': dict(advisory.get('execution_selection', {})),
                'capability_contract': capability,
                'baseline_contract': baseline,
                'model_authority_contract': self._model_authority_contract_payload(),
                'advisory_python': advisory,
                'final_verdict': {
                    'accepted': accepted,
                    'reason': detail,
                    'evidence_id': evidence_id,
                    'expected_state_delta': {'next_state': 'lock_session' if accepted and not self.session_id else ('load_scan_plan' if accepted else 'replan_required')},
                    'policy_state': summary_state,
                    'source': 'cpp_robot_core',
                    'advisory_only': False,
                },
            }
            self.last_final_verdict = verdict
            return verdict
