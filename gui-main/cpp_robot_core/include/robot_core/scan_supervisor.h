#pragma once
#include <string>
namespace robot_core {
class ScanSupervisor {
public:
  std::string stage() const;
  void setStage(const std::string& s);
  void setActiveSegment(int segment_id);
  int activeSegment() const;
  void setProgress(double progress_pct);
  double progress() const;
private:
  std::string stage_{"Precheck"};
  int active_segment_{0};
  double progress_pct_{0.0};
};
}
