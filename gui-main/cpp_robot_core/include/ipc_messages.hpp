#ifndef IPC_MESSAGES_HPP
#define IPC_MESSAGES_HPP

#include <cstdint>

namespace spine_core_pod {

// For maximal zero-copy performance across C++ and Python over ZMQ UDP/TCP,
// we define strict Plain Old Data (POD) structs. These map perfectly to Python's struct.unpack.
// C++ sizeof must match Python calcsize exactly.

#pragma pack(push, 1)

// Direction: Python UI -> C++ Robot Core
// Size: 8 + (16*8) = 8 + 128 = 136 bytes
struct CommandPose {
    int64_t timestamp_ns;     // UI creation time or Target Interpolation time
    double tcp_pose_td[16];   // Target trajectory pose (Homogeneous Matrix 4x4)
};

// Direction: C++ Robot Core -> Python UI
// Size: 8 + (16*8) + (7*8) + 8 + 4 = 8 + 128 + 56 + 8 + 4 = 204 bytes
struct RobotTelemetry {
    int64_t timestamp_ns;          // C++ emission time (Master Clock)
    double tcp_pose_measured[16];  // Actual measured TCP Pose (frame_T_end)
    double joint_angles[7];        // Needed for collision checking/display
    double actual_force_z;         // Z-axis force from getEndTorque()
    int32_t safety_status;         // 0: OK, 1: SoftStop/Retreating, -1: Error
};

#pragma pack(pop)

} // namespace spine_core_pod

#endif // IPC_MESSAGES_HPP
