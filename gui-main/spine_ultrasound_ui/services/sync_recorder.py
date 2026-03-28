import h5py
import numpy as np
import os
import multiprocessing as mp
from loguru import logger
import yaml
from ..core.memory_pool import PreAllocatedRingBuffer
from ..core.ipc_client import ZeroCopyIpcClient
import time
from scipy.spatial.transform import Slerp
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import interp1d

class OnlineSyncRecorder(mp.Process):
    """
    Independent real-time process writing to HDF5 SWMR (Single Writer Multiple Reader).
    It aligns ultrasound frames to robot kinematics using Sub-Millisecond Master Clock interpolation,
    accounting for hardware temporal offsets. 
    It enables 'reconstruction_proc' to read real-time during the scan.
    """
    def __init__(self, session_dir: str, config_path: str = "configs/calibration.yaml"):
        super().__init__()
        self.session_dir = session_dir
        self.run_flag = mp.Value('b', True)
        self.us_frame_queue = mp.Queue(maxsize=1000) # Queue of US frame pointers/timestamps
        self.config_path = config_path

    def _load_calibration(self):
        try:
            with open(self.config_path, "r") as f:
                cfg = yaml.safe_load(f)
                self.dt_latency_ns = int(cfg["temporal_calibration"]["dt_camera_latency_ms"] * 1e6)
                logger.info(f"[SyncRecorder] Loaded Camera Latency: {self.dt_latency_ns} ns")
        except Exception as e:
            logger.warning(f"[SyncRecorder] Failed to load calibration, defaulting latency=0. {e}")
            self.dt_latency_ns = 0

    def run(self):
        # Configure loguru for async background non-blocking IO
        logger.add(os.path.join(self.session_dir, "sync_recorder.log"), enqueue=True)
        self._load_calibration()

        # 1. Initialize Zero-GC Memory Pool
        self.memory_pool = PreAllocatedRingBuffer(capacity_frames=300000)
        
        # 2. Start ZMQ Zero-Copy Client pushing to the pool
        self.ipc_client = ZeroCopyIpcClient(self.memory_pool)
        self.ipc_client.start()
        logger.info("[SyncRecorder] ZMQ Zero-Copy IPC Started. 1kHz Reception active.")

        # 3. Initialize HDF5 in SWMR mode
        file_path = os.path.join(self.session_dir, "scan_session_data.h5")
        
        # Open file in 'w' with Latest version for SWMR
        f = h5py.File(file_path, "w", libver='latest')
        
        # Pre-create stretchable SWMR datasets mapped to our IPC Flat/POD structure
        dset_us_ts = f.create_dataset("timestamp/ultrasound_aligned", shape=(0,), maxshape=(None,), dtype='i8', chunks=(100,))
        dset_tcp_pose = f.create_dataset("robot/tcp_pose", shape=(0, 16), maxshape=(None, 16), dtype='f8', chunks=(100, 16), compression="lzf")
        dset_force = f.create_dataset("robot/cart_force", shape=(0,), maxshape=(None,), dtype='f8', chunks=(100,), compression="lzf")
        
        # Immediately set SWMR mode (after creating datasets)
        f.swmr_mode = True
        logger.info(f"[SyncRecorder] HDF5 SWMR Initialized at {file_path}")

        flush_counter = 0

        while self.run_flag.value:
            try:
                # Poll the ultrasound queue for new frames
                us_data = self.us_frame_queue.get(timeout=0.05)
                # Apply Temporal Offset Calibration (HW Delay Compensation)
                real_event_time_ns = us_data["ts_ns"] - self.dt_latency_ns
                
                # Fetch aligned pose from ring buffer
                res = self.memory_pool.evaluate_pose_at(real_event_time_ns)
                if res is None:
                    continue
                
                closest_ts, tcp_pose = res
                
                # Expand datasets dynamically without locks
                idx = dset_us_ts.shape[0]
                dset_us_ts.resize((idx + 1,))
                dset_tcp_pose.resize((idx + 1, 16))
                dset_force.resize((idx + 1,))
                
                # Write
                dset_us_ts[idx] = us_data["ts_ns"]
                dset_tcp_pose[idx, :] = tcp_pose
                # Force can be retrieved similarly via indices, omitted for brevity here
                dset_force[idx] = 0.0 # Placeholder for aligned force z
                
                # SWMR enforces manual dataset flushes so parallel readers get updates
                dset_tcp_pose.flush()
                dset_us_ts.flush()

            except mp.queues.Empty:
                pass
            except Exception as e:
                logger.error(f"[SyncRecorder] Loop Error: {e}")

        self.ipc_client.stop()
        f.close()
        logger.info("[SyncRecorder] Stopped and HDF5 closed securely.")

    def stop(self):
        self.run_flag.value = False
        self.join(timeout=3.0)

class SyncRecorderAdapter:
    """ Proxy for UI Thread """
    def __init__(self, session_dir: str):
        self.worker = OnlineSyncRecorder(session_dir)
        
    def start(self):
        self.worker.start()
        
    def append_us_frame(self, ts_ns: int):
        self.worker.us_frame_queue.put({"ts_ns": ts_ns})
        
    def stop(self):
        self.worker.stop()
