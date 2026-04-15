from __future__ import annotations
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.bootstrap_env import configure_test_environment
from tests.runtime_compat import enable_runtime_compat

configure_test_environment()
enable_runtime_compat()


_LAYER_PATTERNS = {
    "mock_e2e": ("mainline_mock_e2e",),
    "hil": ("hil_", "_hil", "phase_metrics_validator"),
    "runtime_core": ("runtime_", "protocol_sync", "control_authority", "mainline_runtime_doctor", "mainline_task_tree", "command_guard", "cpp_target", "robot_family", "sdk_usage", "contact_control_contract"),
    "surface_integration": ("headless", "api_bridge", "backend_link", "app_controller", "main_window", "session_products", "governance", "bridge_observability"),
    "contract": ("schema", "contract", "manifest", "release_evidence", "verification_boundary", "architecture_fitness"),
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        nodeid = item.nodeid.lower()
        assigned = False
        for marker_name, patterns in _LAYER_PATTERNS.items():
            if any(pattern in nodeid for pattern in patterns):
                item.add_marker(getattr(pytest.mark, marker_name))
                assigned = True
        if not assigned:
            item.add_marker(pytest.mark.unit)


def pytest_configure(config):
    for marker in (
        "unit: fast isolated unit coverage",
        "contract: schema/contract and manifest alignment coverage",
        "runtime_core: runtime-core and robot-core governance coverage",
        "surface_integration: desktop/headless/backend surface integration coverage",
        "mock_e2e: mock end-to-end orchestration coverage",
        "hil: hardware-in-the-loop or HIL-adjacent coverage",
    ):
        config.addinivalue_line("markers", marker)
