from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState
from spine_ultrasound_ui.core.postprocess.stage_contracts import PostprocessStageStatusBundle
from spine_ultrasound_ui.utils import now_text
from spine_ultrasound_ui.core.postprocess.io_helpers import read_json, read_jsonl, read_npz_bundle
from spine_ultrasound_ui.core.postprocess.timeline_builder import (
    build_alarm_timeline,
    build_frame_sync_index,
    build_quality_timeline,
    build_replay_index,
)
from spine_ultrasound_ui.core.postprocess.reconstruction_builder import (
    build_assessment_agreement_payload,
    build_assessment_artifacts,
    build_assessment_summary_payload,
    build_reconstruction_artifacts,
    should_write_prior_assisted_cobb_sidecar,
)
from spine_ultrasound_ui.core.postprocess.report_builder import (
    build_diagnostics_pack,
    build_qa_pack,
    build_session_compare,
    build_session_report,
    build_session_trends,
)


class PostprocessServiceMixin:
    def _build_stage_manifest(self, session_dir: Path, statuses: PostprocessStageStatusBundle) -> Path:
        payload = {
            "generated_at": now_text(),
            "session_id": self.exp_manager.load_manifest(session_dir)["session_id"],
            "schema": "session/postprocess_stage_manifest_v1.schema.json",
            "stages": [
                {**spec.to_dict(), "ready": bool(getattr(getattr(statuses, spec.stage, None), "ready", False)), "status": str(getattr(getattr(statuses, spec.stage, None), "state", "NOT_RUN"))}
                for spec in self.stage_specs
            ],
        }
        return self.exp_manager.save_json_artifact(session_dir, "derived/postprocess/postprocess_stage_manifest.json", payload)

    def _build_session_integrity(self, session_dir: Path) -> Path:
        payload = self.integrity_service.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/session_integrity.json", payload)

    @staticmethod
    def _blocked(label: str) -> CapabilityStatus:
        return CapabilityStatus(ready=False, state="BLOCKED", implementation=ImplementationState.IMPLEMENTED.value, detail=f"{label}需要先完成一次有效会话。")

    def _ensure_artifact(self, session_dir: Path, relative_path: str, builder) -> Path:
        target = session_dir / relative_path
        if target.exists():
            return target
        return builder(session_dir)

    def _build_pressure_sensor_timeline(self, session_dir: Path) -> Path:
        payload = self.pressure_analysis_service.build_timeline(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "derived/pressure/pressure_sensor_timeline.json", payload)

    def _build_pressure_analysis(self, session_dir: Path) -> Path:
        timeline = self._read_json(session_dir / "derived" / "pressure" / "pressure_sensor_timeline.json")
        payload = self.pressure_analysis_service.build_report(session_dir, timeline)
        return self.exp_manager.save_json_artifact(session_dir, "export/pressure_analysis.json", payload)

    def _build_ultrasound_frame_metrics(self, session_dir: Path) -> Path:
        payload = self.ultrasound_analysis_service.build_frame_metrics(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "derived/ultrasound/ultrasound_frame_metrics.json", payload)

    def _build_ultrasound_analysis(self, session_dir: Path) -> Path:
        frame_metrics = self._read_json(session_dir / "derived" / "ultrasound" / "ultrasound_frame_metrics.json")
        payload = self.ultrasound_analysis_service.build_report(session_dir, frame_metrics)
        return self.exp_manager.save_json_artifact(session_dir, "export/ultrasound_analysis.json", payload)

    def _build_quality_timeline(self, session_dir: Path) -> Path:
        return build_quality_timeline(self, session_dir)

    def _build_alarm_timeline(self, session_dir: Path) -> Path:
        return build_alarm_timeline(self, session_dir)

    def _build_frame_sync_index(self, session_dir: Path) -> Path:
        return build_frame_sync_index(self, session_dir)

    def _build_replay_index(self, session_dir: Path) -> Path:
        return build_replay_index(self, session_dir)

    def _build_reconstruction_artifacts(self, session_dir: Path) -> dict[str, Path]:
        return build_reconstruction_artifacts(self, session_dir)

    def _build_assessment_artifacts(self, session_dir: Path) -> dict[str, Path]:
        return build_assessment_artifacts(self, session_dir)

    @staticmethod
    def _should_write_prior_assisted_cobb_sidecar(measurement: dict) -> bool:
        return should_write_prior_assisted_cobb_sidecar(measurement)

    @staticmethod
    def _build_assessment_summary_payload(assessment_input: dict, measurement: dict, uca_measurement: dict, agreement: dict) -> dict:
        return build_assessment_summary_payload(assessment_input, measurement, uca_measurement, agreement)

    @staticmethod
    def _build_assessment_agreement_payload(measurement: dict, uca_measurement: dict) -> dict:
        return build_assessment_agreement_payload(measurement, uca_measurement)

    def _read_npz_bundle(self, path: Path) -> dict:
        return read_npz_bundle(path)

    def _build_session_report(self, session_dir: Path) -> Path:
        return build_session_report(self, session_dir)

    def _build_session_compare(self, session_dir: Path) -> Path:
        return build_session_compare(self, session_dir)

    def _build_session_trends(self, session_dir: Path) -> Path:
        return build_session_trends(self, session_dir)

    def _build_diagnostics_pack(self, session_dir: Path) -> Path:
        return build_diagnostics_pack(self, session_dir)

    def _build_qa_pack(self, session_dir: Path) -> Path:
        return build_qa_pack(self, session_dir)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict]:
        return read_jsonl(path)

    @staticmethod
    def _read_json(path: Path) -> dict:
        return read_json(path)
