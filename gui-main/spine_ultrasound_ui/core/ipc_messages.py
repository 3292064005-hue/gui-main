import struct
import numpy as np

# Direction: Python UI -> C++ Robot Core
# CommandPose: 
#   int64_t timestamp_ns -> q (8 bytes)
#   double tcp_pose_td[16] -> 16d (128 bytes)
# Total: 136 bytes
FMT_COMMAND_POSE = "=q16d"
SIZE_COMMAND_POSE = struct.calcsize(FMT_COMMAND_POSE)

def pack_command_pose(timestamp_ns, pose_array_16):
    """
    Packs a 16-element target TCP pose matrix into binary.
    Zero object overhead after initial generation.
    """
    return struct.pack(FMT_COMMAND_POSE, int(timestamp_ns), *pose_array_16)


# Direction: C++ Robot Core -> Python UI
# RobotTelemetry:
#   int64_t timestamp_ns          -> q (8 bytes)
#   double tcp_pose_measured[16]  -> 16d (128 bytes)
#   double joint_angles[7]        -> 7d (56 bytes)
#   double actual_force_z         -> d (8 bytes)
#   int32_t safety_status         -> i (4 bytes)
# Total: 204 bytes
FMT_ROBOT_TELEMETRY = "=q16d7ddi"
SIZE_ROBOT_TELEMETRY = struct.calcsize(FMT_ROBOT_TELEMETRY)

def unpack_robot_telemetry(byte_data):
    """
    Returns an unrolled tuple corresponding to the telemetry structure.
    Suitable for zero-allocation RingBuffer insertion via pointer mapping.
    """
    return struct.unpack(FMT_ROBOT_TELEMETRY, byte_data)
