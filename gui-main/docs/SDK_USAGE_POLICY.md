# SDK Usage Policy

- Do not duplicate joint position, velocity, torque, TCP pose or toolset access in Python.
- Do not put ROS2 or PySide6 inside the RT control loop.
- Default scanning control mode is Cartesian impedance.
- Direct torque control is reserved for advanced research mode only.
- Always use a single control authority.
