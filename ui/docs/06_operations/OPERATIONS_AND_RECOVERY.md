---
category: runbook
authority: canonical
audience: operators, validation engineers
owner: repository
status: active
---

# Operations and Recovery

## Scope
Operating bring-up, fault injection, safe stop/retreat, and recovery behavior.

## Operating rules
- Use a single control source.
- Treat recovery as an explicit runtime action with evidence, not an implicit UI-side retry.
- Safe retreat and abort paths must preserve the evidence chain.

## Bring-up and fault injection
Document the host checks, runtime launch steps, controlled fault injection paths, and expected post-fault evidence capture.

## Bring-up checklist
### Host and runtime preflight
```bash
./scripts/check_cpp_prereqs.sh
python scripts/check_protocol_sync.py
./scripts/generate_dev_tls_cert.sh
python scripts/doctor_runtime.py
```

### Launcher rule
- `scripts/start_mainline.py` is the single operator-facing launcher for desktop/headless surfaces.
- Launcher wrappers must forward into it instead of re-implementing runtime backend policy.

### Runtime boundaries
- C++ / robot core owns real motion authority and final runtime verdicts.
- Python headless exposes contracts, evidence access, and profile guards.
- Desktop/Web consume control-plane projections and do not invent parallel truth.
