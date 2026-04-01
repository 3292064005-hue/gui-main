from __future__ import annotations

from spine_ultrasound_ui.core.postprocess.stage_contracts import PostprocessStageSpec


POSTPROCESS_STAGE_REGISTRY: tuple[PostprocessStageSpec, ...] = (
    PostprocessStageSpec(
        stage='preprocess',
        label='图像预处理',
        input_artifacts=(
            'raw/ui/quality_feedback.jsonl',
            'raw/core/alarm_event.jsonl',
            'raw/ui/annotations.jsonl',
        ),
        output_artifacts=(
            'derived/quality/quality_timeline.json',
            'derived/alarms/alarm_timeline.json',
        ),
        retryable=True,
        performance_budget_ms=2000,
        owner_domain='postprocess',
    ),
    PostprocessStageSpec(
        stage='reconstruction',
        label='局部重建',
        input_artifacts=(
            'raw/camera/index.jsonl',
            'raw/ultrasound/index.jsonl',
            'raw/core/contact_state.jsonl',
            'raw/core/scan_progress.jsonl',
            'derived/quality/quality_timeline.json',
            'derived/alarms/alarm_timeline.json',
            'raw/ui/annotations.jsonl',
        ),
        output_artifacts=(
            'derived/sync/frame_sync_index.json',
            'replay/replay_index.json',
        ),
        retryable=True,
        performance_budget_ms=4000,
        owner_domain='postprocess',
    ),
    PostprocessStageSpec(
        stage='assessment',
        label='脊柱侧弯评估',
        input_artifacts=(
            'export/summary.json',
            'derived/quality/quality_timeline.json',
            'derived/alarms/alarm_timeline.json',
            'derived/sync/frame_sync_index.json',
            'replay/replay_index.json',
            'raw/ui/command_journal.jsonl',
            'raw/ui/annotations.jsonl',
        ),
        output_artifacts=(
            'export/session_report.json',
            'export/session_compare.json',
            'export/session_trends.json',
            'export/diagnostics_pack.json',
            'export/qa_pack.json',
            'export/session_integrity.json',
        ),
        retryable=True,
        performance_budget_ms=6000,
        owner_domain='postprocess',
    ),
)


def iter_stage_specs() -> tuple[PostprocessStageSpec, ...]:
    """Return the ordered postprocess stage registry.

    Returns:
        Tuple of stable stage specifications in execution order.

    Raises:
        No exceptions are raised.
    """
    return POSTPROCESS_STAGE_REGISTRY
