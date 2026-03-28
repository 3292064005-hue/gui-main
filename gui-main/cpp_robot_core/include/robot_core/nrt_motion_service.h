#pragma once
namespace robot_core {
class NrtMotionService {
public:
  bool goHome();
  bool approachPrescan();
  bool safeRetreat();
};
}
