#include "pose_interpolator.hpp"
#include "ipc_shm_manager.hpp"
#include <iostream>
#include <chrono>
#include <thread>

int main() {
    std::cout << "Testing PoseRingBuffer and IPCSharedMemoryManager..." << std::endl;

    // Test PoseRingBuffer
    PoseRingBuffer buffer(100);

    // Create some test pose records
    PoseRecord record1;
    record1.timestamp_ns = 1000000000; // 1 second
    record1.position = Eigen::Vector3d(1.0, 2.0, 3.0);
    record1.orientation = Eigen::Quaterniond(1.0, 0.0, 0.0, 0.0);
    record1.external_torques = {0.1, 0.2, 0.3, 0.4, 0.5, 0.6};

    PoseRecord record2;
    record2.timestamp_ns = 2000000000; // 2 seconds
    record2.position = Eigen::Vector3d(2.0, 3.0, 4.0);
    record2.orientation = Eigen::Quaterniond(0.707, 0.0, 0.0, 0.707);
    record2.external_torques = {0.2, 0.3, 0.4, 0.5, 0.6, 0.7};

    buffer.push(record1);
    buffer.push(record2);

    // Test interpolation
    PoseRecord interpolated = buffer.query_interpolated(1.5); // 1.5 seconds
    std::cout << "Interpolated position: " << interpolated.position.transpose() << std::endl;
    std::cout << "Interpolated orientation: " << interpolated.orientation.coeffs().transpose() << std::endl;

    // Test IPCSharedMemoryManager
    IPCSharedMemoryManager shm("/test_shm", 1024, true);
    if (shm.initialize()) {
        std::cout << "Shared memory initialized successfully" << std::endl;

        // Write a test value
        double test_value = 42.0;
        if (shm.write_struct(0, test_value)) {
            std::cout << "Successfully wrote to shared memory" << std::endl;

            // Read it back
            double read_value;
            if (shm.read_struct(0, read_value)) {
                std::cout << "Successfully read from shared memory: " << read_value << std::endl;
            }
        }
    } else {
        std::cout << "Failed to initialize shared memory" << std::endl;
    }

    std::cout << "All tests completed successfully!" << std::endl;
    return 0;
}