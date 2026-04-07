# P1 完整验收清单

## 目标

对照已确认的 P1 收口范围，确认三类热点文件拆分、异常边界、控制面削薄以及 CMake target-scoped 传播已形成稳定主线。

## 验收项

- [x] **P1-1 运行时巨石拆分**
  - `spine_ultrasound_ui/services/headless_command_service.py` 已拆为 façade + `command_guard_service.py` / `command_dispatch_service.py` / `command_audit_service.py`
  - `spine_ultrasound_ui/services/mock_core_runtime.py` 已拆为 façade + `services/mock_runtime/`
  - `cpp_robot_core/src/core_runtime.cpp` 已将状态/会话职责拆分到 `runtime_state_store.cpp` 与 `session_runtime.cpp`

- [x] **P1-2 异常边界显式化**
  - `backend_error_mapper.py` 已接入 Python backend 关键路径
  - runtime verdict 不再把 advisory fallback 伪装成 final verdict
  - structured error envelope 仍作为统一失败出口

- [x] **P1-3 控制面削薄**
  - `control_plane_raw_facts_service.py` 已作为 raw facts 层存在
  - `control_plane_snapshot_service.py` 保留 projection / section ordering / operator hints
  - `headless_control_plane_aggregator.py` 仅保留过渡 façade 角色

- [x] **P1-4 CMake target-scoped include/link 传播**
  - `spine_robot_core_runtime` 通过 `PUBLIC` usage requirements 暴露 `robot_core_build_settings` / `robot_core_proto_deps` / `robot_core_sdk_binding`
  - 新增 `robot_core_test_support` 统一承接 C++ test targets 的 include/link 传播
  - 现有 C++ tests 改为 `robot_core_add_cpp_test(...)` 统一声明，去掉手工散落的 include/link 拼接

## 本轮实际校验

- [x] `cmake -S cpp_robot_core -B <build> -DROBOT_CORE_PROFILE=mock -DROBOT_CORE_WITH_XCORE_SDK=OFF`
- [x] `cmake --build <build> --target test_seqlock`
- [x] `cmake --build <build> --target test_force_control`
- [x] `cmake --build <build> --target test_impedance_scan`
- [x] `cmake --build <build> --target test_protocol_bridge`
- [x] `cmake --build <build> --target test_recovery_manager`
- [x] `ctest --output-on-failure -R 'cpp_(force_control|impedance_scan|protocol_bridge|recovery_manager)'`
- [x] `pytest tests/test_protocol_sync_contract_metadata.py tests/test_cpp_target_scoped_contracts.py`

## 结论

P1 本轮收口后的验收结论为：

- **热点文件拆分：通过**
- **异常边界显式化：通过**
- **控制面削薄：通过**
- **C++ test targets 的 target-scoped 传播：通过**

当前仓库 P1 主线已闭合；后续工作若继续推进，应进入 P2 范围，而不是回到 P1 结构收口。
