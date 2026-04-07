from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Protocol

from spine_ultrasound_ui.models import ArtifactDescriptor, ProcessingStepRecord


class AlgorithmPlugin(Protocol):
    plugin_id: str
    plugin_version: str
    stage: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]

    def validate_inputs(self, inputs: Dict[str, Any]) -> None: ...
    def cache_key(self, session_dir: Path, inputs: Dict[str, Any]) -> str: ...
    def emit_artifacts(self, session_dir: Path, inputs: Dict[str, Any]) -> List[ArtifactDescriptor]: ...
    def emit_metrics(self, session_dir: Path, inputs: Dict[str, Any]) -> Dict[str, Any]: ...
    def run(self, session_dir: Path, inputs: Dict[str, Any]) -> ProcessingStepRecord: ...


@dataclass
class _BasePlugin:
    plugin_id: str
    plugin_version: str
    stage: str
    detail: str
    input_schema: dict[str, Any] = field(default_factory=lambda: {"required": ["input_artifacts", "output_artifacts"]})
    output_schema: dict[str, Any] = field(default_factory=lambda: {"type": "processing_step"})

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        missing = [key for key in self.input_schema.get("required", []) if key not in inputs]
        if missing:
            raise ValueError(f"plugin {self.stage} missing required inputs: {', '.join(missing)}")

    def cache_key(self, session_dir: Path, inputs: Dict[str, Any]) -> str:
        del session_dir
        payload = {"plugin": self.plugin_id, "version": self.plugin_version, "inputs": inputs}
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def emit_artifacts(self, session_dir: Path, inputs: Dict[str, Any]) -> List[ArtifactDescriptor]:
        del session_dir
        return [
            ArtifactDescriptor(
                artifact_type=str(path).replace('/', '_'),
                path=str(path),
                producer=self.plugin_id,
                artifact_id=str(path),
                summary=f"{self.stage} output {path}",
                source_stage=self.stage,
                dependencies=list(inputs.get("input_artifacts", [])),
            )
            for path in inputs.get("output_artifacts", [])
        ]

    def emit_metrics(self, session_dir: Path, inputs: Dict[str, Any]) -> Dict[str, Any]:
        del session_dir
        return {
            "input_count": len(list(inputs.get("input_artifacts", []))),
            "output_count": len(list(inputs.get("output_artifacts", []))),
            "clinical_plane": True,
        }

    def run(self, session_dir: Path, inputs: Dict[str, Any]) -> ProcessingStepRecord:
        input_artifacts = list(inputs.get("input_artifacts", []))
        output_artifacts = list(inputs.get("output_artifacts", []))
        return ProcessingStepRecord(
            step_id=self.stage,
            plugin_id=self.plugin_id,
            plugin_version=self.plugin_version,
            input_artifacts=input_artifacts,
            output_artifacts=output_artifacts,
            status="completed",
            detail=self.detail,
            metrics=self.emit_metrics(session_dir, inputs),
        )


class PreprocessPlugin(_BasePlugin):
    pass


class ReconstructionPlugin(_BasePlugin):
    pass


class AssessmentPlugin(_BasePlugin):
    pass


class GuidancePlugin(_BasePlugin):
    pass


class PluginPlane:
    def __init__(self) -> None:
        self.preprocess = PreprocessPlugin(
            plugin_id="builtin.spine_ultrasound.preprocess",
            plugin_version="3.0",
            stage="preprocess",
            detail="Clinical preprocess stage emits quality and alarm timelines for ultrasound-driven spine sweep review.",
        )
        self.reconstruction = ReconstructionPlugin(
            plugin_id="builtin.spine_ultrasound.sync_replay",
            plugin_version="3.0",
            stage="reconstruction",
            detail="Clinical reconstruction stage emits frame-sync and replay products without freezing a reconstruction body or Cobb implementation.",
        )
        self.assessment = AssessmentPlugin(
            plugin_id="builtin.spine_ultrasound.assessment",
            plugin_version="3.0",
            stage="assessment",
            detail="Clinical assessment stage emits report, compare, trends, diagnostics and QA products around scoliosis review contracts.",
        )
        self.camera_preprocess = GuidancePlugin(
            plugin_id="builtin.spine_ultrasound.guidance.camera_preprocess",
            plugin_version="1.0",
            stage="camera_preprocess",
            detail="Guidance camera preprocessing isolates back ROI evidence before patient guidance freeze.",
        )
        self.spine_midline_estimation = GuidancePlugin(
            plugin_id="builtin.spine_ultrasound.guidance.midline",
            plugin_version="1.0",
            stage="spine_midline_estimation",
            detail="Guidance midline estimation produces the pre-freeze spine centerline and landmarks.",
        )
        self.registration_build = GuidancePlugin(
            plugin_id="builtin.spine_ultrasound.guidance.registration_build",
            plugin_version="1.0",
            stage="registration_build",
            detail="Guidance registration build composes patient-frame and corridor contracts from camera facts.",
        )
        self.registration_validate = GuidancePlugin(
            plugin_id="builtin.spine_ultrasound.guidance.registration_validate",
            plugin_version="1.0",
            stage="registration_validate",
            detail="Guidance registration validation emits the freeze-readiness verdict without changing execution authority.",
        )

    def all_plugins(self) -> List[AlgorithmPlugin]:
        """Return post-processing plugins preserved for backward compatibility."""
        return [self.preprocess, self.reconstruction, self.assessment]

    def guidance_plugins(self) -> List[AlgorithmPlugin]:
        """Return the dedicated camera-guidance plugins.

        Guidance plugins are kept separate from the ultrasound post-processing
        plane so existing post-process registries and tests remain stable while
        session-freeze lineage can still register camera guidance stages.
        """
        return [
            self.camera_preprocess,
            self.spine_midline_estimation,
            self.registration_build,
            self.registration_validate,
        ]
