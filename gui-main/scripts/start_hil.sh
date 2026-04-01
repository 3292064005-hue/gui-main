#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${SPINE_CORE_BUILD_DIR:-/tmp/spine_core_build_runtime}"
CORE_BIN="$BUILD_DIR/spine_robot_core"
SDK_ROOT="${XCORE_SDK_ROOT:-${ROKAE_SDK_ROOT:-}}"
[[ -n "$SDK_ROOT" ]] || { echo "[start_hil] XCORE_SDK_ROOT must be set"; exit 1; }
SDK_LIB_DIR="$SDK_ROOT/lib/Linux/cpp/x86_64"
python3 "$ROOT_DIR/scripts/doctor_runtime.py"
cmake -S "$ROOT_DIR/cpp_robot_core" -B "$BUILD_DIR" -DXCORE_SDK_ROOT="$SDK_ROOT" -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}" -DROBOT_CORE_PROFILE=hil -DROBOT_CORE_WITH_XCORE_SDK=ON -DROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}"
cmake --build "$BUILD_DIR" -j"${CMAKE_BUILD_PARALLEL_LEVEL:-1}"
export LD_LIBRARY_PATH="$SDK_LIB_DIR:${LD_LIBRARY_PATH:-}"
"$CORE_BIN" & CORE_PID=$!
trap 'kill $CORE_PID >/dev/null 2>&1 || true' EXIT
sleep 1
SPINE_UI_BACKEND=core python3 "$ROOT_DIR/run.py" --backend core
