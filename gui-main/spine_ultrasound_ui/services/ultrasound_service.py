import cv2
import numpy as np
import time
import logging
from typing import Tuple, Optional
from .sensor_base import SensorIngestionProcess, SensorProvider

logger = logging.getLogger(__name__)

class UltrasoundIngestionProcess(SensorIngestionProcess):
    """
    Sub-process to grab frames from the Ultrasound device.
    Uses the Ubuntu 22.04 V4L2 video capture path.
    """
    def __init__(self, device_idx: int, width: int, height: int, init_kwargs):
        super().__init__(**init_kwargs)
        self.device_idx = device_idx
        self.width = width
        self.height = height
        self.cap = None
        
    def setup_hardware(self) -> bool:
        logger.info(f"Connecting to Ultrasound Capture Card ID: {self.device_idx}")
        self.cap = cv2.VideoCapture(self.device_idx)
        if not self.cap.isOpened():
            logger.error(f"Failed to open Ultrasound Device {self.device_idx}")
            return False
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30) # often 30 or 60 for US
        return True
        
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], int]:
        if self.cap is None:
            return False, None, 0
            
        ret, frame = self.cap.read()
        ts_ns = time.time_ns()
        
        if ret:
            # Most Ultrasound displays are grayscale, 
            # converting to GRAY saves 66% of memory bandwidth
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # --- Acoustic Coupling Quality Assessment ---
            # Extremely fast thresholding: if >85% of image is pure black, probe is decoupled.
            dark_pixels = np.sum(frame_gray < 15)
            total_pixels = frame_gray.size
            dark_ratio = dark_pixels / total_pixels
            
            if dark_ratio > 0.85:
                logger.warning(f"[Coupling AI] WARNING: Probe Decoupling Detected! Dark region: {dark_ratio:.1%}")
                # Future: Trigger ZMQ command to C++ RecoveryManager to Pause and Retract
            else:
                pass # Quality OK
                
            return True, frame_gray, ts_ns
        else:
            return False, None, ts_ns
            
    def teardown_hardware(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("Ultrasound Capture released.")

class UltrasoundService(SensorProvider):
    """
    Provides a zero-copy stream of Grayscale ultrasound images to the UI.
    Listens for US connection config.
    """
    def __init__(self, device_idx=1, width=800, height=600, parent=None):
        shape = (height, width) # Grayscale
        dtype = np.uint8
        
        # Override start block injected args
        self.device_idx = device_idx
        self.img_width = width
        self.img_height = height
        
        super().__init__(name="ultrasound", shape=shape, dtype=dtype, 
                         process_class=UltrasoundIngestionProcess, parent=parent)
                         
    def start(self):
        """Override to pass specific args to the process constructor."""
        if self._process is not None and self._process.is_alive():
            return
            
        try:
            from multiprocessing import shared_memory as shm
            self._shm = shm.SharedMemory(create=True, size=self.bytes_size, name=self.shm_name)
        except Exception as e:
            logger.error(f"Failed to allocate SHM for Ultrasound. {e}")
            return
            
        self.run_flag.set()
        self.latest_ts_ns.value = 0
        
        init_kwargs = {
            'shm_name': self.shm_name,
            'shape': self.shape,
            'dtype': self.dtype,
            'run_flag': self.run_flag,
            'latest_ts_ns': self.latest_ts_ns
        }
        
        self._process = self.process_class(
            device_idx=self.device_idx,
            width=self.img_width,
            height=self.img_height,
            init_kwargs=init_kwargs
        )
        self._process.start()
        
        from .sensor_base import SensorPoller
        self._poller = SensorPoller(self.latest_ts_ns, self.run_flag)
        self._poller.new_frame_detected.connect(self._on_new_frame)
        self._poller.start()
        logger.info("UltrasoundService started.")
