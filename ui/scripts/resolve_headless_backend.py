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

    The script accepts no arguments and derives the deployment-profile default
    from runtime policy while intentionally ignoring stale low-level surface
    backend environment overrides. Unified launchers must pass explicit backend
    intent via `SPINE_MAINLINE_BACKEND` or CLI flags instead of `SPINE_HEADLESS_BACKEND`.
    """
    decision = resolve_runtime_mode(
        explicit_mode=None,
        surface='headless',
        env=dict(os.environ),
        allow_environment_override=False,
    )
    print(json.dumps(decision.to_dict(), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
