
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path('scripts/check_architecture_fitness.py')
SPEC = importlib.util.spec_from_file_location('check_architecture_fitness', MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)



def test_should_skip_python_file_respects_repository_relative_top_level(tmp_path: Path) -> None:
    root = tmp_path / 'workspace'
    mainline_file = root / 'spine_ultrasound_ui' / 'services' / 'runtime_service.py'
    archive_file = root / 'archive' / 'legacy' / 'old_runtime.py'
    mirror_file = root / 'repo' / 'spine_ultrasound_ui' / 'services' / 'shadow.py'
    test_file = root / 'tests' / 'test_runtime.py'
    config_manager = root / 'spine_ultrasound_ui' / 'services' / 'config_manager.py'
    self_path = root / 'scripts' / 'check_architecture_fitness.py'
    for path in [mainline_file, archive_file, mirror_file, test_file, config_manager, self_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# stub\n', encoding='utf-8')

    assert MODULE._should_skip_python_file(mainline_file, root=root, self_path=self_path, config_manager=config_manager) is False
    assert MODULE._should_skip_python_file(archive_file, root=root, self_path=self_path, config_manager=config_manager) is True
    assert MODULE._should_skip_python_file(mirror_file, root=root, self_path=self_path, config_manager=config_manager) is True
    assert MODULE._should_skip_python_file(test_file, root=root, self_path=self_path, config_manager=config_manager) is True
    assert MODULE._should_skip_python_file(config_manager, root=root, self_path=self_path, config_manager=config_manager) is True
    assert MODULE._should_skip_python_file(self_path, root=root, self_path=self_path, config_manager=config_manager) is True



def test_iter_scannable_python_sources_never_returns_zero_for_valid_mainline_tree(tmp_path: Path) -> None:
    root = tmp_path / 'workspace'
    config_manager = root / 'spine_ultrasound_ui' / 'services' / 'config_manager.py'
    self_path = root / 'scripts' / 'check_architecture_fitness.py'
    mainline_a = root / 'spine_ultrasound_ui' / 'core' / 'app_controller.py'
    mainline_b = root / 'scripts' / 'doctor_runtime_helper.py'
    archive_file = root / 'archive' / 'legacy.py'
    for path in [config_manager, self_path, mainline_a, mainline_b, archive_file]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# stub\n', encoding='utf-8')

    sources = list(MODULE._iter_scannable_python_sources(root=root, self_path=self_path, config_manager=config_manager))
    assert mainline_a in sources
    assert mainline_b in sources
    assert archive_file not in sources
    assert len(sources) == 2


def test_relative_python_path_rejects_paths_outside_repository_root(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    inside = root / "spine_ultrasound_ui" / "services" / "runtime_service.py"
    outside = tmp_path / "external" / "shadow.py"
    inside.parent.mkdir(parents=True, exist_ok=True)
    outside.parent.mkdir(parents=True, exist_ok=True)
    inside.write_text("# stub\n", encoding="utf-8")
    outside.write_text("# stub\n", encoding="utf-8")

    assert MODULE._relative_python_path(inside, root=root) == Path("spine_ultrasound_ui/services/runtime_service.py")
    try:
        MODULE._relative_python_path(outside, root=root)
    except ValueError as exc:
        assert "not inside repository root" in str(exc)
    else:
        raise AssertionError("paths outside repository root must be rejected")
