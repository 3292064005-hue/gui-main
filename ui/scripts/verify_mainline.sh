#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
CMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}"
FULL_TESTS="${FULL_TESTS:-0}"
BUILD_DIR="${BUILD_DIR:-}"
VERIFY_PHASE="${VERIFY_PHASE:-all}"
BUILD_EVIDENCE_REPORT="${BUILD_EVIDENCE_REPORT:-}"
EXPECTED_CPP_TEST_COUNT="${EXPECTED_CPP_TEST_COUNT:-11}"
CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-4}"

CURRENT_PHASE="bootstrap"
CURRENT_PROFILE=""
CURRENT_BUILD_DIR=""
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

on_error() {
  local lineno="$1"
  local command="$2"
  echo "[FAIL] verify_mainline.sh phase=${CURRENT_PHASE} profile=${CURRENT_PROFILE:-n/a} build_dir=${CURRENT_BUILD_DIR:-n/a} line=${lineno} command=${command}" >&2
}

cleanup_generated_artifacts() {
  rm -rf "${BUILD_DIR}" 2>/dev/null || true
  find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type d \( -name __pycache__ -o -name .pytest_cache \) -exec rm -rf {} + 2>/dev/null || true
  find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
}

trap 'on_error "${LINENO}" "${BASH_COMMAND}"' ERR
trap cleanup_generated_artifacts EXIT

if [[ -z "${BUILD_DIR}" ]]; then
  BUILD_DIR=$(mktemp -d /tmp/gui_main_cpp_mainline_build.XXXXXX)
else
  rm -rf "${BUILD_DIR}"
  mkdir -p "${BUILD_DIR}"
fi

cd "${REPO_ROOT}"
cleanup_generated_artifacts

run_repository_gates() {
  CURRENT_PHASE="repository-gates"
  ./scripts/check_repo_hygiene.sh
  python scripts/strict_convergence_audit.py
  python scripts/check_protocol_sync.py
  python scripts/check_canonical_imports.py
  python scripts/check_repository_gates.py
  python scripts/check_architecture_fitness.py
  python scripts/generate_p2_acceptance_artifacts.py
  python scripts/check_p2_acceptance.py
}

run_python_pytest_batch() {
  local label="$1"
  shift
  CURRENT_PHASE="python-${label}"
  python scripts/run_pytest_mainline.py -q "$@"
}

run_python_gate() {
  CURRENT_PHASE="python"
  run_repository_gates
  if [[ "${FULL_TESTS}" == "1" ]]; then
    python scripts/run_pytest_mainline.py -q
  else
    run_python_pytest_batch control-plane       tests/test_api_contract.py       tests/test_api_security.py       tests/test_control_plane.py       tests/test_control_ownership.py       tests/test_runtime_verdict.py       tests/test_headless_runtime.py
    run_python_pytest_batch release-state       tests/test_release_gate.py       tests/test_replay_determinism.py       tests/test_profile_policy.py       tests/test_spawned_core_integration.py       tests/test_vendor_sdk_and_identity.py
    run_python_pytest_batch repository-gates       tests/test_p2_stage_manifests.py       tests/test_p2_repository_gates.py       tests/test_sdk_runtime_assets_and_model_precheck.py       tests/test_mainline_runtime_doctor.py       tests/test_xmate_mainline.py
    run_python_pytest_batch preweight-closure       tests/test_preweight_semantic_closure.py
    run_python_pytest_batch archive-compat       tests/archive/test_robot_family_and_profiles_v2.py       tests/archive/test_runtime_contracts_v3.py       tests/archive/test_runtime_contract_enforcement_v4.py
  fi
}

profile_build_dir() {
  local profile="$1"
  printf '%s/%s\n' "${BUILD_DIR}" "${profile}"
}

configure_cpp_profile() {
  local profile="$1"
  local profile_build_dir_path
  profile_build_dir_path=$(profile_build_dir "${profile}")
  CURRENT_PHASE="configure-${profile}"
  CURRENT_PROFILE="${profile}"
  CURRENT_BUILD_DIR="${profile_build_dir_path}"
  rm -rf "${profile_build_dir_path}"
  mkdir -p "${profile_build_dir_path}"

  local extra_args=( -DROBOT_CORE_PROFILE="${profile}" )
  if [[ "${profile}" == "mock" ]]; then
    extra_args+=( -DROBOT_CORE_WITH_XCORE_SDK=OFF -DROBOT_CORE_WITH_XMATE_MODEL=OFF )
  else
    extra_args+=( -DROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" -DROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" )
  fi

  cmake -S cpp_robot_core -B "${profile_build_dir_path}" -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE}" "${extra_args[@]}"
}

