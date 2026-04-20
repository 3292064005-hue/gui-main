---
category: spec
authority: canonical
audience: release engineers, operators, reviewers
owner: repository
status: active
---

# Profile Matrix

## Purpose
Define runtime profiles, allowed backends, robot-family constraints, and expected authority/evidence levels.

## Profile classes
- `dev`
- `lab`
- `research`
- `clinical`
- `review`

## Profile rules
- headless review may use `mock` **only** for read-only evidence / replay / contract inspection flows
- Profiles that require live SDK/controller truth must not silently degrade writes into mock or contract-only surfaces.
- Mock-only profiles may prove repository behavior but not live motion truth.
- Review profiles may expose replay/evidence inspection without gaining execution authority.
- Release claims must cite the exact evidence tier used by the profile, not a stronger tier.

## xmate3_cobot_6
- sdk class: `xMateRobot`
- robot model: `xmate3`
- axis count: `6`
- controller series: `xCore`
- realtime mainline: `cartesianImpedance`
- supports xMateModel: `yes`
- supports planner: `yes`
- supports drag/path replay: `yes`
- single control source: `required`
- preferred link: `wired_direct`
- headless review backend: `core` by default; `mock` allowed only for read-only evidence / replay / contract inspection

## Rejected families
The following families are intentionally outside the runtime mainline and must be rejected by configuration / identity resolution:

- `xMateErProRobot`
- `StandardRobot`
- `PCB4Robot`
- `PCB3Robot`
- any `axis_count != 6`

## Cross references
- Runtime/profile authority rules: [`../02_governance/CONTROL_AUTHORITY_AND_BOUNDARIES.md`](../02_governance/CONTROL_AUTHORITY_AND_BOUNDARIES.md)
- Release gate expectations: [`./RELEASE_READINESS.md`](./RELEASE_READINESS.md)


> Canonical path: `docs/04_profiles_and_release/PROFILE_MATRIX.md`
