#include "robot_core/scan_supervisor.h"
namespace robot_core {
std::string ScanSupervisor::stage() const { return stage_; }
void ScanSupervisor::setStage(const std::string& s) { stage_ = s; }
void ScanSupervisor::setActiveSegment(int segment_id) { active_segment_ = segment_id; }
int ScanSupervisor::activeSegment() const { return active_segment_; }
void ScanSupervisor::setProgress(double progress_pct) { progress_pct_ = progress_pct; }
double ScanSupervisor::progress() const { return progress_pct_; }
}
