#pragma once

#include <vector>
#include <mutex>
#include <array>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>

struct Vec3d {
    double x{0.0};
    double y{0.0};
    double z{0.0};
};

struct Quaterniond {
    double w{1.0};
    double x{0.0};
    double y{0.0};
    double z{0.0};
};

struct PoseRecord {
    uint64_t timestamp_ns;
    Vec3d position;
    Quaterniond orientation;
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