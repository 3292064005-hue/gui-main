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
- `VERIFY_PHASE=prod`：prod profile build/install/package 门禁（仍可在 contract-only 模式下运行，但不再是 configure-only 证明）
- `VERIFY_PHASE=all`：顺序执行全部阶段

`mock` / `hil` / `prod` 必须使用彼此隔离的 build 目录，禁止复用同一个 CMake cache 混跑多个 profile。

仓库 proof / profile proof / live-controller proof 的口径边界见 `docs/VERIFICATION_BOUNDARY.md`；禁止把 `VERIFY_PHASE=python` 的结果写成 HIL / prod / live SDK 已验证。

`VERIFY_PHASE=python` 在 `FULL_TESTS=0` 的默认模式下会按固定批次执行 pytest。批次拆分不改变覆盖范围，只用于降低受限执行环境中的单进程时长与被外部终止风险。

`VERIFY_PHASE=python` 与 `scripts/final_acceptance_audit.sh` 都必须包含同一组仓库级门禁；至少包括：

- `scripts/check_repo_hygiene.sh`
- `scripts/strict_convergence_audit.py`
- `scripts/check_protocol_sync.py`
- `scripts/check_robot_identity_registry.py`
- `scripts/check_python_compile.py`（正式 Python 文件必须全部可解析/可编译，且不得生成 `__pycache__` / `.pyc` 污染）
- `scripts/check_canonical_imports.py`
- `scripts/check_repository_gates.py`
- `scripts/check_architecture_fitness.py`
- `scripts/check_verification_boundary.py`
- `scripts/generate_p2_acceptance_artifacts.py`
- `scripts/check_p2_acceptance.py`

`final_acceptance_audit.sh` 若不执行完以上仓库级门禁，不得输出等价于“完整 repository gates 全部通过”的结论。默认的 repository/profile gate 运行结束后，建议归档 `scripts/write_verification_report.py` 生成的执行报告；该报告是对“已静态确认 / 已沙箱验证 / 未真实环境验证”边界的机器可读约束。
