# SDK Usage Policy

- Do not duplicate joint position, velocity, torque, TCP pose or toolset access in Python.
- Do not put ROS2 or PySide6 inside the RT control loop.
- Default scanning control mode is Cartesian impedance.
- Direct torque control is reserved for advanced research mode only.
- Always use a single control authority.

- Compile/precheck verdicts must be consumed from the runtime contract kernel (`compile_scan_plan` / `query_final_verdict`) rather than recomputed as final truth in Desktop.
- Development TLS material must be generated locally under `configs/tls/runtime/`; do not commit certificates or keys to the repository root.

## Controlled SDK Ports

`SdkRobotFacade` remains the single official xCore boundary, but upstream runtime services must consume one of the restricted sub-ports rather than treat the whole façade as an undifferentiated object:

- `LifecyclePort`: connect / disconnect / power / operate-mode transitions
- `QueryPort`: read-only runtime, inventory, IO, and contract snapshots
- `NrtExecutionPort`: non-real-time motion batches and profile dispatch
- `RtControlPort`: real-time control loop, RT state stream, and RT phase policy
- `CollaborationPort`: RL, drag, path record / replay, and related session-side collaboration controls

This keeps the official SDK surface centralized while preventing runtime components from depending on unrelated hardware capabilities.
