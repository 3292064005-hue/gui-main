from dataclasses import dataclass, field


@dataclass
class TcpPose:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0


@dataclass
class RunMetrics:
    pressure_current: float = 0.0
    pressure_target: float = 1.5
    pressure_error: float = 0.0
    frame_id: int = 0
    path_index: int = 0
    segment_id: int = 0
    image_quality: float = 0.0
    feature_confidence: float = 0.0
    quality_score: float = 0.0
    cobb_angle: float = 0.0
    assessment_confidence: float = 0.0
    measurement_source: str = ""
    uca_angle: float = 0.0
    scan_progress: float = 0.0
    tcp_pose: TcpPose = field(default_factory=TcpPose)
    joint_pos: list[float] = field(default_factory=lambda: [0.0] * 7)
    joint_vel: list[float] = field(default_factory=lambda: [0.0] * 7)
    joint_torque: list[float] = field(default_factory=lambda: [0.0] * 7)
    cart_force: list[float] = field(default_factory=lambda: [0.0] * 6)
    contact_mode: str = "NO_CONTACT"
    contact_confidence: float = 0.0
    recommended_action: str = "IDLE"
