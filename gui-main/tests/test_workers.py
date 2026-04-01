from spine_ultrasound_ui.workers import AssessmentWorker, PreprocessWorker, ReconstructionWorker, ReplayWorker


def test_workers_are_real_job_types():
    assert PreprocessWorker().stage_name == "preprocess"
    assert ReconstructionWorker().stage_name == "reconstruction"
    assert AssessmentWorker().stage_name == "assessment"
    assert ReplayWorker().stage_name == "replay"
