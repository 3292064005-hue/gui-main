#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import os
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.core.artifact_lifecycle_registry import iter_artifact_lifecycle_specs
from spine_ultrasound_ui.core.artifact_schema_registry import schema_for_artifact

_SCANNED_SUFFIXES = {'.py', '.json', '.yaml', '.yml', '.md'}
_EXCLUDED_PARTS = {'archive', '.git', '.pytest_cache', '__pycache__'}
_EXCLUDED_FILES = {
    ROOT / 'spine_ultrasound_ui' / 'core' / 'artifact_lifecycle_registry.py',
    Path(__file__).resolve(),
}


def _resolved_excluded_files() -> set[Path]:
    return {item.resolve() for item in _EXCLUDED_FILES}


def _iter_scan_files() -> list[Path]:
    roots = [ROOT / 'spine_ultrasound_ui', ROOT / 'scripts']
    files: list[Path] = []
    excluded_files = _resolved_excluded_files()
    for base in roots:
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [name for name in dirnames if name not in _EXCLUDED_PARTS]
            for filename in filenames:
                path = Path(dirpath) / filename
                if path.suffix.lower() not in _SCANNED_SUFFIXES:
                    continue
                if path.stat().st_size > 1_000_000:
                    continue
                if path.resolve() in excluded_files:
                    continue
                files.append(path)
    return files


def _read_corpus(files: list[Path]) -> list[tuple[Path, str]]:
    corpus: list[tuple[Path, str]] = []
    for path in files:
        try:
            corpus.append((path, path.read_text(encoding='utf-8')))
        except UnicodeDecodeError:
            continue
    return corpus


def _symbol_hits(symbols: tuple[str, ...], corpus: list[tuple[Path, str]]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for symbol in symbols:
        cleaned = str(symbol or '').strip()
        if not cleaned:
            continue
        hits[cleaned] = [str(path.relative_to(ROOT)) for path, text in corpus if cleaned in text]
    return hits


def main() -> int:
    specs = list(iter_artifact_lifecycle_specs())
    if not specs:
        print('artifact lifecycle registry is empty', file=sys.stderr)
        return 1
    files = _iter_scan_files()
    corpus = _read_corpus(files)
    seen: set[str] = set()
    required_formal_chain_artifacts = {
        'dataset_export_manifest',
        'lamina_center_dataset_case',
        'uca_dataset_case',
        'training_bridge_model_ready_input_index',
        'nnunet_conversion_manifest',
        'training_backend_request',
        'training_model_package',
        'session_report',
        'qa_pack',
        'release_evidence_pack',
    }
    formal_chain_scopes = {'dataset_export', 'training', 'export'}
    errors: list[str] = []
    producer_hit_summary: dict[str, dict[str, int]] = {}
    consumer_hit_summary: dict[str, dict[str, int]] = {}
    for spec in specs:
        if spec.artifact_name in seen:
            errors.append(f'duplicate artifact lifecycle entry: {spec.artifact_name}')
        seen.add(spec.artifact_name)
        if not spec.producer:
            errors.append(f'artifact lifecycle entry missing producer: {spec.artifact_name}')
        if not spec.consumers:
            errors.append(f'artifact lifecycle entry missing consumers: {spec.artifact_name}')
        if not spec.source_stage:
            errors.append(f'artifact lifecycle entry missing source_stage: {spec.artifact_name}')
        if not spec.retention_tier:
            errors.append(f'artifact lifecycle entry missing retention_tier: {spec.artifact_name}')
        if schema_for_artifact(spec.artifact_name) == '':
            errors.append(f'artifact lifecycle entry missing schema hint: {spec.artifact_name}')
        evidence_scope = str(getattr(spec, 'evidence_chain_scope', '') or '').strip()
        if not evidence_scope:
            errors.append(f'artifact lifecycle entry missing evidence_chain_scope: {spec.artifact_name}')
        if spec.artifact_name in required_formal_chain_artifacts and evidence_scope not in formal_chain_scopes:
            errors.append(f'formal dataset/export/training artifact has wrong evidence_chain_scope: {spec.artifact_name}={evidence_scope}')
        if evidence_scope in formal_chain_scopes and not spec.required_for_release:
            errors.append(f'formal evidence-chain artifact must be required_for_release: {spec.artifact_name}')
        if evidence_scope in formal_chain_scopes and 'placeholder' in str(spec.materialization_policy).lower():
            errors.append(f'formal evidence-chain artifact must not use placeholder materialization policy: {spec.artifact_name}={spec.materialization_policy}')
        required_consumers = tuple(item for item in spec.consumers if str(item).strip())
        if len(required_consumers) != len(set(required_consumers)):
            errors.append(f'artifact lifecycle entry has duplicate consumers: {spec.artifact_name}')
        if not spec.producer_symbols:
            errors.append(f'artifact lifecycle entry missing producer_symbols: {spec.artifact_name}')
        if not spec.consumer_symbols:
            errors.append(f'artifact lifecycle entry missing consumer_symbols: {spec.artifact_name}')
        producer_hits = _symbol_hits(spec.producer_symbols, corpus)
        consumer_hits = _symbol_hits(spec.consumer_symbols, corpus)
        producer_hit_summary[spec.artifact_name] = {symbol: len(paths) for symbol, paths in producer_hits.items()}
        consumer_hit_summary[spec.artifact_name] = {symbol: len(paths) for symbol, paths in consumer_hits.items()}
        if spec.producer_symbols and not any(producer_hits.values()):
            errors.append(f'artifact lifecycle producer has no code/test call-site evidence: {spec.artifact_name}')
        if spec.consumer_symbols and not any(consumer_hits.values()):
            errors.append(f'artifact lifecycle consumer has no code/test call-site evidence: {spec.artifact_name}')
    missing_formal = sorted(required_formal_chain_artifacts - seen)
    if missing_formal:
        errors.append(f'missing formal dataset/export/training lifecycle artifacts: {missing_formal}')
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1
    print(f'artifact lifecycle registry ok: {len(specs)} artifacts, {len(files)} scanned files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
