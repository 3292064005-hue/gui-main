#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INCLUDE_ARCHIVE_COMPAT="${INCLUDE_ARCHIVE_COMPAT:-0}"
LIVE_EVIDENCE_BUNDLE="${LIVE_EVIDENCE_BUNDLE:-}"
ROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}"
ROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}"
CPP_TEST_TARGETS=(
  test_seqlock
  test_force_control
  test_normal_force_estimator
  test_normal_axis_admittance_controller
  test_tangential_scan_controller
  test_orientation_trim_controller
  test_contact_control_contract
  test_impedance_scan
  test_protocol_bridge
  test_recovery_manager
  test_recording_service
  test_rt_motion_service_truth
)
CPP_BUILD_TARGETS=(spine_robot_core_runtime spine_robot_core "${CPP_TEST_TARGETS[@]}")
EXPECTED_CPP_TEST_COUNT="${EXPECTED_CPP_TEST_COUNT:-12}"

count_registered_cpp_tests() {
  local build_dir="$1"
  CTEST_OUTPUT=$(ctest --test-dir "$build_dir" -N 2>/dev/null || true)
  TEST_TOTAL=$(printf '%s
' "$CTEST_OUTPUT" | awk '/Total Tests:/ {print $3}' | tail -n 1)
  if [[ -z "$TEST_TOTAL" ]]; then
    fail "Unable to determine registered C++ test count for $build_dir"
  fi
  printf '%s' "$TEST_TOTAL"
}

cleanup_generated_artifacts() {
  find "$ROOT_DIR" -path "$ROOT_DIR/.git" -prune -o -type d \( -name __pycache__ -o -name .pytest_cache \) -exec rm -rf {} + 2>/dev/null || true
  find "$ROOT_DIR" -path "$ROOT_DIR/.git" -prune -o -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
  rm -f "$ROOT_DIR/derived/postprocess/postprocess_stage_manifest.json" "$ROOT_DIR/derived/session/session_intelligence_manifest.json" 2>/dev/null || true
}
ensure_build_dir() {
  BUILD_DIR="${BUILD_DIR:-}"
  if [[ -z "$BUILD_DIR" ]]; then
    BUILD_DIR=$(mktemp -d /tmp/gui_main_cpp_acceptance.XXXXXX)
  else
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
  fi
}
trap cleanup_generated_artifacts EXIT
cleanup_generated_artifacts
ensure_build_dir
section() { printf '\n== %s ==\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1"; exit 1; }
section "Repository hygiene"
bash scripts/check_repo_hygiene.sh
section "Repository convergence audit"
"$PYTHON_BIN" scripts/strict_convergence_audit.py
section "Protocol asset alignment"
"$PYTHON_BIN" scripts/generate_runtime_command_artifacts.py
"$PYTHON_BIN" scripts/check_protocol_sync.py
section "Robot identity registry"
"$PYTHON_BIN" scripts/check_robot_identity_registry.py
section "Python syntax / bytecode gate"
"$PYTHON_BIN" scripts/check_python_compile.py
section "Canonical import gate"
"$PYTHON_BIN" scripts/check_canonical_imports.py
section "Repository gate registry"
"$PYTHON_BIN" scripts/check_repository_gates.py
section "Architecture fitness"
"$PYTHON_BIN" scripts/check_architecture_fitness.py
section "RT quality gates"
"$PYTHON_BIN" scripts/check_rt_purity_gate.py
"$PYTHON_BIN" scripts/check_rt_quality_gate.py
section "Verification boundary"
"$PYTHON_BIN" scripts/check_verification_boundary.py
section "P2 acceptance artifact generation"
P2_ACCEPTANCE_OUTPUT_ROOT="$BUILD_DIR/p2_acceptance" "$PYTHON_BIN" scripts/generate_p2_acceptance_artifacts.py
section "P2 acceptance artifact validation"
P2_ACCEPTANCE_OUTPUT_ROOT="$BUILD_DIR/p2_acceptance" "$PYTHON_BIN" scripts/check_p2_acceptance.py
section "Pytest collection"
"$PYTHON_BIN" scripts/run_pytest_mainline.py --collect-only -q
run_pytest_batch() {
  local label="$1"
  shift
  section "Critical regression suite: ${label}"
  "$PYTHON_BIN" scripts/run_pytest_mainline.py -q "$@"
}
run_pytest_batch control-plane   tests/test_runtime_refactor_guards.py tests/test_backend_link_and_api_bridge.py tests/test_api_bridge_verdict_service.py tests/test_control_ownership.py   tests/test_runtime_verdict.py tests/test_headless_adapter_surface_refactor.py
run_pytest_batch release-state   tests/test_runtime_verdict_authority_contract.py tests/test_control_authority_claims.py tests/test_guidance_freeze_contracts.py tests/test_runtime_mode_policy.py
run_pytest_batch sdk-and-doctor   tests/test_vendor_sdk_and_identity.py tests/test_sdk_runtime_assets_and_model_precheck.py tests/test_mainline_runtime_doctor.py tests/test_architecture_fitness.py
run_pytest_batch xmate-mainline   tests/test_xmate_mainline.py
if [[ "$INCLUDE_ARCHIVE_COMPAT" == "1" ]]; then
  section "Archive compatibility suite"
  "$PYTHON_BIN" scripts/run_pytest_mainline.py -q \
    tests/archive/test_robot_family_and_profiles_v2.py \
    tests/archive/test_runtime_contracts_v3.py \
    tests/archive/test_runtime_contract_enforcement_v4.py
fi
section "C++ preflight"
bash scripts/check_cpp_prereqs.sh
section "C++ build and test"
for PROFILE in mock hil prod; do
  PROFILE_BUILD_DIR="$BUILD_DIR/$PROFILE"
  mkdir -p "$PROFILE_BUILD_DIR"
  PROFILE_WITH_SDK="${ROBOT_CORE_WITH_XCORE_SDK}"
  PROFILE_WITH_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL}"
  if [[ "$PROFILE" == "mock" ]]; then
    PROFILE_WITH_SDK=OFF
    PROFILE_WITH_MODEL=OFF
  fi
  cmake -S cpp_robot_core -B "$PROFILE_BUILD_DIR" -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}" -DROBOT_CORE_PROFILE="${PROFILE}" -DROBOT_CORE_WITH_XCORE_SDK="${PROFILE_WITH_SDK}" -DROBOT_CORE_WITH_XMATE_MODEL="${PROFILE_WITH_MODEL}" >"$PROFILE_BUILD_DIR.cmake.log" 2>&1 || { tail -n 80 "$PROFILE_BUILD_DIR.cmake.log" || true; fail "C++ configure failed"; }
  "$PYTHON_BIN" scripts/build_cpp_targets.py --build-dir "$PROFILE_BUILD_DIR" --jobs "${CMAKE_BUILD_PARALLEL_LEVEL:-1}" "${CPP_BUILD_TARGETS[@]}"
  REGISTERED_CPP_TESTS=$(count_registered_cpp_tests "$PROFILE_BUILD_DIR")
  if [[ "$REGISTERED_CPP_TESTS" != "$EXPECTED_CPP_TEST_COUNT" ]]; then
    fail "C++ test registration mismatch for profile=$PROFILE: expected $EXPECTED_CPP_TEST_COUNT but ctest registered $REGISTERED_CPP_TESTS"
  fi
  ctest --test-dir "$PROFILE_BUILD_DIR" --output-on-failure || fail "C++ tests failed"
  DESTDIR="$PROFILE_BUILD_DIR/install-root" cmake --install "$PROFILE_BUILD_DIR"
  [[ -x "$PROFILE_BUILD_DIR/install-root/opt/spine_ultrasound/cpp_robot_core/bin/spine_robot_core" ]] || fail "Installed spine_robot_core binary missing"
  if [[ "$PROFILE" == "prod" ]]; then SPINE_DEPLOYMENT_PROFILE=clinical "$PYTHON_BIN" scripts/deployment_smoke_test.py || fail "Prod deployment profile smoke failed"; fi
