from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.training.runtime_adapters.ranking_runtime_adapter import RankingRuntimeAdapter
from spine_ultrasound_ui.utils import now_text


class VPISliceSelectorService:
    """Rank VPI slices for auxiliary-UCA measurement."""

    def __init__(
        self,
        *,
        top_k: int = 4,
        method_version: str = 'vpi_slice_selector_v3',
        runtime_adapter: RankingRuntimeAdapter | None = None,
        runtime_model_config: str | Path | None = None,
    ) -> None:
        self.top_k = int(top_k)
        self.method_version = method_version
        self.runtime_adapter = runtime_adapter
        self.runtime_model_config = runtime_model_config or os.environ.get(
            'SPINE_UCA_RANK_RUNTIME_CONFIG',
            Path(__file__).resolve().parents[3] / 'configs' / 'models' / 'uca_rank_runtime.yaml',
        )
        self.runtime_load_error = ''
        self._try_load_runtime_adapter()

    def rank(self, vpi_bundle: dict[str, Any]) -> dict[str, Any]:
        image = np.asarray(vpi_bundle.get('image'))
        if image.ndim != 2:
            raise ValueError('vpi_bundle.image must be 2D')
        slices = [dict(item) for item in vpi_bundle.get('slices', []) if isinstance(item, dict)]
        runtime_model = self._fallback_runtime_model()
        if self.runtime_adapter is not None and self.runtime_adapter.is_loaded:
            payload = self.runtime_adapter.infer({'slices': slices})
            ranked = [dict(item) for item in payload.get('ranked_slices', [])]
            runtime_model = dict(payload.get('runtime_model', {}))
        else:
            ranked = sorted(slices, key=lambda item: (float(item.get('score', 0.0) or 0.0), float(item.get('peak_intensity', 0.0) or 0.0)), reverse=True)
        return {
            'generated_at': now_text(),
            'session_id': str(vpi_bundle.get('session_id', '') or ''),
            'method_version': self.method_version,
            'ranked_slices': ranked,
            'best_slice': ranked[0] if ranked else {},
            'top_k': ranked[: self.top_k],
            'runtime_model': runtime_model,
        }

    def _try_load_runtime_adapter(self) -> None:
        if self.runtime_adapter is None and self.runtime_model_config:
            self.runtime_adapter = RankingRuntimeAdapter()
        if self.runtime_adapter is None or not self.runtime_model_config:
            return
        config_path = Path(str(self.runtime_model_config))
        if not config_path.exists():
            self.runtime_load_error = f'missing_runtime_model_config:{config_path}'
            return
        try:
            self.runtime_adapter.load(config_path)
        except Exception as exc:  # pragma: no cover - exercised by runtime failures
            self.runtime_load_error = f'{type(exc).__name__}:{exc}'

    def _fallback_runtime_model(self) -> dict[str, Any]:
        return {
            'package_name': 'uca_rank_inline_fallback',
            'backend': 'inline_fallback',
            'runtime_kind': 'deterministic_fallback',
            'release_state': 'degraded',
            'load_error': self.runtime_load_error,
        }
