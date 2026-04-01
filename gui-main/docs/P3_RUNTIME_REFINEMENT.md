# P3 级性能与运行时细化

## 本轮细化项
1. **命令元数据查找 O(1) 化**
   - `command_registry.cpp` 新增 registry index，避免运行期重复线性扫描命令表。
2. **TLS/Protobuf 传输边界加固**
   - 增加 `MAX_FRAME_BYTES`，拒绝异常帧长。
   - `send_tls_command()` 增加 timeout 入参校验并启用 `TCP_NODELAY`。
3. **运行时缓冲区限长化**
   - `CommandAuditService` 改为 `deque(maxlen=...)`。
   - `RobotCoreClientBackend` 的 recent commands / topic catalog 改为 bounded retention。
   - `ApiBridgeBackend` 的 error history 改为 bounded retention。
4. **重连退避策略**
   - robot_core telemetry TLS 通道与 API WebSocket 通道采用指数退避（上限封顶），降低异常期 busy reconnect。

## 目标
- 降低热路径分配与切片开销
- 避免 topic / error / recent command 缓存无界增长
- 提升网络异常期的运行时稳定性
- 收紧传输边界，覆盖异常输入/超大帧/非法 timeout
