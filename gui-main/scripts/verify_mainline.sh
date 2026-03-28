#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
BUILD_DIR="${REPO_ROOT}/cpp_robot_core/build"
CMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}"

cd "${REPO_ROOT}"

./scripts/check_repo_hygiene.sh
python -m pytest -q
cmake -S cpp_robot_core -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE}"
cmake --build "${BUILD_DIR}" -j"${CMAKE_BUILD_PARALLEL_LEVEL:-4}"
ctest --test-dir "${BUILD_DIR}" --output-on-failure
cd "${REPO_ROOT}/ui_frontend"
npm ci --no-audit --no-fund
npm run build
