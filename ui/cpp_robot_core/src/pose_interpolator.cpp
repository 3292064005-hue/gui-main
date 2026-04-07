#include "pose_interpolator.hpp"
#include <algorithm>
#include <cmath>

namespace {

Quaterniond normalizeQuaternion(const Quaterniond& q) {
    const double norm = std::sqrt(q.w * q.w + q.x * q.x + q.y * q.y + q.z * q.z);
    if (norm <= 1e-12) {
        return Quaterniond{};
    }
    return Quaterniond{q.w / norm, q.x / norm, q.y / norm, q.z / norm};
}

Quaterniond negateQuaternion(const Quaterniond& q) {
    return Quaterniond{-q.w, -q.x, -q.y, -q.z};
}

double dotQuaternion(const Quaterniond& a, const Quaterniond& b) {
    return a.w * b.w + a.x * b.x + a.y * b.y + a.z * b.z;
}

Quaterniond lerpQuaternion(const Quaterniond& a, const Quaterniond& b, double alpha) {
    return normalizeQuaternion(Quaterniond{
        a.w + (b.w - a.w) * alpha,
        a.x + (b.x - a.x) * alpha,
        a.y + (b.y - a.y) * alpha,
        a.z + (b.z - a.z) * alpha,
    });
}

Quaterniond slerpQuaternion(Quaterniond a, Quaterniond b, double alpha) {
    a = normalizeQuaternion(a);
    b = normalizeQuaternion(b);
    double dot = dotQuaternion(a, b);
    if (dot < 0.0) {
        b = negateQuaternion(b);
        dot = -dot;
    }
    dot = std::clamp(dot, -1.0, 1.0);
    if (dot > 0.9995) {
        return lerpQuaternion(a, b, alpha);
    }
    const double theta_0 = std::acos(dot);
    const double theta = theta_0 * alpha;
    const double sin_theta = std::sin(theta);
    const double sin_theta_0 = std::sin(theta_0);
    if (std::abs(sin_theta_0) <= 1e-12) {
        return lerpQuaternion(a, b, alpha);
    }
    const double s0 = std::cos(theta) - dot * sin_theta / sin_theta_0;
    const double s1 = sin_theta / sin_theta_0;
    return normalizeQuaternion(Quaterniond{
        s0 * a.w + s1 * b.w,
        s0 * a.x + s1 * b.x,
        s0 * a.y + s1 * b.y,
        s0 * a.z + s1 * b.z,
    });
}

Vec3d lerpVec3(const Vec3d& a, const Vec3d& b, double alpha) {
    return Vec3d{
        a.x + (b.x - a.x) * alpha,
        a.y + (b.y - a.y) * alpha,
        a.z + (b.z - a.z) * alpha,
    };
}

}  // namespace

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
        return PoseRecord{};
    }

    size_t idx1 = tail_;
    size_t idx2 = (tail_ + 1) % capacity_;
    double t1 = buffer_[idx1].timestamp_ns / 1e9;
    double t2 = buffer_[idx2].timestamp_ns / 1e9;

    for (size_t i = 0; i < size_ - 1; ++i) {
        if (timestamp >= t1 && timestamp <= t2) {
            break;
        }
        idx1 = idx2;
        idx2 = (idx2 + 1) % capacity_;
        t1 = buffer_[idx1].timestamp_ns / 1e9;
        t2 = buffer_[idx2].timestamp_ns / 1e9;
    }

    if (timestamp < t1 || timestamp > t2 || std::abs(t2 - t1) <= 1e-12) {
        return PoseRecord{};
    }

    const double alpha = (timestamp - t1) / (t2 - t1);
    const Quaterniond q_interp = slerpQuaternion(buffer_[idx1].orientation, buffer_[idx2].orientation, alpha);
    const Vec3d pos_interp = lerpVec3(buffer_[idx1].position, buffer_[idx2].position, alpha);

    std::array<double, 6> torques_interp{};
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
