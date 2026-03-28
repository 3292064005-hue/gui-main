from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ImplementationState(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    SIMULATED = "SIMULATED"
    PLANNED = "PLANNED"


@dataclass
class CapabilityStatus:
    ready: bool = False
    state: str = "PENDING"
    implementation: str = ImplementationState.PLANNED.value
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowArtifacts:
    has_experiment: bool = False
    experiment_id: str = ""
    session_locked: bool = False
    session_id: str = ""
    session_dir: str = ""
    preview_plan_ready: bool = False
    preview_plan_id: str = ""
    preview_plan_hash: str = ""
    localization: CapabilityStatus = field(
        default_factory=lambda: CapabilityStatus(
            implementation=ImplementationState.SIMULATED.value,
            detail="视觉定位策略当前为模拟实现。",
        )
    )
    scan_plan: CapabilityStatus = field(
        default_factory=lambda: CapabilityStatus(
            implementation=ImplementationState.SIMULATED.value,
            detail="扫查路径生成依赖当前模拟定位结果。",
        )
    )
    preprocess: CapabilityStatus = field(
        default_factory=lambda: CapabilityStatus(
            implementation=ImplementationState.IMPLEMENTED.value,
            detail="正式数据产物链已接入，预处理阶段输出质量时间线。",
        )
    )
    reconstruction: CapabilityStatus = field(
        default_factory=lambda: CapabilityStatus(
            implementation=ImplementationState.IMPLEMENTED.value,
            detail="正式数据产物链已接入，重建阶段输出回放索引。",
        )
    )
    assessment: CapabilityStatus = field(
        default_factory=lambda: CapabilityStatus(
            implementation=ImplementationState.IMPLEMENTED.value,
            detail="正式数据产物链已接入，评估阶段输出会话报告。",
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_experiment": self.has_experiment,
            "experiment_id": self.experiment_id,
            "session_locked": self.session_locked,
            "session_id": self.session_id,
            "session_dir": self.session_dir,
            "preview_plan_ready": self.preview_plan_ready,
            "preview_plan_id": self.preview_plan_id,
            "preview_plan_hash": self.preview_plan_hash,
            "localization": self.localization.to_dict(),
            "scan_plan": self.scan_plan.to_dict(),
            "preprocess": self.preprocess.to_dict(),
            "reconstruction": self.reconstruction.to_dict(),
            "assessment": self.assessment.to_dict(),
        }


@dataclass
class UiViewState:
    state: str
    devices: Dict[str, Any]
    metrics: Dict[str, Any]
    config: Dict[str, Any]
    current_experiment: Optional[Dict[str, Any]]
    robot: Dict[str, Any]
    safety: Dict[str, Any]
    recording: Dict[str, Any]
    permissions: Dict[str, bool]
    workflow: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
