from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.core.postprocess.stage_registry import iter_stage_specs
from spine_ultrasound_ui.services.session_intelligence.registry import iter_product_specs


def test_postprocess_stage_registry_is_ordered_and_budgeted() -> None:
    specs = iter_stage_specs()
    assert [spec.stage for spec in specs] == ['preprocess', 'reconstruction', 'assessment']
    assert all(spec.performance_budget_ms > 0 for spec in specs)
    assert all(spec.output_artifacts for spec in specs)


def test_session_intelligence_registry_has_release_and_governance_products() -> None:
    specs = iter_product_specs()
    names = {spec.product for spec in specs}
    assert 'release_gate_decision' in names
    assert 'contract_kernel_diff' in names
    assert 'session_evidence_seal' in names
    assert all(spec.performance_budget_ms > 0 for spec in specs)


def test_stage_manifest_schema_and_artifact_hints_exist() -> None:
    schema = json.loads(Path('schemas/session/postprocess_stage_manifest_v1.schema.json').read_text(encoding='utf-8'))
    intel_schema = json.loads(Path('schemas/session/session_intelligence_manifest_v1.schema.json').read_text(encoding='utf-8'))
    assert schema['title'] == 'Postprocess stage manifest v1'
    assert intel_schema['title'] == 'Session intelligence manifest v1'


def test_finalize_and_postprocess_services_materialize_manifest_artifacts() -> None:
    finalize_source = Path('spine_ultrasound_ui/core/session_finalize_service.py').read_text(encoding='utf-8')
    postprocess_source = Path('spine_ultrasound_ui/core/postprocess_service.py').read_text(encoding='utf-8')
    assert 'derived/session/session_intelligence_manifest.json' in finalize_source
    assert 'derived/postprocess/postprocess_stage_manifest.json' in postprocess_source


def test_session_intelligence_registry_declares_materialization_and_read_policy() -> None:
    specs = iter_product_specs()
    assert all(spec.materialization_phase for spec in specs)
    assert all(spec.read_policy == "materialized_only" for spec in specs)
    assert all(spec.stale_policy for spec in specs)
