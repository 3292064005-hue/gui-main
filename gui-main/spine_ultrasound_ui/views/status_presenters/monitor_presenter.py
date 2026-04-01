from __future__ import annotations

from .common import StatusViewContext, join_lines


class MonitorPresenter:
    def apply(self, ctx: StatusViewContext) -> None:
        window = ctx.window
        metrics = ctx.metrics
        pose = ctx.pose
        pose_text = f"x={pose['x']:.1f}, y={pose['y']:.1f}, z={pose['z']:.1f}, rx={pose['rx']:.1f}, ry={pose['ry']:.1f}, rz={pose['rz']:.1f}"
        window.robot_monitor_page.lbl_joint_pos.setText(str(metrics["joint_pos"]))
        window.robot_monitor_page.lbl_joint_vel.setText(str(metrics["joint_vel"]))
        window.robot_monitor_page.lbl_joint_torque.setText(str(metrics["joint_torque"]))
        window.robot_monitor_page.lbl_tcp.setText(pose_text)
        window.robot_monitor_page.lbl_cart_force.setText(str(metrics["cart_force"]))
        window.robot_monitor_page.lbl_operate_mode.setText(ctx.robot.get("operate_mode", "-"))
        window.robot_monitor_page.lbl_power_state.setText("ON" if ctx.robot.get("powered", False) else "OFF")
        window.robot_monitor_page.lbl_rl_state.setText(f"{ctx.rl_status.get('loaded_project', '-')}/{ctx.rl_status.get('loaded_task', '-')} / {'RUN' if ctx.rl_status.get('running') else 'IDLE'}")
        window.robot_monitor_page.lbl_drag.setText(f"{'ON' if ctx.drag_status.get('enabled') else 'OFF'} / {ctx.drag_status.get('space', '-')} / {ctx.drag_status.get('type', '-')}")

        controller_logs = list(ctx.sdk_runtime.get('controller_logs', []))
        if controller_logs:
            window.robot_monitor_page.log_view.setPlainText(join_lines([f"[{item.get('level', '-')}] {item.get('source', '-')}: {item.get('message', '-')}" for item in controller_logs], "暂无控制器日志。"))

        rl_projects = list(ctx.sdk_runtime.get('rl_projects', []))
        io_snapshot = dict(ctx.sdk_runtime.get('io_snapshot', {}))
        path_library = list(ctx.sdk_runtime.get('path_library', []))
        safety_profile = dict(ctx.sdk_runtime.get('safety_profile', {}))
        motion_contract = dict(ctx.sdk_runtime.get('motion_contract', {}))
        register_snapshot = dict(ctx.sdk_runtime.get('register_snapshot', {}))
        runtime_alignment = dict(ctx.sdk_runtime.get('runtime_alignment', {}))
        xmate_model_summary = dict(ctx.sdk_runtime.get('xmate_model_summary', {}))
        runtime_config_snapshot = dict(ctx.sdk_runtime.get('runtime_config_snapshot', {}))
        environment_doctor = dict(ctx.sdk_runtime.get('environment_doctor', {}))
        identity_contract = dict(ctx.sdk_runtime.get('identity_contract', {}))
        clinical_mainline_contract = dict(ctx.sdk_runtime.get('clinical_mainline_contract', {}))
        capability_contract = dict(ctx.sdk_runtime.get('capability_contract', {}))
        model_authority_contract = dict(ctx.sdk_runtime.get('model_authority_contract', {}))
        session_freeze = dict(ctx.sdk_runtime.get('session_freeze', {}))
        recovery_contract = dict(ctx.sdk_runtime.get('recovery_contract', {}))
        release_contract = dict(ctx.sdk_runtime.get('release_contract', {}))
        asset_lines = [
            f"RL 状态：{ctx.rl_status.get('loaded_project', '-')}/{ctx.rl_status.get('loaded_task', '-')} / {'RUN' if ctx.rl_status.get('running') else 'IDLE'}",
            f"拖动示教：{'ON' if ctx.drag_status.get('enabled') else 'OFF'} / {ctx.drag_status.get('space', '-')} / {ctx.drag_status.get('type', '-')}",
            "",
            "RL 工程:",
        ]
        asset_lines.extend([f"- {item.get('name')} :: tasks={', '.join(item.get('tasks', []))}" for item in rl_projects] or ["- 无"])
        asset_lines.extend(["", "路径库:"])
        asset_lines.extend([f"- {item.get('name')} :: rate={item.get('rate')} / points={item.get('points')}" for item in path_library] or ["- 无"])
        asset_lines.extend(["", f"I/O DI={io_snapshot.get('di', {})}", f"I/O DO={io_snapshot.get('do', {})}", f"寄存器={io_snapshot.get('registers', {})}", f"寄存器快照={register_snapshot.get('registers', {})}", f"xPanel={io_snapshot.get('xpanel_vout_mode', '-')}", "", f"安全配置：collision={safety_profile.get('collision_detection_enabled', '-')}, soft_limit={safety_profile.get('soft_limit_enabled', '-')}, singularity={safety_profile.get('singularity_avoidance_enabled', '-')}", f"运动契约：rt={motion_contract.get('rt_mode', '-')}, tolerance={motion_contract.get('network_tolerance_percent', '-')}, link={motion_contract.get('preferred_link', '-')}" ])
        if runtime_alignment:
            asset_lines.extend(["", f"运行时对齐：{runtime_alignment.get('sdk_family', '-')}", f"robot={runtime_alignment.get('robot_model', '-')}/{runtime_alignment.get('sdk_robot_class', '-')}/{runtime_alignment.get('axis_count', '-')}", f"network={runtime_alignment.get('remote_ip', '-')}/{runtime_alignment.get('local_ip', '-')} / link={runtime_alignment.get('preferred_link', '-')} / rt={runtime_alignment.get('rt_mode', '-')}", f"single_control_source={runtime_alignment.get('single_control_source', '-')}, sdk_available={runtime_alignment.get('sdk_available', '-')}, source={runtime_alignment.get('source', '-')}" ])
        if xmate_model_summary:
            asset_lines.extend(["", f"xMate 模型摘要：{xmate_model_summary.get('robot_model', '-')} / class={xmate_model_summary.get('sdk_robot_class', '-')} / dof={xmate_model_summary.get('axis_count', '-')}", f"model source={xmate_model_summary.get('source', '-')} / approximate={xmate_model_summary.get('approximate', '-')}", f"supported_rt_modes={', '.join(xmate_model_summary.get('supported_rt_modes', [])) or '-'}" ])
        if runtime_config_snapshot:
            asset_lines.extend(["", f"SDK 运行配置：remote={runtime_config_snapshot.get('remote_ip', '-')} / local={runtime_config_snapshot.get('local_ip', '-')} / tolerance={runtime_config_snapshot.get('rt_network_tolerance_percent', '-')}", f"filters=joint {runtime_config_snapshot.get('joint_filter_hz', '-')}, cart {runtime_config_snapshot.get('cart_filter_hz', '-')}, torque {runtime_config_snapshot.get('torque_filter_hz', '-')}", f"fc_frame={runtime_config_snapshot.get('fc_frame_type', '-')} / desired_wrench={runtime_config_snapshot.get('desired_wrench_n', [])}" ])
        if identity_contract:
            asset_lines.extend(["", f"身份合同：{identity_contract.get('robot_model', '-')} / {identity_contract.get('sdk_robot_class', '-')} / {identity_contract.get('axis_count', '-')}", f"支持 RT：{', '.join(identity_contract.get('supported_rt_modes', [])) or '-'}", f"主线模式：{identity_contract.get('clinical_mainline_mode', '-')} / link={identity_contract.get('preferred_link', '-')}" ])
        if clinical_mainline_contract:
            asset_lines.extend(["", f"临床主线合同：loop={clinical_mainline_contract.get('rt_loop_hz', '-')} Hz / single_control_source={clinical_mainline_contract.get('single_control_source_required', '-')}", f"主线序列：{' -> '.join(clinical_mainline_contract.get('required_sequence', [])) or '-'}" ])
        if capability_contract:
            asset_lines.extend(["", f"能力合同：rt={capability_contract.get('scan_rt_mode', '-')} / source={capability_contract.get('runtime_source', '-')}"])
            modules = capability_contract.get('modules', [])
            if modules:
                asset_lines.append("模块矩阵：")
                asset_lines.extend([f"- {item.get('module', '-')} :: {item.get('status', '-')}" for item in modules[:6]])
        if model_authority_contract:
            asset_lines.extend(["", f"模型权威合同：kernel={model_authority_contract.get('authoritative_kernel', '-')} / authoritative_precheck={model_authority_contract.get('authoritative_precheck', '-')}", f"planner={model_authority_contract.get('planner_supported', '-')} / xmate_model={model_authority_contract.get('xmate_model_supported', '-')} / source={model_authority_contract.get('runtime_source', '-')}" ])
        if session_freeze:
            asset_lines.extend(["", f"会话冻结：locked={'YES' if session_freeze.get('session_locked') else 'NO'} / session={session_freeze.get('session_id', '-')}", f"frozen rt={session_freeze.get('rt_mode', '-')} / plan_hash={session_freeze.get('plan_hash', '-')} / segment={session_freeze.get('active_segment', '-')}" ])
        if recovery_contract:
            asset_lines.extend(["", f"恢复合同：collision={recovery_contract.get('collision_behavior', '-')} / safe_retreat={recovery_contract.get('safe_retreat_enabled', '-')}", f"force limits：warn={recovery_contract.get('warning_z_force_n', '-')}N / max={recovery_contract.get('max_z_force_n', '-')}N / resume_band={recovery_contract.get('resume_force_band_n', '-')}N" ])
        if release_contract:
            asset_lines.extend(["", f"发布合同：compile_ready={release_contract.get('compile_ready', '-')} / freeze_consistent={release_contract.get('session_freeze_consistent', '-')}", f"release={release_contract.get('release_recommendation', '-')} / runtime_source={release_contract.get('runtime_source', '-')}" ])
        if environment_doctor:
            asset_lines.extend(["", f"环境医生：{environment_doctor.get('summary_label', '-')}", f"环境说明：{environment_doctor.get('detail', '-')}"])
            if environment_doctor.get('blockers'):
                asset_lines.extend(["- blocker: " + item.get('name', '-') + " :: " + item.get('detail', '-') for item in environment_doctor.get('blockers', [])[:4]])
            elif environment_doctor.get('warnings'):
                asset_lines.extend(["- warning: " + item.get('name', '-') + " :: " + item.get('detail', '-') for item in environment_doctor.get('warnings', [])[:4]])
        if ctx.sdk_runtime.get('errors'):
            asset_lines.extend(["", "资产刷新错误:"])
            asset_lines.extend([f"- {item}" for item in ctx.sdk_runtime.get('errors', [])])
        if ctx.backend_link:
            asset_lines.extend(["", f"前后端链路：{ctx.backend_link.get('summary_label', '-')}", f"链路说明：{ctx.backend_link.get('detail', '-')}", f"REST={'UP' if ctx.backend_link.get('rest_reachable') else 'DOWN'} / telemetry={'ON' if ctx.backend_link.get('telemetry_connected') else 'OFF'} / camera={'ON' if ctx.backend_link.get('camera_connected') else 'OFF'} / ultrasound={'ON' if ctx.backend_link.get('ultrasound_connected') else 'OFF'}", f"endpoint={ctx.backend_link.get('http_base', '-')} / ws={ctx.backend_link.get('ws_base', '-')}" ])
            if ctx.control_plane:
                asset_lines.extend([f"控制面：{ctx.control_plane.get('summary_label', '-')}", f"控制面说明：{ctx.control_plane.get('detail', '-')}", f"配置同步：{ctx.control_plane.get('config_sync', {}).get('detail', '-')}", f"协议状态：{ctx.control_plane.get('protocol_status', {}).get('detail', '-')}", f"topic 覆盖：{ctx.control_plane.get('topic_coverage', {}).get('coverage_percent', 0)}% / 缺失 {', '.join(ctx.control_plane.get('topic_coverage', {}).get('missing', [])) or '无'}" ])
            if ctx.bridge_observability:
                asset_lines.extend([f"桥接观测：{ctx.bridge_observability.get('summary_label', '-')}", f"桥接说明：{ctx.bridge_observability.get('detail', '-')}", f"遥测新鲜度：{ctx.bridge_observability.get('freshness', {}).get('summary_label', '-')} / worst_age={ctx.bridge_observability.get('freshness', {}).get('worst_age_ms', '-')}", f"命令确认：{ctx.bridge_observability.get('command_observability', {}).get('summary_label', '-')} / latest={ctx.bridge_observability.get('command_observability', {}).get('latest_checked_command', '-')}" ])
                recent_commands = ctx.control_plane.get('command_window', {}).get('recent_commands', [])
                if recent_commands:
                    asset_lines.extend(["最近命令窗口:"])
                    asset_lines.extend([f"- {item.get('command', '-')} :: {'OK' if item.get('ok') else 'FAIL'} :: {item.get('message', '-')}" for item in recent_commands[-5:]])
        if ctx.session_governance:
            asset_lines.extend(["", f"会话治理：{ctx.session_governance.get('summary_label', '-')}", f"治理说明：{ctx.session_governance.get('detail', '-')}", f"发布门禁：{'PASS' if ctx.session_governance.get('release_gate', {}).get('release_allowed') else 'BLOCK'}", f"artifact ready={ctx.session_governance.get('artifact_counts', {}).get('ready', 0)} / {ctx.session_governance.get('artifact_counts', {}).get('registered', 0)}" ])
        asset_text = join_lines(asset_lines, "暂无 SDK 资产。")
        window.robot_monitor_page.asset_view.setPlainText(asset_text)
        window.replay_page.asset_view.setPlainText(asset_text)
