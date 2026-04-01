# Control-plane rewrite wave D

This wave continues the convergence work by moving the remaining desktop/headless/UI projection logic out of the largest legacy files.

## What changed

- Introduced `spine_ultrasound_ui/core/app_workflow_operations.py` and moved the primary experiment/localization/path/scan/postprocess/export workflow logic out of `AppController`.
- Reduced `AppController` to orchestration/wiring plus local alarm and telemetry handling.
- Introduced `spine_ultrasound_ui/views/main_window_status_presenter.py` and moved the large runtime status projection out of `MainWindow`.
- `MainWindow` now delegates status application to a dedicated presenter so the window can focus on layout, routing, and Qt lifecycle.
- Simplified `HeadlessAdapter` session/evidence access by delegating `current_*` reads through `HeadlessSessionProductsReader` via `__getattr__`, keeping the adapter more transport-oriented.

## Resulting direction

The remaining large files are now clearly transitional rather than permanent homes for workflow logic. Future work should continue shrinking:

- `AppController` toward lifecycle + command entrypoints only
- `HeadlessAdapter` toward transport + session tracking only
- `MainWindow` toward widget shell + action routing only

## Verification

This wave was verified with targeted `py_compile` checks and refactor-adjacent regression suites covering:

- `AppController`
- `HeadlessAdapter`
- session product reads
- API contract/security
- control-plane refactor
- UI runtime governance
- mock mainline E2E
