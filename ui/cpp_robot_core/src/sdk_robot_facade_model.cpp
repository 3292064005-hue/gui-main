#include "robot_core/sdk_robot_facade_internal.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <string>
#include <vector>

namespace robot_core {
namespace {

bool isFiniteVector(const std::vector<double>& values, std::size_t count) {
  if (values.size() < count) return false;
  for (std::size_t i = 0; i < count; ++i) {
    if (!std::isfinite(values[i])) return false;
  }
  return true;
}

template <std::size_t N>
bool isFiniteArray(const std::array<double, N>& values) {
  return std::all_of(values.begin(), values.end(), [](double value) { return std::isfinite(value); });
}

double normalizeAngleRad(double value) {
  if (!std::isfinite(value)) return value;
  if (std::fabs(value) > (2.0 * M_PI + 1e-6)) {
    return value * M_PI / 180.0;
  }
  return value;
}

double normalizeLengthM(double value) {
  if (!std::isfinite(value)) return value;
  if (std::fabs(value) > 2.0) {
    return value / 1000.0;
  }
  return value;
}

std::array<double, 16> waypointToPoseMatrix(const ScanWaypoint& waypoint) {
  std::array<double, 6> xyzabc{
      normalizeLengthM(waypoint.x),
      normalizeLengthM(waypoint.y),
      normalizeLengthM(waypoint.z),
      normalizeAngleRad(waypoint.rx),
      normalizeAngleRad(waypoint.ry),
      normalizeAngleRad(waypoint.rz),
  };
  std::array<double, 16> pose{};
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  rokae::Utils::postureToTransArray(xyzabc, pose);
#else
  (void)xyzabc;
#endif
  return pose;
}

template <std::size_t N>
std::array<double, N> vectorToArrayN(const std::vector<double>& values, double default_value = 0.0) {
  std::array<double, N> out{};
  out.fill(default_value);
  for (std::size_t i = 0; i < std::min<std::size_t>(N, values.size()); ++i) {
    out[i] = values[i];
  }
  return out;
}

std::array<double, 3> inertiaFirst3(const std::array<double, 6>& values) {
  return {values[0], values[1], values[2]};
}

double determinant6x6(const std::array<double, 36>& jacobian) {
  double matrix[6][6];
  for (int row = 0; row < 6; ++row) {
    for (int col = 0; col < 6; ++col) {
      matrix[row][col] = jacobian[static_cast<std::size_t>(row * 6 + col)];
    }
  }
  double det = 1.0;
  int sign = 1;
  for (int pivot = 0; pivot < 6; ++pivot) {
    int best = pivot;
    double best_abs = std::fabs(matrix[pivot][pivot]);
    for (int row = pivot + 1; row < 6; ++row) {
      const double value_abs = std::fabs(matrix[row][pivot]);
      if (value_abs > best_abs) {
        best_abs = value_abs;
        best = row;
      }
    }
    if (best_abs < 1e-12) {
      return 0.0;
    }
    if (best != pivot) {
      for (int col = 0; col < 6; ++col) {
        std::swap(matrix[pivot][col], matrix[best][col]);
      }
      sign *= -1;
    }
    const double pivot_value = matrix[pivot][pivot];
    det *= pivot_value;
    for (int row = pivot + 1; row < 6; ++row) {
      const double factor = matrix[row][pivot] / pivot_value;
      for (int col = pivot + 1; col < 6; ++col) {
        matrix[row][col] -= factor * matrix[pivot][col];
      }
    }
  }
  return det * static_cast<double>(sign);
}

}  // namespace

SdkRobotFacade::AuthoritativeKinematicsCheckResult SdkRobotFacade::validatePlanAuthoritativeKinematics(const ScanPlan& plan) const {
  AuthoritativeKinematicsCheckResult result;
#if !defined(ROBOT_CORE_WITH_XCORE_SDK) || !defined(ROBOT_CORE_WITH_XMATE_MODEL)
  result.reason = "authoritative_xmatemodel_unavailable_in_build";
  return result;
#else
  if (!sdkAvailable() || !xmateModelAvailable()) {
    result.reason = "authoritative_xmatemodel_unavailable_in_build";
    return result;
  }
  if (!live_binding_established_ || robot_ == nullptr) {
    result.reason = "authoritative_kinematics_requires_live_binding";
    return result;
  }
  if (rt_config_.axis_count != 6) {
    result.reason = "authoritative_kinematics_supports_only_xmate_6_axis_in_current_runtime";
    return result;
  }

  try {
    auto model = robot_->model();
    const auto tcp_frame = sdk_robot_facade_internal::normalizeFrameMatrixMmToM(rt_config_.tcp_frame_matrix_m);
    const std::array<double, 16> stiffness_frame{1.0, 0.0, 0.0, 0.0,
                                                 0.0, 1.0, 0.0, 0.0,
                                                 0.0, 0.0, 1.0, 0.0,
                                                 0.0, 0.0, 0.0, 1.0};
    model.setTcpCoor(tcp_frame, stiffness_frame);
    model.setLoad(rt_config_.load_kg, rt_config_.load_com_m, inertiaFirst3(rt_config_.load_inertia));

    std::error_code ec;
    std::array<double, 6> seed = isFiniteVector(joint_pos_, 6) ? vectorToArrayN<6>(joint_pos_) : robot_->jointPos(ec);
    if (ec || !isFiniteArray(seed)) {
      result.available = true;
      result.passed = false;
      result.reason = "authoritative_kinematics_seed_unavailable";
      return result;
    }

    std::array<double, 6> zeros{};
    result.available = true;
    for (const auto& segment : plan.segments) {
      for (std::size_t index = 0; index < segment.waypoints.size(); ++index) {
        const auto& waypoint = segment.waypoints[index];
        const auto pose = waypointToPoseMatrix(waypoint);
        std::array<double, 6> solved{};
        const int ik_status = model.getJointPos(pose, 0.0, seed, solved);
        if (ik_status != 0 || !isFiniteArray(solved)) {
          result.passed = false;
          result.reason = "kinematic_valid: authoritative xMateModel IK failed at segment=" + std::to_string(segment.segment_id) +
                          " waypoint=" + std::to_string(index + 1) + " status=" + std::to_string(ik_status);
          return result;
        }
        const auto jacobian = model.jacobian(solved);
        if (!isFiniteArray(jacobian)) {
          result.passed = false;
          result.reason = "kinematic_valid: authoritative jacobian contains non-finite values at segment=" + std::to_string(segment.segment_id) +
                          " waypoint=" + std::to_string(index + 1);
          return result;
        }
        const double det = determinant6x6(jacobian);
        if (!std::isfinite(det) || std::fabs(det) < 1e-8) {
          result.passed = false;
          result.reason = "kinematic_valid: authoritative jacobian singularity margin insufficient at segment=" + std::to_string(segment.segment_id) +
                          " waypoint=" + std::to_string(index + 1);
          return result;
        }
        const auto gravity_torque = model.getTorque(solved, zeros, zeros, rokae::TorqueType::gravity);
        if (!isFiniteArray(gravity_torque)) {
          result.passed = false;
          result.reason = "kinematic_valid: authoritative torque model returned non-finite values at segment=" + std::to_string(segment.segment_id) +
                          " waypoint=" + std::to_string(index + 1);
          return result;
        }
        for (double value : gravity_torque) {
          if (std::fabs(value) > 500.0) {
            result.warnings.push_back("authoritative torque magnitude exceeded advisory envelope at segment=" + std::to_string(segment.segment_id) +
                                      " waypoint=" + std::to_string(index + 1));
            break;
          }
        }
        seed = solved;
      }
    }
    result.passed = true;
    result.reason = "authoritative xMateModel feasibility passed";
    return result;
  } catch (const std::exception& ex) {
    result.available = true;
    result.passed = false;
    result.reason = std::string("kinematic_valid: authoritative xMateModel exception: ") + ex.what();
    return result;
  }
#endif
}

}  // namespace robot_core
