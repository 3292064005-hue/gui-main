from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from spine_ultrasound_ui.services.authoritative_artifact_reader import AuthoritativeArtifactReader
from spine_ultrasound_ui.services.headless_telemetry_cache import HeadlessTelemetryCache
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_intelligence.registry import iter_product_specs
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService


class HeadlessSessionProductsReader:
    """Owns session-derived read APIs so HeadlessAdapter can stay transport-focused."""

    def __init__(
        self,
        *,
        telemetry_cache: HeadlessTelemetryCache,
        resolve_session_dir: Callable[[], Path | None],
        current_session_id: Callable[[], str],
        manifest_reader: Callable[[Path | None], dict[str, Any]],
        json_reader: Callable[[Path], dict[str, Any]],
        json_if_exists_reader: Callable[[Path], dict[str, Any]],
        jsonl_reader: Callable[[Path], list[dict[str, Any]]],
        status_reader: Callable[[], dict[str, Any]],
        derive_recovery_state: Callable[[dict[str, Any]], str],
        command_policy_catalog: Callable[[], dict[str, Any]],
        integrity_service: SessionIntegrityService,
        session_intelligence: SessionIntelligenceService,
        evidence_seal_service: SessionEvidenceSealService,
    ) -> None:
        self.telemetry_cache = telemetry_cache
        self._resolve_session_dir = resolve_session_dir
        self._current_session_id = current_session_id
        self._read_manifest_if_available = manifest_reader
        self._read_json = json_reader
        self._read_json_if_exists = json_if_exists_reader
        self._read_jsonl = jsonl_reader
        self._status = status_reader
        self._derive_recovery_state = derive_recovery_state
        self._command_policy_catalog = command_policy_catalog
        self.integrity_service = integrity_service
        self.session_intelligence = session_intelligence
        self.evidence_seal_service = evidence_seal_service
        self._artifact_reader = AuthoritativeArtifactReader()
        self._product_specs = {spec.product: spec for spec in iter_product_specs()}

    def require_session_dir(self) -> Path:
        session_dir = self._resolve_session_dir()
        if session_dir is None:
            raise FileNotFoundError('no active session')
        return session_dir

    def current_session(self) -> dict[str, Any]:
        """Return the current session product surface without read-side writes.

        Returns compatibility booleans together with registry-driven
        materialization facts for session-intelligence products.
        """
        session_dir = self.require_session_dir()
        manifest = self._read_manifest_if_available(session_dir)
        report_path = session_dir / 'export' / 'session_report.json'
        replay_path = session_dir / 'replay' / 'replay_index.json'
        qa_path = session_dir / 'export' / 'qa_pack.json'
        compare_path = session_dir / 'export' / 'session_compare.json'
        trends_path = session_dir / 'export' / 'session_trends.json'
        diagnostics_path = session_dir / 'export' / 'diagnostics_pack.json'
        assessment_snapshot = self._assessment_availability_snapshot(session_dir)
        intelligence_products = self._session_intelligence_materialization(session_dir)
        return {
            'session_id': manifest.get('session_id', self._current_session_id() or session_dir.name),
            'session_dir': str(session_dir),
            'session_started_at': manifest.get('created_at', ''),
            'artifacts': manifest.get('artifacts', {}),
            'artifact_registry': manifest.get('artifact_registry', {}),
            'report_available': report_path.exists(),
            'replay_available': replay_path.exists(),
            'qa_pack_available': qa_path.exists(),
            'compare_available': compare_path.exists(),
            'trends_available': trends_path.exists(),
            'diagnostics_available': diagnostics_path.exists(),
            'readiness_available': (session_dir / 'meta' / 'device_readiness.json').exists(),
            'profile_available': (session_dir / 'meta' / 'xmate_profile.json').exists(),
            'patient_registration_available': (session_dir / 'meta' / 'patient_registration.json').exists(),
            'scan_protocol_available': (session_dir / 'derived' / 'preview' / 'scan_protocol.json').exists(),
            'frame_sync_available': (session_dir / 'derived' / 'sync' / 'frame_sync_index.json').exists(),
            'command_trace_available': (session_dir / 'raw' / 'ui' / 'command_journal.jsonl').exists(),
            'assessment_available': bool(assessment_snapshot['assessment_available']),
            'assessment_status': str(assessment_snapshot['assessment_state']),
            'assessment_authoritative_available': bool(assessment_snapshot['authoritative_available']),
            'contact_available': True,
            'recovery_available': True,
            'integrity_available': (session_dir / 'meta' / 'manifest.json').exists(),
            'operator_incidents_available': (session_dir / 'derived' / 'alarms' / 'alarm_timeline.json').exists() or (session_dir / 'raw' / 'ui' / 'annotations.jsonl').exists(),
            'event_log_index_available': (session_dir / 'derived' / 'events' / 'event_log_index.json').exists(),
            'recovery_timeline_available': (session_dir / 'derived' / 'recovery' / 'recovery_decision_timeline.json').exists(),
            'resume_attempts_available': (session_dir / 'derived' / 'session' / 'resume_attempts.json').exists(),
            'resume_outcomes_available': (session_dir / 'derived' / 'session' / 'resume_attempt_outcomes.json').exists(),
            'command_policy_available': (session_dir / 'derived' / 'session' / 'command_state_policy.json').exists(),
            'command_policy_snapshot_available': (session_dir / 'derived' / 'session' / 'command_policy_snapshot.json').exists(),
            'contract_kernel_diff_available': (session_dir / 'derived' / 'session' / 'contract_kernel_diff.json').exists(),
            'contract_consistency_available': (session_dir / 'derived' / 'session' / 'contract_consistency.json').exists(),
            'event_delivery_summary_available': (session_dir / 'derived' / 'events' / 'event_delivery_summary.json').exists(),
            'selected_execution_rationale_available': (session_dir / 'derived' / 'planning' / 'selected_execution_rationale.json').exists(),
            'release_evidence_available': (session_dir / 'export' / 'release_evidence_pack.json').exists(),
            'release_gate_available': (session_dir / 'export' / 'release_gate_decision.json').exists(),
            'control_plane_snapshot_available': (session_dir / 'derived' / 'session' / 'control_plane_snapshot.json').exists(),
            'control_authority_snapshot_available': (session_dir / 'derived' / 'session' / 'control_authority_snapshot.json').exists(),
            'bridge_observability_report_available': (session_dir / 'derived' / 'events' / 'bridge_observability_report.json').exists(),
            'session_intelligence_manifest_available': (session_dir / 'derived' / 'session' / 'session_intelligence_manifest.json').exists(),
            'session_evidence_seal_available': (session_dir / 'meta' / 'session_evidence_seal.json').exists(),
            'evidence_seal_available': (session_dir / 'meta' / 'session_evidence_seal.json').exists(),
            'session_intelligence_products': intelligence_products,
            'materialization_contract': {
                'read_side_effects': False,
                'refresh_entrypoint': 'SessionService.refresh_session_intelligence',
                'missing_product_policy': 'report_not_materialized',
            },
            'status': self._status(),
        }

    def current_contact(self) -> dict[str, Any]:
        core = dict(self.telemetry_cache.latest_by_topic.get('core_state', {}))
        contact = dict(self.telemetry_cache.latest_by_topic.get('contact_state', {}))
        progress = dict(self.telemetry_cache.latest_by_topic.get('scan_progress', {}))
        return {
            'session_id': str(core.get('session_id', self._current_session_id())),
            'execution_state': str(core.get('execution_state', 'BOOT')),
            'contact_mode': str(contact.get('mode', 'NO_CONTACT')),
            'contact_confidence': float(contact.get('confidence', 0.0) or 0.0),
            'pressure_current': float(contact.get('pressure_current', 0.0) or 0.0),
            'recommended_action': str(contact.get('recommended_action', 'IDLE')),
            'contact_stable': bool(contact.get('contact_stable', core.get('contact_stable', False))),
            'active_segment': int(progress.get('active_segment', core.get('active_segment', 0)) or 0),
        }

    def current_recovery(self) -> dict[str, Any]:
        core = dict(self.telemetry_cache.latest_by_topic.get('core_state', {}))
        safety = dict(self.telemetry_cache.latest_by_topic.get('safety_status', {}))
        return {
            'session_id': str(core.get('session_id', self._current_session_id())),
            'execution_state': str(core.get('execution_state', 'BOOT')),
            'recovery_state': str(core.get('recovery_state', self._derive_recovery_state(core))),
            'recovery_reason': str(safety.get('recovery_reason', '')),
            'last_recovery_action': str(safety.get('last_recovery_action', '')),
            'active_interlocks': list(safety.get('active_interlocks', [])),
        }

    def current_integrity(self) -> dict[str, Any]:
        return self.integrity_service.build(self.require_session_dir())

    def current_lineage(self) -> dict[str, Any]:
        return self._read_or_build('meta/lineage.json', 'lineage')

    def current_resume_state(self) -> dict[str, Any]:
        return self._read_or_build('meta/resume_state.json', 'resume_state')

    def current_recovery_report(self) -> dict[str, Any]:
        return self._read_or_build('export/recovery_report.json', 'recovery_report')

    def current_operator_incidents(self) -> dict[str, Any]:
        return self._read_or_build('export/operator_incident_report.json', 'operator_incident_report')

    def current_incidents(self) -> dict[str, Any]:
        return self._read_or_build('derived/incidents/session_incidents.json', 'session_incidents')

    def current_resume_decision(self) -> dict[str, Any]:
        return self._read_or_build('meta/resume_decision.json', 'resume_decision')

    def current_event_log_index(self) -> dict[str, Any]:
        return self._read_or_build('derived/events/event_log_index.json', 'event_log_index')

    def current_recovery_timeline(self) -> dict[str, Any]:
        return self._read_or_build('derived/recovery/recovery_decision_timeline.json', 'recovery_decision_timeline')

    def current_resume_attempts(self) -> dict[str, Any]:
        return self._read_or_build('derived/session/resume_attempts.json', 'resume_attempts')

    def current_resume_outcomes(self) -> dict[str, Any]:
        return self._read_or_build('derived/session/resume_attempt_outcomes.json', 'resume_attempt_outcomes')

    def current_command_policy(self) -> dict[str, Any]:
        session_dir = self._resolve_session_dir()
        if session_dir is not None:
            path = session_dir / 'derived' / 'session' / 'command_state_policy.json'
            if path.exists():
                return self._read_json(path)
        return self._command_policy_catalog()

    def current_contract_kernel_diff(self) -> dict[str, Any]:
        return self._read_or_build('derived/session/contract_kernel_diff.json', 'contract_kernel_diff')

    def current_command_policy_snapshot(self) -> dict[str, Any]:
        return self._read_or_build('derived/session/command_policy_snapshot.json', 'command_policy_snapshot')

    def current_event_delivery_summary(self) -> dict[str, Any]:
        return self._read_or_build('derived/events/event_delivery_summary.json', 'event_delivery_summary')

    def current_contract_consistency(self) -> dict[str, Any]:
        return self._read_or_build('derived/session/contract_consistency.json', 'contract_consistency')

    def current_selected_execution_rationale(self) -> dict[str, Any]:
        return self._read_or_build('derived/planning/selected_execution_rationale.json', 'selected_execution_rationale')

    def current_release_gate_decision(self) -> dict[str, Any]:
        return self._read_or_build('export/release_gate_decision.json', 'release_gate_decision')

    def current_release_evidence(self) -> dict[str, Any]:
        return self._read_or_build('export/release_evidence_pack.json', 'release_evidence_pack')

    def current_evidence_seal(self) -> dict[str, Any]:
        return self._read_or_build('meta/session_evidence_seal.json', 'session_evidence_seal')

    def current_report(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'export' / 'session_report.json')

    def current_replay(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'replay' / 'replay_index.json')

    def current_quality(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'derived' / 'quality' / 'quality_timeline.json')

    def current_frame_sync(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'derived' / 'sync' / 'frame_sync_index.json')

    def current_alarms(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'derived' / 'alarms' / 'alarm_timeline.json')

    def current_artifacts(self) -> dict[str, Any]:
        session_dir = self.require_session_dir()
        manifest = self._read_manifest_if_available(session_dir)
        return {
            'session_id': manifest.get('session_id', session_dir.name),
            'artifacts': manifest.get('artifacts', {}),
            'artifact_registry': manifest.get('artifact_registry', {}),
            'processing_steps': manifest.get('processing_steps', []),
            'algorithm_registry': manifest.get('algorithm_registry', {}),
            'warnings': manifest.get('warnings', []),
        }

    def current_compare(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'export' / 'session_compare.json')

    def current_qa_pack(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'export' / 'qa_pack.json')

    def current_trends(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'export' / 'session_trends.json')

    def current_diagnostics(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'export' / 'diagnostics_pack.json')

    def current_annotations(self) -> dict[str, Any]:
        session_dir = self.require_session_dir()
        return {
            'session_id': self._read_manifest_if_available(session_dir).get('session_id', session_dir.name),
            'annotations': [entry.get('data', {}) for entry in self._read_jsonl(session_dir / 'raw' / 'ui' / 'annotations.jsonl')],
        }

    def current_readiness(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'meta' / 'device_readiness.json')

    def current_profile(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'meta' / 'xmate_profile.json')

    def current_patient_registration(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'meta' / 'patient_registration.json')

    def current_scan_protocol(self) -> dict[str, Any]:
        return self._read_json(self.require_session_dir() / 'derived' / 'preview' / 'scan_protocol.json')

    def current_command_trace(self) -> dict[str, Any]:
        session_dir = self.require_session_dir()
        manifest = self._read_manifest_if_available(session_dir)
        rows = [entry.get('data', {}) for entry in self._read_jsonl(session_dir / 'raw' / 'ui' / 'command_journal.jsonl')]
        return {
            'session_id': manifest.get('session_id', session_dir.name),
            'entries': rows,
            'summary': {
                'count': len(rows),
                'failed': sum(1 for row in rows if not bool(dict(row.get('reply', {})).get('ok', True))),
                'latest_command': rows[-1].get('command', '') if rows else '',
            },
        }

    def current_assessment(self) -> dict[str, Any]:
        """Return the assessment surface without synthesizing missing artifacts."""
        session_dir = self.require_session_dir()
        manifest = self._read_manifest_if_available(session_dir)
        report = self._read_json_if_exists(session_dir / 'export' / 'session_report.json')
        frame_sync = self._read_json_if_exists(session_dir / 'derived' / 'sync' / 'frame_sync_index.json')
        annotations = [entry.get('data', {}) for entry in self._read_jsonl(session_dir / 'raw' / 'ui' / 'annotations.jsonl')]
        authoritative = self._load_assessment_artifacts(session_dir)
        measurement = authoritative['measurement']
        summary_payload = authoritative['summary']
        effective_source_path = str(authoritative.get('measurement_source_path', 'derived/assessment/cobb_measurement.json'))
        effective_status = str(authoritative.get('effective_status', 'authoritative'))
        if measurement or summary_payload:
            confidence = float(summary_payload.get('confidence', measurement.get('confidence', 0.0)) or 0.0)
            manual_review = bool(summary_payload.get('requires_manual_review', measurement.get('requires_manual_review', False))) or len(annotations) > 0
            evidence_frames = [dict(item) for item in measurement.get('evidence_refs', []) if isinstance(item, dict)]
            landmark_track = self._read_json_if_exists(session_dir / 'derived' / 'reconstruction' / 'landmark_track.json')
            landmark_candidates = [dict(item) for item in landmark_track.get('landmarks', []) if isinstance(item, dict)]
            uca = self._read_json_if_exists(session_dir / 'derived' / 'assessment' / 'uca_measurement.json')
            agreement = self._read_json_if_exists(session_dir / 'derived' / 'assessment' / 'assessment_agreement.json')
            contamination_flags = sorted({str(item) for item in list(summary_payload.get('source_contamination_flags', measurement.get('source_contamination_flags', []))) if str(item)})
            curve_status = effective_status or 'authoritative'
            curve_source = effective_source_path or 'derived/assessment/cobb_measurement.json'
            assessment_state = self._assessment_state_from_effective_status(curve_status)
            return {
                'session_id': manifest.get('session_id', session_dir.name),
                'robot_model': manifest.get('robot_profile', {}).get('robot_model', ''),
                'summary': {
                    'avg_quality_score': float(report.get('quality_summary', {}).get('avg_quality_score', 0.0) or 0.0),
                    'usable_sync_ratio': float(report.get('quality_summary', {}).get('usable_sync_ratio', frame_sync.get('summary', {}).get('usable_ratio', 0.0) or 0.0)),
                    'annotation_count': len(annotations),
                    'confidence': confidence,
                },
                'curve_candidate': {
                    'status': curve_status,
                    'source': curve_source,
                    'description': 'Authoritative lamina-center Cobb assessment generated from reconstruction and session evidence artifacts.' if curve_status == 'authoritative' else 'Prior-assisted, blocked, or degraded Cobb assessment resolved from explicit closure-verdict metadata.',
                    'measurement_source': str(summary_payload.get('measurement_source', measurement.get('measurement_source', 'curve_window_fallback')) or 'curve_window_fallback'),
                },
                'cobb_candidate_deg': measurement.get('angle_deg'),
                'uca_candidate_deg': uca.get('angle_deg'),
                'agreement': agreement,
                'confidence': confidence,
                'requires_manual_review': manual_review,
                'landmark_candidates': landmark_candidates,
                'evidence_frames': evidence_frames,
                'open_issues': list(report.get('open_issues', [])),
                'assessment_state': assessment_state,
                'materialization_state': 'materialized',
                'authoritative_available': True,
                'legacy_fallback_used': False,
                'is_authoritative': curve_status == 'authoritative',
                'source_contamination_flags': contamination_flags,
            }
        has_legacy_inputs = bool(report) or bool(frame_sync) or bool(annotations) or bool(self._read_json_if_exists(session_dir / 'export' / 'qa_pack.json'))
        if has_legacy_inputs:
            return self._legacy_assessment_payload(session_dir, manifest, report, frame_sync, annotations)
        return self._missing_assessment_payload(session_dir, manifest)

    def _load_assessment_artifacts(self, session_dir: Path) -> dict[str, dict[str, Any]]:
        """Load authoritative assessment artifacts when available.

        Args:
            session_dir: Locked session directory.

        Returns:
            Dictionary containing ``measurement`` and ``summary`` payloads. When
            an artifact is absent, the corresponding value is an empty dict.

        Raises:
            No exceptions are raised.
        """
        measurement_resolution = self._artifact_reader.read_cobb_measurement(session_dir)
        return {
            'measurement': dict(measurement_resolution.get('effective_payload', {})),
            'measurement_source_path': str(measurement_resolution.get('effective_source_path', 'derived/assessment/cobb_measurement.json')),
            'effective_status': str(measurement_resolution.get('effective_status', 'authoritative')),
            'summary': dict(measurement_resolution.get('summary', {})),
            'prior_assisted_cobb': dict(measurement_resolution.get('sidecar', {})),
        }

    def _legacy_assessment_payload(
        self,
        session_dir: Path,
        manifest: dict[str, Any],
        report: dict[str, Any],
        frame_sync: dict[str, Any],
        annotations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build the historical assessment response for legacy sessions.

        Args:
            session_dir: Locked session directory.
            manifest: Session manifest payload.
            report: Session report payload.
            frame_sync: Frame-sync index payload.
            annotations: Session annotations extracted from JSONL.

        Returns:
            Backward-compatible assessment response synthesized from legacy
            session products.

        Raises:
            No exceptions are raised.
        """
        qa_pack = self._read_json_if_exists(session_dir / 'export' / 'qa_pack.json')
        quality_summary = dict(report.get('quality_summary', {}))
        usable_ratio = float(quality_summary.get('usable_sync_ratio', frame_sync.get('summary', {}).get('usable_ratio', 0.0) or 0.0))
        avg_quality = float(quality_summary.get('avg_quality_score', 0.0) or 0.0)
        confidence = round(min(1.0, max(0.0, (avg_quality * 0.65) + (usable_ratio * 0.35))), 4)
        manual_review = confidence < 0.82 or len(annotations) > 0
        evidence_frames: list[dict[str, Any]] = []
        for row in frame_sync.get('rows', []):
            if not bool(row.get('usable', True)):
                continue
            evidence_frames.append({
                'frame_id': row.get('frame_id', row.get('seq', len(evidence_frames))),
                'segment_id': row.get('segment_id', 0),
                'ts_ns': row.get('ts_ns', 0),
                'quality_score': row.get('quality_score', row.get('image_quality', 0.0)),
                'contact_confidence': row.get('contact_confidence', 0.0),
            })
            if len(evidence_frames) >= 8:
                break
        landmark_candidates = [
            annotation
            for annotation in annotations
            if str(annotation.get('kind', '')).lower() in {'landmark_hint', 'anatomy_marker', 'manual_review_note'}
        ][:10]
        open_issues = list(report.get('open_issues', []))
        return {
            'session_id': manifest.get('session_id', session_dir.name),
            'robot_model': manifest.get('robot_profile', {}).get('robot_model', ''),
            'summary': {
                'avg_quality_score': avg_quality,
                'usable_sync_ratio': usable_ratio,
                'annotation_count': len(annotations),
                'confidence': confidence,
            },
            'curve_candidate': {
                'status': 'legacy_fallback_only',
                'source': 'session_report',
                'description': 'Legacy session without authoritative assessment artifacts; synthesized QA evidence is returned for backward compatibility only.',
            },
            'cobb_candidate_deg': qa_pack.get('assessment', {}).get('cobb_candidate_deg') if isinstance(qa_pack.get('assessment'), dict) else None,
            'confidence': confidence,
            'requires_manual_review': manual_review,
            'landmark_candidates': landmark_candidates,
            'evidence_frames': evidence_frames,
            'open_issues': open_issues,
            'assessment_state': 'legacy_fallback_only',
            'materialization_state': 'legacy_fallback_only',
            'authoritative_available': False,
            'legacy_fallback_used': True,
            'is_authoritative': False,
            'source_contamination_flags': [],
        }

    def _missing_assessment_payload(self, session_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        return {
            'session_id': manifest.get('session_id', session_dir.name),
            'robot_model': manifest.get('robot_profile', {}).get('robot_model', ''),
            'summary': {
                'avg_quality_score': 0.0,
                'usable_sync_ratio': 0.0,
                'annotation_count': 0,
                'confidence': 0.0,
            },
            'curve_candidate': {
                'status': 'missing',
                'source': '',
                'description': 'Assessment artifacts have not been materialized. Refresh session intelligence or rerun postprocess stages before reading assessment outputs.',
            },
            'cobb_candidate_deg': None,
            'uca_candidate_deg': None,
            'agreement': {},
            'confidence': 0.0,
            'requires_manual_review': True,
            'landmark_candidates': [],
            'evidence_frames': [],
            'open_issues': ['assessment_not_materialized'],
            'assessment_state': 'missing',
            'materialization_state': 'not_materialized',
            'authoritative_available': False,
            'legacy_fallback_used': False,
            'is_authoritative': False,
            'source_contamination_flags': [],
        }

    def _session_intelligence_materialization(self, session_dir: Path) -> list[dict[str, Any]]:
        return [self._materialization_fact(session_dir, spec.product) for spec in self._product_specs.values()]

    def _assessment_availability_snapshot(self, session_dir: Path) -> dict[str, Any]:
        resolution = self._artifact_reader.read_cobb_measurement(session_dir)
        has_authoritative_surface = bool(resolution.get('effective_payload')) or bool(resolution.get('summary'))
        if has_authoritative_surface:
            status = self._assessment_state_from_effective_status(str(resolution.get('effective_status', 'authoritative')))
            return {
                'assessment_available': True,
                'authoritative_available': True,
                'assessment_state': status,
            }
        if (session_dir / 'export' / 'session_report.json').exists() and (session_dir / 'derived' / 'sync' / 'frame_sync_index.json').exists():
            return {
                'assessment_available': False,
                'authoritative_available': False,
                'assessment_state': 'legacy_fallback_only',
            }
        return {
            'assessment_available': False,
            'authoritative_available': False,
            'assessment_state': 'missing',
        }

    @staticmethod
    def _assessment_state_from_effective_status(effective_status: str) -> str:
        mapping = {
            'authoritative': 'authoritative_ready',
            'prior_assisted': 'prior_assisted_ready',
            'blocked': 'blocked_ready',
            'degraded': 'degraded_ready',
        }
        return mapping.get(str(effective_status or 'authoritative'), 'authoritative_ready')

    def _materialization_fact(self, session_dir: Path, product_name: str) -> dict[str, Any]:
        spec = self._product_specs.get(product_name)
        if spec is None:
            return {
                'product': product_name,
                'output_artifact': '',
                'materialization_phase': 'unknown',
                'read_policy': 'unknown',
                'stale_policy': 'unknown',
                'materialization_state': 'unknown',
                'artifact_exists': False,
            }
        artifact_path = session_dir.joinpath(*spec.output_artifact.split('/'))
        return {
            'product': spec.product,
            'output_artifact': spec.output_artifact,
            'owner_domain': spec.owner_domain,
            'performance_budget_ms': spec.performance_budget_ms,
            'materialization_phase': spec.materialization_phase,
            'read_policy': spec.read_policy,
            'stale_policy': spec.stale_policy,
            'materialization_state': 'materialized' if artifact_path.exists() else 'not_materialized',
            'artifact_exists': artifact_path.exists(),
        }

    def _read_or_build(self, relative_path: str, intelligence_key: str) -> dict[str, Any]:
        session_dir = self.require_session_dir()
        path = session_dir.joinpath(*relative_path.split('/'))
        if path.exists():
            payload = self._read_json(path)
            result = dict(payload)
            spec = self._product_specs.get(intelligence_key)
            result.setdefault('session_id', self._read_manifest_if_available(session_dir).get('session_id', session_dir.name))
            result.setdefault('product', intelligence_key)
            result.setdefault('output_artifact', relative_path)
            if spec is not None:
                result.setdefault('owner_domain', spec.owner_domain)
                result.setdefault('performance_budget_ms', spec.performance_budget_ms)
                result.setdefault('materialization_phase', spec.materialization_phase)
                result.setdefault('read_policy', spec.read_policy)
                result.setdefault('stale_policy', spec.stale_policy)
            result['materialization_state'] = 'materialized'
            result['artifact_exists'] = True
            return result
        spec = self._product_specs.get(intelligence_key)
        response = {
            'session_id': self._read_manifest_if_available(session_dir).get('session_id', session_dir.name),
            'product': intelligence_key,
            'output_artifact': relative_path,
            'artifact_exists': False,
            'materialization_state': 'not_materialized',
            'detail': 'Artifact has not been materialized by the session-finalize pipeline.',
        }
        if spec is not None:
            response.update({
                'owner_domain': spec.owner_domain,
                'performance_budget_ms': spec.performance_budget_ms,
                'materialization_phase': spec.materialization_phase,
                'read_policy': spec.read_policy,
                'stale_policy': spec.stale_policy,
            })
        return response
