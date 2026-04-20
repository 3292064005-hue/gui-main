#if __has_include("rokae/robot.h")
#include "rokae/robot.h"
#endif

#include <type_traits>

int main() {
#if defined(ROBOT_CORE_WITH_XCORE_SDK) && defined(ROBOT_CORE_WITH_XMATE_MODEL) && defined(XMATEMODEL_LIB_SUPPORTED) && __has_include("rokae/robot.h")
  static_assert(std::is_same_v<decltype(std::declval<rokae::xMateRobot&>().model()), rokae::xMateModel<6>>,
                "xMateRobot::model() must resolve to rokae::xMateModel<6> when authoritative model support is enabled");
#endif
  return 0;
}
