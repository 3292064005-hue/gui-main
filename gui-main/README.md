# Spine Ultrasound Platform

正式主线固定为 Ubuntu 22.04。

这个仓库现在只保留两条正式产品路径：

- 桌面主线：`run.py --backend mock|core`
- Headless/Web 适配层：`spine_ultrasound_ui.api_server:app`

不再保留历史开发壳、第二套协议栈、第二套 runtime，或未接入构建与测试的“名义主线”。

## Mainline Layout

- `cpp_robot_core/`
  唯一机器人控制核心，正式 runtime 名称统一为 `spine_robot_core`
- `spine_ultrasound_ui/`
  PySide6 桌面主线、session/workflow 编排、图像与回放能力
- `ui_frontend/`
  可选 Web 消费端，只能通过 headless v1 adapter 访问主线状态
- `configs/force_control.json`
  力控阈值、默认接触力和安全回缩距离的唯一正式来源

## Supported Environment

- OS: `Ubuntu 22.04`
- Python: `3.11+`
- C++ toolchain: `cmake`, `g++`, `protobuf`, `OpenSSL`, `Eigen3`
- Node.js: `20.x` for `ui_frontend/`

`requirements.txt` 是 Ubuntu 22.04 主线最小依赖。
`requirements-clinical.txt` 是在主线之上的 Ubuntu 22.04 临床扩展依赖。

## Setup

### Python mainline

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Optional clinical extension

```bash
python -m pip install -r requirements-clinical.txt
```

### Optional web frontend

```bash
cd ui_frontend
npm ci
```

## Run

### Desktop in mock mode

```bash
python run.py --backend mock
```

### Desktop against the mock core server

```bash
python scripts/mock_robot_core_server.py
# new terminal
SPINE_UI_BACKEND=core python run.py --backend core
```

### Build and start `spine_robot_core`

```bash
cmake -S cpp_robot_core -B cpp_robot_core/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp_robot_core/build -j
./cpp_robot_core/build/spine_robot_core
```

### Start the headless adapter

```bash
./scripts/start_headless.sh
```

or:

```bash
uvicorn spine_ultrasound_ui.api_server:app --host 0.0.0.0 --port 8000
```

## Verification

仓库级唯一正式验收命令：

```bash
./scripts/verify_mainline.sh
```

它会按 Ubuntu 22.04 主线顺序执行：

- repo hygiene 检查
- `python -m pytest -q`
- `cmake` / `ctest`
- `cd ui_frontend && npm ci && npm run build`

如果本机安装了 ROS 或第三方 pytest 插件，优先使用 `python -m pytest`，避免外部插件污染主线测试面。

## Product Rules

- 正式协议只有一套：TLS 1.3 + length-prefixed Protobuf
- 正式消息只有三类：`Command`、`Reply`、`TelemetryEnvelope`
- `protocol_version` 不匹配必须在进入业务逻辑前拒绝
- `cpp_robot_core` 是唯一执行状态源
- Python 保留 workflow / session 语义，但不复制执行状态机
- `AppController` 的关键命令链必须具备明确失败动作、回退日志和用户提示

## Documents

- 架构总则：[ARCHITECTURE.md](ARCHITECTURE.md)
- 主线收敛框架：[docs/STRONG_CONVERGENCE_FRAMEWORK.md](docs/STRONG_CONVERGENCE_FRAMEWORK.md)
- IPC 合同：[docs/IPC_PROTOCOL.md](docs/IPC_PROTOCOL.md)
- Headless API v1 合同：[docs/HEADLESS_API_V1.md](docs/HEADLESS_API_V1.md)

## Current Mainline Outcomes

- `run.py --backend mock|core` 是唯一正式桌面入口
- `spine_ultrasound_ui.api_server:app` 是唯一正式 headless/Web 入口
- `configs/force_control.json` 统一驱动 Python schema、mock runtime、C++ 力控默认值与测试阈值
- `ui_frontend` 只消费 `/api/v1/*` 和 `/ws/*`，不再直连另一套协议栈
