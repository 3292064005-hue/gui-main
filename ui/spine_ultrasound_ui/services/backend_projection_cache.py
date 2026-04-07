from __future__ import annotations

"""Incremental cache for backend projection partitions."""

from dataclasses import dataclass
from threading import RLock
from typing import Any

from spine_ultrasound_ui.utils.runtime_fingerprint import payload_hash
from spine_ultrasound_ui.utils.time_utils import now_ns


@dataclass(frozen=True)
class ProjectionPartitionSnapshot:
    """Immutable metadata for a cached projection partition."""

    version: int
    fingerprint: str
    updated_ns: int


class BackendProjectionCache:
    """Track per-partition cache state for backend control-plane assembly.

    The cache provides atomic read snapshots so callers can consume a coherent
    ``revision``/``meta``/``payload`` bundle even when telemetry and control
    threads update partitions concurrently.
    """

    def __init__(self) -> None:
        self._payloads: dict[str, Any] = {}
        self._meta: dict[str, ProjectionPartitionSnapshot] = {}
        self._revision = 0
        self._lock = RLock()

    @property
    def revision(self) -> int:
        """Return the current monotonic projection revision."""
        with self._lock:
            return self._revision

    def update_partition(self, name: str, payload: Any) -> bool:
        """Update a partition if its serialized fingerprint changed.

        Args:
            name: Stable partition name.
            payload: JSON-like payload stored as-is after normalization.

        Returns:
            ``True`` when the payload changed and the partition version was
            incremented, otherwise ``False``.

        Raises:
            No exceptions are raised.

        Boundary behavior:
            Idempotent updates do not change the global revision.
        """
        with self._lock:
            normalized = self._normalize(payload)
            fingerprint = payload_hash({"partition": name, "payload": normalized})
            current = self._meta.get(name)
            if current is not None and current.fingerprint == fingerprint:
                return False
            version = 1 if current is None else current.version + 1
            updated_ns = now_ns()
            self._payloads[name] = normalized
            self._meta[name] = ProjectionPartitionSnapshot(version=version, fingerprint=fingerprint, updated_ns=updated_ns)
            self._revision += 1
            return True

    def get_partition(self, name: str, default: Any = None) -> Any:
        """Return a normalized copy of a cached partition payload."""
        with self._lock:
            payload = self._payloads.get(name, default)
            return self._normalize(payload)

    def partition_meta(self, name: str) -> dict[str, Any]:
        """Return metadata for a single partition."""
        with self._lock:
            meta = self._meta.get(name)
            if meta is None:
                return {"version": 0, "fingerprint": "", "updated_ns": 0}
            return {"version": meta.version, "fingerprint": meta.fingerprint, "updated_ns": meta.updated_ns}

    def meta_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return an atomic snapshot of all partition metadata."""
        return dict(self.snapshot()["partitions"])

    def payload_snapshot(self) -> dict[str, Any]:
        """Return an atomic snapshot of all cached payloads."""
        return dict(self.snapshot()["payloads"])

    def snapshot(self) -> dict[str, Any]:
        """Return a coherent cache snapshot.

        Returns:
            Dictionary with ``revision``, ``partitions`` and ``payloads``.
        """
        with self._lock:
            return {
                "revision": self._revision,
                "partitions": {
                    name: {"version": meta.version, "fingerprint": meta.fingerprint, "updated_ns": meta.updated_ns}
                    for name, meta in sorted(self._meta.items())
                },
                "payloads": {name: self._normalize(payload) for name, payload in sorted(self._payloads.items())},
            }

    @staticmethod
    def _normalize(payload: Any) -> Any:
        if isinstance(payload, dict):
            return {str(key): BackendProjectionCache._normalize(value) for key, value in payload.items()}
        if isinstance(payload, list):
            return [BackendProjectionCache._normalize(item) for item in payload]
        if isinstance(payload, tuple):
            return [BackendProjectionCache._normalize(item) for item in payload]
        return payload
