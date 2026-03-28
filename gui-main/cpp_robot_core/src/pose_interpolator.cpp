#include "pose_interpolator.hpp"
#include <algorithm>
#include <cmath>

PoseRingBuffer::PoseRingBuffer(size_t capacity)
    : capacity_(capacity), size_(0), head_(0), tail_(0) {
    buffer_.resize(capacity);
}

void PoseRingBuffer::push(const PoseRecord& pose) {
    std::lock_guard<std::mutex> lock(mutex_);
    buffer_[head_] = pose;
    head_ = (head_ + 1) % capacity_;
    if (size_ < capacity_) {
        size_++;
    } else {
        tail_ = (tail_ + 1) % capacity_;
    }
}

PoseRecord PoseRingBuffer::query_interpolated(double timestamp) const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (size_ < 2) {
        return PoseRecord{}; // Not enough data for interpolation
    }

    // Find the two poses to interpolate between
    size_t idx1 = tail_;
    size_t idx2 = (tail_ + 1) % capacity_;
    double t1 = buffer_[idx1].timestamp_ns / 1e9; // Convert to seconds
    double t2 = buffer_[idx2].timestamp_ns / 1e9;

    // Binary search for the right interval
    for (size_t i = 0; i < size_ - 1; ++i) {
        if (timestamp >= t1 && timestamp <= t2) {
            break;
        }
        idx1 = idx2;
        idx2 = (idx2 + 1) % capacity_;
        t1 = buffer_[idx1].timestamp_ns / 1e9;
        t2 = buffer_[idx2].timestamp_ns / 1e9;
    }

    if (timestamp < t1 || timestamp > t2) {
        return PoseRecord{}; // Timestamp out of range
    }

    // Linear interpolation factor
    double alpha = (timestamp - t1) / (t2 - t1);

    // Slerp for quaternion interpolation
    Eigen::Quaterniond q1(buffer_[idx1].orientation);
    Eigen::Quaterniond q2(buffer_[idx2].orientation);

    Eigen::Quaterniond q_interp = q1.slerp(alpha, q2);

    // Linear interpolation for position
    Eigen::Vector3d pos1(buffer_[idx1].position);
    Eigen::Vector3d pos2(buffer_[idx2].position);
    Eigen::Vector3d pos_interp = pos1 + alpha * (pos2 - pos1);

    // Linear interpolation for torques
    std::array<double, 6> torques_interp;
    for (size_t i = 0; i < 6; ++i) {
        torques_interp[i] = buffer_[idx1].external_torques[i] +
                           alpha * (buffer_[idx2].external_torques[i] - buffer_[idx1].external_torques[i]);
    }

    PoseRecord result;
    result.timestamp_ns = static_cast<uint64_t>(timestamp * 1e9);
    result.position = pos_interp;
    result.orientation = q_interp;
    result.external_torques = torques_interp;

    return result;
}