done
section "Verification boundary report"
READINESS_MANIFEST_REPORT="$BUILD_DIR/runtime_readiness_manifest.json"
VERIFICATION_REPORT="$BUILD_DIR/verification_execution_report.json"
BUILD_EVIDENCE_REPORT="$BUILD_DIR/build_evidence_report.json"
ACCEPTANCE_SUMMARY_REPORT="$BUILD_DIR/acceptance_summary.json"
WRITE_ARGS=(--phase python --phase mock --phase hil --phase prod --output "$VERIFICATION_REPORT")
if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" == "ON" ]]; then WRITE_ARGS+=(--with-sdk); fi
if [[ "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" == "ON" ]]; then WRITE_ARGS+=(--with-model); fi
if [[ -n "$LIVE_EVIDENCE_BUNDLE" ]]; then
  WRITE_ARGS+=(--live-evidence-bundle "$LIVE_EVIDENCE_BUNDLE")
else
  WRITE_ARGS+=(--write-readiness-manifest "$READINESS_MANIFEST_REPORT")
fi
"$PYTHON_BIN" scripts/write_verification_report.py "${WRITE_ARGS[@]}" || fail "verification report generation failed"
section "C++ build evidence report"
EVIDENCE_ARGS=(--profile hil --report "$BUILD_EVIDENCE_REPORT")
if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" == "ON" ]]; then EVIDENCE_ARGS+=(--with-sdk); fi
if [[ "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" == "ON" ]]; then EVIDENCE_ARGS+=(--with-model); fi
"$PYTHON_BIN" scripts/verify_cpp_build_evidence.py "${EVIDENCE_ARGS[@]}" || fail "build evidence report generation failed"
section "Acceptance summary"
SUMMARY_ARGS=(--output "$ACCEPTANCE_SUMMARY_REPORT" --build-dir "$BUILD_DIR" --verification-report "$VERIFICATION_REPORT" --readiness-manifest "$READINESS_MANIFEST_REPORT" --build-evidence-report "$BUILD_EVIDENCE_REPORT")
if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" == "ON" ]]; then SUMMARY_ARGS+=(--with-sdk); fi
if [[ "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" == "ON" ]]; then SUMMARY_ARGS+=(--with-model); fi
for PROFILE in mock hil prod; do
  SUMMARY_ARGS+=(--profile "$PROFILE")
  SUMMARY_ARGS+=(--installed-binary "$BUILD_DIR/$PROFILE/install-root/opt/spine_ultrasound/cpp_robot_core/bin/spine_robot_core")
done
"$PYTHON_BIN" scripts/write_acceptance_summary.py "${SUMMARY_ARGS[@]}" || fail "acceptance summary generation failed"
section "Post-run payload hygiene"
cleanup_generated_artifacts
bash scripts/check_repo_hygiene.sh
section "Acceptance audit completed"
echo "Repository/profile acceptance gates passed for the checks executed by final_acceptance_audit.sh; see $VERIFICATION_REPORT for claim-safe reporting. Live-controller/HIL validation is not implied unless report.real_environment.validated=true."
