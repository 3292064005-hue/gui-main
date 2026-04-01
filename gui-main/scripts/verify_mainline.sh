#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
CMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}"
FULL_TESTS="${FULL_TESTS:-0}"
BUILD_DIR="${BUILD_DIR:-}"
if [[ -z "${BUILD_DIR}" ]]; then
  BUILD_DIR=$(mktemp -d /tmp/gui_main_cpp_mainline_build.XXXXXX)
else
  rm -rf "${BUILD_DIR}"
  mkdir -p "${BUILD_DIR}"
fi

cd "${REPO_ROOT}"

cleanup_generated_artifacts() {
  rm -rf "${BUILD_DIR}" 2>/dev/null || true
  find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type d \( -name __pycache__ -o -name .pytest_cache \) -exec rm -rf {} + 2>/dev/null || true
  find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
}

trap cleanup_generated_artifacts EXIT

cleanup_generated_artifacts

./scripts/check_repo_hygiene.sh
python scripts/strict_convergence_audit.py
python scripts/check_protocol_sync.py
python scripts/check_canonical_imports.py
python scripts/check_repository_gates.py
python scripts/generate_p2_acceptance_artifacts.py
python scripts/check_p2_acceptance.py

if [[ "$FULL_TESTS" == "1" ]]; then
  python scripts/run_pytest_mainline.py -q
else
  python scripts/run_pytest_mainline.py -q \
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
    tests/test_p2_stage_manifests.py \
    tests/test_p2_repository_gates.py \
    tests/test_sdk_runtime_assets_and_model_precheck.py \
    tests/test_mainline_runtime_doctor.py \
    tests/test_xmate_mainline.py \
    tests/archive/test_robot_family_and_profiles_v2.py \
    tests/archive/test_runtime_contracts_v3.py \
    tests/archive/test_runtime_contract_enforcement_v4.py
fi

mainline_cpp_profile_gate() {
  for PROFILE in mock hil prod; do
    EXTRA_ARGS=( -DROBOT_CORE_PROFILE="${PROFILE}" )
    if [[ "${PROFILE}" == "mock" ]]; then
      EXTRA_ARGS+=( -DROBOT_CORE_WITH_XCORE_SDK=OFF -DROBOT_CORE_WITH_XMATE_MODEL=OFF )
    elif [[ "${PROFILE}" == "hil" ]]; then
      EXTRA_ARGS+=( -DROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" -DROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" )
    else
      EXTRA_ARGS+=( -DROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}" -DROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}" )
    fi
    cmake -S cpp_robot_core -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE}" "${EXTRA_ARGS[@]}"
    if [[ "${PROFILE}" != "prod" ]]; then
      python scripts/build_cpp_targets.py --build-dir "${BUILD_DIR}" --jobs "${CMAKE_BUILD_PARALLEL_LEVEL:-1}" spine_robot_core_runtime spine_robot_core test_seqlock test_force_control test_impedance_scan test_protocol_bridge test_recovery_manager
      ctest --test-dir "${BUILD_DIR}" --output-on-failure
    fi
  done
}

mainline_cpp_profile_gate
