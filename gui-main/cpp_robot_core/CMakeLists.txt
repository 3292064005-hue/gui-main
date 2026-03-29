cmake_minimum_required(VERSION 3.10)
project(SpineUltrasoundCore)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Force optimizations for Real-Time Core
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -pthread")

# Include directories
include_directories(include)
include_directories(${CMAKE_CURRENT_BINARY_DIR})  # For generated protobuf files
include_directories(/usr/include/eigen3)

# Find absolute dependencies for Zero-Copy and System Locking
find_package(Threads REQUIRED)
find_package(Protobuf REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(Eigen3 REQUIRED)
enable_testing()
add_compile_definitions(ROBOT_CORE_FORCE_CONTROL_CONFIG_PATH="${CMAKE_SOURCE_DIR}/../configs/force_control.json")

# Protobuf generation
protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS proto/ipc_messages.proto)

# Source files mapping for the canonical spine_robot_core runtime.
set(CORE_RUNTIME_SOURCES
    src/command_server.cpp
    src/core_runtime.cpp
    src/contact_gate.cpp
    src/contact_observer.cpp
    src/nrt_motion_service.cpp
    src/recording_service.cpp
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
    src/telemetry_publisher.cpp
    src/trajectory_compiler.cpp
    src/kinematics_validator.cpp
    src/pose_interpolator.cpp
    ${PROTO_SRCS}
)

add_library(spine_robot_core_runtime STATIC ${CORE_RUNTIME_SOURCES})

# Build the Hard-RT Executable
add_executable(spine_robot_core src/main_ubuntu_rt.cpp)

# Build test executable for Seqlock IPC
add_executable(test_seqlock src/test_seqlock.cpp)

# Build test executable for Force Control Safety System
add_executable(test_force_control src/test_force_control.cpp)

# Build test executable for Impedance Scan Controller
add_executable(test_impedance_scan src/test_impedance_scan.cpp)

# Build smoke test executable for protocol bridge
add_executable(test_protocol_bridge src/test_protocol_bridge.cpp)

# Build smoke test executable for recovery manager
add_executable(test_recovery_manager src/test_recovery_manager.cpp)

# Build example executable for Impedance Scan Controller
add_executable(impedance_scan_example src/impedance_scan_example.cpp)

target_link_libraries(spine_robot_core_runtime
    Threads::Threads
    protobuf::libprotobuf
    OpenSSL::SSL
    OpenSSL::Crypto
    rt
    # rokae_xcore_sdk 
)

target_link_libraries(spine_robot_core spine_robot_core_runtime)

target_link_libraries(test_seqlock
    Threads::Threads
    rt
)

target_link_libraries(test_force_control
    Threads::Threads
)

target_link_libraries(test_impedance_scan
    Threads::Threads
)

target_link_libraries(test_protocol_bridge
    spine_robot_core_runtime
)

target_link_libraries(test_recovery_manager
    spine_robot_core_runtime
)

target_link_libraries(impedance_scan_example
    Threads::Threads
)

add_test(NAME cpp_force_control COMMAND test_force_control)
add_test(NAME cpp_impedance_scan COMMAND test_impedance_scan)
add_test(NAME cpp_protocol_bridge COMMAND test_protocol_bridge)
add_test(NAME cpp_recovery_manager COMMAND test_recovery_manager)

# Install location matching the systemd service template
install(TARGETS spine_robot_core DESTINATION /opt/spine_ultrasound/cpp_robot_core/build)
