#pragma once

#include "robot_core/sdk_robot_facade.h"

#ifdef ROBOT_CORE_WITH_XCORE_SDK
#include "rokae/data_types.h"
#include "rokae/robot.h"
#include "rokae/utility.h"
#endif

#include <algorithm>
#include <cmath>

namespace robot_core {
namespace sdk_robot_facade_internal {

constexpr std::size_t kTranslationIndices[3] = {3, 7, 11};

inline bool looksLikeMillimetres(double value) {
  return std::abs(value) > 2.0;
}

inline double mmToM(double value_mm) {
  return value_mm / 1000.0;
}

inline std::array<double, 16> normalizeFrameMatrixMmToM(const std::array<double, 16>& matrix) {
  auto normalized = matrix;
  for (const auto idx : kTranslationIndices) {
    if (looksLikeMillimetres(normalized[idx])) {
      normalized[idx] = mmToM(normalized[idx]);
    }
  }
  return normalized;
}

inline std::array<double, 3> normalizeLoadComMmToM(const std::array<double, 3>& values) {
  return {mmToM(values[0]), mmToM(values[1]), mmToM(values[2])};
}

inline std::size_t translationIndexForAxis(int axis) {
  switch (axis) {
    case 0: return 3;
    case 1: return 7;
    default: return 11;
  }
}

inline std::array<double, 16> postureVectorToMatrix(const std::vector<double>& posture) {
  std::array<double, 16> matrix{};
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  std::array<double, 6> xyzabc{0.0, 0.0, 0.240, 0.0, 0.0, 0.0};
  for (std::size_t idx = 0; idx < std::min<std::size_t>(xyzabc.size(), posture.size()); ++idx) {
    xyzabc[idx] = posture[idx];
  }
  rokae::Utils::postureToTransArray(xyzabc, matrix);
#else
  matrix = {1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.240,
            0.0, 0.0, 0.0, 1.0};
#endif
  return matrix;
}

inline double clampSigned(double value, double magnitude) {
  return std::max(-std::abs(magnitude), std::min(std::abs(magnitude), value));
}

inline std::array<double, 16> identityPoseMatrix() {
  return {1.0, 0.0, 0.0, 0.0,
          0.0, 1.0, 0.0, 0.0,
          0.0, 0.0, 1.0, 0.240,
          0.0, 0.0, 0.0, 1.0};
}

inline double degToRad(double value_deg) {
  return value_deg * M_PI / 180.0;
}

#ifdef ROBOT_CORE_WITH_XCORE_SDK
inline std::array<double, 6> toArray6(const std::vector<double>& values) {
  std::array<double, 6> out{};
  for (std::size_t idx = 0; idx < std::min<std::size_t>(out.size(), values.size()); ++idx) {
    out[idx] = values[idx];
  }
  return out;
}

inline std::array<double, 3> toArray3(const std::vector<double>& values) {
  std::array<double, 3> out{};
  for (std::size_t idx = 0; idx < std::min<std::size_t>(out.size(), values.size()); ++idx) {
    out[idx] = values[idx];
  }
  return out;
}
#endif

}  // namespace sdk_robot_facade_internal
}  // namespace robot_core
