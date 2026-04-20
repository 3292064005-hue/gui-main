#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
CMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}"
FULL_TESTS="${FULL_TESTS:-0}"
INCLUDE_ARCHIVE_COMPAT="${INCLUDE_ARCHIVE_COMPAT:-0}"
BUILD_DIR="${BUILD_DIR:-}"
VERIFY_PHASE="${VERIFY_PHASE:-all}"
BUILD_EVIDENCE_REPORT="${BUILD_EVIDENCE_REPORT:-}"
VERIFICATION_REPORT="${VERIFICATION_REPORT:-}"
READINESS_MANIFEST_REPORT="${READINESS_MANIFEST_REPORT:-}"
LIVE_EVIDENCE_BUNDLE="${LIVE_EVIDENCE_BUNDLE:-}"
CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-4}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

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
  test_execution_plan_runtime_truth
  test_xmate_model_compile_contract
)
CPP_BUILD_TARGETS=(spine_robot_core_runtime spine_robot_core "${CPP_TEST_TARGETS[@]}")
EXPECTED_CPP_TEST_COUNT="${EXPECTED_CPP_TEST_COUNT:-${#CPP_TEST_TARGETS[@]}}"

cpp_test_targets_for_profile() {
  local profile="$1"
  local targets=("${CPP_TEST_TARGETS[@]}")
  local with_sdk="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}"
  local with_model="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}"
  if [[ "$profile" == "mock" || "$with_sdk" != "ON" || "$with_model" != "ON" ]]; then
    local filtered=()
    local target
    for target in "${targets[@]}"; do
      [[ "$target" == "test_xmate_model_compile_contract" ]] && continue
      filtered+=("$target")
    done
    targets=("${filtered[@]}")
  fi
  printf '%s\n' "${targets[@]}"
}

cpp_build_targets_for_profile() {
  local profile="$1"
  local targets=(spine_robot_core_runtime spine_robot_core)
  while IFS= read -r target; do
    [[ -n "$target" ]] && targets+=("$target")
  done < <(cpp_test_targets_for_profile "$profile")
  printf '%s\n' "${targets[@]}"
}

on_error() {
  local lineno="$1"
  local command="$2"
  echo "[FAIL] verify_mainline.sh phase=${CURRENT_PHASE} profile=${CURRENT_PROFILE:-n/a} build_dir=${CURRENT_BUILD_DIR:-n/a} line=${lineno} command=${command}" >&2
}

cleanup_repo_generated_artifacts() {
  local cleanup_roots=(
    "${REPO_ROOT}"
    "${REPO_ROOT}/spine_ultrasound_ui"
    "${REPO_ROOT}/tests"
    "${REPO_ROOT}/scripts"
    "${REPO_ROOT}/runtime"
  )
  local root
  for root in "${cleanup_roots[@]}"; do
    [[ -d "${root}" ]] || continue
    find "${root}" -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} + 2>/dev/null || true
    find "${root}" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
  done
}

cleanup_generated_artifacts() {
  rm -rf "${BUILD_DIR}" 2>/dev/null || true
  cleanup_repo_generated_artifacts
}

trap 'on_error "${LINENO}" "${BASH_COMMAND}"' ERR

if [[ -z "${BUILD_DIR}" ]]; then
  BUILD_DIR=$(mktemp -d /tmp/gui_main_cpp_mainline_build.XXXXXX)
else
  rm -rf "${BUILD_DIR}"
  mkdir -p "${BUILD_DIR}"
fi

cd "${REPO_ROOT}"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
cleanup_generated_artifacts

emit_phase_scope_note() {
  case "$1" in
    python)
      echo "[scope] VERIFY_PHASE=python closes repository/Python gates only; it is not HIL/prod/live-controller validation."
      ;;
    mock)
      echo "[scope] VERIFY_PHASE=mock proves mock-profile contract/runtime gates only; no live SDK, live telemetry, or HIL truth is implied."
      ;;
    hil)
      if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" != "ON" || "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" != "ON" ]]; then
        echo "[scope] VERIFY_PHASE=hil is running without live SDK/model bindings; this is contract-shell/build-shell proof, not live SDK validation."
      fi
      ;;
    prod)
      if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" != "ON" || "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" != "ON" ]]; then
        echo "[scope] VERIFY_PHASE=prod is running without live SDK/model bindings; this is prod-contract/build/install/package proof, not live-controller validation."
      fi
      ;;
  esac
}

