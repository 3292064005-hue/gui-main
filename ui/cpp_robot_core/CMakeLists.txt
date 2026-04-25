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
find_package(Python3 REQUIRED COMPONENTS Interpreter)
enable_testing()

set(ROBOT_CORE_IDENTITY_REGISTRY ${CMAKE_CURRENT_SOURCE_DIR}/../configs/robot_identity_mainline.json)
file(READ ${ROBOT_CORE_IDENTITY_REGISTRY} ROBOT_CORE_IDENTITY_REGISTRY_JSON)
string(JSON ROBOT_CORE_MAINLINE_FAMILY_KEY GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} family_key)
string(JSON ROBOT_CORE_MAINLINE_ROBOT_MODEL GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} robot_model)
string(JSON ROBOT_CORE_MAINLINE_DISPLAY_NAME GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} display_name)
string(JSON ROBOT_CORE_MAINLINE_SDK_CLASS GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} sdk_robot_class)
string(JSON ROBOT_CORE_MAINLINE_AXIS_COUNT GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} axis_count)
string(JSON ROBOT_CORE_MAINLINE_CONTROLLER_FAMILY GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} controller_family)
string(JSON ROBOT_CORE_MAINLINE_CONTROLLER_VERSION GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} controller_version)
string(JSON ROBOT_CORE_MAINLINE_PREFERRED_LINK GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} preferred_link)
string(JSON ROBOT_CORE_MAINLINE_CLINICAL_MODE GET ${ROBOT_CORE_IDENTITY_REGISTRY_JSON} clinical_mainline_mode)

set(RUNTIME_COMMAND_MANIFEST_JSON ${CMAKE_CURRENT_SOURCE_DIR}/../schemas/runtime_command_manifest.json)
set(GENERATED_RUNTIME_COMMAND_MANIFEST_INC ${CMAKE_CURRENT_SOURCE_DIR}/include/robot_core/generated_command_manifest.inc)
add_custom_command(
  OUTPUT ${GENERATED_RUNTIME_COMMAND_MANIFEST_INC}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../scripts/generate_runtime_command_artifacts.py
  DEPENDS
    ${RUNTIME_COMMAND_MANIFEST_JSON}
    ${CMAKE_CURRENT_SOURCE_DIR}/../scripts/generate_runtime_command_artifacts.py
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/..
  COMMENT "Generating shared runtime command artifacts"
  VERBATIM
)
add_custom_target(generate_runtime_command_artifacts ALL DEPENDS ${GENERATED_RUNTIME_COMMAND_MANIFEST_INC})

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
  ROBOT_CORE_IDENTITY_REGISTRY_PATH="${ROBOT_CORE_IDENTITY_REGISTRY}"
  ROBOT_CORE_MAINLINE_FAMILY_KEY="${ROBOT_CORE_MAINLINE_FAMILY_KEY}"
  ROBOT_CORE_DEFAULT_ROBOT_MODEL="${ROBOT_CORE_MAINLINE_ROBOT_MODEL}"
  ROBOT_CORE_DEFAULT_ROBOT_LABEL="${ROBOT_CORE_MAINLINE_DISPLAY_NAME}"
  ROBOT_CORE_DEFAULT_SDK_CLASS="${ROBOT_CORE_MAINLINE_SDK_CLASS}"
  ROBOT_CORE_DEFAULT_AXIS_COUNT=${ROBOT_CORE_MAINLINE_AXIS_COUNT}
  ROBOT_CORE_DEFAULT_CONTROLLER_FAMILY="${ROBOT_CORE_MAINLINE_CONTROLLER_FAMILY}"
  ROBOT_CORE_DEFAULT_CONTROLLER_VERSION="${ROBOT_CORE_MAINLINE_CONTROLLER_VERSION}"
  ROBOT_CORE_DEFAULT_PREFERRED_LINK="${ROBOT_CORE_MAINLINE_PREFERRED_LINK}"
  ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE="${ROBOT_CORE_MAINLINE_CLINICAL_MODE}"
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
    target_compile_definitions(robot_core_sdk_binding INTERFACE ROBOT_CORE_WITH_XMATE_MODEL=1 XMATEMODEL_LIB_SUPPORTED=1)
  endif()
endif()

