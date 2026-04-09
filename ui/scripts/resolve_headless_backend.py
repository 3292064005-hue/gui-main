#!/usr/bin/env python3
from __future__ import annotations

"""Resolve the authoritative headless backend default from runtime policy."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.runtime_mode_policy import resolve_runtime_mode


def main() -> int:
    """Print the resolved headless backend mode.

    The script accepts no arguments and derives the decision from the current
    environment so shell launchers can stay synchronized with the Python policy
    source of truth.
    """
    decision = resolve_runtime_mode(
        explicit_mode=os.environ.get('SPINE_HEADLESS_BACKEND'),
        surface='headless',
        env=dict(os.environ),
    )
    print(json.dumps(decision.to_dict(), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