run_repository_gates() {
  CURRENT_PHASE="repository-gates"
  bash scripts/check_repo_hygiene.sh
  "$PYTHON_BIN" scripts/strict_convergence_audit.py
  "$PYTHON_BIN" scripts/generate_runtime_command_artifacts.py
  "$PYTHON_BIN" scripts/check_protocol_sync.py
"$PYTHON_BIN" scripts/check_runtime_config_contract.py
"$PYTHON_BIN" scripts/check_runtime_contract_parity.py
  "$PYTHON_BIN" scripts/check_backend_authority_parity.py
  "$PYTHON_BIN" scripts/check_rt_purity_gate.py
  "$PYTHON_BIN" scripts/check_rt_quality_gate.py
"$PYTHON_BIN" scripts/check_model_bundle_contract.py
  "$PYTHON_BIN" scripts/check_robot_identity_registry.py
  "$PYTHON_BIN" scripts/check_python_compile.py
  "$PYTHON_BIN" scripts/check_canonical_imports.py
  "$PYTHON_BIN" scripts/check_repository_gates.py
  # compatibility hint: python scripts/check_architecture_fitness.py
  "$PYTHON_BIN" scripts/check_architecture_fitness.py
  "$PYTHON_BIN" scripts/check_artifact_lifecycle_registry.py
  "$PYTHON_BIN" scripts/check_algorithm_plugin_contracts.py
  "$PYTHON_BIN" scripts/check_verification_boundary.py
  P2_ACCEPTANCE_OUTPUT_ROOT="${BUILD_DIR}/p2_acceptance" "$PYTHON_BIN" scripts/generate_p2_acceptance_artifacts.py
  P2_ACCEPTANCE_OUTPUT_ROOT="${BUILD_DIR}/p2_acceptance" "$PYTHON_BIN" scripts/check_p2_acceptance.py
}

run_python_pytest_batch() {
  local label="$1"
  shift
  CURRENT_PHASE="python-${label}"
  "$PYTHON_BIN" scripts/run_pytest_mainline.py -q "$@"
}

