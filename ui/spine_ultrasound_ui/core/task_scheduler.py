from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Any, Callable
from uuid import uuid4


@dataclass(slots=True)
class ScheduledTask:
    task_id: str
    name: str
    created_at: float
    status: str = "queued"
    started_at: float | None = None
    finished_at: float | None = None
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "created_at": self.created_at,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class TaskScheduler:
    """Small in-process scheduler for post-processing and replay jobs.

    The scheduler deliberately stays non-RT and bounded: it provides a single
    place for background work so the UI no longer depends on placeholder worker
    files or ad-hoc thread creation.
    """

    def __init__(self, *, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="spine-task")
        self._lock = Lock()
        self._tasks: dict[str, ScheduledTask] = {}
        self._futures: dict[str, Future[Any]] = {}

    def submit(
        self,
        name: str,
        fn: Callable[..., Any],
        *args: Any,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        task_id = f"task-{uuid4().hex[:12]}"
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            created_at=monotonic(),
            metadata=dict(metadata or {}),
        )

        def _runner() -> Any:
            with self._lock:
                task.status = "running"
                task.started_at = monotonic()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - exercised by runtime failures
                with self._lock:
                    task.status = "failed"
                    task.finished_at = monotonic()
                    task.error = str(exc)
                raise
            with self._lock:
                task.status = "completed"
                task.finished_at = monotonic()
                task.result = result
            return result

        future = self._executor.submit(_runner)
        with self._lock:
            self._tasks[task_id] = task
            self._futures[task_id] = future
        return task_id

    def snapshot(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return None if task is None else task.snapshot()

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            return [task.snapshot() for task in self._tasks.values()]

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            future = self._futures.get(task_id)
            task = self._tasks.get(task_id)
        if future is None or task is None:
            return False
        cancelled = future.cancel()
        if cancelled:
            with self._lock:
                task.status = "cancelled"
                task.finished_at = monotonic()
        return cancelled

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)
