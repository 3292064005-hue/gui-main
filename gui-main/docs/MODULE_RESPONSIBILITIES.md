# Module Responsibilities

## cpp_robot_core
### SdkRobotFacade
Wraps official xCore SDK without re-implementing robot primitives.

### RobotStateHub
Owns the canonical robot state snapshot published upward.

### NrtMotionService
Handles only free-space / non-contact motion.

### RtMotionService
Owns the 1 ms control loop and RT command generation.

### ContactObserver
Fuses joint torque, cartesian force, pose, velocity, optional pressure and quality signals.

### ScanSupervisor
Runs segmented scan workflow and pause/resume/rescan logic.

### SafetyService
Fuses SDK-native safety and project-level safety guards.

## spine_ultrasound_ui
### workflow_state_machine
Controls allowed user actions and page-level permissions.

### experiment_manager
Creates experiment folders, metadata, and save roots.

### robot_core_client
Client-only transport; no robot logic here.

### quality_monitor
Provides online quality scoring for operator guidance.

### reconstruction / assessment
Offline or background processing only; never in RT loop.
