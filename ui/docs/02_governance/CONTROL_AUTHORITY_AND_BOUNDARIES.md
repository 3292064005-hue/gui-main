---
category: policy
authority: canonical
audience: developers, reviewers, auditors
owner: repository
status: active
---

# Control Authority and Boundaries

## Purpose
Unify repository boundary rules, freeze rules, and SDK-usage constraints in one governing document.

## Canonical rules
- Real robot SDK control belongs to `cpp_robot_core` only.
- Runtime write-control authority and lease ownership belong to `cpp_robot_core` only.
- Python/UI may project runtime-owned authority and forward lease requests, but must not fabricate parallel execution authority or final write-command verdicts.
- Session freeze turns advisory inputs into immutable runtime inputs.
- Compatibility aliases must never become the only documented entry after a canonical command exists.

## Freeze policy
- Guidance and planning remain advisory before session lock.
- At session lock, the project must freeze the execution-relevant artifact set, including runtime config snapshot, plan digest, and required provenance.
- Post-freeze changes require explicit re-validation and a new freeze revision.

## Mock / contract / live truth
- Mock proof: repository and UI behavior only.
- Contract-shell proof: transport and interface shape only.
- Live binding proof: robot-core bound to actual SDK/controller.
- HIL/live proof: controller-side behavior validated under real runtime conditions.

## Deprecated alias policy
- `start_procedure` is canonical.
- `start_scan` is compatibility-only.
- UI façade or documentation may retain user-facing language, but canonical contract references must point to `start_procedure`.


## Lease boundary
- Canonical control-lease mutations are `acquire_control_lease`, `renew_control_lease`, and `release_control_lease`.
- API bridge and headless surfaces may proxy all three lease lifecycle commands, but the resulting `control_authority` snapshot must still come from runtime-published state.
- Typed runtime command contracts for write and plan-compile paths explicitly expose optional `_command_context` so authority metadata is part of the canonical contract surface instead of an undocumented side-channel.
- The core path may auto-issue an implicit lease only inside `cpp_robot_core` and only when deployment policy allows it.
- Any Python-side guard may block on deployment/profile/runtime capability policy, but it must not replace the runtime as the final write authority.
