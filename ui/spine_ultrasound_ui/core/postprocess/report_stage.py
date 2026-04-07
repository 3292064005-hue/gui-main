from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState


class ReportStage:
    """Build authoritative scoliosis assessment and report artifacts."""

    def run(self, service, session_dir: Path | None) -> CapabilityStatus:
        """Execute the assessment/report stage."""
        if session_dir is None:
            return service._blocked('脊柱侧弯评估')
        service._ensure_artifact(session_dir, 'derived/quality/quality_timeline.json', service._build_quality_timeline)
        service._ensure_artifact(session_dir, 'derived/pressure/pressure_sensor_timeline.json', service._build_pressure_sensor_timeline)
        service._ensure_artifact(session_dir, 'derived/ultrasound/ultrasound_frame_metrics.json', service._build_ultrasound_frame_metrics)
        service._ensure_artifact(session_dir, 'derived/alarms/alarm_timeline.json', service._build_alarm_timeline)
        service._ensure_artifact(session_dir, 'derived/sync/frame_sync_index.json', service._build_frame_sync_index)
        service._ensure_artifact(session_dir, 'replay/replay_index.json', service._build_replay_index)
        reconstruction_targets = service._build_reconstruction_artifacts(session_dir)
        assessment_targets = service._build_assessment_artifacts(session_dir)
        ultrasound_target = service._build_ultrasound_analysis(session_dir)
        pressure_target = service._build_pressure_analysis(session_dir)
        report_target = service._build_session_report(session_dir)
        compare_target = service._build_session_compare(session_dir)
        trends_target = service._build_session_trends(session_dir)
        diagnostics_target = service._build_diagnostics_pack(session_dir)
        qa_target = service._build_qa_pack(session_dir)
        integrity_target = service._build_session_integrity(session_dir)
        for name, target in {
            'ultrasound_frame_metrics': session_dir / 'derived' / 'ultrasound' / 'ultrasound_frame_metrics.json',
            'pressure_sensor_timeline': session_dir / 'derived' / 'pressure' / 'pressure_sensor_timeline.json',
            **assessment_targets,
            'ultrasound_analysis': ultrasound_target,
            'pressure_analysis': pressure_target,
            'session_report': report_target,
            'session_compare': compare_target,
            'session_trends': trends_target,
            'diagnostics_pack': diagnostics_target,
            'qa_pack': qa_target,
            'session_integrity': integrity_target,
        }.items():
            service.exp_manager.append_artifact(session_dir, name, target)
        service.exp_manager.append_processing_step(
            session_dir,
            service.plugin_executor.run(
                service.plugin_registry.get('assessment'),
                session_dir,
                {
                    'input_artifacts': [
                        'export/summary.json',
                        'derived/quality/quality_timeline.json',
                        'derived/pressure/pressure_sensor_timeline.json',
                        'derived/ultrasound/ultrasound_frame_metrics.json',
                        'derived/alarms/alarm_timeline.json',
                        'derived/sync/frame_sync_index.json',
                        'replay/replay_index.json',
                        'derived/reconstruction/coronal_vpi.npz',
                        'derived/reconstruction/vpi_preview.png',
                        'derived/reconstruction/bone_mask.npz',
                        'derived/reconstruction/frame_anatomy_points.json',
                        'derived/reconstruction/lamina_candidates.json',
                        'derived/reconstruction/spine_curve.json',
                        'derived/reconstruction/landmark_track.json',
                        'derived/reconstruction/reconstruction_summary.json',
                        'raw/ui/command_journal.jsonl',
                        'raw/ui/annotations.jsonl',
                    ],
                    'output_artifacts': [
                        'derived/reconstruction/vpi_ranked_slices.json',
                        'derived/reconstruction/vpi_bone_feature_mask.npz',
                        'derived/assessment/vertebra_pairs.json',
                        'derived/assessment/tilt_candidates.json',
                        'derived/assessment/cobb_measurement.json',
                        'derived/assessment/uca_measurement.json',
                        'derived/assessment/assessment_agreement.json',
                        'derived/assessment/assessment_overlay.png',
                        'derived/assessment/assessment_summary.json',
                        'export/ultrasound_analysis.json',
                        'export/pressure_analysis.json',
                        'export/session_report.json',
                        'export/session_compare.json',
                        'export/session_trends.json',
                        'export/diagnostics_pack.json',
                        'export/qa_pack.json',
                    ],
                },
            ),
        )
        service.exp_manager.update_manifest(
            session_dir,
            algorithm_registry={plugin.stage: {'plugin_id': plugin.plugin_id, 'plugin_version': plugin.plugin_version} for plugin in service.plugins.all_plugins()},
        )
        produced = [*assessment_targets.values(), ultrasound_target, pressure_target, report_target, compare_target, trends_target, diagnostics_target, qa_target, integrity_target]
        return service.job_manager.run_stage(
            stage='assessment',
            session_dir=session_dir,
            metadata={'artifacts': [str(target) for target in produced]},
            build_status=lambda: CapabilityStatus(
                ready=True,
                state='AVAILABLE',
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=('正式 lamina-center Cobb / UCA 辅助评估、assessment summary、会话报告、对比分析、趋势分析、诊断包与 QA 包已生成：' f'{report_target.name}'),
            ),
        )
