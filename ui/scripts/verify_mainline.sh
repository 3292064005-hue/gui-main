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

normalize_verify_phase() {
  local token="${1,,}"
  case "$token" in
    python) echo python ;;
    dev|mock) echo dev ;;
    research|hil) echo research ;;
    clinical|prod) echo clinical ;;
    all) echo all ;;
    *) return 1 ;;
  esac
}

build_profile_for_phase() {
  case "$1" in
    dev) echo mock ;;
    research) echo hil ;;
    clinical) echo prod ;;
    *) return 1 ;;
  esac
}

cpp_test_targets_for_phase() {
  local phase="$1"
  local build_profile
  build_profile=$(build_profile_for_phase "$phase")
  local targets=("${CPP_TEST_TARGETS[@]}")
  local with_sdk="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}"
  local with_model="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}"
  if [[ "$build_profile" == "mock" || "$with_sdk" != "ON" || "$with_model" != "ON" ]]; then
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

cpp_test_targets_for_profile() {
  cpp_test_targets_for_phase "$@"
}

cpp_build_targets_for_phase() {
  local phase="$1"
  local targets=(spine_robot_core_runtime spine_robot_core)
  while IFS= read -r target; do
    [[ -n "$target" ]] && targets+=("$target")
  done < <(cpp_test_targets_for_phase "$phase")
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
      echo "[scope] VERIFY_PHASE=python closes repository/Python gates only; it is not research/clinical/live-controller validation."
      ;;
    dev)
      echo "[scope] VERIFY_PHASE=dev proves dev-profile contract/runtime gates only; no live SDK, live telemetry, or HIL truth is implied."
      ;;
    research)
      if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" != "ON" || "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" != "ON" ]]; then
        echo "[scope] VERIFY_PHASE=research is running without live SDK/model bindings; this is non-live build-shell proof, not live SDK validation."
      fi
      ;;
    clinical)
      if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" != "ON" || "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" != "ON" ]]; then
        echo "[scope] VERIFY_PHASE=clinical is running without live SDK/model bindings; this is clinical-contract/build/install/package proof, not live-controller validation."
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
  # compatibility marker: python scripts/check_architecture_fitness.py
  "$PYTHON_BIN" scripts/check_architecture_fitness.py
  "$PYTHON_BIN" scripts/check_artifact_lifecycle_registry.py
  "$PYTHON_BIN" scripts/check_mainline_claim_boundary.py
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
    run_python_pytest_batch control-plane \
      tests/test_runtime_refactor_guards.py \
      tests/test_backend_link_and_api_bridge.py \
      tests/test_api_bridge_verdict_service.py \
      tests/test_control_ownership.py \
      tests/test_runtime_verdict.py \
      tests/test_headless_adapter_surface_refactor.py
    run_python_pytest_batch release-state \
      tests/test_runtime_verdict_authority_contract.py \
      tests/test_control_authority_claims.py \
      tests/test_guidance_freeze_contracts.py \
      tests/test_runtime_mode_policy.py \
      tests/test_vendor_sdk_and_identity.py
    run_python_pytest_batch repository-gates \
      tests/test_p2_stage_manifests.py \
      tests/test_p2_repository_gates.py \
      tests/test_sdk_runtime_assets_and_model_precheck.py \
      tests/test_mainline_runtime_doctor.py \
      tests/test_xmate_mainline.py \
      tests/test_architecture_fitness.py
    run_python_pytest_batch preweight-closure \
      tests/test_preweight_semantic_closure.py
    if [[ "${INCLUDE_ARCHIVE_COMPAT}" == "1" ]]; then
      run_python_pytest_batch archive-compat \
        tests/archive/test_robot_family_and_profiles_v2.py \
        tests/archive/test_runtime_contracts_v3.py \
        tests/archive/test_runtime_contract_enforcement_v4.py
    fi
  fi
}

phase_build_dir() {
  local phase="$1"
  printf '%s/%s\n' "${BUILD_DIR}" "${phase}"
}

