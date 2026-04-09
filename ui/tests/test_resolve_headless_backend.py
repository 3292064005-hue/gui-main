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


def test_resolve_headless_backend_script_preserves_explicit_mode() -> None:
    script = Path('scripts/resolve_headless_backend.py')
    env = dict(os.environ)
    env['SPINE_DEPLOYMENT_PROFILE'] = 'lab'
    env['SPINE_HEADLESS_BACKEND'] = 'core'
    result = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload['mode'] == 'core'
    assert payload['resolution_source'] == 'explicit'



def test_resolve_headless_backend_review_defaults_to_core_and_allows_explicit_mock() -> None:
    script = Path('scripts/resolve_headless_backend.py')

    default_env = dict(os.environ)
    default_env.pop('SPINE_HEADLESS_BACKEND', None)
    default_env['SPINE_DEPLOYMENT_PROFILE'] = 'review'
    default_result = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True, env=default_env)
    assert default_result.returncode == 0, default_result.stderr
    default_payload = json.loads(default_result.stdout)
    assert default_payload['mode'] == 'core'
    assert default_payload['profile_name'] == 'review'

    mock_env = dict(default_env)
    mock_env['SPINE_HEADLESS_BACKEND'] = 'mock'
    mock_result = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True, env=mock_env)
    assert mock_result.returncode == 0, mock_result.stderr
    mock_payload = json.loads(mock_result.stdout)
    assert mock_payload['mode'] == 'mock'
    assert mock_payload['resolution_source'] == 'explicit'
