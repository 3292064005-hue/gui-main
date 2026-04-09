from __future__ import annotations

"""Demo-only worker task adapters.

These wrappers keep legacy UI preview workers alive while preventing the worker
modules themselves from directly binding the formal worker surface to the demo
imaging implementation tree.
"""

from typing import Any

from spine_ultrasound_ui.imaging.assessment import run_assessment as _run_demo_assessment
from spine_ultrasound_ui.imaging.preprocess import run_preprocess as _run_demo_preprocess
from spine_ultrasound_ui.imaging.reconstruction import run_reconstruction as _run_demo_reconstruction


def run_demo_preprocess(payload: Any) -> dict[str, Any]:
    return _run_demo_preprocess(payload)


def run_demo_reconstruction(payload: Any) -> dict[str, Any]:
    return _run_demo_reconstruction(payload)


def run_demo_assessment(payload: Any) -> dict[str, Any]:
    return _run_demo_assessment(payload)
