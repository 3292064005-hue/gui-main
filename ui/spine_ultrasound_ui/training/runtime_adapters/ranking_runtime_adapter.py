from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import resolve_model_package


class RankingRuntimeAdapter:
    """Runtime adapter for baseline UCA slice-ranking packages."""

    def __init__(self) -> None:
        self._loaded = False
        self._meta: dict[str, Any] = {}
        self._parameters: dict[str, Any] = {}

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, model_dir_or_config: str | Path) -> None:
        payload = resolve_model_package(model_dir_or_config)
        self._meta = dict(payload['meta'])
        self._parameters = dict(payload['parameters'])
        self._loaded = True

    def infer(self, slice_stack: dict[str, Any]) -> dict[str, Any]:
        if not self._loaded:
            raise RuntimeError('ranking runtime adapter is not loaded')
        slices = [dict(item) for item in slice_stack.get('slices', []) if isinstance(item, dict)]
        weights = dict(self._parameters.get('score_weights', {'mean_intensity': 0.6, 'peak_intensity': 0.4}))
        ranked = sorted(
            slices,
            key=lambda item: (
                float(weights.get('mean_intensity', 0.6)) * float(item.get('score', 0.0) or 0.0)
                + float(weights.get('peak_intensity', 0.4)) * float(item.get('peak_intensity', 0.0) or 0.0)
            ),
            reverse=True,
        )
        return {
            'ranked_slices': ranked,
            'best_slice': ranked[0] if ranked else {},
            'runtime_model': dict(self._meta),
        }
