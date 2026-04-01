# Control Plane Rewrite Wave C

This wave completes the next stage of convergence work:

- `AppController` now delegates governance refresh and status/governance payload assembly to `ControlPlaneReader`.
- `api_server.py` no longer carries the full endpoint surface inline; routes are split into system/session/events/commands/websocket modules under `spine_ultrasound_ui/api_routes/`.
- Frontend state imports now resolve through `ui_frontend/src/state/` only. Legacy `store/` and `stores/` shim directories were removed.
- Legacy Qt signal bus naming is clarified via `core/qt_signal_bus.py`, while `core/event_bus.py` remains as a compatibility shim.

This wave is intentionally focused on removing second-source orchestration pressure before deeper C++ authority integration.
