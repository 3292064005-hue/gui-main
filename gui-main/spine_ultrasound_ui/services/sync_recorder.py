from __future__ import annotations

import multiprocessing as mp
import os
from queue import Empty

import h5py
import yaml
from loguru import logger

from ..core.ipc_client import ZeroCopyIpcClient
from ..core.memory_pool import PreAllocatedRingBuffer


class OnlineSyncRecorder(mp.Process):
    """
    Independent real-time process writing aligned ultrasound/robot samples to HDF5
    in SWMR mode. The recorder compensates for calibrated camera latency and stores
    the closest robot pose together with the aligned Cartesian Z force sample.
    """

    def __init__(self, session_dir: str, config_path: str = "configs/calibration.yaml"):
        super().__init__()
        self.session_dir = session_dir
        self.run_flag = mp.Value('b', True)
        self.us_frame_queue = mp.Queue(maxsize=1000)
        self.config_path = config_path

    def _load_calibration(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                temporal_cfg = cfg.get("temporal_calibration", {})
                latency_ms = float(temporal_cfg.get("dt_camera_latency_ms", 0.0) or 0.0)
                self.dt_latency_ns = int(latency_ms * 1e6)
                logger.info("[SyncRecorder] Loaded camera latency: {} ns", self.dt_latency_ns)
        except Exception as exc:  # pragma: no cover - defensive runtime branch
            logger.warning("[SyncRecorder] Failed to load calibration, defaulting latency=0. {}", exc)
            self.dt_latency_ns = 0

    def run(self):
        logger.add(os.path.join(self.session_dir, "sync_recorder.log"), enqueue=True)
        self._load_calibration()
        self.memory_pool = PreAllocatedRingBuffer(capacity_frames=300000)
        self.ipc_client = ZeroCopyIpcClient(self.memory_pool)
        self.ipc_client.start()
        logger.info("[SyncRecorder] ZMQ zero-copy IPC started.")

        file_path = os.path.join(self.session_dir, "scan_session_data.h5")
        f = h5py.File(file_path, "w", libver="latest")
        dset_us_ts = f.create_dataset("timestamp/ultrasound_aligned", shape=(0,), maxshape=(None,), dtype="i8", chunks=(100,))
        dset_tcp_pose = f.create_dataset("robot/tcp_pose", shape=(0, 16), maxshape=(None, 16), dtype="f8", chunks=(100, 16), compression="lzf")
        dset_force = f.create_dataset("robot/cart_force", shape=(0,), maxshape=(None,), dtype="f8", chunks=(100,), compression="lzf")
        dset_robot_ts = f.create_dataset("timestamp/robot_closest", shape=(0,), maxshape=(None,), dtype="i8", chunks=(100,))
        f.swmr_mode = True
        logger.info("[SyncRecorder] HDF5 SWMR initialized at {}", file_path)

        try:
            while self.run_flag.value:
                try:
                    us_data = self.us_frame_queue.get(timeout=0.05)
                except Empty:
                    continue

                real_event_time_ns = int(us_data["ts_ns"]) - self.dt_latency_ns
                sample = self.memory_pool.evaluate_sample_at(real_event_time_ns)
                if sample is None:
                    continue

                idx = dset_us_ts.shape[0]
                dset_us_ts.resize((idx + 1,))
                dset_tcp_pose.resize((idx + 1, 16))
                dset_force.resize((idx + 1,))
                dset_robot_ts.resize((idx + 1,))

                dset_us_ts[idx] = int(us_data["ts_ns"])
                dset_robot_ts[idx] = int(sample["timestamp_ns"])
                dset_tcp_pose[idx, :] = sample["tcp_pose"]
                dset_force[idx] = float(sample["force_z"])

                dset_robot_ts.flush()
                dset_tcp_pose.flush()
                dset_us_ts.flush()
                dset_force.flush()
        except Exception as exc:  # pragma: no cover - background process safety net
            logger.exception("[SyncRecorder] Loop error: {}", exc)
        finally:
            self.ipc_client.stop()
            f.close()
            logger.info("[SyncRecorder] Stopped and HDF5 closed securely.")

    def stop(self):
        self.run_flag.value = False
        self.join(timeout=3.0)


class SyncRecorderAdapter:
    """Proxy used by the UI thread."""

    def __init__(self, session_dir: str):
        self.worker = OnlineSyncRecorder(session_dir)

    def start(self):
        self.worker.start()

    def append_us_frame(self, ts_ns: int):
        self.worker.us_frame_queue.put({"ts_ns": int(ts_ns)})

    def stop(self):
        self.worker.stop()
