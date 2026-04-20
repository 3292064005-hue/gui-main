---
category: governance
authority: canonical
audience: developers, reviewers
owner: repository
status: active
---

# Canonical Modules and Dependencies

## Scope
Canonical module registry and cross-layer dependency ownership summary.

## Canonical module registry
| Old shim / alias | Canonical path |
| --- | --- |
| `spine_ultrasound_ui.compat` | `tests.runtime_compat` |
| `spine_ultrasound_ui.core.event_bus` | `spine_ultrasound_ui.core.ui_local_bus` |
| `spine_ultrasound_ui.services.runtime_event_platform` | `spine_ultrasound_ui.services.event_bus` / `spine_ultrasound_ui.services.event_replay_bus` |
| `spine_ultrasound_ui.services.sdk_unit_contract` | `spine_ultrasound_ui.utils.sdk_unit_contract` |
| `spine_ultrasound_ui.core_pipeline.shm_client` | `spine_ultrasound_ui.services.transport.shm_client` |

## Dependency ownership rules
- Each cross-layer dependency should have one authoritative owning module.
- Runtime envelope, session freeze, and plan/runtime validation are canonical dependency boundaries.
- UI/service layers may consume canonical runtime data but must not recreate ownership locally.
- Do not reintroduce shim files or import archived aliases into current production code.
- `enable_runtime_compat()` is test-only and must come from `tests.runtime_compat`.

## Audit entrypoints
- `scripts/check_canonical_imports.py`
- `scripts/check_architecture_fitness.py`
