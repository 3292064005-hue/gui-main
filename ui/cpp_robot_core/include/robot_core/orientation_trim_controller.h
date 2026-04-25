#pragma once

namespace robot_core {

struct OrientationTrimConfig {
  double gain{0.08};
  double max_trim_deg{1.5};
  double lowpass_hz{8.0};
};

struct OrientationTrimState {
  double trim_rad{0.0};
  bool saturated{false};
};

class OrientationTrimController {
public:
  void configure(const OrientationTrimConfig& config);
  OrientationTrimState step(double force_error_n, double dt_s);
  void reset();
  const OrientationTrimState& state() const { return state_; }

private:
  struct LocalStateStore {
    OrientationTrimConfig config{};
  };
  LocalStateStore state_store_{};
  OrientationTrimState state_{};
};

}  // namespace robot_core
