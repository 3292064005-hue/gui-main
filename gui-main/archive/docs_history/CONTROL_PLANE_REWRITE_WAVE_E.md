# Control Plane Rewrite Wave E

This wave continues the convergence work by extracting runtime bridge responsibilities out of the remaining desktop and headless coordinator files.

## What changed

### Desktop runtime convergence
- Added `spine_ultrasound_ui/core/app_runtime_bridge.py`
- Added `spine_ultrasound_ui/views/main_window_runtime_bridge.py`
- `AppController` now delegates telemetry handling, guarded command behavior, governance refresh, local alarms, and session-product refresh to `AppRuntimeBridge`.
- `MainWindow` now delegates runtime preference persistence, alarm/log propagation, pixmap routing, and e-stop confirmation to `MainWindowRuntimeBridge`.

### Headless convergence
- Added `spine_ultrasound_ui/services/headless_runtime_introspection.py`
- `HeadlessAdapter` now delegates status/health/schema/catalog introspection to `HeadlessRuntimeIntrospection`.

## Why this matters

The previous structure still left too much operational logic inside the old entrypoint files. This wave reduces the chance that UI, desktop orchestration, and headless runtime introspection each grow separate interpretations of system truth.

## Current convergence outcome

- `app_controller.py`: reduced again
- `main_window.py`: reduced again
- `headless_adapter.py`: reduced again
- targeted governance / adapter / UI runtime tests pass

## Next pressure points

1. Continue shrinking `MainWindow` by extracting remaining panel/button construction helpers.
2. Continue shrinking `HeadlessAdapter` by extracting lease/command-control plane wiring.
3. Move more command-family methods out of `AppController` into explicit action modules.
