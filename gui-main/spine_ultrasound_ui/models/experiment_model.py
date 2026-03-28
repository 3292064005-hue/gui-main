from dataclasses import dataclass


@dataclass
class ExperimentRecord:
    exp_id: str
    created_at: str
    state: str
    cobb_angle: float
    pressure_target: float
    save_dir: str
    session_id: str = ""
    plan_id: str = ""
