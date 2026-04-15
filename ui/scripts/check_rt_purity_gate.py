#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RT_SENSITIVE_RULES: dict[Path, dict[str, object]] = {
    ROOT / 'cpp_robot_core' / 'src' / 'rt_motion_service.cpp': {
        'forbidden_tokens': {
            'json::': 'RT motion service must not emit JSON on the hot path',
            'std::ofstream': 'RT motion service must not write files on the hot path',
            'std::ifstream': 'RT motion service must not read files on the hot path',
            'appendRecord': 'RT motion service must not touch recorder append APIs on the hot path',
            'std::cout': 'RT motion service must not log to stdout on the hot path',
            'printf(': 'RT motion service must not use formatted stdout on the hot path',
            'fmt::': 'RT motion service must not perform formatting-heavy work on the hot path',
            'std::make_unique': 'RT motion service must not allocate dynamic objects on the hot path',
            'std::make_shared': 'RT motion service must not allocate shared dynamic objects on the hot path',
            'new ': 'RT motion service must not allocate heap objects on the hot path',
        },
        'required_tokens': {
            'snapshot_.overrun_count': 'RT motion service must export overrun_count into the RT snapshot',
            'snapshot_.last_wake_jitter_ms': 'RT motion service must export wake jitter into the RT snapshot',
            'snapshot_.jitter_budget_ms': 'RT motion service must preserve a jitter budget in the RT snapshot',
            'snapshot_.current_period_ms': 'RT motion service must preserve the current fixed control period in the RT snapshot',
        },
        'allowed_line_patterns': [
            r'RtMotionService::RtMotionService',
            r'impedance_manager_\(',
            r'adaptive_timer_\(',
        ],
    },
    ROOT / 'cpp_robot_core' / 'src' / 'sdk_robot_facade_rt.cpp': {
        'forbidden_tokens': {
            'json::': 'RT facade must not emit JSON on the hot path',
            'std::ofstream': 'RT facade must not write files on the hot path',
            'std::ifstream': 'RT facade must not read files on the hot path',
            'appendRecord': 'RT facade must not touch recorder append APIs on the hot path',
            'std::cout': 'RT facade must not log to stdout on the hot path',
            'printf(': 'RT facade must not use formatted stdout on the hot path',
            'fmt::': 'RT facade must not perform formatting-heavy work on the hot path',
            'std::make_unique': 'RT facade must not allocate dynamic objects on the hot path',
            'std::make_shared': 'RT facade must not allocate shared dynamic objects on the hot path',
            'new ': 'RT facade must not allocate heap objects on the hot path',
        },
        'required_tokens': {
            'startLoop(false)': 'RT facade must keep non-blocking fixed-period loop startup on the RT path',
        },
        'allowed_line_patterns': [],
    },
    ROOT / 'cpp_robot_core' / 'src' / 'command_server.cpp': {
        'forbidden_tokens': {
            'std::ofstream': 'Command server RT-adjacent loop must not write files on the hot path',
            'std::ifstream': 'Command server RT-adjacent loop must not read files on the hot path',
            'appendRecord': 'Command server RT-adjacent loop must not append recorder payloads',
            'std::make_shared': 'Command server RT-adjacent loop must not allocate shared dynamic objects on the hot path',
            'new ': 'Command server RT-adjacent loop must not allocate heap objects on the hot path',
        },
        'required_tokens': {
            'PeriodicLoopController controller(std::chrono::microseconds(1000))': 'RT loop must preserve a 1 ms fixed nominal period',
            'runtime_.recordRtLoopSample(sample.period_ms, sample.execution_ms, sample.wake_jitter_ms, sample.overrun);': 'RT loop must publish jitter/overrun samples to the runtime gate',
            'sample.overrun': 'RT loop must retain overrun evidence in the measured sample',
            'sample.wake_jitter_ms': 'RT loop must retain wake jitter evidence in the measured sample',
        },
        'allowed_line_patterns': [],
    },
    ROOT / 'cpp_robot_core' / 'src' / 'telemetry_publisher.cpp': {
        'forbidden_tokens': {
            'std::ofstream': 'Telemetry publisher must not write files on the publish path',
            'std::ifstream': 'Telemetry publisher must not read files on the publish path',
            'appendRecord': 'Telemetry publisher must not append recorder payloads on the publish path',
            'std::make_shared': 'Telemetry publisher must not allocate shared dynamic objects on the publish path',
            'new ': 'Telemetry publisher must not allocate heap objects on the publish path',
        },
        'required_tokens': {},
        'allowed_line_patterns': [],
    },
    ROOT / 'cpp_robot_core' / 'src' / 'runtime_state_store.cpp': {
        'forbidden_tokens': {},
        'required_tokens': {
            'rt_snapshot.overrun_count == 0': 'Runtime state store must gate RT health on overrun_count',
            'rt_snapshot.max_cycle_ms <= (rt_snapshot.current_period_ms + rt_snapshot.jitter_budget_ms)': 'Runtime state store must gate RT health on cycle budget',
            'std::abs(rt_snapshot.last_wake_jitter_ms) <= rt_snapshot.jitter_budget_ms': 'Runtime state store must gate RT health on jitter budget',
            'rt_jitter_ok_ = !overrun && within_jitter_budget && within_cycle_budget;': 'Runtime state store must fail hard when the measured RT sample violates jitter/overrun budget',
        },
        'allowed_line_patterns': [],
    },
    ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_contracts.cpp': {
        'forbidden_tokens': {},
        'required_tokens': {
            'field("overrun_count"': 'Runtime contracts must publish overrun_count to the governance surface',
            'field("last_wake_jitter_ms"': 'Runtime contracts must publish last_wake_jitter_ms to the governance surface',
            'field("jitter_budget_ms"': 'Runtime contracts must publish jitter_budget_ms to the governance surface',
            'field("current_period_ms"': 'Runtime contracts must publish current_period_ms to the governance surface',
            'field("rt_quality_gate_passed"': 'Runtime contracts must publish rt_quality_gate_passed to the governance surface',
            'field("fixed_period_enforced"': 'Runtime contracts must publish fixed_period_enforced to the governance surface',
        },
        'allowed_line_patterns': [],
    },
}

COMMENT_RE = re.compile(r'//.*?$|/\*.*?\*/', re.DOTALL | re.MULTILINE)
INCLUDE_RE = re.compile(r'^\s*#\s*include\b.*$', re.MULTILINE)


def sanitize(source: str) -> str:
    without_comments = re.sub(COMMENT_RE, '', source)
    return re.sub(INCLUDE_RE, '', without_comments)


def main() -> int:
    failures: list[str] = []
    for path, rule in RT_SENSITIVE_RULES.items():
        text = sanitize(path.read_text(encoding='utf-8'))
        allowed_patterns = [re.compile(pattern) for pattern in rule.get('allowed_line_patterns', [])]
        for token, reason in dict(rule.get('required_tokens', {})).items():
            if token not in text:
                failures.append(f'{path.relative_to(ROOT)}:missing required token: {reason} ({token})')
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in allowed_patterns):
                continue
            for token, reason in dict(rule.get('forbidden_tokens', {})).items():
                if token in line:
                    failures.append(f'{path.relative_to(ROOT)}:{line_no}: {reason} ({token})')
    if failures:
        for item in failures:
            print(f'[FAIL] {item}')
        return 1
    print('rt purity gate: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
