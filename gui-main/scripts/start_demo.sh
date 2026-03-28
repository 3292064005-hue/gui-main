#!/usr/bin/env bash
set -e
python3 scripts/mock_robot_core_server.py &
MOCK_PID=$!
sleep 1
SPINE_UI_BACKEND=core python3 run.py --backend core
kill $MOCK_PID || true
