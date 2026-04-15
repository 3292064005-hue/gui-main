# Backend Authority Surface

## Scope

This document records the canonical authority/query surface introduced to close the last Python-side gaps around control-authority, final-verdict, and authoritative runtime envelope reads.

## Canonical read API

All desktop backends must expose the following methods:

- `resolve_authoritative_runtime_envelope()`
- `resolve_control_authority()`
- `resolve_final_verdict(..., read_only=...)`

These methods are implemented by:

- `BackendBase`
- `ApiBridgeBackend`
- `RobotCoreClientBackend`
- `MockBackend`
- `HeadlessAdapter` (server-side API/runtime surface)

## Ownership rules

### Runtime-owned facts

Only the runtime/core side is allowed to authoritatively publish:

- `control_authority`
- `final_verdict`
- `runtime_config_applied`
- `session_freeze`
- `plan_digest`
- `write_capabilities`

Python/UI layers may:

- cache
- project
- render
- enrich with operator-facing detail

Python/UI layers may **not** synthesize a stronger fact than the runtime actually returned.

## Route contract

The FastAPI system router now exposes direct read endpoints:

- `GET /api/v1/control-authority`
- `GET /api/v1/authoritative-runtime-envelope`
- `GET /api/v1/final-verdict`

The router must prefer canonical backend methods over legacy summary surfaces. When a backend already exposes the canonical methods, the router must return explicit unavailable/degraded payloads rather than falling back to synthesized control-plane summaries.

## Link snapshot contract

Backend link snapshots now surface these top-level fields in addition to the historical nested control-plane payload:

- `authoritative_runtime_envelope`
- `control_authority`
- `final_verdict`

This keeps read consumers from scraping nested control-plane payloads when a canonical runtime-owned surface already exists.

## Migration guidance

### Old pattern

Read consumers previously pulled authority/verdict data from one of:

- `backend_link.control_plane.*`
- local backend caches
- synthesized control-plane projections

### New pattern

Use the canonical read API first:

1. `resolve_authoritative_runtime_envelope()`
2. `resolve_control_authority()`
3. `resolve_final_verdict(..., read_only=True)`

Nested control-plane reads are now compatibility-only fallbacks for adapters that do not yet implement the canonical surface. Canonical backend methods themselves must not synthesize stronger authority/envelope/verdict facts from control-plane caches.

## Rollback strategy

If a regression is found:

1. Keep the new canonical methods in place.
2. Temporarily re-enable a compatibility read fallback in the specific consumer.
3. Do **not** remove the new authority surface or restore multi-source re-interpretation.
4. Fix the producer/adapter normalization gap and then remove the temporary fallback.

## Verification

Static/repository gates:

- `check_backend_authority_parity.py` now exercises real backend objects (base/api/core/mock/headless) and verifies that canonical authority reads do not fabricate runtime-owned facts on failure.

- `python scripts/check_backend_authority_parity.py`
- `python scripts/check_protocol_sync.py`
- `python scripts/check_architecture_fitness.py`

Targeted tests:

- `tests/test_backend_authority_surface.py`
- `tests/test_api_system_authority_routes.py`
- `tests/test_api_bridge_verdict_service.py`
- `tests/test_backend_link_and_api_bridge.py`


## Backend link snapshot boundary

`backend_link` now exposes two distinct layers:

- canonical top-level fields: `authoritative_runtime_envelope`, `control_authority`, `final_verdict`
- compatibility/projection fields: `control_plane`, `projected_control_authority`, `projected_final_verdict`

Rules:

1. Top-level `control_authority` and `final_verdict` are **authoritative-only** and must be empty when no runtime-published authoritative envelope exists.
2. `control_plane` and `projected_*` fields may remain populated for degraded/operator rendering, but they are not canonical runtime truth.
3. Consumers that need runtime-owned truth must read the canonical top-level fields or the explicit backend methods below, never `control_plane` fallbacks.
