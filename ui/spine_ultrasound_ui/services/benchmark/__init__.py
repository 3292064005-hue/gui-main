from __future__ import annotations

"""Benchmark service exports.

This package avoids eager cross-imports because some training adapters import
benchmark services during module initialization. Importing the full benchmark
package eagerly can therefore create circular-import failures during test
collection.
"""

__all__ = ['AssessmentBenchmarkService', 'FrameAnatomyBenchmarkService', 'RuntimeModelReleaseGateService']


def __getattr__(name: str):
    if name == 'AssessmentBenchmarkService':
        from .assessment_benchmark_service import AssessmentBenchmarkService
        return AssessmentBenchmarkService
    if name == 'FrameAnatomyBenchmarkService':
        from .frame_anatomy_benchmark_service import FrameAnatomyBenchmarkService
        return FrameAnatomyBenchmarkService
    if name == 'RuntimeModelReleaseGateService':
        from .runtime_model_release_gate_service import RuntimeModelReleaseGateService
        return RuntimeModelReleaseGateService
    raise AttributeError(name)
