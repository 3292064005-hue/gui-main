cmake_minimum_required(VERSION 3.24)
project(SpineUltrasoundCore LANGUAGES CXX)

find_program(ROBOT_CORE_LLVM_AR NAMES llvm-ar HINTS /usr/local/swift/usr/bin)
find_program(ROBOT_CORE_LLVM_RANLIB NAMES llvm-ranlib HINTS /usr/local/swift/usr/bin)
if(ROBOT_CORE_LLVM_AR AND ROBOT_CORE_LLVM_RANLIB AND CMAKE_AR MATCHES "/usr/bin/ar" AND CMAKE_RANLIB MATCHES "/usr/bin/ranlib")
  message(STATUS "Using llvm-ar/llvm-ranlib to avoid static archive failures observed with system binutils in CI containers")
  set(CMAKE_AR "${ROBOT_CORE_LLVM_AR}" CACHE FILEPATH "Archiver" FORCE)
  set(CMAKE_RANLIB "${ROBOT_CORE_LLVM_RANLIB}" CACHE FILEPATH "Ranlib" FORCE)
endif()

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

option(ROBOT_CORE_WITH_XCORE_SDK "Enable direct xCore SDK integration hooks" ON)
option(ROBOT_CORE_WITH_XMATE_MODEL "Enable xMateModel support when vendored SDK is available" ON)
option(ROBOT_CORE_ENABLE_NATIVE_ARCH "Enable -march=native for lab-host optimized builds" OFF)
option(ROBOT_CORE_BUILD_EXAMPLES "Build example executables in the default mainline build" OFF)
set(XCORE_SDK_ROOT "" CACHE PATH "Path to xCore SDK root")

include(cmake/RobotCoreProfiles.cmake)

if(NOT XCORE_SDK_ROOT AND DEFINED ENV{XCORE_SDK_ROOT})
  set(XCORE_SDK_ROOT "$ENV{XCORE_SDK_ROOT}" CACHE PATH "Path to xCore SDK root" FORCE)
endif()
if(NOT XCORE_SDK_ROOT AND DEFINED ENV{ROKAE_SDK_ROOT})
  set(XCORE_SDK_ROOT "$ENV{ROKAE_SDK_ROOT}" CACHE PATH "Path to xCore SDK root" FORCE)
endif()
if(NOT XCORE_SDK_ROOT AND ROBOT_CORE_PROFILE STREQUAL "mock")
  set(_VENDORED_SDK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/rokae_xcore_sdk/robot")
  if(EXISTS "${_VENDORED_SDK_ROOT}/include/rokae/robot.h")
    set(XCORE_SDK_ROOT "${_VENDORED_SDK_ROOT}" CACHE PATH "Path to xCore SDK root" FORCE)
  endif()
endif()

find_package(Threads REQUIRED)
find_package(OpenSSL REQUIRED)
enable_testing()

if(ROBOT_CORE_WITH_XCORE_SDK)
  find_package(VendoredRokaeSdk QUIET)
  if(VendoredRokaeSdk_FOUND)
  elseif(NOT ROBOT_CORE_PROFILE STREQUAL "prod")
    message(WARNING "ROBOT_CORE_WITH_XCORE_SDK=ON but SDK was not found. Falling back to simulated contract runtime.")
  endif()
endif()

add_library(robot_core_build_settings INTERFACE)
target_compile_definitions(robot_core_build_settings INTERFACE
  ROBOT_CORE_FORCE_CONTROL_CONFIG_PATH="${CMAKE_SOURCE_DIR}/../configs/force_control.json"
  ROBOT_CORE_DEFAULT_ROBOT_MODEL="xmate3"
  ROBOT_CORE_DEFAULT_SDK_CLASS="xMateRobot"
)
target_include_directories(robot_core_build_settings INTERFACE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_BINARY_DIR}
)

add_library(robot_core_proto_deps INTERFACE)
target_include_directories(robot_core_proto_deps INTERFACE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_BINARY_DIR}
)

add_library(robot_core_sdk_binding INTERFACE)
if(VendoredRokaeSdk_FOUND)
  target_compile_definitions(robot_core_sdk_binding INTERFACE ROBOT_CORE_WITH_XCORE_SDK=1)
  target_include_directories(robot_core_sdk_binding INTERFACE ${VendoredRokaeSdk_INCLUDE_DIR} ${VendoredRokaeSdk_EXTERNAL_DIR})
  if(ROBOT_CORE_WITH_XMATE_MODEL AND TARGET Rokae::xMateModel)
    target_compile_definitions(robot_core_sdk_binding INTERFACE ROBOT_CORE_WITH_XMATE_MODEL=1)
  endif()
endif()

