import cv2
import cv2.aruco as aruco
import numpy as np
import time
from loguru import logger

class CameraArucoService:
    """
    Substitutes expensive $10K depth cameras using a simple printed ArUco tag.
    1. Glued to the Patient's spine flank.
    2. A standard webcam tracks its 6-DOF movement caused by breathing.
    3. The T_shift matrix is extracted and sent to the C++ core via IPC.
    This creates an absolute "Patient Coordinate Frame" offsetting the rigid robot world.
    """
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        self.running = False
        
        # Select common dictionary of ArUco tags
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_5X5_250)
        self.parameters = aruco.DetectorParameters()
        self.detector = aruco.ArucoDetector(self.aruco_dict, self.parameters)
        
        # Camera Intrinsics (Mocking typical Logitech 1080p C920)
        # Needs calibration for real-world precision!
        self.camera_matrix = np.array([[800, 0, 320], [0, 800, 240], [0, 0, 1]], dtype=float)
        self.dist_coeffs = np.zeros((4,1))
        self.marker_length = 0.05 # 5cm width ArUco 
        
        # Base Matrix
        self.initial_pose = None
        self.latest_shift = np.eye(4) # T_patient_shift

    def start_tracking(self):
        logger.info("[ArUco Tracker] Breathing Compensation Camera armed.")
        self.running = True
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret: continue
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = self.detector.detectMarkers(gray)
            
            if ids is not None and len(ids) > 0:
                # Assuming the patient marker is ID=1
                patient_idx = np.where(ids == 1)[0]
                if len(patient_idx) > 0:
                    rvec, tvec, _ = aruco.estimatePoseSingleMarkers(
                        corners[patient_idx[0]], self.marker_length, 
                        self.camera_matrix, self.dist_coeffs
                    )
                    
                    # Convert rotation vector to Rotation Matrix
                    R, _ = cv2.Rodrigues(rvec[0])
                    current_pose = np.eye(4)
                    current_pose[:3, :3] = R
                    current_pose[:3, 3] = tvec[0][0]
                    
                    if self.initial_pose is None:
                        # Lock zero position when scan starts
                        self.initial_pose = current_pose
                        logger.success("ArUco Patient Reference Frame Locked!")
                    
                    # Compute relative shift due to breathing distortion: T_shift = T_curr * T_init^-1
                    self.latest_shift = np.dot(current_pose, np.linalg.inv(self.initial_pose))

            # Push T_shift into Memory Pool IPC so C++ modifies its path on the fly!
            # Example (Assuming pool linkage): memory_pool.push_patient_shift(self.latest_shift)

            time.sleep(1/30.0) # 30FPS camera tracking

    def stop(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()
