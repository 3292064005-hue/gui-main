#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from spine_ultrasound_ui.services.benchmark.assessment_benchmark_service import AssessmentBenchmarkService


def main() -> int:
    parser = argparse.ArgumentParser(description='Evaluate scoliosis assessment sessions against offline ground truth.')
    parser.add_argument('session_dirs', nargs='+', help='Session directories to evaluate.')
    parser.add_argument('--ground-truth', nargs='*', default=None, help='Optional per-session ground-truth json files.')
    args = parser.parse_args()

    if args.ground_truth is not None and len(args.ground_truth) not in {0, len(args.session_dirs)}:
        raise SystemExit('--ground-truth must either be omitted or match session count')

    case_specs = []
    gt_list = list(args.ground_truth or [])
    for index, session_dir in enumerate(args.session_dirs):
        spec = {'session_dir': session_dir}
        if gt_list:
            spec['ground_truth_path'] = gt_list[index]
        case_specs.append(spec)

    report = AssessmentBenchmarkService().evaluate_many(case_specs)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
