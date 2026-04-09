## v21 - proof portability and readiness-state alignment

- Reworked `write_verification_report.py` and `write_acceptance_summary.py` so packaged proof members are recorded with paths relative to the proof-file directory instead of leaking build-machine absolute paths or stale versioned work directories.
- Adjusted `RuntimeReadinessManifestService` so the top-level manifest no longer reports `ready` while `doctor_snapshot` remains blocked; repository/sandbox readiness now degrades to `warning` until live environment blockers are cleared.
- Normalized repository-owned paths emitted by `SdkEnvironmentDoctorService` to package-relative form while keeping host-only tool paths explicit.
- Added regression coverage for portable proof paths and the readiness-state downgrade rule, then regenerated the machine-readable repository-proof bundle.

## v20 - verification evidence closure and delivery hygiene

- Removed duplicate `using namespace sdk_robot_facade_internal;` directives across the `sdk_robot_facade*` translation units so the lifecycle/runtime source set no longer carries avoidable namespace hygiene debt.
- Hardened `scripts/verify_cpp_build_evidence.py` with bounded per-target timeouts and explicit `evidence_mode` / fallback fields, so sandbox repository proof now closes with a truthful `syntax_only_fallback` report instead of hanging or being summarized as a full C++ build.
- Added `tests/test_cpp_build_evidence_report.py` to keep the bounded fallback evidence path executable and claim-safe.
- Added machine-readable repository-proof artifacts under `artifacts/verification/sandbox_repository_proof/`, including the readiness manifest, verification execution report, build evidence report, acceptance summary, and the focused pytest log for this delivery.

## v19 - canonical lifecycle binding closure

- Moved `SdkRobotFacade` constructor plus authoritative `connect()/disconnect()` lifecycle ownership back into `cpp_robot_core/src/sdk_robot_facade.cpp`, so the canonical source file now carries the live-binding truth contract expected by the mainline gates.
- Hardened the live-bind failure path to explicitly reassert `binding_detail_ = "live_binding_failed"` after exception capture, preventing any accidental regression toward contract-shell-success semantics after a failed vendor bind attempt.
- Added function-level boundary documentation for the lifecycle entrypoints and revalidated the mock-profile C++ build / targeted runtime contract suites against the new source layout.

## v18 - RT recorder purity, canonical verdict API, and review-mode lease hardening

- Switched `RecordingService.recordAlarm()` to the same asynchronous queue/worker path used by robot-state/contact/progress samples, so `CoreRuntime::queueAlarmLocked()` no longer performs inline JSON/file I/O under the runtime state mutex.
- Added canonical backend API `resolve_final_verdict(plan, config, read_only=...)` and moved `RuntimeVerdictKernelService` to that single authority surface instead of probing multiple legacy verdict methods.
- Guarded `ApiBridgeBackend.send_command()` and startup lease acquisition with the deployment profile and `include_lease` intent so desktop `review` mode and read-only verdict queries no longer mutate API-side control authority.
- Hardened `ApiBridgeVerdictService` so failed `query_final_verdict` / `validate_scan_plan` replies raise typed runtime errors instead of silently falling back to stale cached verdicts.
- Split API-bridge lease handling and final-verdict resolution into dedicated services (`ApiBridgeLeaseService`, `ApiBridgeVerdictService`) while preserving the external backend façade.
- Hardened architecture gates/tests so async alarm persistence and canonical verdict resolution cannot silently regress.

## Audit closeout: verification-boundary hardening
- Added `docs/VERIFICATION_BOUNDARY.md` to separate repository proof, profile proof, and live-controller/HIL validation claims.
- Added `scripts/check_verification_boundary.py` and wired it into repository gates so README/docs cannot silently overstate validation scope.
- Updated `scripts/verify_mainline.sh` to emit phase-scope notes, preventing `VERIFY_PHASE=python` or SDK-off runs from being misreported as HIL / prod / live-controller validation.

## v16 - audit remediation and packaging closure

- Restored the repository-owned `tools/monai_label_app/` package so offline MONAI Label skeleton imports, descriptors, and server-task tests are present in the delivery payload instead of being documented-but-missing.
- Fixed `scripts/check_repo_hygiene.sh` execute permissions so `VERIFY_PHASE=python ./scripts/verify_mainline.sh` no longer fails before running repository gates.
- Kept the MONAI Label tooling import-safe without introducing runtime MONAI dependencies into the desktop path.

## v15 - governance projection decoupling

- Split desktop governance refresh paths into explicit full / backend-link / bridge-observability / session-governance projections so high-frequency status emission no longer recompiles runtime verdicts or re-reads session artifacts.
- Added read-only final-verdict snapshot APIs across backends and kept plan compilation as an explicit path instead of coupling it to every status-facing read.
- Enabled `review` + `headless` + `mock` for read-only contract/evidence inspection while preserving profile-level write blocking.
- Added filesystem-signature caching to `SessionGovernanceService` to bound repeated operator refresh cost for unchanged sessions.
- Hardened controller semantics so `stop_scan` is explicitly treated as the UI alias of canonical `safe_retreat`.

