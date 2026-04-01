# DEPLOYMENT

Canonical deployment entrypoint for the converged runtime.

Profiles:
- `dev`: local iteration, relaxed seal requirements, debug-level logging
- `research`: writable runtime with strong evidence and provenance capture
- `clinical`: strict control authority, token-gated writes, strict evidence seal
- `review`: read-only replay/review/export profile

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
sudo apt-get install -y cmake g++ libssl-dev libeigen3-dev
```

Real runtime launch honors `XCORE_SDK_ROOT` / `ROKAE_SDK_ROOT` when building the C++ core.
Desktop entrypoints require a real PySide6>=6.7 installation; only tests may opt into the compatibility stub.
Python mainline currently expects `protobuf>=3.20.3,<8` at runtime.

System protobuf compiler/headers are not required for the current C++ mainline; the repository ships a compatible in-tree wire codec.

Observability additions:
- control-plane responses expose `authoritative_runtime_envelope` for runtime-owned truth.
- projection caches expose `projection_revision` / `projection_partitions` so stale control-plane assembly can be diagnosed without reintroducing parallel truth sources.
