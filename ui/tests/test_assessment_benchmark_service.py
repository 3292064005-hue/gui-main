import json
from pathlib import Path

from spine_ultrasound_ui.services.benchmark.assessment_benchmark_service import AssessmentBenchmarkService


def test_assessment_benchmark_service_aggregates_case_metrics(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session_a'
    (session_dir / 'derived' / 'assessment').mkdir(parents=True)
    (session_dir / 'derived' / 'assessment' / 'assessment_summary.json').write_text(
        json.dumps({
            'session_id': 'S-1',
            'cobb_angle_deg': 12.5,
            'measurement_source': 'lamina_center_cobb',
            'requires_manual_review': False,
            'manual_review_reasons': [],
        }),
        encoding='utf-8',
    )
    (session_dir / 'derived' / 'assessment' / 'cobb_measurement.json').write_text(
        json.dumps({'angle_deg': 12.5, 'measurement_source': 'lamina_center_cobb'}),
        encoding='utf-8',
    )
    gt_path = session_dir / 'derived' / 'assessment' / 'ground_truth_cobb.json'
    gt_path.write_text(json.dumps({'cobb_angle_deg': 10.0}), encoding='utf-8')

    report = AssessmentBenchmarkService().evaluate_many([
        {'session_dir': session_dir, 'ground_truth_path': gt_path},
    ])
    assert report['case_count'] == 1
    assert report['ground_truth_case_count'] == 1
    assert report['mean_absolute_error_deg'] == 2.5
    assert report['manual_review_rate'] == 0.0