build_cpp_profile_targets() {
  local profile="$1"
  local profile_build_dir_path
  profile_build_dir_path=$(profile_build_dir "${profile}")
  CURRENT_PHASE="build-${profile}"
  CURRENT_PROFILE="${profile}"
  CURRENT_BUILD_DIR="${profile_build_dir_path}"
  python scripts/build_cpp_targets.py --build-dir "${profile_build_dir_path}" --jobs "${CMAKE_BUILD_PARALLEL_LEVEL}" "${CPP_BUILD_TARGETS[@]}"
}

assert_registered_cpp_tests() {
  local profile="$1"
  local profile_build_dir_path
  profile_build_dir_path=$(profile_build_dir "${profile}")
  CURRENT_PHASE="list-tests-${profile}"
  CURRENT_PROFILE="${profile}"
  CURRENT_BUILD_DIR="${profile_build_dir_path}"
  local listing
  listing=$(ctest --test-dir "${profile_build_dir_path}" -N)
  printf '%s\n' "${listing}"
  local total
  total=$(printf '%s\n' "${listing}" | awk '/Total Tests:/ {print $3}' | tail -n 1)
  if [[ -z "${total}" ]]; then
    echo "[FAIL] unable to determine registered ctest count for profile=${profile}" >&2
    return 1
  fi
  if [[ "${total}" != "${EXPECTED_CPP_TEST_COUNT}" ]]; then
    echo "[FAIL] profile=${profile} expected ${EXPECTED_CPP_TEST_COUNT} registered ctests but found ${total}" >&2
    return 1
  fi
}

run_cpp_profile_tests() {
  local profile="$1"
  local profile_build_dir_path
  profile_build_dir_path=$(profile_build_dir "${profile}")
  CURRENT_PHASE="ctest-${profile}"
  CURRENT_PROFILE="${profile}"
  CURRENT_BUILD_DIR="${profile_build_dir_path}"
  ctest --test-dir "${profile_build_dir_path}" --output-on-failure
}

run_cpp_profile_gate() {
  local profile="$1"
  configure_cpp_profile "${profile}"
  if [[ "${profile}" == "prod" ]]; then
    return 0
  fi
  build_cpp_profile_targets "${profile}"
  assert_registered_cpp_tests "${profile}"
  run_cpp_profile_tests "${profile}"
}

emit_build_evidence_report() {
  if [[ -z "${BUILD_EVIDENCE_REPORT}" ]]; then
    return 0
  fi
  if [[ "${VERIFY_PHASE}" != "all" && "${VERIFY_PHASE}" != "hil" ]]; then
    return 0
  fi
  CURRENT_PHASE="build-evidence"
  CURRENT_PROFILE="hil"
  CURRENT_BUILD_DIR="$(profile_build_dir hil)"
  EXTRA_EVIDENCE_ARGS=()
  if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" == "ON" ]]; then
    EXTRA_EVIDENCE_ARGS+=(--with-sdk)
  fi
  if [[ "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" == "ON" ]]; then
    EXTRA_EVIDENCE_ARGS+=(--with-model)
  fi
  python scripts/verify_cpp_build_evidence.py --profile hil "${EXTRA_EVIDENCE_ARGS[@]}" --report "${BUILD_EVIDENCE_REPORT}"
}

case "${VERIFY_PHASE}" in
  python)
    run_python_gate
    ;;
  mock)
    run_cpp_profile_gate mock
    ;;
  hil)
    run_cpp_profile_gate hil
    emit_build_evidence_report
    ;;
  prod)
    run_cpp_profile_gate prod
    ;;
  all)
    run_python_gate
    run_cpp_profile_gate mock
    run_cpp_profile_gate hil
    run_cpp_profile_gate prod
    emit_build_evidence_report
    ;;
  *)
    echo "Unsupported VERIFY_PHASE=${VERIFY_PHASE}. Expected one of: python, mock, hil, prod, all" >&2
    exit 2
    ;;
esac