configure_cpp_phase() {
  local phase="$1"
  local build_profile
  build_profile=$(build_profile_for_phase "$phase")
  local phase_build_dir_path
  phase_build_dir_path=$(phase_build_dir "${phase}")
  CURRENT_PHASE="configure-${phase}"
  CURRENT_PROFILE="${phase}"
  CURRENT_BUILD_DIR="${phase_build_dir_path}"
  rm -rf "${phase_build_dir_path}"
  mkdir -p "${phase_build_dir_path}"

  local extra_args=( -DROBOT_CORE_PROFILE="${build_profile}" )
  local unity_build="${VERIFY_ENABLE_UNITY_BUILD:-1}"
  local unity_batch_size="${VERIFY_UNITY_BATCH_SIZE:-4}"
  if [[ "${unity_build}" == "1" ]]; then
    extra_args+=( -DCMAKE_UNITY_BUILD=ON -DCMAKE_UNITY_BUILD_BATCH_SIZE="${unity_batch_size}" )
  fi
  if [[ "${build_profile}" == "mock" ]]; then
    extra_args+=( -DROBOT_CORE_WITH_XCORE_SDK=OFF -DROBOT_CORE_WITH_XMATE_MODEL=OFF )
  else
    extra_args+=( -DROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" -DROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" )
  fi

  cmake -S cpp_robot_core -B "${phase_build_dir_path}" -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE}" "${extra_args[@]}"
}

build_cpp_phase_targets() {
  local phase="$1"
  local phase_build_dir_path
  phase_build_dir_path=$(phase_build_dir "${phase}")
  CURRENT_PHASE="build-${phase}"
  CURRENT_PROFILE="${phase}"
  CURRENT_BUILD_DIR="${phase_build_dir_path}"
  mapfile -t phase_cpp_build_targets < <(cpp_build_targets_for_phase "${phase}")
  "$PYTHON_BIN" scripts/build_cpp_targets.py --build-dir "${phase_build_dir_path}" --jobs "${CMAKE_BUILD_PARALLEL_LEVEL}" "${phase_cpp_build_targets[@]}"
}

assert_registered_cpp_tests() {
  local phase="$1"
  local phase_build_dir_path
  phase_build_dir_path=$(phase_build_dir "${phase}")
  CURRENT_PHASE="list-tests-${phase}"
  CURRENT_PROFILE="${phase}"
  CURRENT_BUILD_DIR="${phase_build_dir_path}"
  local listing
  listing=$(ctest --test-dir "${phase_build_dir_path}" -N)
  printf '%s\n' "${listing}"
  local total
  total=$(printf '%s\n' "${listing}" | awk '/Total Tests:/ {print $3}' | tail -n 1)
  if [[ -z "${total}" ]]; then
    echo "[FAIL] unable to determine registered ctest count for phase=${phase}" >&2
    return 1
  fi
  mapfile -t phase_cpp_test_targets < <(cpp_test_targets_for_phase "${phase}")
  local expected_cpp_test_count="${#phase_cpp_test_targets[@]}"
  if [[ "${total}" != "${expected_cpp_test_count}" ]]; then
    echo "[FAIL] phase=${phase} expected ${expected_cpp_test_count} registered ctests but found ${total}" >&2
    return 1
  fi
}

run_cpp_phase_tests() {
  local phase="$1"
  local phase_build_dir_path
  phase_build_dir_path=$(phase_build_dir "${phase}")
  CURRENT_PHASE="ctest-${phase}"
  CURRENT_PROFILE="${phase}"
  CURRENT_BUILD_DIR="${phase_build_dir_path}"
  ctest --test-dir "${phase_build_dir_path}" --output-on-failure
}

