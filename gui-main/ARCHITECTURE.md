# Spine Ultrasound Platform Architecture

## Final principle
- Official xCore SDK is used only inside `cpp_robot_core`.
- Python UI never enters the 1 ms real-time loop.
- Free-space motion uses SDK non-real-time motion.
- Contact scanning defaults to Cartesian impedance.
- External pressure sensing is auxiliary; robot state remains the primary contact signal.
- ROS2 is optional and never becomes the real-time control owner.
- `cpp_robot_core` is the single execution-state authority.
- Session manifest is the single source of truth for replay/export inputs.

## Execution units
1. `cpp_robot_core`: single control authority for the robot.
2. `spine_ultrasound_ui`: research platform, GUI, experiment orchestration, imaging and assessment.
3. `ros2_bridge` (optional): mirror and integration layer only.

## Layered responsibilities
### SDK-native layer
ROKAE xCore SDK primitives, robot state, NRT motion, RT motion, planner, model, collision, soft limits, logs.

### Robot abstraction layer
`SdkRobotFacade`, `RobotStateHub`, `NrtMotionService`, `RtMotionService`, `SafetyService`.

### Scan control layer
`ContactObserver`, `TrajectoryCompiler`, `ScanSupervisor`, `RecoveryManager`.

### Experiment and data layer
`ExperimentManager`, `SessionManifest`, `SyncRecorder`, `ReplayService`, `ExportService`.

### Research application layer
PySide6 GUI, `AppController`, quality monitoring, reconstruction, assessment, reporting.
