#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)

cd "${REPO_ROOT}"

fail() {
  echo "hygiene check failed: $1" >&2
  exit 1
}

for path in   requirements-win-dev.txt   legacy   tools/rt_experiments   gui_project   demo_spatio_temporal_sync.py   launch_notes.txt   spine_ultrasound_ui/legacy_frontend_architecture_demo.py   spine_ultrasound_ui/legacy_frontend_unit_demo.py   spine_ultrasound_ui/ws_broadcaster.py   ui_frontend   xCore_SDK_C++使用手册V2.1_A.pdf   pytest.py   sitecustomize.py
 do
  if [ -e "${path}" ]; then
    fail "remove obsolete mainline asset: ${path}"
  fi
done

for path in .pytest_cache __pycache__ data/runtime/session_meta.json data/runtime/ui_preferences.json configs/tls/runtime cpp_robot_core/build cpp_robot_core/build_check cpp_robot_core/build_check_recheck final_acceptance.log full_suite.log pytest_full.log pytest_mainline.log derived/postprocess/postprocess_stage_manifest.json derived/session/session_intelligence_manifest.json; do
  if [ -e "${path}" ]; then
    fail "remove generated/runtime artifact from repository payload: ${path}"
  fi
done

if find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -print -quit | grep -q .; then
  fail "cached Python artifacts are not allowed in the repository payload"
fi

if find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type f -name '*.ps1' -print -quit | grep -q .; then
  fail "PowerShell assets are not allowed in the Ubuntu 22.04 mainline"
fi

if find "${REPO_ROOT}" -maxdepth 1 -type f -name 'test_*.py' | grep -q .; then
  fail "root-level experimental test_*.py scripts are not allowed in the mainline"
fi

if [ -d "${REPO_ROOT}/docs/history" ]; then
  fail "docs/history must be archived under archive/docs_history"
fi
if [ -d "${REPO_ROOT}/tests/history" ]; then
  fail "tests/history must be archived under tests/archive"
fi
if [ -d "${REPO_ROOT}/cpp_robot_core/apps" ] && find "${REPO_ROOT}/cpp_robot_core/apps" -type f -print -quit | grep -q .; then
  fail "legacy C++ app entrypoints must be archived out of cpp_robot_core/apps"
fi

if rg -n "Windows|PowerShell|api_server_win_mock|requirements-win-dev|ui_frontend" README.md docs >/dev/null; then
  fail "README.md and docs/ must stay focused on the current mainline payload"
fi

echo "repo hygiene: OK"

if [ ! -f "${REPO_ROOT}/docs/CANONICAL_MODULE_REGISTRY.md" ]; then
  fail "docs/CANONICAL_MODULE_REGISTRY.md must exist"
fi
if [ ! -f "${REPO_ROOT}/.github/CODEOWNERS" ]; then
  fail ".github/CODEOWNERS must exist"
fi
