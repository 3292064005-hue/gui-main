---
category: policy
authority: canonical
audience: maintainers, reviewers, auditors
owner: repository
status: active
---

# Document Authority Policy

## Purpose
Define how repository documents are classified, which files are authoritative, and how superseded material is retained.

## Required metadata
Canonical documents should declare:
- category: `index | policy | spec | runbook | verification | governance | historical`
- authority: `canonical | informative | historical`
- audience
- owner
- status
- `last_verified_against`, when applicable

## Authority levels
- **Canonical**: current repository source of truth.
- **Informative**: supporting explanation that must not override canonical files.
- **Historical**: preserved for audit history only.

## Lifecycle rules
- New rules go into a canonical document, not a phase checklist.
- Active documentation is kept in the layered tree rooted at `docs/00_START_HERE.md`.
- Superseded, phase, and audit material is retained as packaged history under `docs/90_archive/README.md` instead of redirect stubs spread through the active tree.
- README and `docs/00_START_HERE.md` may only point to canonical files or the single historical package index.

## Cross-reference rules
- Canonical files may reference historical material only as evidence, never as controlling specifications.
- Root-level repository docs must remain entrypoint-oriented; architecture, deployment, and verification detail belongs inside the canonical layered tree.
