#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)

cd "${REPO_ROOT}"

fail() {
  echo "hygiene check failed: $1" >&2
  exit 1
}

for path in \
  requirements-win-dev.txt \
  legacy \
  tools/rt_experiments \
  gui_project \
  demo_spatio_temporal_sync.py \
  launch_notes.txt \
  spine_ultrasound_ui/legacy_frontend_architecture_demo.py \
  spine_ultrasound_ui/legacy_frontend_unit_demo.py \
  spine_ultrasound_ui/ws_broadcaster.py \
  spine_ultrasound_ui/bootstrap.py \
  spine_ultrasound_ui/constants.py
do
  if [ -e "${path}" ]; then
    fail "remove obsolete mainline asset: ${path}"
  fi
done

if find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type f -name '*.ps1' -print -quit | grep -q .; then
  fail "PowerShell assets are not allowed in the Ubuntu 22.04 mainline"
fi

if [ -d "${REPO_ROOT}/ui_frontend/node_modules" ] && git ls-files 'ui_frontend/node_modules/**' | grep -q .; then
  fail "vendored ui_frontend/node_modules is not allowed in git"
fi

if [ -d "${REPO_ROOT}/ui_frontend/dist" ] && git ls-files 'ui_frontend/dist/**' | grep -q .; then
  fail "tracked ui_frontend/dist artifacts are not allowed in git"
fi

if find "${REPO_ROOT}" -maxdepth 1 -type f -name 'test_*.py' | grep -q .; then
  fail "root-level experimental test_*.py scripts are not allowed in the mainline"
fi

if rg -n "Windows|PowerShell|api_server_win_mock|requirements-win-dev" README.md docs >/dev/null; then
  fail "README.md and docs/ must stay Ubuntu-only and free of Windows references"
fi

echo "repo hygiene: OK"
