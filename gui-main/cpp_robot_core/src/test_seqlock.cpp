#include "ipc_shm_manager.hpp"
#include <iostream>
#include <thread>
#include <chrono>
#include <atomic>

std::atomic<bool> keep_running{true};

int main() {
    try {
        IPCSharedMemoryManager shm("/test_seqlock_shm");

        // Create test pose data
        PoseData test_pose;
        test_pose.timestamp_ns = 1000000000ULL;
        test_pose.position[0] = 1.0;
        test_pose.position[1] = 2.0;
        test_pose.position[2] = 3.0;
        test_pose.orientation[0] = 1.0; // w
        test_pose.orientation[1] = 0.0; // x
        test_pose.orientation[2] = 0.0; // y
        test_pose.orientation[3] = 0.0; // z
        for (int i = 0; i < 6; ++i) {
            test_pose.external_torques[i] = static_cast<double>(i) * 0.1;
        }

        std::cout << "[Test] Publishing pose data continuously..." << std::endl;

        // Publish data continuously
        while (keep_running) {
            test_pose.timestamp_ns += 1000000ULL; // +1ms
            shm.publish_pose(test_pose);
            std::this_thread::sleep_for(std::chrono::milliseconds(10)); // 100Hz for testing
        }

        std::cout << "[Test] Seqlock IPC test completed successfully!" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "[Test] Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}