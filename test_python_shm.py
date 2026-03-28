#!/usr/bin/env python3

import sys
import os
import time
import subprocess
import signal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine_ultrasound_ui.core_pipeline.shm_client import ShmPoseReader

def test_cross_language_ipc():
    cpp_process = None
    try:
        # Start C++ publisher in background
        cpp_process = subprocess.Popen(
            ['./cpp_robot_core/build/test_seqlock'],
            cwd='/home/chen/gui-main'
        )

        # Wait a bit for C++ to initialize
        time.sleep(2)

        # Try to connect to the shared memory
        reader = ShmPoseReader("test_seqlock_shm")
        print("[Python Test] Connected to shared memory")

        # Try to read data multiple times
        for i in range(10):
            result = reader.get_latest_pose()
            if result:
                ts, pos, ori, torques = result
                print(f"[Python Test] Read pose at {ts}: pos={pos}, z-force={torques[2]:.2f}")
            else:
                print("[Python Test] No data available")
            time.sleep(0.1)

        reader.close()

    except Exception as e:
        print(f"[Python Test] Error: {e}")
    finally:
        # Clean up C++ process
        if cpp_process:
            cpp_process.terminate()
            try:
                cpp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cpp_process.kill()

if __name__ == "__main__":
    test_cross_language_ipc()