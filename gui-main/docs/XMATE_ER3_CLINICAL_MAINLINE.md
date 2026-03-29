# xMate ER3 临床主线（脊柱侧弯超声扫描）

本仓库的正式主线固定为：

`xMate ER3 + xCore SDK(C++) + 外置压力传感器 + 超声设备 + 相机`。

## 控制顺序
1. 非实时接近：MoveAbsJ / MoveJ / MoveL
2. 实时柔顺接触：cartesianImpedance
3. 实时扫描：cartesianImpedance + 压力闭环
4. 安全退让：hold / controlled retract / estop

## 正式冻结资产
- `meta/xmate_profile.json`
- `meta/patient_registration.json`
- `derived/preview/scan_protocol.json`
- `meta/device_readiness.json`
- `meta/manifest.json`

## 控制规则
- 单控制源
- 有线直连优先
- 1 kHz 实时主线只在 C++
- 临床主线不直接使用 torque direct control
- 外置压力传感器是接触安全主真值
