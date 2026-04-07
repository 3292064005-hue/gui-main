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

    def resolve(self, backend: Any, plan: ScanPlan | None, config: RuntimeConfig) -> dict[str, Any]:
        advisory = self.advisory_model_service.build_report(plan, config)
        runtime_verdict, runtime_error = self._query_runtime_verdict(backend, plan, config)
        if runtime_verdict:
            return self.authority_resolver.normalize(runtime_verdict, advisory)
        return self.advisory_builder.build_unavailable(advisory, runtime_error=runtime_error)

    def _query_runtime_verdict(self, backend: Any, plan: ScanPlan | None, config: RuntimeConfig) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if backend is None or not hasattr(backend, 'get_final_verdict'):
            return {}, {
                'error_type': 'runtime_unavailable',
                'detail': 'backend does not expose get_final_verdict',
                'retryable': False,
            }
        try:
            verdict = backend.get_final_verdict(plan, config)
        except TypeError:
            try:
                verdict = backend.get_final_verdict(plan)
            except Exception as exc:
                normalized = normalize_backend_exception(exc, command='query_final_verdict', context='runtime-verdict')
                return {}, {
                    'error_type': normalized.error_type,
                    'detail': normalized.message,
                    'retryable': normalized.retryable,
                }
        except Exception as exc:
            normalized = normalize_backend_exception(exc, command='query_final_verdict', context='runtime-verdict')
            return {}, {
                'error_type': normalized.error_type,
                'detail': normalized.message,
                'retryable': normalized.retryable,
            }
        return dict(verdict or {}), None
