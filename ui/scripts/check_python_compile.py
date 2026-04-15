#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = ("scripts", "runtime", "spine_ultrasound_ui", "tests")


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for dirname in SCAN_ROOTS:
        root = ROOT / dirname
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return sorted(files)


def _compile_source(path: Path) -> str | None:
    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    except (OSError, SyntaxError, ValueError) as exc:
        rel = path.relative_to(ROOT)
        return f"{rel}: {exc}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile-check repository Python files without writing bytecode.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only print failures.")
    args = parser.parse_args([] if argv is None else argv)

    failures = [failure for path in iter_python_files() if (failure := _compile_source(path))]
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"Python compile gate passed: {len(iter_python_files())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
