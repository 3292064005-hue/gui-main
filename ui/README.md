# Spine Ultrasound Platform

This repository uses a single active canonical documentation tree rooted at [`docs/00_START_HERE.md`](docs/00_START_HERE.md).

## Start here
- Repository entry: [`docs/00_START_HERE.md`](docs/00_START_HERE.md)
- Document authority policy: [`docs/DOCUMENT_AUTHORITY_POLICY.md`](docs/DOCUMENT_AUTHORITY_POLICY.md)
- Verification scope policy: [`docs/05_verification/VERIFICATION_POLICY.md`](docs/05_verification/VERIFICATION_POLICY.md)

## Mainline domains
- `configs/`
- `cpp_robot_core/`
- `spine_ultrasound_ui/`
- `schemas/`
- `scripts/`
- `tests/`
- `docs/`
- `runtime/`

## Historical / non-mainline areas
- `archive/`

## Runtime and robot authority
- Real SDK binding is allowed only inside `cpp_robot_core`.
- Runtime canonical command entry is `start_procedure(scan)`.
- Desktop/API/mock layers may consume runtime projections but do not own execution authority.
- Mainline robot identity is `xmate3`, SDK class `xMateRobot`, axis count `6`, preferred link `wired_direct`, realtime mainline `cartesianImpedance`.

## Headless/runtime policy notes
- `runtime_mode_policy` is the canonical source for runtime backend selection policy.
- `scripts/start_mainline.py` is the single operator-facing launcher for desktop/headless surfaces; wrapper scripts such as `start_hil.sh`, `start_prod.sh`, and `start_headless.sh` only map named deployment profiles and launcher-level backend intent into it; stale low-level `SPINE_UI_BACKEND` / `SPINE_HEADLESS_BACKEND` values are ignored by unified mainline entrypoints.
- launcher waits for core command/telemetry sockets before starting the surface, so desktop/headless no longer races ahead of a cold core boot.
- headless/backend selection still flows through `runtime_mode_policy`; wrapper scripts no longer duplicate profile/build/model policy, and the unified launcher ignores stale low-level surface backend env when `--backend auto` is used.
- headless 默认后端由 deployment profile 决定：`dev -> mock`，`lab/research/clinical/review -> core`；其中 `review` 仅允许在只读 evidence / replay / contract inspection 场景显式切到 `mock`。
- desktop 是真实操作台：`api` 只允许显式 review/integration 桌面，不允许用于 `lab/research/clinical` 写控制主线。
- package-level lazy exports keep `spine_ultrasound_ui.core` / `spine_ultrasound_ui.utils` import-safe for non-GUI scripts and headless services.

## Runtime dependency baseline
- `PySide6 >= 6.7`
- `protobuf>=3.20.3,<8`
- C++ toolchain: CMake 3.24+

## Common commands
```bash
./scripts/check_cpp_prereqs.sh
./scripts/generate_dev_tls_cert.sh
python scripts/check_protocol_sync.py
python scripts/doctor_runtime.py
python scripts/start_mainline.py --surface desktop --profile dev --backend mock
python scripts/run_pytest_mainline.py -q
./scripts/verify_mainline.sh
```

## Documentation map
- System overview: [`docs/01_overview/`](docs/01_overview/)
- Governance: [`docs/02_governance/`](docs/02_governance/)
- Runtime specs: [`docs/03_runtime/`](docs/03_runtime/)
- Profiles and release: [`docs/04_profiles_and_release/`](docs/04_profiles_and_release/)
- Verification: [`docs/05_verification/`](docs/05_verification/)
- Operations: [`docs/06_operations/`](docs/06_operations/)
- Repository governance: [`docs/07_repo_governance/`](docs/07_repo_governance/)
- Historical package: [`docs/90_archive/README.md`](docs/90_archive/README.md)
