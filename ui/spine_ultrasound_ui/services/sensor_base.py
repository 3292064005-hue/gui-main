import multiprocessing as mp
import multiprocessing.shared_memory as shm
import numpy as np
import time
import logging
import uuid
from typing import Tuple, Optional, Any
from PySide6.QtCore import QObject, Signal, QThread, Slot

logger = logging.getLogger(__name__)

class SharedMemoryArray:
    """Helper to manage numpy arrays backed by shared memory."""
    def __init__(self, name: str, shape: Tuple[int, ...], dtype: np.dtype):
        self.name = name
        self.shape = shape
        self.dtype = dtype
        self.size = int(np.prod(shape) * dtype.itemsize)
        self._shm = shm.SharedMemory(name=self.name)
        self.array = np.ndarray(self.shape, dtype=self.dtype, buffer=self._shm.buf)
    
    def close(self):
        try:
            self._shm.close()
        except:
            pass

class SensorIngestionProcess(mp.Process):
    """
    Sub-process that runs continuously, polling hardware (camera/ultrasound)
    and writing the latest frame into a pre-allocated shared memory block.
    This prevents the GIL and slow I/O from blocking the PySide6 UI thread.
    """
    def __init__(self, shm_name: str, shape: Tuple[int, ...], dtype: np.dtype, 
                 run_flag: mp.Event, latest_ts_ns: mp.Value):
        super().__init__()
        self.shm_name = shm_name
        self.shape = shape
        self.dtype = dtype
        self.run_flag = run_flag
        # Using a shared memory Value to store the latest timestamp atomically
        self.latest_ts_ns = latest_ts_ns
    
    def setup_hardware(self) -> bool:
        """Override this to initialize the specific camera/US SDK. Return False if fail."""
        return True
        
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], int]:
        """Override this to grab a frame. Return (success, image_array, timestamp_ns)."""
        return False, None, 0
        
    def teardown_hardware(self):
        """Override this to release resources."""
        pass
        
    def run(self):
        logger.info(f"[{self.__class__.__name__}] Process started. Attaching to SHM: {self.shm_name}")
        try:
            # Need to attach to the shared memory created by the main process
            shared_mem = shm.SharedMemory(name=self.shm_name)
            dst_array = np.ndarray(self.shape, dtype=self.dtype, buffer=shared_mem.buf)
        except Exception as e:
            logger.error(f"Failed to attach SHM: {e}")
            return
            
        if not self.setup_hardware():
            logger.error("Hardware setup failed. Exiting ingestion process.")
            shared_mem.close()
            return
            
        while self.run_flag.is_set():
            success, frame, ts_ns = self.read_frame()
            if success and frame is not None:
                # Zero-copy transfer: write directly to shared memory buffer
                np.copyto(dst_array, frame)
                # Atomically update the timestamp to signal a new frame is ready
                self.latest_ts_ns.value = ts_ns
            else:
                # Prevent CPU blasting on failure
                time.sleep(0.005)
                
        self.teardown_hardware()
        shared_mem.close()
        logger.info(f"[{self.__class__.__name__}] Process exited.")

class SensorProvider(QObject):
    """
    The Main-Process proxy for a SensorIngestionProcess.
    It provisions the shared memory, launches the subprocess, 
    and emits Signals when a new frame is detected via timestamp polling.
    """
    # Emits: (shm_name, shape, dtype_str, timestamp_ns)
    frame_ready = Signal(str, tuple, str, int)
    
    def __init__(self, name: str, shape: Tuple[int, ...], dtype: np.dtype, process_class: type, parent=None):
        super().__init__(parent)
        self.name = name
        self.shape = shape
        self.dtype = np.dtype(dtype)
        
        # Determine bytes size for SHM
        self.bytes_size = int(np.prod(shape) * self.dtype.itemsize)
        self.shm_name = f"shm_{self.name}_{uuid.uuid4().hex[:8]}"
        self._shm = None
        
        # IPC coordination
        self.run_flag = mp.Event()
        self.latest_ts_ns = mp.Value('q', 0) # 'q' is signed long long (int64)
        
        self.process_class = process_class
        self._process: Optional[mp.Process] = None
        self._poller: Optional[QThread] = None
        
    def start(self):
        if self._process is not None and self._process.is_alive():
            logger.warning(f"Sensor {self.name} already running.")
            return
            
        # Allocate Shared Memory
        try:
            self._shm = shm.SharedMemory(create=True, size=self.bytes_size, name=self.shm_name)
        except Exception as e:
            logger.error(f"Failed to allocate shared memory for {self.name}. Did a previous run crash? {e}")
            return
            
        self.run_flag.set()
        self.latest_ts_ns.value = 0
        
        # Spawn the ingestion process
        self._process = self.process_class(
            shm_name=self.shm_name,
            shape=self.shape,
            dtype=self.dtype,
            run_flag=self.run_flag,
            latest_ts_ns=self.latest_ts_ns
        )
        self._process.start()
        
        # Create a lightweight QThread just to poll the integer timestamp
        # This is MUCH cheaper than moving images across threads.
        self._poller = SensorPoller(self.latest_ts_ns, self.run_flag)
        self._poller.new_frame_detected.connect(self._on_new_frame)
        self._poller.start()
        
        logger.info(f"Sensor {self.name} started (PID: {self._process.pid}).")
        
    def stop(self):
        self.run_flag.clear()
        
        if self._poller is not None:
            self._poller.wait()
            self._poller = None
            
        if self._process is not None:
            self._process.join(timeout=2.0)
            if self._process.is_alive():
                self._process.terminate()
            self._process = None
            
        if self._shm is not None:
            self._shm.close()
            self._shm.unlink() # Crucial: release OS memory
            self._shm = None
            
        logger.info(f"Sensor {self.name} stopped and SHM released.")
        
    @Slot(int)
    def _on_new_frame(self, ts_ns: int):
        self.frame_ready.emit(self.shm_name, self.shape, str(self.dtype), ts_ns)

class SensorPoller(QThread):
    new_frame_detected = Signal(int)
    
    def __init__(self, latest_ts_ns: Any, run_flag: Any):
        super().__init__()
        self.latest_ts_ns = latest_ts_ns
        self.run_flag = run_flag
        
    def run(self):
        last_seen = 0
        while self.run_flag.is_set():
            current = self.latest_ts_ns.value
            if current > last_seen:
                last_seen = current
                self.new_frame_detected.emit(current)
            else:
                # Sleep approx 1ms
                time.sleep(0.001)
