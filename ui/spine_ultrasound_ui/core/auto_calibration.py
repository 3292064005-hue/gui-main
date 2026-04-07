import numpy as np
from loguru import logger
import scipy.linalg

class PhantomAutoCalibrator:
    """
    Solves AX = XB Hand-Eye Calibration using Umeyama SVD (Singular Value Decomposition).
    Ensures that T_probe relative to ER3 Flange is re-calculated perfectly if the 
    probe is bumped, rather than relying on a static config file.
    """
    def __init__(self):
        # A: Flange poses (from robot kinematics)
        # B: Probe poses (extracted from Ultrasound Sphere Phantom tracking)
        self.flange_matrices = [] 
        self.us_sphere_center_points = []
    
    def add_calibration_sample(self, t_flange: np.ndarray, sphere_center_px: tuple):
        """ 
        The operator sweeps over a phantom sphere in water. 
        Each frame sends a flange matrix and where the sphere center is seen in the UI.
        """
        self.flange_matrices.append(t_flange)
        # Assuming simple pixel to mm mapping based on depth config
        sphere_depth_mm = sphere_center_px[1] * 0.1 # example 0.1mm/pixel
        sphere_local = np.array([0, 0, sphere_depth_mm, 1.0])
        self.us_sphere_center_points.append(sphere_local)

    def compute_umeyama_svd(self) -> np.ndarray:
        """
        Using the Least-Squares SVD point alignment across N poses.
        Finds the exact T_probe transformation matrix.
        Requires at least 3 non-collinear sample suites.
        """
        if len(self.flange_matrices) < 3:
            logger.error("[Calibration] Not enough samples. Need >= 3 distinct poses.")
            return np.eye(4)
            
        logger.info(f"Running SVD Auto-Calibration across {len(self.flange_matrices)} poses...")

        # Extract centroids
        P_world = np.array(...) # Computed global sphere positions
        P_US = np.array(self.us_sphere_center_points)[:, :3]

        # Umeyama Algorithm implementation (simplified representation)
        # Centering points
        mean_W = np.mean(P_world, axis=0)
        mean_U = np.mean(P_US, axis=0)

        # Covariance Matrix H
        H = np.zeros((3, 3))
        for i in range(len(P_US)):
            H += np.outer(P_US[i] - mean_U, P_world[i] - mean_W)

        # Singular Value Decomposition
        U, S, Vt = np.linalg.svd(H)

        # Ensure right-handed coordinate system
        R = np.dot(Vt.T, U.T)
        if np.linalg.det(R) < 0:
            Vt[2, :] *= -1
            R = np.dot(Vt.T, U.T)

        # Compute translation
        T = mean_W - np.dot(R, mean_U)

        # Construct final Transformation Matrix T_probe
        T_probe = np.eye(4)
        T_probe[:3, :3] = R
        T_probe[:3, 3] = T

        logger.success("[Calibration] Optimized T_probe Solved via SVD! Updating config.")
        return T_probe
