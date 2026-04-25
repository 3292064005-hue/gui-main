#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tokenize

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = ("scripts", "runtime", "spine_ultrasound_ui", "tests")
PRUNED_DIRS = {"__pycache__", ".pytest_cache", ".git", "archive"}


def iter_python_files() -> list[Path]:
    """Return active Python files covered by the source syntax gate.

    Archive compatibility tests are intentionally pruned because they are not in
    the active pytest surface. The archive boundary remains covered by
    ``tests/archive/README.md`` and explicit opt-in archive suites.
    """
    files: list[Path] = []
    for dirname in SCAN_ROOTS:
        root = ROOT / dirname
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in PRUNED_DIRS]
            for filename in filenames:
                if filename.endswith(".py"):
                    files.append(Path(dirpath) / filename)
    return sorted(files)


def _compile_source(path: Path) -> str | None:
    """Tokenize one Python source file without importing it or writing bytecode."""
    try:
        with tokenize.open(path) as handle:
            for _token in tokenize.generate_tokens(handle.readline):
                pass
    except (OSError, SyntaxError, UnicodeDecodeError, tokenize.TokenError, ValueError) as exc:
        rel = path.relative_to(ROOT)
        return f"{rel}: {exc}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tokenize active repository Python files without importing them or writing bytecode.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only print failures.")
    args = parser.parse_args([] if argv is None else argv)

    files = iter_python_files()
    failures: list[str] = []
    for index, path in enumerate(files, start=1):
        if not args.quiet and (index == 1 or index % 100 == 0):
            print(f"Python source gate scanning {index}/{len(files)}: {path.relative_to(ROOT)}", flush=True)
        failure = _compile_source(path)
        if failure:
            failures.append(failure)
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"Python source gate passed: {len(files)} active files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
