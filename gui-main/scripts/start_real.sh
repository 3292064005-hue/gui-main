#!/usr/bin/env bash
set -e

# Official Ubuntu 22.04 desktop + core launcher.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/cpp_robot_core/build_runtime"
CORE_BIN="$BUILD_DIR/spine_robot_core"

cmake -S "$ROOT_DIR/cpp_robot_core" -B "$BUILD_DIR"
cmake --build "$BUILD_DIR" -j

"$CORE_BIN" &
CORE_PID=$!
trap 'kill $CORE_PID >/dev/null 2>&1 || true' EXIT
sleep 1

SPINE_UI_BACKEND=core python3 "$ROOT_DIR/run.py" --backend core
