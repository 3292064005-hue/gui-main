from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.runtime.model_bundle_contract import load_model_bundle_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_model_bundle_manifests_exist_for_runtime_models() -> None:
    manifests = list((ROOT / 'models').glob('*/bundle_manifest.json'))
    assert manifests


def test_load_model_bundle_manifest_requires_required_fields() -> None:
    manifests = list((ROOT / 'models').glob('*/bundle_manifest.json'))
    manifest = load_model_bundle_manifest(manifests[0].parent)
    assert manifest['bundle_version'] == 'v1'
    assert manifest['artifacts']['entrypoint']
