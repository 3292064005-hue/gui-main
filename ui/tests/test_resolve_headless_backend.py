from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_resolve_headless_backend_script_uses_runtime_policy_default(tmp_path: Path) -> None:
    script = Path('scripts/resolve_headless_backend.py')
    env = dict(os.environ)
    env.pop('SPINE_HEADLESS_BACKEND', None)
    env['SPINE_DEPLOYMENT_PROFILE'] = 'dev'
    result = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload['surface'] == 'headless'
    assert payload['profile_name'] == 'dev'
    assert payload['mode'] == 'mock'


def test_resolve_headless_backend_script_ignores_low_level_headless_env_override() -> None:
    script = Path('scripts/resolve_headless_backend.py')
    env = dict(os.environ)
    env['SPINE_DEPLOYMENT_PROFILE'] = 'research'
    env['SPINE_HEADLESS_BACKEND'] = 'mock'
    result = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload['mode'] == 'core'
    assert payload['resolution_source'] == 'profile_default'


def test_resolve_headless_backend_review_defaults_to_core_even_with_stale_headless_env() -> None:
    script = Path('scripts/resolve_headless_backend.py')

    default_env = dict(os.environ)
    default_env.pop('SPINE_HEADLESS_BACKEND', None)
    default_env['SPINE_DEPLOYMENT_PROFILE'] = 'review'
    default_result = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True, env=default_env)
    assert default_result.returncode == 0, default_result.stderr
    default_payload = json.loads(default_result.stdout)
    assert default_payload['mode'] == 'core'
    assert default_payload['profile_name'] == 'review'

    stale_env = dict(default_env)
    stale_env['SPINE_HEADLESS_BACKEND'] = 'mock'
    stale_result = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True, env=stale_env)
    assert stale_result.returncode == 0, stale_result.stderr
    stale_payload = json.loads(stale_result.stdout)
    assert stale_payload['mode'] == 'core'
    assert stale_payload['resolution_source'] == 'profile_default'
