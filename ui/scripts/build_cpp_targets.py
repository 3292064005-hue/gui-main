#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build C++ targets sequentially with heartbeats and one retry.')
    parser.add_argument('--build-dir', required=True)
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('targets', nargs='+')
    return parser.parse_args()


def run_target(build_dir: Path, target: str, jobs: int) -> int:
    cmd = ['cmake', '--build', str(build_dir), '--target', target, f'-j{jobs}']
    for attempt in (1, 2):
        print(f'[build] target={target} attempt={attempt}', flush=True)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert proc.stdout is not None
        last_emit = time.monotonic()
        buffered: list[str] = []
        try:
            while True:
                line = proc.stdout.readline()
                if line:
                    print(line, end='')
                    buffered.append(line)
                    last_emit = time.monotonic()
                elif proc.poll() is not None:
                    break
                else:
                    if time.monotonic() - last_emit >= 10:
                        print(f'[build] still building {target}...', flush=True)
                        last_emit = time.monotonic()
                    time.sleep(0.2)
        finally:
            proc.wait()
        if proc.returncode == 0:
            return 0
        print(f'[build] target={target} failed with exit={proc.returncode}', file=sys.stderr, flush=True)
        if attempt == 1:
            print(f'[build] retrying {target} once...', file=sys.stderr, flush=True)
    return proc.returncode


def main() -> int:
    args = parse_args()
    build_dir = Path(args.build_dir)
    for target in args.targets:
        rc = run_target(build_dir, target, args.jobs)
        if rc != 0:
            return rc
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
