from __future__ import annotations

from pathlib import Path


def test_verify_mainline_enables_optional_unity_build_for_cpp_profiles() -> None:
    script = Path("scripts/verify_mainline.sh").read_text(encoding="utf-8")
    assert "VERIFY_ENABLE_UNITY_BUILD" in script
    assert "-DCMAKE_UNITY_BUILD=ON" in script
    assert "-DCMAKE_UNITY_BUILD_BATCH_SIZE=" in script
    assert "run_cpp_profile_gate prod" in script
