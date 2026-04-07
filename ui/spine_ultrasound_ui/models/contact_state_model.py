from dataclasses import dataclass


@dataclass
class ContactState:
    mode: str = "NO_CONTACT"
    confidence: float = 0.0
    stable_score: float = 0.0
    overpressure_score: float = 0.0
    slip_score: float = 0.0
    recommended_speed_scale: float = 1.0
    recommended_z_bias: float = 0.0