run_python_gate() {
  CURRENT_PHASE="python"
  run_repository_gates
  if [[ "${FULL_TESTS}" == "1" ]]; then
    "$PYTHON_BIN" scripts/run_pytest_mainline.py -q
  else
    run_python_pytest_batch control-plane       tests/test_runtime_refactor_guards.py       tests/test_backend_link_and_api_bridge.py       tests/test_api_bridge_verdict_service.py       tests/test_control_ownership.py       tests/test_runtime_verdict.py       tests/test_headless_adapter_surface_refactor.py
    run_python_pytest_batch release-state       tests/test_runtime_verdict_authority_contract.py       tests/test_control_authority_claims.py       tests/test_guidance_freeze_contracts.py       tests/test_runtime_mode_policy.py       tests/test_vendor_sdk_and_identity.py
    run_python_pytest_batch repository-gates       tests/test_p2_stage_manifests.py       tests/test_p2_repository_gates.py       tests/test_sdk_runtime_assets_and_model_precheck.py       tests/test_mainline_runtime_doctor.py       tests/test_xmate_mainline.py       tests/test_architecture_fitness.py
    run_python_pytest_batch preweight-closure       tests/test_preweight_semantic_closure.py
    if [[ "${INCLUDE_ARCHIVE_COMPAT}" == "1" ]]; then
      run_python_pytest_batch archive-compat         tests/archive/test_robot_family_and_profiles_v2.py         tests/archive/test_runtime_contracts_v3.py         tests/archive/test_runtime_contract_enforcement_v4.py
    fi
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
  local unity_build="${VERIFY_ENABLE_UNITY_BUILD:-1}"
  local unity_batch_size="${VERIFY_UNITY_BATCH_SIZE:-4}"
  if [[ "${unity_build}" == "1" ]]; then
    extra_args+=( -DCMAKE_UNITY_BUILD=ON -DCMAKE_UNITY_BUILD_BATCH_SIZE="${unity_batch_size}" )
  fi
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
  mapfile -t profile_cpp_build_targets < <(cpp_build_targets_for_profile "${profile}")
  "$PYTHON_BIN" scripts/build_cpp_targets.py --build-dir "${profile_build_dir_path}" --jobs "${CMAKE_BUILD_PARALLEL_LEVEL}" "${profile_cpp_build_targets[@]}"
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
  mapfile -t profile_cpp_test_targets < <(cpp_test_targets_for_profile "${profile}")
  local expected_cpp_test_count="${#profile_cpp_test_targets[@]}"
  if [[ "${total}" != "${expected_cpp_test_count}" ]]; then
    echo "[FAIL] profile=${profile} expected ${expected_cpp_test_count} registered ctests but found ${total}" >&2
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

run_cpp_profile_install_check() {
  local profile="$1"
  local profile_build_dir_path
  local install_root
  profile_build_dir_path=$(profile_build_dir "${profile}")
  install_root="${profile_build_dir_path}/install-root"
  CURRENT_PHASE="install-${profile}"
  CURRENT_PROFILE="${profile}"
  CURRENT_BUILD_DIR="${profile_build_dir_path}"
  rm -rf "${install_root}"
  mkdir -p "${install_root}"
  DESTDIR="${install_root}" cmake --install "${profile_build_dir_path}"
  local installed_binary="${install_root}/opt/spine_ultrasound/cpp_robot_core/bin/spine_robot_core"
  [[ -x "${installed_binary}" ]] || {
    echo "[FAIL] installed spine_robot_core binary missing at ${installed_binary}" >&2
    return 1
  }
}

run_prod_profile_release_smoke() {
  CURRENT_PHASE="prod-release-smoke"
  SPINE_DEPLOYMENT_PROFILE=clinical "$PYTHON_BIN" scripts/deployment_smoke_test.py
}

run_cpp_profile_gate() {
  local profile="$1"
  configure_cpp_profile "${profile}"
  build_cpp_profile_targets "${profile}"
  assert_registered_cpp_tests "${profile}"
  run_cpp_profile_tests "${profile}"
  run_cpp_profile_install_check "${profile}"
  if [[ "${profile}" == "prod" ]]; then
    run_prod_profile_release_smoke
  fi
}

emit_verification_report() {
  if [[ -z "${VERIFICATION_REPORT}" ]]; then
    return 0
  fi
  local -a phases=()
  case "${VERIFY_PHASE}" in
    all)
      phases=(python mock hil prod)
      ;;
    *)
      phases=("${VERIFY_PHASE}")
      ;;
  esac
  CURRENT_PHASE="verification-report"
  local -a args=()
  for phase in "${phases[@]}"; do
    args+=(--phase "${phase}")
  done
  if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" == "ON" ]]; then
    args+=(--with-sdk)
  fi
  if [[ "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" == "ON" ]]; then
    args+=(--with-model)
  fi
  if [[ -n "${LIVE_EVIDENCE_BUNDLE}" ]]; then
    args+=(--live-evidence-bundle "${LIVE_EVIDENCE_BUNDLE}")
  elif [[ -n "${READINESS_MANIFEST_REPORT}" ]]; then
    args+=(--write-readiness-manifest "${READINESS_MANIFEST_REPORT}")
  fi
  "$PYTHON_BIN" scripts/write_verification_report.py "${args[@]}" --output "${VERIFICATION_REPORT}"
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
  "$PYTHON_BIN" scripts/verify_cpp_build_evidence.py --profile hil "${EXTRA_EVIDENCE_ARGS[@]}" --report "${BUILD_EVIDENCE_REPORT}"
}

case "${VERIFY_PHASE}" in
  python)
    emit_phase_scope_note python
    run_python_gate
    ;;
  mock)
    emit_phase_scope_note mock
    run_cpp_profile_gate mock
    ;;
  hil)
    emit_phase_scope_note hil
    run_cpp_profile_gate hil
    emit_build_evidence_report
    ;;
  prod)
    emit_phase_scope_note prod
    run_cpp_profile_gate prod
    ;;
  all)
    emit_phase_scope_note python
    run_python_gate
    emit_phase_scope_note mock
    run_cpp_profile_gate mock
    emit_phase_scope_note hil
    run_cpp_profile_gate hil
    emit_phase_scope_note prod
    run_cpp_profile_gate prod
    emit_build_evidence_report
    ;;
  *)
    echo "Unsupported VERIFY_PHASE=${VERIFY_PHASE}. Expected one of: python, mock, hil, prod, all" >&2
    exit 2
    ;;
esac

cleanup_repo_generated_artifacts
emit_verification_report

exit 0
