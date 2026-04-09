from __future__ import annotations

"""Guidance/localization freeze bundle normalization helpers."""

from typing import Any, Callable

from spine_ultrasound_ui.services.planning.types import LocalizationResult


class SessionGuidanceBundleService:
    """Build canonical guidance-freeze artifacts for ``SessionService``.

    This service keeps guidance/localization bundle synthesis out of the public
    ``SessionService`` façade so freeze-specific artifact derivation can evolve
    without growing the compatibility surface.
    """

    @staticmethod
    def coalesce(
        *,
        registration_payload: dict[str, Any],
        localization_result: LocalizationResult | None,
        hash_payload: Callable[[dict[str, Any]], str],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        """Normalize guidance freeze artifacts for canonical freeze paths.

        Args:
            registration_payload: Registration snapshot already selected for
                session freeze.
            localization_result: Structured localization result produced by the
                canonical localization pipeline.
            hash_payload: Canonical hashing function used by ``SessionService``.

        Returns:
            Tuple of ``(localization_readiness, calibration_bundle,
            manual_adjustment, source_frame_set, localization_replay_index,
            guidance_algorithm_registry, guidance_processing_steps)`` ready for
            ``SessionLockService``.

        Raises:
            RuntimeError: Raised when session freeze attempts to proceed without
                canonical localization evidence.
            ValueError: Propagated when supplied payloads cannot be serialized by
                the supplied hashing function.

        Boundary behavior:
            - Canonical localization results pass through unchanged.
            - Session freeze without canonical localization evidence fails fast
              so no compatibility path can synthesize non-authoritative
              guidance artifacts.
        """
        if localization_result is not None:
            return (
                dict(localization_result.localization_readiness),
                dict(localization_result.calibration_bundle),
                dict(localization_result.manual_adjustment),
                dict(localization_result.source_frame_set),
                dict(localization_result.localization_replay_index),
                dict(localization_result.guidance_algorithm_registry),
                list(localization_result.guidance_processing_steps),
            )

        raise RuntimeError(
            'session freeze requires canonical localization_result; '
            'compatibility synthesis without authoritative localization artifacts is no longer supported'
        )
