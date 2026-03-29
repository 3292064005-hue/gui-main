from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


class SelectedExecutionRationaleService:
    def build(self, session_dir: Path) -> dict[str, Any]:
        scan_plan = self._read_json(session_dir / 'meta' / 'scan_plan.json')
        validation_summary = dict(scan_plan.get('validation_summary', {}))
        rationale = dict(validation_summary.get('selection_rationale', {}))
        candidates = list(validation_summary.get('execution_candidates', []))
        score = dict(scan_plan.get('score_summary', {}))
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        return {
            'generated_at': now_text(),
            'session_id': str(manifest.get('session_id', session_dir.name)),
            'selected_candidate_id': str(rationale.get('selected_candidate_id', rationale.get('selected_plan_id', ''))),
            'selected_plan_id': str(rationale.get('selected_plan_id', scan_plan.get('plan_id', ''))),
            'selection_basis': dict(rationale.get('selection_basis', {})),
            'tradeoff_summary': dict(rationale.get('tradeoff_summary', {})),
            'selected_score': dict(rationale.get('selected_score', score)),
            'ranking_snapshot': list(rationale.get('ranking_snapshot', candidates)),
            'rejected_candidate_reasons': list(rationale.get('rejected_candidate_reasons', [])),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))
