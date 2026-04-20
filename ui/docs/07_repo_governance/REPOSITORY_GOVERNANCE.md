---
category: governance
authority: canonical
audience: maintainers, reviewers
owner: repository
status: active
---

# Repository Governance

## Scope
Repository gate policy, required checks, and structural hygiene expectations.

## Required checks
The following job names are the canonical required checks for protected-branch configuration:

- `hygiene`
- `mainline-verification`
- `canonical-import-gate`
- `protocol-sync-gate`
- `runtime-core-gate`
- `evidence-gate`
- `mock-e2e`

## Structural rules
- Historical compatibility breadcrumbs, if any, must remain outside the active canonical tree and must never be treated as canonical references.
- Documentation reorganizations must preserve link stability by updating active references to canonical files; do not add new redirect stubs back into the active tree.
- Any retained historical breadcrumb must be explicitly marked non-canonical and kept out of active reading paths.
- `.github/CODEOWNERS` is the ownership declaration source.

## Mainline verification phases
`scripts/verify_mainline.sh` is the local/CI-aligned mainline gate and supports:

- `VERIFY_PHASE=python`
- `VERIFY_PHASE=mock`
- `VERIFY_PHASE=hil`
- `VERIFY_PHASE=prod`
- `VERIFY_PHASE=all`

Build directories for `mock`, `hil`, and `prod` must remain isolated. Evidence-scope wording must follow [`../05_verification/VERIFICATION_POLICY.md`](../05_verification/VERIFICATION_POLICY.md).

## Required repository-level gate family
At minimum, repository/profile gate execution must include:

- `scripts/check_repo_hygiene.sh`
- `scripts/strict_convergence_audit.py`
- `scripts/check_protocol_sync.py`
- `scripts/check_robot_identity_registry.py`
- `scripts/check_python_compile.py`
- `scripts/check_canonical_imports.py`
- `scripts/check_repository_gates.py`
- `scripts/check_architecture_fitness.py`
- `scripts/check_verification_boundary.py`


Canonical verification policy: `docs/05_verification/VERIFICATION_POLICY.md`
