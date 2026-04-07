from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


class FrameAnatomyPointDataset:
    """Dataset adapter for frame-level raw-ultrasound anatomy point training.

    The dataset is intentionally lightweight: a manifest references grayscale
    ultrasound frames together with left/right landmark annotations in pixel
    coordinates. This keeps the training/export path import-safe while still
    producing a genuine exported-weight package consumed by the runtime adapter.
    """

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = Path(manifest_path)
        if not self.manifest_path.exists():
            raise FileNotFoundError(self.manifest_path)
        payload = json.loads(self.manifest_path.read_text(encoding='utf-8'))
        items = payload.get('cases', [])
        if not isinstance(items, list):
            raise ValueError('frame anatomy manifest must contain a list of cases')
        self._items: list[dict[str, Any]] = []
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            frame_path = Path(str(item.get('image_path', '') or ''))
            if not frame_path.is_absolute():
                frame_path = (self.manifest_path.parent / frame_path).resolve()
            left = dict(item.get('left', {}) or {})
            right = dict(item.get('right', {}) or {})
            if not frame_path.exists() or not left or not right:
                continue
            self._items.append({
                'case_id': str(item.get('case_id', f'frame_case_{idx:04d}') or f'frame_case_{idx:04d}'),
                'image_path': str(frame_path),
                'left': left,
                'right': right,
                'metadata': dict(item.get('metadata', {}) or {}),
            })
        if not self._items:
            raise ValueError('frame anatomy dataset does not contain any valid annotated frames')

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        item = self._items[index]
        with Image.open(item['image_path']) as image:
            array = np.asarray(image.convert('L'), dtype=np.float32)
        return {
            'case_id': item['case_id'],
            'image': self._normalize(array),
            'left': dict(item['left']),
            'right': dict(item['right']),
            'metadata': dict(item['metadata']),
            'image_path': item['image_path'],
        }

    def case_ids(self) -> list[str]:
        return [str(item['case_id']) for item in self._items]

    @staticmethod
    def _normalize(image: np.ndarray) -> np.ndarray:
        image = np.asarray(image, dtype=np.float32)
        if image.size == 0:
            return np.zeros((0, 0), dtype=np.float32)
        low = float(image.min())
        high = float(image.max())
        if high <= low:
            return np.zeros_like(image, dtype=np.float32)
        return (image - low) / (high - low)
