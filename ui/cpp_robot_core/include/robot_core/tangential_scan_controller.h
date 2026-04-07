#pragma once

namespace robot_core {

struct TangentialScanConfig {
  double tangent_speed_min_mm_s{2.0};
  double tangent_speed_max_mm_s{12.0};
  double max_travel_mm{120.0};
  bool enable_lateral_modulation{true};
  double lateral_amplitude_mm{0.5};
  double modulation_frequency_hz{0.25};
};

struct TangentialScanState {
  double progress_m{0.0};
  double lateral_offset_m{0.0};
  bool saturated{false};
};

class TangentialScanController {
public:
  void configure(const TangentialScanConfig& config);
  TangentialScanState advance(double requested_speed_mm_s, double dt_s);
  TangentialScanState hold() const { return state_; }
  void reset();
  const TangentialScanState& state() const { return state_; }

private:
  TangentialScanConfig config_{};
  TangentialScanState state_{};
};

}  // namespace robot_core
