# Spine Ultrasound Strong-Convergence Framework

Official production environment: Ubuntu 22.04.

## North Star

This repository has exactly one production runtime, one production protocol, one production desktop path, and one canonical verification surface:

- Runtime: `cpp_robot_core/build/spine_robot_core`
- Desktop mainline: PySide6 `run.py --backend core|mock`
- Protocol: TLS 1.3 + length-prefixed Protobuf
- Command/Reply/Telemetry contracts: `Command`, `Reply`, `TelemetryEnvelope`
- Canonical Python test entry: `python -m pytest -q`
- Canonical repo verification entry: `./scripts/verify_mainline.sh`

Anything else is either:

- a thin adapter on top of the same mainline, or
- legacy/demo code that must not silently become a second production path.

## Fixed Execution Order

### Wave 1. Mainline Convergence

Goal:

- Make desktop + runtime + protocol + tests unambiguous.

Source of truth:

- Desktop orchestration: `spine_ultrasound_ui/core/app_controller.py`
- Python core transport: `spine_ultrasound_ui/services/robot_core_client.py`
- Shared transport decoding: `spine_ultrasound_ui/services/core_transport.py`
- Runtime protocol bridge: `cpp_robot_core/src/protobuf_protocol.cpp`
- Canonical build graph: `cpp_robot_core/CMakeLists.txt`

Required invariants:

- `spine_robot_core` is the only production executable name.
- The runtime library and executable are built from the same source graph.
- Python and C++ reject protocol-version mismatch immediately.
- Curated tests live under `tests/` and run without third-party pytest plugin pollution.
- Command failure semantics are explicit and test-backed.

Exit criteria:

- `python -m pytest -q` passes.
- `cmake --build cpp_robot_core/build` passes.
- `ctest --test-dir cpp_robot_core/build --output-on-failure` passes.
- No production doc points at `robot_core_main`.

### Wave 2. RT / Force / Safety Convergence

Goal:

- Make impedance, hold, retract, retry, and estop behaviors deterministic.

Source of truth:

- `cpp_robot_core/include/impedance_control_manager.hpp`
- `cpp_robot_core/src/rt_motion_service.cpp`
- `cpp_robot_core/src/core_runtime.cpp`
- `cpp_robot_core/src/recovery_manager.cpp`

Required invariants:

- Business-side force requests use `setDesiredContactForce(double)`.
- RT-side force requests use `setDesiredWrench(std::array<double, 6>)`.
- Both APIs write into the same desired-wrench state.
- Dangerous branches land in `PAUSED_HOLD`, `safe_retreat`, or `ESTOP`.
- Recovery state is queryable and smoke-tested.

Exit criteria:

- Force threshold smoke tests cover safe, Z-overlimit, and XY-overlimit cases.
- Recovery tests cover hold, retract, retry, and retry completion semantics.
- Overpressure no longer leaves the runtime in an ambiguous state.

### Wave 3. Headless / Web Extension

Goal:

- Expose mainline state and commands to web consumers without duplicating business logic.

Source of truth:

- `spine_ultrasound_ui/services/headless_adapter.py`
- `spine_ultrasound_ui/api_server.py`

Required invariants:

- Web commands flow through the same command contract as desktop.
- Web telemetry is a translated view over the same mainline state.
- No second execution state machine exists in the API layer.

Exit criteria:

- The adapter can execute commands in `mock` and `core` modes.
- REST/WebSocket endpoints expose status and telemetry snapshots derived from the mainline.
- Headless adapter tests exercise the same state transitions as desktop.

## Implementation Framework

Every optimization change should satisfy all five checks before merge:

1. Source of truth check
   Is the change extending the mainline path, or accidentally creating a second path?

2. Failure semantics check
   If this command fails, do we roll back, hold, retreat, or estop explicitly?

3. Version-contract check
   If the payload version is wrong, do we reject it before business logic runs?

4. Test-surface check
   Is the behavior covered by the curated Python or C++ test surface?

5. Operator clarity check
   Would a new engineer know which executable, protocol, and test command are real?

## Canonical Verification

Run this before merging any convergence work:

```bash
./scripts/verify_mainline.sh
```

This enforces:

- curated Python tests
- C++ build
- C++ smoke tests

CI mirrors the same contract in `.github/workflows/mainline.yml`.

## Current Mainline Assets

- Python protocol guard: `spine_ultrasound_ui/services/ipc_protocol.py`
- Shared TLS/Protobuf transport decode path: `spine_ultrasound_ui/services/core_transport.py`
- Desktop command orchestration and rollback policy: `spine_ultrasound_ui/core/app_controller.py`
- Headless adapter command/status surface: `spine_ultrasound_ui/services/headless_adapter.py`
- Runtime protocol bridge: `cpp_robot_core/src/protobuf_protocol.cpp`
- Runtime/recovery safety chain: `cpp_robot_core/src/core_runtime.cpp`
- C++ smoke registration: `cpp_robot_core/CMakeLists.txt`

## Remaining High-Value Backlog

These are next, but they should extend the same framework instead of bypassing it:

1. Real C++ runtime integration tests against a spawned `spine_robot_core`
2. Thin web adapter tests using FastAPI `TestClient` when FastAPI is part of the environment
3. Recorder/replay contract tests for desktop and web consumers
4. Legacy quarantine pass for old script-style entry points and demos
5. Single-source force thresholds/config export into docs, runtime, and tests

## Self-Review Gate

Before closing a task, ask:

- Did this remove ambiguity, or only move it?
- Did I harden failure behavior, or only log it?
- Did I reuse the mainline transport/state path, or clone logic again?
- Did I add a test that would catch regression?
- Would this save the next engineer time, or make them guess again?
