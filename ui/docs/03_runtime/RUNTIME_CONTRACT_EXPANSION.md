---
category: supplement
authority: canonical
audience: runtime maintainers, reviewers
owner: repository
status: active
---

# Runtime Contract Expansion

## Purpose
Track the incremental runtime-facing contract surfaces that sit on top of the runtime kernel.

## Current expanded contract families
- identity contract
- clinical mainline contract
- session freeze contract
- recovery contract
- typed runtime command request/response families

## Boundary
The execution model, phase semantics, and validation ownership live in:
- [`RUNTIME_KERNEL.md`](./RUNTIME_KERNEL.md)
- [`PLAN_VALIDATION_AND_EXECUTION.md`](./PLAN_VALIDATION_AND_EXECUTION.md)

This document only records the additional contract surfaces and generated artifacts introduced around them.