set(CORE_RUNTIME_SOURCES
  src/command_server.cpp
  src/command_registry.cpp
  src/core_runtime.cpp
  src/core_runtime_power_validation.cpp
  src/core_runtime_session_execution.cpp
  src/core_runtime_contracts.cpp
  src/runtime_state_store.cpp
  src/session_runtime.cpp
  src/contact_gate.cpp
  src/contact_observer.cpp
  src/model_authority.cpp
  src/nrt_motion_service.cpp
  src/recovery_kernel.cpp
  src/robot_family_descriptor.cpp
  src/vendor_robot_port.cpp
  src/recording_service.cpp
  src/ipc_messages.pb.cpp
  src/protobuf_protocol.cpp
  src/recovery_manager.cpp
  src/recovery_policy.cpp
  src/robot_state_hub.cpp
  src/scan_plan_parser.cpp
  src/scan_plan_validator.cpp
  src/state_machine_guard.cpp
  src/rt_motion_service.cpp
  src/safety_service.cpp
  src/sdk_robot_facade.cpp
  src/sdk_robot_facade_lifecycle.cpp
  src/sdk_robot_facade_nrt.cpp
  src/sdk_robot_facade_rt.cpp
  src/sdk_robot_facade_cache.cpp
  src/sdk_robot_facade_ports.cpp
  src/sdk_robot_facade_state.cpp
  src/normal_force_estimator.cpp
  src/normal_axis_admittance_controller.cpp
  src/tangential_scan_controller.cpp
  src/orientation_trim_controller.cpp
  src/contact_control_contract.cpp
  src/telemetry_publisher.cpp
  src/kinematics_validator.cpp
  src/pose_interpolator.cpp
)

add_library(spine_robot_core_runtime STATIC ${CORE_RUNTIME_SOURCES})
robot_core_apply_common_options(spine_robot_core_runtime)
target_link_libraries(spine_robot_core_runtime
  PUBLIC
    robot_core_build_settings
    robot_core_proto_deps
    robot_core_sdk_binding
  PRIVATE
    Threads::Threads
    OpenSSL::SSL
    OpenSSL::Crypto
    rt
)
robot_core_apply_sdk_policy(spine_robot_core_runtime)

add_library(robot_core_test_support INTERFACE)
target_link_libraries(robot_core_test_support INTERFACE
  robot_core_build_settings
  robot_core_proto_deps
  robot_core_sdk_binding
  Threads::Threads
)

function(robot_core_add_cpp_test target_name source_file)
  add_executable(${target_name} ${source_file})
  robot_core_apply_common_options(${target_name})
  target_link_libraries(${target_name} PRIVATE robot_core_test_support ${ARGN})
endfunction()

add_executable(spine_robot_core src/main_ubuntu_rt.cpp)
robot_core_apply_common_options(spine_robot_core)
target_link_libraries(spine_robot_core PRIVATE spine_robot_core_runtime)

robot_core_add_cpp_test(test_seqlock tests/test_seqlock.cpp rt)

robot_core_add_cpp_test(test_force_control tests/test_force_control.cpp spine_robot_core_runtime)
robot_core_add_cpp_test(test_normal_force_estimator tests/test_normal_force_estimator.cpp spine_robot_core_runtime)
robot_core_add_cpp_test(test_normal_axis_admittance_controller tests/test_normal_axis_admittance_controller.cpp spine_robot_core_runtime)
robot_core_add_cpp_test(test_tangential_scan_controller tests/test_tangential_scan_controller.cpp spine_robot_core_runtime)
robot_core_add_cpp_test(test_orientation_trim_controller tests/test_orientation_trim_controller.cpp spine_robot_core_runtime)
robot_core_add_cpp_test(test_contact_control_contract tests/test_contact_control_contract.cpp spine_robot_core_runtime)

robot_core_add_cpp_test(test_impedance_scan tests/test_impedance_scan.cpp spine_robot_core_runtime)

robot_core_add_cpp_test(test_protocol_bridge tests/test_protocol_bridge.cpp spine_robot_core_runtime)

robot_core_add_cpp_test(test_recovery_manager tests/test_recovery_manager.cpp spine_robot_core_runtime)
robot_core_add_cpp_test(test_recording_service tests/test_recording_service.cpp spine_robot_core_runtime)
robot_core_add_cpp_test(test_rt_motion_service_truth tests/test_rt_motion_service_truth.cpp spine_robot_core_runtime)

if(ROBOT_CORE_BUILD_EXAMPLES)
  add_executable(impedance_scan_example examples/impedance_scan_example.cpp)
  robot_core_apply_common_options(impedance_scan_example)
  target_link_libraries(impedance_scan_example PRIVATE spine_robot_core_runtime)
endif()

add_test(NAME cpp_seqlock COMMAND test_seqlock)
add_test(NAME cpp_force_control COMMAND test_force_control)
add_test(NAME cpp_normal_force_estimator COMMAND test_normal_force_estimator)
add_test(NAME cpp_normal_axis_admittance_controller COMMAND test_normal_axis_admittance_controller)
add_test(NAME cpp_tangential_scan_controller COMMAND test_tangential_scan_controller)
add_test(NAME cpp_orientation_trim_controller COMMAND test_orientation_trim_controller)
add_test(NAME cpp_contact_control_contract COMMAND test_contact_control_contract)
add_test(NAME cpp_impedance_scan COMMAND test_impedance_scan)
add_test(NAME cpp_protocol_bridge COMMAND test_protocol_bridge)
add_test(NAME cpp_recovery_manager COMMAND test_recovery_manager)
add_test(NAME cpp_recording_service COMMAND test_recording_service)

install(TARGETS spine_robot_core DESTINATION /opt/spine_ultrasound/cpp_robot_core/bin)
install(TARGETS spine_robot_core_runtime DESTINATION /opt/spine_ultrasound/cpp_robot_core/lib)

add_test(NAME cpp_rt_motion_service_truth COMMAND test_rt_motion_service_truth)
