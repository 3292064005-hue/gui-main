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
