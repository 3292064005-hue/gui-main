from spine_ultrasound_ui.workers import AssessmentWorker, PreprocessWorker, ReconstructionWorker, ReplayWorker


def test_workers_are_real_job_types():
    assert PreprocessWorker().stage_name == "preprocess"
    assert ReconstructionWorker().stage_name == "reconstruction"
    assert AssessmentWorker().stage_name == "assessment"
    assert ReplayWorker().stage_name == "replay"


def test_demo_workers_route_through_demo_postprocess_task_surface() -> None:
    preprocess_source = __import__('pathlib').Path('spine_ultrasound_ui/workers/preprocess_worker.py').read_text(encoding='utf-8')
    reconstruction_source = __import__('pathlib').Path('spine_ultrasound_ui/workers/reconstruction_worker.py').read_text(encoding='utf-8')
    assessment_source = __import__('pathlib').Path('spine_ultrasound_ui/workers/assessment_worker.py').read_text(encoding='utf-8')
    assert 'demo_postprocess_tasks' in preprocess_source
    assert 'spine_ultrasound_ui.imaging.' not in preprocess_source
    assert 'demo_postprocess_tasks' in reconstruction_source
    assert 'spine_ultrasound_ui.imaging.' not in reconstruction_source
    assert 'demo_postprocess_tasks' in assessment_source
    assert 'spine_ultrasound_ui.imaging.' not in assessment_source
