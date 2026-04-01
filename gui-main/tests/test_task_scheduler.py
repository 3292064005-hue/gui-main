from spine_ultrasound_ui.core.task_scheduler import TaskScheduler


def test_task_scheduler_tracks_completion():
    scheduler = TaskScheduler(max_workers=1)
    try:
        task_id = scheduler.submit("sum", lambda a, b: a + b, 2, 3, metadata={"kind": "unit"})
        snapshot = scheduler.snapshot(task_id)
        assert snapshot is not None
        while snapshot["status"] in {"queued", "running"}:
            snapshot = scheduler.snapshot(task_id)
        assert snapshot["status"] == "completed"
        assert snapshot["result"] == 5
        assert snapshot["metadata"]["kind"] == "unit"
    finally:
        scheduler.shutdown(wait=True)
