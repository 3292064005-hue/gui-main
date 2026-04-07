from __future__ import annotations

from typing import Any


class HeadlessAdapterProductsSurface:
    """Explicit session-product surface shared by ``HeadlessAdapter``.

    The methods stay explicitly named and reviewable while allowing the main
    adapter module to remain within the repository line-budget gate.
    """

    def current_session(self) -> dict[str, Any]:
        """Return the canonical session product ``current_session``."""
        return self.session_products.current_session()

    def current_contact(self) -> dict[str, Any]:
        """Return the canonical session product ``current_contact``."""
        return self.session_products.current_contact()

    def current_recovery(self) -> dict[str, Any]:
        """Return the canonical session product ``current_recovery``."""
        return self.session_products.current_recovery()

    def current_integrity(self) -> dict[str, Any]:
        """Return the canonical session product ``current_integrity``."""
        return self.session_products.current_integrity()

    def current_lineage(self) -> dict[str, Any]:
        """Return the canonical session product ``current_lineage``."""
        return self.session_products.current_lineage()

    def current_resume_state(self) -> dict[str, Any]:
        """Return the canonical session product ``current_resume_state``."""
        return self.session_products.current_resume_state()

    def current_recovery_report(self) -> dict[str, Any]:
        """Return the canonical session product ``current_recovery_report``."""
        return self.session_products.current_recovery_report()

    def current_operator_incidents(self) -> dict[str, Any]:
        """Return the canonical session product ``current_operator_incidents``."""
        return self.session_products.current_operator_incidents()

    def current_incidents(self) -> dict[str, Any]:
        """Return the canonical session product ``current_incidents``."""
        return self.session_products.current_incidents()

    def current_resume_decision(self) -> dict[str, Any]:
        """Return the canonical session product ``current_resume_decision``."""
        return self.session_products.current_resume_decision()

    def current_event_log_index(self) -> dict[str, Any]:
        """Return the canonical session product ``current_event_log_index``."""
        return self.session_products.current_event_log_index()

    def current_recovery_timeline(self) -> dict[str, Any]:
        """Return the canonical session product ``current_recovery_timeline``."""
        return self.session_products.current_recovery_timeline()

    def current_resume_attempts(self) -> dict[str, Any]:
        """Return the canonical session product ``current_resume_attempts``."""
        return self.session_products.current_resume_attempts()

    def current_resume_outcomes(self) -> dict[str, Any]:
        """Return the canonical session product ``current_resume_outcomes``."""
        return self.session_products.current_resume_outcomes()

    def current_command_policy(self) -> dict[str, Any]:
        """Return the canonical session product ``current_command_policy``."""
        return self.session_products.current_command_policy()

    def current_contract_kernel_diff(self) -> dict[str, Any]:
        """Return the canonical session product ``current_contract_kernel_diff``."""
        return self.session_products.current_contract_kernel_diff()

    def current_command_policy_snapshot(self) -> dict[str, Any]:
        """Return the canonical session product ``current_command_policy_snapshot``."""
        return self.session_products.current_command_policy_snapshot()

    def current_event_delivery_summary(self) -> dict[str, Any]:
        """Return the canonical session product ``current_event_delivery_summary``."""
        return self.session_products.current_event_delivery_summary()

    def current_contract_consistency(self) -> dict[str, Any]:
        """Return the canonical session product ``current_contract_consistency``."""
        return self.session_products.current_contract_consistency()

    def current_selected_execution_rationale(self) -> dict[str, Any]:
        """Return the canonical session product ``current_selected_execution_rationale``."""
        return self.session_products.current_selected_execution_rationale()

    def current_release_gate_decision(self) -> dict[str, Any]:
        """Return the canonical session product ``current_release_gate_decision``."""
        return self.session_products.current_release_gate_decision()

    def current_release_evidence(self) -> dict[str, Any]:
        """Return the canonical session product ``current_release_evidence``."""
        return self.session_products.current_release_evidence()

    def current_evidence_seal(self) -> dict[str, Any]:
        """Return the canonical session product ``current_evidence_seal``."""
        return self.session_products.current_evidence_seal()

    def current_report(self) -> dict[str, Any]:
        """Return the canonical session product ``current_report``."""
        return self.session_products.current_report()

    def current_replay(self) -> dict[str, Any]:
        """Return the canonical session product ``current_replay``."""
        return self.session_products.current_replay()

    def current_quality(self) -> dict[str, Any]:
        """Return the canonical session product ``current_quality``."""
        return self.session_products.current_quality()

    def current_frame_sync(self) -> dict[str, Any]:
        """Return the canonical session product ``current_frame_sync``."""
        return self.session_products.current_frame_sync()

    def current_alarms(self) -> dict[str, Any]:
        """Return the canonical session product ``current_alarms``."""
        return self.session_products.current_alarms()

    def current_artifacts(self) -> dict[str, Any]:
        """Return the canonical session product ``current_artifacts``."""
        return self.session_products.current_artifacts()

    def current_compare(self) -> dict[str, Any]:
        """Return the canonical session product ``current_compare``."""
        return self.session_products.current_compare()

    def current_qa_pack(self) -> dict[str, Any]:
        """Return the canonical session product ``current_qa_pack``."""
        return self.session_products.current_qa_pack()

    def current_trends(self) -> dict[str, Any]:
        """Return the canonical session product ``current_trends``."""
        return self.session_products.current_trends()

    def current_diagnostics(self) -> dict[str, Any]:
        """Return the canonical session product ``current_diagnostics``."""
        return self.session_products.current_diagnostics()

    def current_annotations(self) -> dict[str, Any]:
        """Return the canonical session product ``current_annotations``."""
        return self.session_products.current_annotations()

    def current_readiness(self) -> dict[str, Any]:
        """Return the canonical session product ``current_readiness``."""
        return self.session_products.current_readiness()

    def current_profile(self) -> dict[str, Any]:
        """Return the canonical session product ``current_profile``."""
        return self.session_products.current_profile()

    def current_patient_registration(self) -> dict[str, Any]:
        """Return the canonical session product ``current_patient_registration``."""
        return self.session_products.current_patient_registration()

    def current_scan_protocol(self) -> dict[str, Any]:
        """Return the canonical session product ``current_scan_protocol``."""
        return self.session_products.current_scan_protocol()

    def current_command_trace(self) -> dict[str, Any]:
        """Return the canonical session product ``current_command_trace``."""
        return self.session_products.current_command_trace()

    def current_assessment(self) -> dict[str, Any]:
        """Return the canonical session product ``current_assessment``."""
        return self.session_products.current_assessment()
