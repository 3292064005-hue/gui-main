from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.release_gate.input_loader import ReleaseGateInputLoader
from spine_ultrasound_ui.services.release_gate.policy_evaluator import ReleaseGatePolicyEvaluator


class ReleaseGateDecisionService:
    GATE_VERSION = 'release_gate_v3'

    def __init__(self) -> None:
        self.input_loader = ReleaseGateInputLoader()
        self.policy_evaluator = ReleaseGatePolicyEvaluator(self.GATE_VERSION)

    def build(self, session_dir: Path) -> dict[str, Any]:
        return self.policy_evaluator.evaluate(session_dir, self.input_loader.load(session_dir))