## v14 - authority/runtime bridge convergence

- Extracted `AppRuntimeBridge` to centralize telemetry handling, guarded command behavior, governance refresh, local alarm emission, and session product refresh away from `AppController`.
- Extracted `MainWindowRuntimeBridge` so runtime preference restore/save, alarm/log propagation, pixmap routing, and emergency-stop confirmation no longer live directly in `MainWindow`.
- Extracted `HeadlessRuntimeIntrospection` so adapter status/health/schema/catalog introspection is no longer embedded directly in `HeadlessAdapter`.
- Reduced core transition files further: `app_controller.py` -> ~414 lines, `main_window.py` -> ~525 lines, `headless_adapter.py` -> ~529 lines.
- Verified targeted refactor and governance suites pass after migration.

## v12 - convergence rewrite wave D

- Added `app_workflow_operations.py` and moved the largest experiment / scan / export workflow paths out of `AppController`, reducing desktop orchestration sprawl.
- Added `MainWindowStatusPresenter` and moved the runtime status projection out of `MainWindow`, so the main window now stays focused on layout and action routing.
- Simplified `HeadlessAdapter` by routing `current_*` evidence/session reads through `HeadlessSessionProductsReader` via delegated lookup, keeping the adapter closer to transport and session tracking.
- Removed duplicate governance-refresh implementations left over from transitional rewrites and kept a single `ControlPlaneReader` path for desktop status/governance projection.
- Added rewrite-wave documentation and regression coverage for the refactor-adjacent paths.


## v11 - control-plane convergence rewrite

- Extracted session-derived read APIs from `HeadlessAdapter` into `HeadlessSessionProductsReader`, so the adapter is no longer the only place that knows how to serve session evidence and derived products.
- Added `ApiCommandGuardService` with deployment-profile-aware write gating, normalized command provenance, and optional token checks for strict clinical profiles.
- Consolidated runtime control, contract, and evidence modules around the current headless/mainline payload.
- Added `RuntimePersistenceService` so desktop config/UI persistence is no longer hard-coded inside `AppController`.
- Removed the committed TLS private key, added runtime TLS generation script and repo/documentation hardening for secret-backed deployments.


## v10 - control-plane rewrite wave A
- Added desktop orchestration split: `CommandOrchestrator`, `GovernanceCoordinator`, `SessionFacade`, `UiProjectionService`.
- Added explicit deployment profile and unified control-plane snapshot services.
- Headless adapter now exposes deployment profile and unified control-plane snapshot in its control-plane payload.
- API now exposes `/api/v1/profile` and forwards `x-spine-session-id` into command context.
- Added regression tests for deployment profile, control-plane snapshot, and controller status projection.

## v9 - Control authority and evidence sealing

- 新增 `ControlAuthorityService`，把唯一控制权、lease、session 绑定和写命令冲突阻断纳入正式主线
- `HeadlessAdapter`、`ApiBridgeBackend`、desktop 状态投影现在都会携带 `control_authority` 摘要，不再只看 link/control plane 声明
- 新增 `SessionEvidenceSealService` 与 `session_evidence_seal_v1` schema，session 冻结后会输出正式证据封印文件
- headless API 新增控制租约与 evidence seal 读取接口，命令请求头支持 actor/workspace/lease/intent 透传
- CORS 改为环境变量驱动的受限来源配置，不再默认 `*`
- 新增控制权与证据封印测试，覆盖 lease 冲突阻断、adapter 命令门禁和 session seal 生成

## v8 - Bridge observability hardening

- 新增 `BridgeObservabilityService`，把前端对后端 runtime 的观测证据纳入正式治理，而不是只看链路和控制面声明
- 正式检查关键 topic 新鲜度、执行态一致性、最近关键命令是否被前端观测确认
- `AppController.start_scan()` 新增桥接观测门禁；topic 陈旧、状态不一致、命令未被观测确认都会阻止启动
- 总览页、系统准备、机器人监控、实验回放、系统设置新增桥接观测摘要
- 新增 `docs/BRIDGE_OBSERVABILITY_MAINLINE.md` 与对应测试


## v7 - Backend control plane hardening

- 新增 `BackendControlPlaneService`，把协议一致性、配置漂移、topic 覆盖、最近命令窗口纳入前后端互联治理
- headless API 新增 `/api/v1/control-plane` 与 `/api/v1/commands/recent`
- `ApiBridgeBackend` 现在会缓存并展示 control plane 状态，而不是只看 REST/WS 可达性
- `ViewStateFactory` 新增“前后端配置一致”“控制面协议一致”两项 readiness 检查
- `MockBackend` 与 `RobotCoreClientBackend` 补齐 `link_snapshot`，三种 backend 现在都有统一链路摘要
- 机器人监控页与系统设置页增加控制面摘要、配置同步、协议状态与最近命令窗口展示

