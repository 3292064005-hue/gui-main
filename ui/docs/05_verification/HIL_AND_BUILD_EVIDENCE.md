---
category: verification
authority: canonical
audience: release engineers, validation engineers
owner: repository
status: active
---

# HIL and Build Evidence

## Scope
Build evidence expectations, HIL checklist requirements, and runtime validation artifacts.

## Build evidence
- Build logs must identify profile, SDK/model flags, and resulting test inventory.
- Verification scripts must not hard-code stale test counts.
- Default behavior should detect vendored SDK/model support when appropriate instead of silently validating only the reduced path.

## HIL checklist
HIL / live-controller proof should include:
- host readiness
- controller and network readiness
- live binding established
- execution-path evidence
- fault/recovery evidence
- archived runtime readiness manifest
- archived RT phase metrics / controller-side artifact bundle

## Field rule
If a claim depends on authoritative kinematic or controller behavior, repository-only proof is insufficient.

## Cross references
- Evidence scope and wording: [`./VERIFICATION_POLICY.md`](./VERIFICATION_POLICY.md)
- Open gaps and unclosed proof chains: [`./CURRENT_KNOWN_GAPS.md`](./CURRENT_KNOWN_GAPS.md)
