import cv2
import numpy as np
import time
import logging
from typing import Tuple, Optional
from .sensor_base import SensorIngestionProcess, SensorProvider

logger = logging.getLogger(__name__)

class CameraIngestionProcess(SensorIngestionProcess):
    """
    Sub-process that grabs frames from an OpenCV device and writes them 
    into the shared memory block setup by the main UI process.
    """
    def __init__(self, camera_idx: int, width: int, height: int, init_kwargs):
        super().__init__(**init_kwargs)
        self.camera_idx = camera_idx
        self.width = width
        self.height = height
        self.cap = None
        
    def setup_hardware(self) -> bool:
        logger.info(f"Connecting to Camera ID: {self.camera_idx}")
        self.cap = cv2.VideoCapture(self.camera_idx)
        if not self.cap.isOpened():
            logger.error(f"Failed to open Camera {self.camera_idx}")
            return False
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        return True
        
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], int]:
        if self.cap is None:
            return False, None, 0
            
        ret, frame = self.cap.read()
        ts_ns = time.time_ns()
        
        if ret:
            # OpenCV is BGR. You can convert to RGB here or in the UI layer.
            # Doing it here means shifting load from UI to this child CPU core.
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return True, frame_rgb, ts_ns
        else:
            return False, None, ts_ns
            
    def teardown_hardware(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("Camera released.")

class CameraService(SensorProvider):
    """
    Provides a zero-copy stream of RGB images to the UI.
    Listens for camera connection config.
    """
    def __init__(self, camera_idx=0, width=1280, height=720, parent=None):
        shape = (height, width, 3) 
        dtype = np.uint8
        
        # We pass process_class, but we also need to pass the class-specific args.
        # So we override start() lightly to inject these.
        self.camera_idx = camera_idx
        self.img_width = width
        self.img_height = height
        
        super().__init__(name="camera", shape=shape, dtype=dtype, 
                         process_class=CameraIngestionProcess, parent=parent)
                         
    def start(self):
        """Override to pass specific args to the process constructor."""
        if self._process is not None and self._process.is_alive():
            return
            
        # Allocate Shared Memory (from parent)
        try:
            from multiprocessing import shared_memory as shm
            self._shm = shm.SharedMemory(create=True, size=self.bytes_size, name=self.shm_name)
        except Exception as e:
            logger.error(f"Failed to allocate SHM for Camera. {e}")
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
            camera_idx=self.camera_idx,
            width=self.img_width,
            height=self.img_height,
            init_kwargs=init_kwargs
        )
        self._process.start()
        
        from .sensor_base import SensorPoller
        self._poller = SensorPoller(self.latest_ts_ns, self.run_flag)
        self._poller.new_frame_detected.connect(self._on_new_frame)
        self._poller.start()
        logger.info("CameraService started.")
