from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState


class ReportStage:
    """Build report-style assessment artifacts for a session."""

    def run(self, service, session_dir: Path | None) -> CapabilityStatus:
        """Execute the assessment/report stage.

        Args:
            service: ``PostprocessService`` façade instance.
            session_dir: Session directory or ``None`` when unavailable.

        Returns:
            ``CapabilityStatus`` describing stage availability.

        Raises:
            RuntimeError: Propagated from the façade when artifact generation
                fails.
        """
        if session_dir is None:
            return service._blocked("脊柱侧弯评估")
        service._ensure_artifact(session_dir, "derived/quality/quality_timeline.json", service._build_quality_timeline)
        service._ensure_artifact(session_dir, "derived/alarms/alarm_timeline.json", service._build_alarm_timeline)
        service._ensure_artifact(session_dir, "derived/sync/frame_sync_index.json", service._build_frame_sync_index)
        service._ensure_artifact(session_dir, "replay/replay_index.json", service._build_replay_index)
        report_target = service._build_session_report(session_dir)
        compare_target = service._build_session_compare(session_dir)
        trends_target = service._build_session_trends(session_dir)
        diagnostics_target = service._build_diagnostics_pack(session_dir)
        qa_target = service._build_qa_pack(session_dir)
        integrity_target = service._build_session_integrity(session_dir)
        for name, target in {
            "session_report": report_target,
            "session_compare": compare_target,
            "session_trends": trends_target,
            "diagnostics_pack": diagnostics_target,
            "qa_pack": qa_target,
            "session_integrity": integrity_target,
        }.items():
            service.exp_manager.append_artifact(session_dir, name, target)
        service.exp_manager.append_processing_step(
            session_dir,
            service.plugin_executor.run(
                service.plugin_registry.get("assessment"),
                session_dir,
                {
                    "input_artifacts": [
                        "export/summary.json",
                        "derived/quality/quality_timeline.json",
                        "derived/alarms/alarm_timeline.json",
                        "derived/sync/frame_sync_index.json",
                        "replay/replay_index.json",
                        "raw/ui/command_journal.jsonl",
                        "raw/ui/annotations.jsonl",
                    ],
                    "output_artifacts": [
                        "export/session_report.json",
                        "export/session_compare.json",
                        "export/session_trends.json",
                        "export/diagnostics_pack.json",
                        "export/qa_pack.json",
                    ],
                },
            ),
        )
        service.exp_manager.update_manifest(
            session_dir,
            algorithm_registry={plugin.stage: {"plugin_id": plugin.plugin_id, "plugin_version": plugin.plugin_version} for plugin in service.plugins.all_plugins()},
        )
        return service.job_manager.run_stage(
            stage="assessment",
            session_dir=session_dir,
            metadata={"artifacts": [str(report_target), str(compare_target), str(trends_target), str(diagnostics_target), str(qa_target), str(integrity_target)]},
            build_status=lambda: CapabilityStatus(
                ready=True,
                state="AVAILABLE",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f"会话报告、对比分析、趋势分析、诊断包与 QA 包已生成：{report_target.name}",
            ),
        )
