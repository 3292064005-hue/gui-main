# Repository Gates

P2 要求把仓库治理收成不可漂移的硬门禁。

## Canonical required checks

以下 job 名称必须保持稳定，供 GitHub protected branch 配置为 required status checks：

- `hygiene`
- `mainline-verification`
- `canonical-import-gate`
- `protocol-sync-gate`
- `runtime-core-gate`
- `evidence-gate`
- `mock-e2e`

## Domain ownership

- `cpp_robot_core/**` -> runtime core
- `spine_ultrasound_ui/services/**` -> python runtime/governance
- `scripts/**` -> build/release
- `docs/**` -> architecture/specs

`.github/CODEOWNERS` 是仓库内的声明源，仓库设置中的 protected branch 需要将上述 checks 配成 required。


## Mainline verification phases

`scripts/verify_mainline.sh` 是主线 gate 的本地/CI 对齐入口，并支持下列显式阶段：

- `VERIFY_PHASE=python`：仓库门禁 + 主线 pytest
- `VERIFY_PHASE=mock`：mock profile C++ configure/build/ctest
- `VERIFY_PHASE=hil`：hil profile C++ configure/build/ctest
- `VERIFY_PHASE=prod`：prod profile 配置门禁（可在 contract-only 模式下运行）
- `VERIFY_PHASE=all`：顺序执行全部阶段

`mock` / `hil` / `prod` 必须使用彼此隔离的 build 目录，禁止复用同一个 CMake cache 混跑多个 profile。

`VERIFY_PHASE=python` 在 `FULL_TESTS=0` 的默认模式下会按固定批次执行 pytest。批次拆分不改变覆盖范围，只用于降低受限执行环境中的单进程时长与被外部终止风险。