# Changelog

## 2026-03-30 (rewrite pass 7)
- Added `ApiBridgeBackend` so the desktop can run against the headless FastAPI/WebSocket adapter instead of only `mock` or direct `core` transport.
- Added `/api/v1/runtime-config` and `/api/v1/backend/link-state` to synchronize runtime configuration and expose backend connectivity state to frontend consumers.
- Added `BackendLinkService` to formalize frontend-backend link health, stream status, command success rate, reconnect counts, and blocker/warning synthesis.
- Extended readiness and desktop status payloads with `backend_link`, so launch gating now includes frontend-backend connectivity rather than only SDK/model/config/session governance.
- Surfaced backend-link state in Overview, Prepare, Robot Monitor, Replay, and Settings views.


## SDK-aligned optimization round
- Added xCore SDK capability/alignment service and preflight blockers
- Extended runtime config with robot/local IP fields and richer SDK parameters
- Upgraded config form to preserve non-edited SDK fields and expose robot class/link/filters/tolerance/tool/TCP/load
- Added SDK alignment views to Prepare and Settings pages
- Block start_scan when SDK mainline blockers exist
- Added SDK alignment tests and architecture note

## 2026-03-30 (rewrite pass 6)
- Added `ClinicalConfigService` so runtime configuration now has a formal baseline check separate from SDK alignment and model precheck.
- Added `SessionGovernanceService` to summarize release gate, integrity, resume viability, incidents, and selected execution into a desktop-facing governance digest.
- Added explicit desktop operations for applying the xMate clinical baseline, exporting a governance snapshot, and refreshing session governance.
- Extended readiness to include config-baseline status, and block `start_scan` when configuration blockers exist.
- Surfaced config/session governance summaries in Overview, Prepare, Robot Monitor, Replay, and Settings views.
- Added tests covering baseline normalization, config-blocked scan prevention, governance export, and session governance summarization.

## 2026-03-30 (rewrite pass 5)
- Extended RuntimeConfig / ConfigForm with collision detection, soft limit, singularity avoidance, RL project/task, and xPanel output controls.
- Added `SdkRuntimeAssetService` to aggregate controller logs, RL inventory, path libraries, I/O snapshots, safety profile, and motion contract into the desktop payload.
- Added `XMateModelService` to generate deterministic path precheck reports with envelope metrics, execution-selection summary, and approximate DH-backed validation.
- Reworked `MainWindow` runtime rendering so Prepare / Vision / Robot Monitor / Replay / Settings pages now surface SDK runtime assets and model-precheck governance instead of placeholder text.
- Fixed mock runtime controller-log bookkeeping and added tests for SDK runtime assets and model precheck payloads.

## 2026-03-29 (rewrite pass 4)
- Upgraded desktop workflow governance: command buttons now expose human-readable enable/disable reasons.
- Added readiness scoring, blocker summaries, and next-step recommendations to the desktop main window.
- Added runtime config persistence and UI layout persistence under the workspace `runtime/` directory.
- Replaced the placeholder settings page with a real persistence / recovery operations panel.
- Added governance tests covering readiness payloads, action reasons, and config/UI persistence.

## Rewrite round: clinical data products + headless product shell hardening
- Added runtime compatibility layer for headless/test environments without PySide6.
- Added artifact registry and processing step registry to session manifests.
- Added session compare, alarm timeline, and QA pack formal outputs.
- Added artifact JSON schemas under `schemas/` and exposed them via headless API.
- Expanded headless API with quality / alarms / artifacts / compare / qa-pack endpoints.
- Added read-only review mode to the headless adapter and frontend awareness.
- Hardened frontend contracts for expanded force-control and session-product payloads.
- Rewrote convergence docs to match the actual single-mainline architecture.

## 2026-03-28 (rewrite pass 3)
- Removed frontend-generated session identity and tightened Web state to adapter-fed execution/session truth.
- Extended session products with trends, diagnostics, annotations, stronger artifact registry metadata, and manifest freeze fields.
- Added headless read-only endpoints for trends, diagnostics, and annotations; strengthened typed frontend envelopes and session console review panel.


## Wave C
- Added `ControlPlaneReader` to centralize governance/status projection in the desktop controller.
- Split `api_server.py` into modular routers under `spine_ultrasound_ui/api_routes/`.
- Removed legacy frontend `store/` and `stores/` shim directories; `src/state/` is now the canonical state entrypoint.
- Clarified legacy Qt event bus naming with `core/qt_signal_bus.py`.

## v22 - portable proof-chain closure
- make C++ build evidence report path-safe for packaged delivery by replacing ephemeral tmp build dirs with symbolic metadata rather than host-specific absolute paths
- enrich acceptance summary with verification boundary / reported tiers / build evidence mode so package consumers can inspect the claim boundary without chasing three JSON files
- refresh sandbox proof README wording to stay version-neutral
