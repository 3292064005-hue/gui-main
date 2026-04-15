# SDK Usage Policy

- Do not duplicate joint position, velocity, torque, TCP pose or toolset access in Python.
- Do not put ROS2 or PySide6 inside the RT control loop.
- Default scanning control mode is Cartesian impedance.
- Direct torque control is reserved for advanced research mode only.
- Always use a single control authority.

- Compile/precheck verdicts must be consumed from the runtime contract kernel (`validate_scan_plan` / `query_final_verdict`). `compile_scan_plan` remains a compatibility alias and must not be treated as the canonical command name in Desktop or API code.
- All Python consumers must read `control_authority`, `final_verdict`, and `authoritative_runtime_envelope` through the canonical governance projection surface. Python layers may cache, render, or annotate these facts, but they must not synthesize a competing final verdict. Runtime-owned final verdict data must outrank release-contract and model-report fallbacks whenever the authoritative envelope is present.
- Deprecated command aliases must carry an explicit retirement window (`deprecation_stage`, `removal_target`, `replacement_command`, `compatibility_note`) in the shared manifest and generated C++ registry.
- Development TLS material must be generated locally under `configs/tls/runtime/`; do not commit certificates or keys to the repository root.

## Controlled SDK Ports

`SdkRobotFacade` remains the single official xCore boundary, but upstream runtime services must consume one of the restricted sub-ports rather than treat the whole façade as an undifferentiated object:

- `LifecyclePort`: connect / disconnect / power / operate-mode transitions
- `QueryPort`: read-only runtime, inventory, IO, and contract snapshots
- `NrtExecutionPort`: non-real-time motion batches and profile dispatch
- `RtControlPort`: real-time control loop, RT state stream, and RT phase policy
- `CollaborationPort`: RL, drag, path record / replay, and related session-side collaboration controls

This keeps the official SDK surface centralized while preventing runtime components from depending on unrelated hardware capabilities.
