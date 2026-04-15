set(ROBOT_CORE_PROFILE "" CACHE STRING "Runtime profile for the robot core build")
set_property(CACHE ROBOT_CORE_PROFILE PROPERTY STRINGS mock hil prod)

if(NOT CMAKE_CONFIGURATION_TYPES)
  if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Choose the build type" FORCE)
  endif()
endif()
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g3" CACHE STRING "Debug flags" FORCE)
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING "Release flags" FORCE)
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g -DNDEBUG" CACHE STRING "RelWithDebInfo flags" FORCE)
set(CMAKE_CXX_FLAGS_MINSIZEREL "-Os -DNDEBUG" CACHE STRING "MinSizeRel flags" FORCE)

if(NOT ROBOT_CORE_PROFILE)
  message(FATAL_ERROR "ROBOT_CORE_PROFILE must be explicitly set to mock, hil, or prod.")
endif()


if(ROBOT_CORE_PROFILE STREQUAL "mock")
  set(CMAKE_CXX_FLAGS_RELEASE "-O0 -DNDEBUG" CACHE STRING "Release flags" FORCE)
  set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O0 -g -DNDEBUG" CACHE STRING "RelWithDebInfo flags" FORCE)
endif()

include(cmake/RobotCoreBuildOptions.cmake)
include(cmake/RobotCoreSdkPolicy.cmake)

function(robot_core_apply_common_options target_name)
  robot_core_apply_build_options(${target_name})
  target_compile_definitions(${target_name} PRIVATE ROBOT_CORE_PROFILE_${ROBOT_CORE_PROFILE}=1)
endfunction()
