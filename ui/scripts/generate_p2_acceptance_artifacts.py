from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _output_root() -> Path:
    configured = os.environ.get('P2_ACCEPTANCE_OUTPUT_ROOT', '').strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(tempfile.gettempdir()) / 'spine_p2_acceptance_static'

from spine_ultrasound_ui.core.postprocess.stage_registry import iter_stage_specs
from spine_ultrasound_ui.services.session_intelligence.registry import iter_product_specs
from spine_ultrasound_ui.utils import now_text


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    output_root = _output_root()
    _write_json(
        output_root / 'derived/postprocess/postprocess_stage_manifest.json',
        {
            'generated_at': now_text(),
            'session_id': 'P2_ACCEPTANCE_STATIC',
            'schema': 'session/postprocess_stage_manifest_v1.schema.json',
            'stages': [
                {**spec.to_dict(), 'ready': False, 'status': 'NOT_RUN'}
                for spec in iter_stage_specs()
            ],
        },
    )
    _write_json(
        output_root / 'derived/session/session_intelligence_manifest.json',
        {
            'generated_at': now_text(),
            'session_id': 'P2_ACCEPTANCE_STATIC',
            'schema': 'session/session_intelligence_manifest_v1.schema.json',
            'products': [
                {**spec.to_dict(), 'materialized': False}
                for spec in iter_product_specs()
            ],
        },
    )


if __name__ == '__main__':
    main()
