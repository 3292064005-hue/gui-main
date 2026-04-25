---
category: runbook
authority: canonical
audience: release engineers, auditors
owner: repository
status: active
---

# Release Readiness

## Purpose
Define readiness expectations for deployment profiles and their repository/live evidence boundaries.

## Required evidence families
- repository gates
- profile gate logs
- runtime doctor/readiness manifest
- build evidence
- HIL/live evidence where applicable
- release ledger (`release_ledger.json`) that indexes the linked proof files

## Readiness rules
- Python-only or repository-only verification cannot be described as research/clinical proof.
- If a release claim depends on authoritative SDK/model execution, the evidence must come from a build/test path that actually enables those components.
- Rollback instructions must exist for every release profile that can issue real robot writes.

## Release package rule
- Final acceptance output must include a single `release_ledger.json` that links verification report, build evidence report, and acceptance summary, plus either a local readiness manifest or an archived live bundle that embeds the readiness manifest for that claim path.
- The release ledger is an index, not a claim amplifier; if linked evidence remains repository/sandbox-only, the ledger must preserve that boundary.
- `research` and `clinical` release ledgers are fail-closed: they must link an archived live/HIL evidence bundle validated by the verification report, or ledger generation must fail.

## Deployment baseline
### Supported profiles
- `dev`: local iteration, relaxed seal requirements, debug-oriented logging
- `lab`: controlled rehearsal / bring-up profile
- `research`: writable preclinical execution profile with strong evidence and provenance capture
- `clinical`: strict control authority, token-gated writes, strict evidence sealing
- `review`: read-only replay/review/export profile

### Operator entrypoints
- `scripts/start_mainline.py` is the single launcher contract for desktop/headless bring-up.
- wrapper launchers must not redefine backend/profile/build/model policy; they only bind named deployment profiles such as `research` or `clinical` into `scripts/start_mainline.py`. Unified launcher `auto` backend resolution ignores stale low-level surface backend env so wrapper/CLI profile intent remains authoritative.

### Primary smoke and preflight
```bash
python scripts/deployment_smoke_test.py
./scripts/check_cpp_prereqs.sh
python scripts/check_protocol_sync.py
./scripts/generate_dev_tls_cert.sh
python scripts/doctor_runtime.py
```

### Runtime dependency baseline
- `PySide6 >= 6.7`
- `protobuf>=3.20.3,<8`
- Ubuntu 22.04 real-runtime hosts additionally require `cmake`, `g++`, and `libssl-dev`.

## Repo / Live Truth Ledgers

Mainline release material now carries both `repo_truth_ledger` and `live_truth_ledger`. Repo truth is required for every build; live truth remains pending until controller/HIL evidence is attached.


Runtime-config evidence is now anchored by `schemas/runtime/runtime_config_v1.schema.json`. Every persisted runtime config snapshot carries `runtime_config_contract.digest` and `runtime_config_contract.schema_version`; release ledgers must preserve those fields without rewriting them.


`strict_runtime_freeze_gate` is operator-configurable as `off`, `warn`, or `enforce`. `off` records freeze facts without blocking runtime transitions, `warn` emits gate warnings while allowing execution, and `enforce` blocks lock/start/runtime transitions on freeze drift or missing live-controller evidence.