set(CORE_RUNTIME_SOURCES
  src/command_server.cpp
  src/command_registry.cpp
  src/runtime_command_contracts.cpp
  src/core_runtime.cpp
  src/core_runtime_dispatcher.cpp
  src/core_runtime_query_commands.cpp
  src/core_runtime_query_operational.cpp
  src/core_runtime_query_motion.cpp
  src/core_runtime_query_identity.cpp
  src/core_runtime_query_contracts.cpp
  src/core_runtime_contract_publisher.cpp
  src/core_runtime_power_validation.cpp
  src/core_runtime_authority.cpp
  src/core_runtime_session_execution.cpp
  src/core_runtime_session_commands.cpp
  src/core_runtime_execution_commands.cpp
  src/core_runtime_contracts.cpp
  src/core_runtime_contract_identity.cpp
  src/core_runtime_contract_safety.cpp
  src/core_runtime_contract_governance.cpp
  src/core_runtime_contract_execution.cpp
  src/core_runtime_contract_release.cpp
  src/core_runtime_contract_projection.cpp
  src/core_runtime_contract_envelope.cpp
  src/runtime_state_store.cpp
  src/session_runtime.cpp
  src/session_freeze_runtime.cpp
  src/execution_plan_runtime.cpp
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
  src/rt_host_bootstrap.cpp
  src/deployment_policy.cpp
  src/safety_service.cpp
  src/sdk_robot_facade.cpp
  src/sdk_robot_facade_lifecycle.cpp
  src/sdk_robot_facade_nrt.cpp
  src/sdk_robot_facade_rt.cpp
  src/sdk_robot_facade_rt_phase.cpp
  src/sdk_robot_facade_rt_contract.cpp
  src/sdk_robot_facade_cache.cpp
  src/sdk_robot_facade_ports.cpp
  src/sdk_robot_facade_state.cpp
  src/sdk_robot_facade_model.cpp
  src/normal_force_estimator.cpp
  src/normal_axis_admittance_controller.cpp
  src/tangential_scan_controller.cpp
  src/orientation_trim_controller.cpp
  src/contact_control_contract.cpp
  src/telemetry_publisher.cpp
  src/pose_interpolator.cpp
)

add_library(spine_robot_core_runtime STATIC ${CORE_RUNTIME_SOURCES} ${GENERATED_RUNTIME_COMMAND_MANIFEST_INC})
set_source_files_properties(
  src/core_runtime_contracts.cpp
  src/core_runtime_contract_identity.cpp
  src/core_runtime_contract_safety.cpp
  src/core_runtime_contract_governance.cpp
  src/core_runtime_contract_execution.cpp
  src/core_runtime_contract_release.cpp
  src/core_runtime_contract_projection.cpp
  src/core_runtime_contract_envelope.cpp
  src/runtime_state_store.cpp
  src/sdk_robot_facade.cpp
  src/sdk_robot_facade_rt.cpp
  src/sdk_robot_facade_rt_phase.cpp
  src/sdk_robot_facade_rt_contract.cpp
  src/normal_axis_admittance_controller.cpp
  src/tangential_scan_controller.cpp
  PROPERTIES SKIP_UNITY_BUILD_INCLUSION ON
)
add_dependencies(spine_robot_core_runtime generate_runtime_command_artifacts)
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
add_dependencies(spine_robot_core generate_runtime_command_artifacts)
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
robot_core_add_cpp_test(test_execution_plan_runtime_truth tests/test_execution_plan_runtime_truth.cpp spine_robot_core_runtime)

set(ROBOT_CORE_ENABLE_XMATE_MODEL_COMPILE_GATE OFF)
if(ROBOT_CORE_WITH_XCORE_SDK AND ROBOT_CORE_WITH_XMATE_MODEL AND VendoredRokaeSdk_FOUND AND TARGET Rokae::xMateModel)
  set(ROBOT_CORE_ENABLE_XMATE_MODEL_COMPILE_GATE ON)
  robot_core_add_cpp_test(test_xmate_model_compile_contract tests/test_xmate_model_compile_contract.cpp)
endif()

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
add_test(NAME cpp_execution_plan_runtime_truth COMMAND test_execution_plan_runtime_truth)
if(ROBOT_CORE_ENABLE_XMATE_MODEL_COMPILE_GATE)
  add_test(NAME cpp_xmate_model_compile_contract COMMAND test_xmate_model_compile_contract)
endif()
