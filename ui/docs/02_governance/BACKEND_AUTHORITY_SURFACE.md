---
category: supplement
authority: canonical
audience: backend maintainers, reviewers
owner: repository
status: active
---

# Backend Authority Surface

## Purpose
Define the backend-specific read API that exposes runtime-owned truth without recreating control authority in Python/UI layers.

## Canonical backend methods
All desktop/headless backends must expose:
- `resolve_authoritative_runtime_envelope()`
- `resolve_control_authority()`
- `resolve_final_verdict(..., read_only=...)`

## Boundary
General ownership rules live in [`CONTROL_AUTHORITY_AND_BOUNDARIES.md`](./CONTROL_AUTHORITY_AND_BOUNDARIES.md). This document only describes the backend-facing surface and migration rule:
- consume canonical backend methods first
- treat nested control-plane payloads as compatibility-only
- never synthesize a stronger runtime fact from degraded projections
- on the core path, Python/headless layers may normalize `_command_context` and forward `acquire_control_lease` / `renew_control_lease` / `release_control_lease`, but they must not become the final lease owner or command arbiter

## Verification entrypoints
- `python scripts/check_backend_authority_parity.py`
- `tests/test_backend_authority_surface.py`
