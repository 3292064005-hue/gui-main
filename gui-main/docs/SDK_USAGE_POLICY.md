# SDK Usage Policy

- Do not duplicate joint position, velocity, torque, TCP pose or toolset access in Python.
- Do not put ROS2 or PySide6 inside the RT control loop.
- Default scanning control mode is Cartesian impedance.
- Direct torque control is reserved for advanced research mode only.
- Always use a single control authority.

- Compile/precheck verdicts must be consumed from the runtime contract kernel (`compile_scan_plan` / `query_final_verdict`) rather than recomputed as final truth in Desktop.
- Development TLS material must be generated locally under `configs/tls/runtime/`; do not commit certificates or keys to the repository root.
