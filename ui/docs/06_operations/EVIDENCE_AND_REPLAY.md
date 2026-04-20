---
category: runbook
authority: canonical
audience: operators, reviewers, auditors
owner: repository
status: active
---

# Evidence and Replay

## Scope
Authoritative artifact schema, replay schema, and interpretation policy.

## Rules
- Evidence artifacts must declare provenance and authority class.
- Fixture data, repository snapshots, and live-captured artifacts must not be conflated.
- Replay indexes must preserve enough source linkage to distinguish execution truth from derived summaries.
