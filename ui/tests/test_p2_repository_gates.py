from __future__ import annotations

from pathlib import Path

from scripts.check_canonical_imports import main as canonical_import_main
from scripts.check_repository_gates import main as repository_gates_main
from scripts.check_verification_boundary import main as verification_boundary_main


def test_canonical_import_audit_passes() -> None:
    assert canonical_import_main() == 0


def test_repository_gates_audit_passes() -> None:
    assert repository_gates_main() == 0


def test_codeowners_and_gate_docs_exist() -> None:
    assert Path('.github/CODEOWNERS').exists()
    assert Path('docs/REPOSITORY_GATES.md').exists()
    assert Path('docs/CANONICAL_MODULE_REGISTRY.md').exists()
    assert Path('docs/VERIFICATION_BOUNDARY.md').exists()


def test_verification_boundary_audit_passes() -> None:
    assert verification_boundary_main() == 0
