from __future__ import annotations

from pathlib import Path

from scripts.start_mainline import _normalize_deployment_profile


def test_launcher_accepts_legacy_profile_aliases() -> None:
    assert _normalize_deployment_profile('mock') == 'dev'
    assert _normalize_deployment_profile('hil') == 'research'
    assert _normalize_deployment_profile('prod') == 'clinical'


def test_start_hil_wrapper_uses_research_profile_via_mainline_launcher() -> None:
    source = Path('scripts/start_hil.sh').read_text(encoding='utf-8')
    assert 'SPINE_DEPLOYMENT_PROFILE="${SPINE_DEPLOYMENT_PROFILE:-research}"' in source
    assert 'scripts/start_mainline.py' in source


def test_start_prod_wrapper_uses_clinical_profile_via_mainline_launcher() -> None:
    source = Path('scripts/start_prod.sh').read_text(encoding='utf-8')
    assert 'SPINE_DEPLOYMENT_PROFILE="${SPINE_DEPLOYMENT_PROFILE:-clinical}"' in source
    assert 'scripts/start_mainline.py' in source



def test_start_hil_wrapper_only_binds_profile_and_backend_into_mainline_launcher() -> None:
    source = Path('scripts/start_hil.sh').read_text(encoding='utf-8')
    assert 'SPINE_DOCTOR_STRICT' not in source
    assert 'ROBOT_CORE_WITH_XCORE_SDK' not in source
    assert 'ROBOT_CORE_WITH_XMATE_MODEL' not in source


def test_start_prod_wrapper_only_binds_profile_and_backend_into_mainline_launcher() -> None:
    source = Path('scripts/start_prod.sh').read_text(encoding='utf-8')
    assert 'SPINE_DOCTOR_STRICT' not in source
    assert 'ROBOT_CORE_WITH_XCORE_SDK' not in source
    assert 'ROBOT_CORE_WITH_XMATE_MODEL' not in source
