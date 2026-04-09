from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception
from spine_ultrasound_ui.services.verdict_advisory_builder import VerdictAdvisoryBuilder
from spine_ultrasound_ui.services.verdict_authority_resolver import VerdictAuthorityResolver
from spine_ultrasound_ui.services.xmate_model_service import XMateModelService


class RuntimeVerdictKernelService:
    """Resolve the canonical runtime verdict.

    The desktop may compute an advisory application-side approximation for
    operator context, but it must not synthesize a final authoritative verdict
    when the runtime path is unavailable.
    """

    def __init__(self, advisory_model_service: XMateModelService | None = None) -> None:
        self.advisory_model_service = advisory_model_service or XMateModelService()
        self.authority_resolver = VerdictAuthorityResolver()
        self.advisory_builder = VerdictAdvisoryBuilder()

    def resolve(
        self,
        backend: Any,
        plan: ScanPlan | None,
        config: RuntimeConfig,
        *,
        refresh_runtime_verdict: bool = False,
    ) -> dict[str, Any]:
        """Resolve the runtime verdict through the canonical backend API.

        Args:
            backend: Active backend surface exposing ``resolve_final_verdict``.
            plan: Optional execution plan.
            config: Runtime configuration snapshot.
            refresh_runtime_verdict: When ``True`` the service requests a plan
                compile; otherwise it performs a read-only final-verdict query.
        """
        advisory = self.advisory_model_service.build_report(plan, config)
        runtime_verdict, runtime_error = self._query_runtime_verdict(
            backend,
            plan,
            config,
            refresh_runtime_verdict=refresh_runtime_verdict,
        )
        if runtime_verdict:
            return self.authority_resolver.normalize(runtime_verdict, advisory)
        return self.advisory_builder.build_unavailable(advisory, runtime_error=runtime_error)

    def _query_runtime_verdict(
        self,
        backend: Any,
        plan: ScanPlan | None,
        config: RuntimeConfig,
        *,
        refresh_runtime_verdict: bool,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if backend is None:
            return {}, {
                "error_type": "runtime_unavailable",
                "detail": "backend is not configured",
                "retryable": False,
            }
        resolve_method = getattr(backend, "resolve_final_verdict", None)
        if resolve_method is None:
            return {}, {
                "error_type": "runtime_unavailable",
                "detail": "backend does not expose canonical resolve_final_verdict()",
                "retryable": False,
            }
        try:
            verdict = resolve_method(plan, config, read_only=not refresh_runtime_verdict)
        except Exception as exc:
            normalized = normalize_backend_exception(
                exc,
                command="validate_scan_plan" if refresh_runtime_verdict else "query_final_verdict",
                context="runtime-verdict",
            )
            return {}, {
                "error_type": normalized.error_type,
                "detail": normalized.message,
                "retryable": normalized.retryable,
            }
        return dict(verdict or {}), None
