#pragma once

#include <Eigen/Dense>
#include <Eigen/Geometry>
#include <vector>
#include <mutex>
#include <array>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>

struct PoseRecord {
    uint64_t timestamp_ns;
    Eigen::Vector3d position;
    Eigen::Quaterniond orientation;
    std::array<double, 6> external_torques;
};

class PoseRingBuffer {
private:
    size_t capacity_;
    size_t size_;
    size_t head_;
    size_t tail_;
    std::vector<PoseRecord> buffer_;
    mutable std::mutex mutex_;

public:
    explicit PoseRingBuffer(size_t capacity);

    void push(const PoseRecord& record);

    // Query interpolated pose at given timestamp (in seconds)
    PoseRecord query_interpolated(double timestamp) const;
};