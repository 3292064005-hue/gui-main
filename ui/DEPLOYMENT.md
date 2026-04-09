# DEPLOYMENT

Canonical deployment entrypoint for the converged runtime.

Profiles:
- `dev`: local iteration, relaxed seal requirements, debug-level logging
- `research`: writable runtime with strong evidence and provenance capture
- `clinical`: strict control authority, token-gated writes, strict evidence seal
- `review`: read-only replay/review/export profile


Deployment identity contract:
- robot model: `xmate3`
- SDK robot class: `xMateRobot`
- axis count: `6`
- preferred link: `wired_direct`
- RT mode: `cartesianImpedance`

Real runtime launch now assumes a single live-binding target inside `cpp_robot_core`; multi-model runtime dispatch is not part of the supported deployment surface.

Primary smoke check:
```bash
python scripts/deployment_smoke_test.py
```

Runtime boundaries:
- C++ / robot core owns real motion authority and final runtime verdicts
- Python headless exposes contracts, evidence access, and profile guards
- Desktop/Web consume the control-plane snapshot and do not invent parallel truth

Preflight:

```bash
./scripts/check_cpp_prereqs.sh
python scripts/check_protocol_sync.py
# 首次 real-runtime bringup 若尚无 TLS 材料，先生成开发证书
./scripts/generate_dev_tls_cert.sh
python scripts/doctor_runtime.py
```

Ubuntu 22.04 host dependencies for `cpp_robot_core`:

```bash
sudo apt-get update
sudo apt-get install -y cmake g++ libssl-dev
```

Real runtime launch defaults to the vendored SDK at `third_party/rokae_xcore_sdk/robot`; hosts with an official SDK install may override it via `XCORE_SDK_ROOT` / `ROKAE_SDK_ROOT` when building the C++ core.
Desktop entrypoints require a real PySide6>=6.7 installation; only tests may opt into the compatibility stub.
Python mainline currently expects `protobuf>=3.20.3,<8` at runtime.

System protobuf compiler/headers are not required for the current C++ mainline; the repository ships a compatible in-tree wire codec.

Observability additions:
- control-plane responses expose `authoritative_runtime_envelope` for runtime-owned truth.
- projection caches expose `projection_revision` / `projection_partitions` so stale control-plane assembly can be diagnosed without reintroducing parallel truth sources.


## HIL validation

For the remaining controller-side validation items, run the field checklist in `docs/HIL_VALIDATION_CHECKLIST.md` and the host readiness probe in `scripts/run_hil_readiness.sh`.


Backend/profile truth matrix:
- `dev`: desktop=`mock` (default), headless=`mock` (default)
- `lab`: desktop=`core|api`, headless=`core`
- `research`: desktop=`core|api`, headless=`core`
- `clinical`: desktop=`core|api`, headless=`core`
- `review`: desktop=`api` (default), headless=`core`

A live-SDK profile may not execute write commands on `mock`, contract-only, or `core` surfaces whose runtime doctor/control-plane snapshot still reports vendor-boundary or live-takeover blockers.


## Session-product materialization contract

Headless/session read APIs now operate in **materialized-only** mode for session-intelligence products. Missing lineage / release / governance artifacts are reported as `not_materialized` and must be regenerated through `SessionService.refresh_session_intelligence()` (or the equivalent finalize/export path) rather than being created on demand by a GET/read surface.
