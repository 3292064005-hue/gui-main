import numpy as np
import threading


class PreAllocatedRingBuffer:
    """Pre-allocated telemetry ring buffer used by the sync recorder and IPC client."""

    def __init__(self, capacity_frames=300000):
        self.capacity = capacity_frames
        self.head = 0
        self.size = 0
        self.timestamps_ns = np.zeros((self.capacity,), dtype=np.int64)
        self.tcp_poses = np.zeros((self.capacity, 16), dtype=np.float64)
        self.joint_angles = np.zeros((self.capacity, 7), dtype=np.float64)
        self.forces_z = np.zeros((self.capacity,), dtype=np.float64)
        self.safety_statuses = np.zeros((self.capacity,), dtype=np.int32)
        self._lock = threading.Lock()

    def write_frame_zero_copy(self, raw_tuple_from_struct):
        idx = self.head
        self.timestamps_ns[idx] = raw_tuple_from_struct[0]
        self.tcp_poses[idx] = raw_tuple_from_struct[1:17]
        self.joint_angles[idx] = raw_tuple_from_struct[17:24]
        self.forces_z[idx] = raw_tuple_from_struct[24]
        self.safety_statuses[idx] = raw_tuple_from_struct[25]
        self.head = (idx + 1) % self.capacity
        if self.size < self.capacity:
            self.size += 1

    def _active_views(self):
        if self.size == 0:
            return None
        if self.size < self.capacity:
            end = self.head
            return (
                self.timestamps_ns[:end],
                self.tcp_poses[:end],
                self.forces_z[:end],
                self.safety_statuses[:end],
            )
        order = (np.arange(self.capacity, dtype=np.int64) + self.head) % self.capacity
        return (
            self.timestamps_ns[order],
            self.tcp_poses[order],
            self.forces_z[order],
            self.safety_statuses[order],
        )

    def evaluate_sample_at(self, target_timestamp_ns):
        views = self._active_views()
        if views is None:
            return None
        active_ts, active_poses, active_forces, active_statuses = views
        idx = int(np.searchsorted(active_ts, target_timestamp_ns, side="left"))
        idx = max(0, min(idx, len(active_ts) - 1))
        if idx > 0 and idx < len(active_ts):
            prev_idx = idx - 1
            if abs(int(active_ts[prev_idx]) - int(target_timestamp_ns)) <= abs(int(active_ts[idx]) - int(target_timestamp_ns)):
                idx = prev_idx
        return {
            "timestamp_ns": int(active_ts[idx]),
            "tcp_pose": active_poses[idx].copy(),
            "force_z": float(active_forces[idx]),
            "safety_status": int(active_statuses[idx]),
        }

    def evaluate_pose_at(self, target_timestamp_ns):
        sample = self.evaluate_sample_at(target_timestamp_ns)
        if sample is None:
            return None
        return sample["timestamp_ns"], sample["tcp_pose"]