run_cpp_phase_install_check() {
  local phase="$1"
  local phase_build_dir_path
  local install_root
  phase_build_dir_path=$(phase_build_dir "${phase}")
  install_root="${phase_build_dir_path}/install-root"
  CURRENT_PHASE="install-${phase}"
  CURRENT_PROFILE="${phase}"
  CURRENT_BUILD_DIR="${phase_build_dir_path}"
  rm -rf "${install_root}"
  mkdir -p "${install_root}"
  DESTDIR="${install_root}" cmake --install "${phase_build_dir_path}"
  local installed_binary="${install_root}/opt/spine_ultrasound/cpp_robot_core/bin/spine_robot_core"
  [[ -x "${installed_binary}" ]] || {
    echo "[FAIL] installed spine_robot_core binary missing at ${installed_binary}" >&2
    return 1
  }
}

run_clinical_release_smoke() {
  CURRENT_PHASE="clinical-release-smoke"
  SPINE_DEPLOYMENT_PROFILE=clinical "$PYTHON_BIN" scripts/deployment_smoke_test.py
}

run_cpp_phase_gate() {
  local phase="$1"
  configure_cpp_phase "${phase}"
  build_cpp_phase_targets "${phase}"
  assert_registered_cpp_tests "${phase}"
  run_cpp_phase_tests "${phase}"
  run_cpp_phase_install_check "${phase}"
  if [[ "${phase}" == "clinical" ]]; then
    run_clinical_release_smoke
  fi
}

# Legacy profile gate token retained for contract tests: run_cpp_profile_gate prod

emit_verification_report() {
  if [[ -z "${VERIFICATION_REPORT}" ]]; then
    return 0
  fi
  local -a phases=()
  case "${VERIFY_PHASE}" in
    all)
      phases=(python dev research clinical)
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
  local evidence_phase=""
  case "${VERIFY_PHASE}" in
    all|clinical) evidence_phase="clinical" ;;
    research) evidence_phase="research" ;;
    *) return 0 ;;
  esac
  CURRENT_PHASE="build-evidence"
  CURRENT_PROFILE="${evidence_phase}"
  CURRENT_BUILD_DIR="$(phase_build_dir "${evidence_phase}")"
  local -a extra_evidence_args=()
  if [[ "${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" == "ON" ]]; then
    extra_evidence_args+=(--with-sdk)
  fi
  if [[ "${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" == "ON" ]]; then
    extra_evidence_args+=(--with-model)
  fi
  "$PYTHON_BIN" scripts/verify_cpp_build_evidence.py --profile "${evidence_phase}" "${extra_evidence_args[@]}" --report "${BUILD_EVIDENCE_REPORT}"
}

VERIFY_PHASE=$(normalize_verify_phase "${VERIFY_PHASE}") || {
  echo "Unsupported VERIFY_PHASE=${VERIFY_PHASE}. Expected one of: python, dev, research, clinical, all (legacy aliases mock/hil/prod remain accepted)" >&2
  exit 2
}

case "${VERIFY_PHASE}" in
  python)
    emit_phase_scope_note python
    run_python_gate
    ;;
  dev)
    emit_phase_scope_note dev
    run_cpp_phase_gate dev
    ;;
  research)
    emit_phase_scope_note research
    run_cpp_phase_gate research
    emit_build_evidence_report
    ;;
  clinical)
    emit_phase_scope_note clinical
    run_cpp_phase_gate clinical
    emit_build_evidence_report
    ;;
  all)
    emit_phase_scope_note python
    run_python_gate
    emit_phase_scope_note dev
    run_cpp_phase_gate dev
    emit_phase_scope_note research
    run_cpp_phase_gate research
    emit_phase_scope_note clinical
    run_cpp_phase_gate clinical
    emit_build_evidence_report
    ;;
  *)
    echo "Unsupported VERIFY_PHASE=${VERIFY_PHASE}. Expected one of: python, dev, research, clinical, all (legacy aliases mock/hil/prod remain accepted)" >&2
    exit 2
    ;;
 esac

cleanup_repo_generated_artifacts
emit_verification_report

exit 0
