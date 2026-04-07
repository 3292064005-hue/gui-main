#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

missing=()
check_bin() {
  command -v "$1" >/dev/null 2>&1 || missing+=("$1")
}

check_bin cmake
if ! command -v g++ >/dev/null 2>&1 && ! command -v clang++ >/dev/null 2>&1; then
  missing+=("g++/clang++")
fi

if command -v cmake >/dev/null 2>&1; then
  if ! python - "$(cmake --version | awk 'NR==1{print $3}')" <<'PY'
import re
import sys
raw = sys.argv[1] if len(sys.argv) > 1 else ""
parts = tuple(int(token) for token in re.findall(r"\d+", raw)[:2])
sys.exit(0 if parts >= (3, 24) else 1)
PY
  then
    missing+=("cmake>=3.24")
  fi
fi

[[ -f /usr/include/openssl/ssl.h ]] || missing+=("libssl-dev")

if ((${#missing[@]})); then
  echo "[FAIL] C++ prerequisites missing: ${missing[*]}"
  echo "Install on Ubuntu 22.04 with:"
  echo "  sudo apt-get update && sudo apt-get install -y cmake g++ libssl-dev"
  exit 1
fi

BUILD_DIR="${BUILD_DIR:-}"
if [[ -z "$BUILD_DIR" ]]; then
  BUILD_DIR=$(mktemp -d /tmp/gui_main_cpp_prereqs.XXXXXX)
else
  rm -rf "$BUILD_DIR"
  mkdir -p "$BUILD_DIR"
fi
cleanup_build_dir() {
  rm -rf "$BUILD_DIR" 2>/dev/null || true
}
trap cleanup_build_dir EXIT
if cmake -S cpp_robot_core -B "$BUILD_DIR" \
  -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}" \
  -DROBOT_CORE_PROFILE="${ROBOT_CORE_PROFILE:-mock}" \
  -DROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" \
  -DROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" \
  >"$BUILD_DIR/cmake.log" 2>&1; then
  echo "[PASS] C++ prerequisites satisfied for configure stage"
  exit 0
fi

echo "[FAIL] C++ configure still blocked (SDK path or toolchain mismatch)"
tail -n 60 "$BUILD_DIR/cmake.log" || true
exit 1
