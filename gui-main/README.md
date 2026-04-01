# Spine Ultrasound Platform

当前主线仓库仅包含以下正式域：

- `configs/`
- `cpp_robot_core/`
- `spine_ultrasound_ui/`
- `schemas/`
- `scripts/`
- `tests/`
- `docs/`
- `runtime/`
- `archive/`

## 运行要求

桌面 / headless 主线：

- Ubuntu 22.04（CI / 发布基线；非 22.04 主机会在 doctor 中明确告警）
- Python 3.11+
- PySide6 >= 6.7（桌面入口）
- `pip install -r requirements.txt`

C++ robot_core 主线：

- CMake 3.24+
- `g++` 或 `clang++`
- `libssl-dev`
- `libeigen3-dev`
- 官方 xCore SDK（prod/HIL 构建时显式提供；可通过 `XCORE_SDK_ROOT` 或 `ROKAE_SDK_ROOT` 指定）
- C++ 主线已移除对系统级 `protoc/libprotobuf-dev` 的硬依赖；Python 侧仍需 `protobuf` 运行时（当前主线要求 `protobuf>=3.20.3,<8`）

推荐先执行：

```bash
./scripts/check_cpp_prereqs.sh
python scripts/check_protocol_sync.py
# 首次 real-runtime bringup 若尚无 TLS 材料，先生成开发证书
./scripts/generate_dev_tls_cert.sh
python scripts/doctor_runtime.py
```

## 常用入口

桌面程序：

```bash
python run.py --backend mock
```

Python 主线测试：

```bash
python scripts/run_pytest_mainline.py -q
```

主线验证：

```bash
./scripts/verify_mainline.sh
```

实时运行脚本默认把 C++ 构建产物放到 `/tmp`，避免污染仓库 payload。

## 目录说明

- `cpp_robot_core/`：机器人 C++ 执行内核与构建脚本
- `spine_ultrasound_ui/`：Python 桌面、headless 适配层、治理与会话能力
- `schemas/`：运行态与会话证据 schema
- `archive/`：历史文档、历史测试、归档入口

## 仓库门禁

- `.github/CODEOWNERS` 定义目录责任边界。
- `docs/REPOSITORY_GATES.md` 定义应配置为 required checks 的 workflow job 名称。
- `scripts/check_canonical_imports.py` 与 `scripts/check_repository_gates.py` 用于在本地/CI 审计 P2 收口约束。

## 说明

- 本仓库不再包含前端构建目录、运行态缓存、历史 legacy 可执行入口和提交态生成产物。
- 包根 `spine_ultrasound_ui` 不再执行导入时兼容注入；测试若需要 PySide6 stub，必须显式调用 `tests.runtime_compat.enable_runtime_compat()`。
- 桌面运行要求真实 PySide6；不允许在正式入口静默降级为测试桩。

## 控制面约束

- `cpp_robot_core` / headless runtime 现在统一发布 `authoritative_runtime_envelope`，其中包含控制权、已应用运行时配置、会话冻结、plan digest 与最终裁决。
- Desktop / API / mock backend 只能消费该 envelope，不再本地拼接并宣称并行 authority。
- control-plane 快照同时暴露 `projection_revision` 与 `projection_partitions`，用于调试增量物化与缓存失效。


## SDK / RT truthfulness

- `cpp_robot_core` now distinguishes **vendored SDK detection**, **contract-shell readiness**, and **live binding established** in runtime contracts.
- RT runtime contracts export measured loop timing (`current_period_ms`, `max_cycle_ms`, `last_wake_jitter_ms`, `overrun_count`) instead of only nominal declarations.
- `projection_revision` / `projection_partitions` are produced from atomic cache snapshots so control-plane reads do not see torn metadata.
