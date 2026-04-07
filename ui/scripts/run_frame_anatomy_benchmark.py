from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.benchmark.frame_anatomy_benchmark_service import FrameAnatomyBenchmarkService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Benchmark a frame-anatomy runtime package against pixel annotations')
    parser.add_argument('--runtime', required=True, type=Path, help='Runtime config or package directory')
    parser.add_argument('--manifest', required=True, type=Path, help='JSON manifest containing benchmark cases')
    parser.add_argument('--output', type=Path, default=None, help='Optional report output path')
    args = parser.parse_args(argv)

    payload = json.loads(args.manifest.read_text(encoding='utf-8'))
    report = FrameAnatomyBenchmarkService().evaluate_many(args.runtime, list(payload.get('cases', [])))
    output_path = args.output or (args.runtime if args.runtime.is_dir() else args.runtime.parent) / 'benchmark_manifest.json'
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
