from dataclasses import dataclass, field


@dataclass
class RobotStateSnapshot:
    timestamp_ns: int = 0
    power_state: str = "off"
    operate_mode: str = "manual"
    operation_state: str = "idle"
    joint_pos: list[float] = field(default_factory=lambda: [0.0] * 7)
    joint_vel: list[float] = field(default_factory=lambda: [0.0] * 7)
    joint_torque: list[float] = field(default_factory=lambda: [0.0] * 7)
    tcp_pose: list[float] = field(default_factory=lambda: [0.0] * 6)
    cart_force: list[float] = field(default_factory=lambda: [0.0] * 6)
    cart_torque: list[float] = field(default_factory=lambda: [0.0] * 6)
    tool_name: str = "-"
    wobj_name: str = "-"
