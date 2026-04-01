#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

cleanup_generated_artifacts() {
  find "$ROOT_DIR" -path "$ROOT_DIR/.git" -prune -o -type d \( -name __pycache__ -o -name .pytest_cache \) -exec rm -rf {} + 2>/dev/null || true
  find "$ROOT_DIR" -path "$ROOT_DIR/.git" -prune -o -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
}

trap cleanup_generated_artifacts EXIT

cleanup_generated_artifacts

section() {
  printf '\n== %s ==\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1"
  exit 1
}

section "Repository hygiene"
./scripts/check_repo_hygiene.sh

section "Repository convergence audit"
"$PYTHON_BIN" scripts/strict_convergence_audit.py

section "Protocol asset alignment"
"$PYTHON_BIN" scripts/check_protocol_sync.py

section "Python bytecode compilation"
"$PYTHON_BIN" -m compileall -q spine_ultrasound_ui tests

section "Pytest collection"
"$PYTHON_BIN" scripts/run_pytest_mainline.py --collect-only -q

section "Critical regression suite"
"$PYTHON_BIN" scripts/run_pytest_mainline.py -q \
  tests/test_api_contract.py \
  tests/test_api_security.py \
  tests/test_control_plane.py \
  tests/test_control_ownership.py \
  tests/test_runtime_verdict.py \
  tests/test_headless_runtime.py \
  tests/test_release_gate.py \
  tests/test_replay_determinism.py \
  tests/test_profile_policy.py \
  tests/test_spawned_core_integration.py \
  tests/test_vendor_sdk_and_identity.py \
  tests/test_sdk_runtime_assets_and_model_precheck.py \
  tests/test_mainline_runtime_doctor.py \
  tests/test_xmate_mainline.py \
  tests/archive/test_robot_family_and_profiles_v2.py \
  tests/archive/test_runtime_contracts_v3.py \
  tests/archive/test_runtime_contract_enforcement_v4.py

section "C++ preflight"
./scripts/check_cpp_prereqs.sh

section "C++ build and test"
BUILD_DIR="${BUILD_DIR:-}"
if [[ -z "$BUILD_DIR" ]]; then
  BUILD_DIR=$(mktemp -d /tmp/gui_main_cpp_acceptance.XXXXXX)
else
  rm -rf "$BUILD_DIR"
  mkdir -p "$BUILD_DIR"
fi
for PROFILE in mock hil prod; do
  cmake -S cpp_robot_core -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}" -DROBOT_CORE_PROFILE="${PROFILE}" -DROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" -DROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" >"$BUILD_DIR/cmake.log" 2>&1 || {
    tail -n 80 "$BUILD_DIR/cmake.log" || true
    fail "C++ configure failed"
  }
  if [[ "$PROFILE" != "prod" ]]; then
    python scripts/build_cpp_targets.py --build-dir "$BUILD_DIR" --jobs "${CMAKE_BUILD_PARALLEL_LEVEL:-1}" spine_robot_core_runtime spine_robot_core test_seqlock test_force_control test_impedance_scan test_protocol_bridge test_recovery_manager
    ctest --test-dir "$BUILD_DIR" --output-on-failure || fail "C++ tests failed"
  fi
done

section "Post-run payload hygiene"
cleanup_generated_artifacts
"$ROOT_DIR/scripts/check_repo_hygiene.sh"

section "Acceptance audit completed"
echo "Mainline Python + C++ acceptance gates passed."
