from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


class UCADataset:
    """Dataset adapter for exported auxiliary-UCA training cases."""

    def __init__(
        self,
        dataset_root: Path,
        split_file: Path,
        split_name: str,
        *,
        require_annotations: bool = True,
    ) -> None:
        self.dataset_root = Path(dataset_root)
        self.split_file = Path(split_file)
        self.split_name = str(split_name)
        self.require_annotations = bool(require_annotations)
        self._items = self._build_items()

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        item = self._items[index]
        vpi = self._load_npz(Path(item['case_dir']) / 'coronal_vpi.npz')
        uca_label = self._read_json(Path(item['label_path'])) if item.get('label_path') else {}
        ranking = self._read_json(Path(item['ranking_path'])) if item.get('ranking_path') else {}
        feature_mask = self._load_optional_npz(Path(item['feature_mask_path']), shape=vpi.shape)
        meta = self._read_json(Path(item['case_dir']) / 'meta.json')
        return {
            'case_id': item['case_id'],
            'patient_id': item['patient_id'],
            'session_id': item['session_id'],
            'slice_stack': vpi.astype(np.float32),
            'best_slice_index': int(uca_label.get('best_slice_index', ranking.get('best_slice', {}).get('slice_index', 0)) or 0),
            'bone_feature_mask': feature_mask.astype(np.float32),
            'uca_angle_deg': float(uca_label.get('uca_angle_deg', 0.0) or 0.0),
            'meta': meta,
            'ranking': ranking,
        }

    def case_ids(self) -> list[str]:
        return [str(item['case_id']) for item in self._items]

    def _build_items(self) -> list[dict[str, Any]]:
        if not self.dataset_root.exists():
            raise FileNotFoundError(self.dataset_root)
        if not self.split_file.exists():
            raise FileNotFoundError(self.split_file)
        split_payload = self._read_json(self.split_file)
        case_ids = [str(case_id) for case_id in split_payload.get(self.split_name, [])]
        items: list[dict[str, Any]] = []
        for case_id in case_ids:
            patient_id, session_id = self._split_case_id(case_id)
            case_dir = self.dataset_root / 'raw_cases' / patient_id / session_id
            if not case_dir.exists():
                continue
            label_path = self.dataset_root / 'annotations' / 'uca_labels' / f'{patient_id}__{session_id}.json'
            ranking_path = self.dataset_root / 'annotations' / 'slice_ranking' / f'{patient_id}__{session_id}.json'
            feature_mask_path = self.dataset_root / 'annotations' / 'bone_feature_masks' / f'{patient_id}__{session_id}.npz'
            if self.require_annotations and not label_path.exists():
                continue
            items.append({
                'case_id': case_id,
                'patient_id': patient_id,
                'session_id': session_id,
                'case_dir': str(case_dir),
                'label_path': str(label_path) if label_path.exists() else '',
                'ranking_path': str(ranking_path) if ranking_path.exists() else '',
                'feature_mask_path': str(feature_mask_path),
            })
        return items

    @staticmethod
    def _split_case_id(case_id: str) -> tuple[str, str]:
        normalized = case_id.replace('\\', '/').replace('__', '/')
        parts = [part for part in normalized.split('/') if part]
        if len(parts) < 2:
            raise ValueError(f'invalid case_id: {case_id}')
        return parts[-2], parts[-1]

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def _load_npz(path: Path) -> np.ndarray:
        if not path.exists():
            raise FileNotFoundError(path)
        payload = np.load(path, allow_pickle=False)
        if not payload.files:
            return np.zeros((0, 0), dtype=np.float32)
        return np.asarray(payload[payload.files[0]], dtype=np.float32)

    @staticmethod
    def _load_optional_npz(path: Path, *, shape: tuple[int, ...]) -> np.ndarray:
        if not path.exists():
            return np.zeros(shape, dtype=np.float32)
        payload = np.load(path, allow_pickle=False)
        if not payload.files:
            return np.zeros(shape, dtype=np.float32)
        return np.asarray(payload[payload.files[0]], dtype=np.float32)
