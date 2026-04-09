# Spine Ultrasound Platform

当前主线仓库仅包含以下正式域：

- `configs/`
- `cpp_robot_core/`
- `spine_ultrasound_ui/`
- `schemas/`
- `scripts/`
- `tests/`
- `docs/`
- `runtime/`
- `spine_ultrasound_ui/training/`
- `archive/`

## xMateRobot-only 主线约束

当前正式控机主线已收敛为 **xMate3 / xMateRobot / 6 轴协作机**：

- `robot_model = xmate3`
- `sdk_robot_class = xMateRobot`
- `axis_count = 6`
- `preferred_link = wired_direct`
- RT 主线固定为 `cartesianImpedance`
- 真实 SDK 绑定仅允许在 `cpp_robot_core` 内建立

若配置不满足以上约束，runtime 会在 profile / session 初始化阶段直接拒绝启动，而不是在运行时做隐式机型分发。

## 运行要求

桌面 / headless 主线：

- Ubuntu 22.04（CI / 发布基线；非 22.04 主机会在 doctor 中明确告警）
- Python 3.11+
- PySide6 >= 6.7（桌面入口）
- `pip install -r requirements.txt`

C++ robot_core 主线：

- CMake 3.24+
- `g++` 或 `clang++`
- `libssl-dev`
- 仓库内已附带 vendored xCore SDK（`third_party/rokae_xcore_sdk/robot`）；prod/HIL 主机也可通过 `XCORE_SDK_ROOT` 或 `ROKAE_SDK_ROOT` 显式覆盖为官方安装路径
- C++ 主线已移除对系统级 `protoc/libprotobuf-dev` 的硬依赖；Python 侧仍需 `protobuf` 运行时（当前主线要求 `protobuf>=3.20.3,<8`）

推荐先执行：

```bash
./scripts/check_cpp_prereqs.sh
python scripts/check_protocol_sync.py
# 首次 real-runtime bringup 若尚无 TLS 材料，先生成开发证书
./scripts/generate_dev_tls_cert.sh
python scripts/doctor_runtime.py
```

## 常用入口

桌面程序：

```bash
python run.py --backend mock
```

运行面 / profile 约束：

- `dev`：desktop 默认 `mock`；headless 默认 `mock`
- `lab` / `research` / `clinical`：desktop 默认 `core`；headless 只允许 `core`
- `review`：desktop 默认 `api`；headless 默认 `core`，显式 `mock` 仅允许只读 evidence / replay / contract inspection
- 当 profile 要求 live SDK（`research` / `clinical`）时，写命令不会再静默落到 `mock`、contract-only 或 `core + 非 live binding` 运行面
- `scripts/start_demo.sh` / `start_hil.sh` / `start_prod.sh` 保持显式固定 profile + backend；`scripts/start_headless.sh` 改为委托 `runtime_mode_policy` 解析 headless 默认 backend，避免脚本与策略漂移

Python 主线测试：

```bash
python scripts/run_pytest_mainline.py -q
```

主线验证：

```bash
./scripts/verify_mainline.sh
# 仅跑 Python 门禁与主线 pytest
VERIFY_PHASE=python ./scripts/verify_mainline.sh
# 仅跑 mock / hil / prod 单阶段 gate
VERIFY_PHASE=mock ./scripts/verify_mainline.sh
VERIFY_PHASE=hil ./scripts/verify_mainline.sh
VERIFY_PHASE=prod ROBOT_CORE_WITH_XCORE_SDK=OFF ROBOT_CORE_WITH_XMATE_MODEL=OFF ./scripts/verify_mainline.sh
```

`verify_mainline.sh` 会为 `mock` / `hil` / `prod` 使用独立 build 目录，并在 `ctest` 前输出注册测试清单；`VERIFY_PHASE=python` 在默认主线模式下会将 pytest 拆成确定性的多个批次，以降低受限容器内长进程被外部终止的概率；实时运行脚本默认把 C++ 构建产物放到 `/tmp`，避免污染仓库 payload。

验证口径边界见 `docs/VERIFICATION_BOUNDARY.md`。同时请运行 `python scripts/check_robot_identity_registry.py`，确保 xMate3/xMateRobot/6 轴主线身份事实未在 Python/C++/文档之间漂移。其中 `VERIFY_PHASE=python` 只闭合 repository/Python 级 gate，不得表述为 HIL / prod / live-controller 已验证。建议把 `scripts/write_verification_report.py` 产出的执行报告与 `scripts/doctor_runtime.py --manifest-only` 的 readiness manifest 一并归档。

## 目录说明

- `cpp_robot_core/`：机器人 C++ 执行内核与构建脚本
- `spine_ultrasound_ui/`：Python 桌面、headless 适配层、治理与会话能力
- `schemas/`：运行态与会话证据 schema
- `archive/`：历史文档、历史测试、归档入口

## 仓库门禁

- `.github/CODEOWNERS` 定义目录责任边界。
- `docs/REPOSITORY_GATES.md` 定义应配置为 required checks 的 workflow job 名称。
- `scripts/check_canonical_imports.py` 与 `scripts/check_repository_gates.py` 用于在本地/CI 审计 P2 收口约束。

## 说明

- 本仓库不再包含前端构建目录、运行态缓存、历史 legacy 可执行入口和提交态生成产物。
- 包根 `spine_ultrasound_ui` 不再执行导入时兼容注入；测试若需要 PySide6 stub，必须显式调用 `tests.runtime_compat.enable_runtime_compat()`。
- 桌面运行要求真实 PySide6；不允许在正式入口静默降级为测试桩。

## 控制面约束

- `cpp_robot_core` / headless runtime 现在统一发布 `authoritative_runtime_envelope`，其中包含控制权、已应用运行时配置、会话冻结、plan digest 与最终裁决。
- Desktop / API / mock backend 只能消费该 envelope，不再本地拼接并宣称并行 authority。
- control-plane 快照同时暴露 `projection_revision` 与 `projection_partitions`，用于调试增量物化与缓存失效。


## SDK / RT truthfulness

- `cpp_robot_core` now distinguishes **vendored SDK detection**, **contract-shell readiness**, and **live binding established** in runtime contracts.
- RT runtime contracts export measured loop timing (`current_period_ms`, `max_cycle_ms`, `last_wake_jitter_ms`, `overrun_count`) instead of only nominal declarations.
- `projection_revision` / `projection_partitions` are produced from atomic cache snapshots so control-plane reads do not see torn metadata.


## HIL validation

For the remaining controller-side validation items, run the field checklist in `docs/HIL_VALIDATION_CHECKLIST.md` and the host readiness probe in `scripts/run_hil_readiness.sh`.


## Camera guidance freeze bundle

The camera subsystem is guidance-only. Before session lock it may contribute back ROI, spine midline, landmarks, body surface, and a scan corridor. At session lock the project now freezes a full guidance bundle instead of only a loose registration payload:

- `meta/patient_registration.json`
- `meta/localization_readiness.json`
- `meta/calibration_bundle.json`
- `meta/localization_freeze.json`
- `meta/manual_adjustment.json`
- `derived/sync/source_frame_set.json`
- `replay/localization_replay_index.json`

After session freeze these artifacts remain advisory lineage and do not grant the camera authority to rewrite RT execution.


### Guidance provider and review workflow

- `camera_guidance_input_mode` supports `synthetic`, `filesystem`, and `opencv_camera`.
- `filesystem` mode consumes `.npy/.npz` or common image files from `camera_guidance_source_path` and is the preferred offline validation path.
- When guidance falls back to `READY_WITH_REVIEW`, call `approve_localization_review(...)` from the application controller before path generation or session lock. Approval records a `manual_adjustment` artifact, re-runs the freeze gate, and flips workflow readiness so planning can proceed.
- `device_readiness` now cross-checks `source_frame_set`, guidance plugin registry completeness, and review approval state against the runtime/telemetry device snapshot; localization callers must provide an authoritative pre-freeze device roster. Guidance-only freeze no longer synthesizes compatibility artifacts when canonical localization evidence is missing, and canonical `source_frame_set` contracts now require `device_fact_sources`.
- Camera guidance remains pre-scan only and never becomes RT execution authority; xCore RT remains the single control source and runs at the controller 1 ms cycle boundary.


## Ultrasound / Pressure session artifacts
- raw/ultrasound/index.jsonl and raw/ultrasound/frames store ultrasound frame evidence.
- raw/pressure/samples.jsonl stores normalized pressure-sensor samples captured from contact telemetry.
- derived/ultrasound/ultrasound_frame_metrics.json summarizes stored ultrasound frames.
- derived/pressure/pressure_sensor_timeline.json summarizes stored pressure samples.
- export/ultrasound_analysis.json and export/pressure_analysis.json provide operator-facing analytics.


## Authoritative reconstruction / assessment artifacts

The postprocess mainline now treats reconstruction and scoliosis assessment as first-class authoritative artifacts instead of report-side placeholders:

- `derived/reconstruction/reconstruction_input_index.json`
- `derived/reconstruction/spine_curve.json`
- `derived/reconstruction/landmark_track.json`
- `derived/reconstruction/reconstruction_summary.json`
- `derived/assessment/cobb_measurement.json`
- `derived/assessment/assessment_summary.json`

`ReconstructStage` materializes the reconstruction artifacts after sync/replay indexing, `ReportStage` materializes the Cobb assessment artifacts before session-report/QA export, and runtime/headless readers now consume those files as the authoritative source for Cobb-angle outputs. Legacy `spine_ultrasound_ui/imaging/*` functions remain demo adapters only and are no longer the postprocess authority path.


## Contact-control mainline

The clinical real-time mainline keeps `cartesianImpedance` as the xCore execution mode while the project computes a **project-side normal-axis admittance outer loop**. The outer loop uses a fused `NormalForceEstimator` (pressure + wrench), a `NormalAxisAdmittanceController` for the surface-normal axis, a `TangentialScanController` for along-spine travel, and an `OrientationTrimController` for bounded probe attitude compensation. Camera guidance does not participate in the admittance loop.
Compatibility note: `contact_control`, `force_estimator`, and `orientation_trim` are the primary configuration surfaces. Legacy flat RT fields remain only as compatibility projections, and `cpp_robot_core/examples/impedance_scan_example.cpp` is now a controller-composition demo rather than a production control path.



## Lamina-center Cobb development pipeline

The authoritative runtime now supports a staged scoliosis-measurement stack:

- dataset export via `SessionExportService` and `AnnotationManifestBuilder`
- lamina-aware reconstruction artifacts (`coronal_vpi`, `bone_mask`, `lamina_candidates`)
- primary assessment via `lamina_center_cobb`
- auxiliary assessment via `uca_auxiliary`

Runtime assessment remains engineering-oriented and non-clinically-certified. Training-time tooling such as MONAI Label or nnU-Net must remain out of the UI runtime process; exported session artifacts provide the bridge into offline annotation and model training workflows.


## Phase-1 annotation + Phase-2 training interface

The repository now includes an offline training interface under `spine_ultrasound_ui/training/`:

- dataset adapters for lamina-center and UCA exports
- structured training specs
- deterministic baseline trainers
- model package exporters
- lightweight runtime adapters for exported packages

Session exports remain the bridge between runtime and training:

- `export_lamina_training_case(...)` writes lamina-center cases
- `export_uca_training_case(...)` writes UCA cases
- `build_annotation_manifest(...)` materializes patient-level split metadata

Training-time tooling such as MONAI Label or nnU-Net remains out of the desktop runtime process. Runtime reconstruction/assessment services may optionally consume exported packages through `SegmentationRuntimeAdapter`, `KeypointRuntimeAdapter`, and `RankingRuntimeAdapter`. Deterministic no-weight execution is now exposed as the explicit `preweight_deterministic` profile rather than being treated as an undocumented runtime failure fallback.


## Offline annotation and training interfaces

This repository now includes a dedicated offline training layer under `spine_ultrasound_ui/training/` and a MONAI Label application skeleton under `tools/monai_label_app/`. The desktop runtime does **not** depend on MONAI, MONAI Label, nnU-Net, or TensorRT at import time.

The intended workflow is:

1. export session cases into `datasets/lamina_center` or `datasets/uca`;
2. build patient-level annotation manifests;
3. annotate cases with the MONAI Label skeleton or another offline tool;
4. run a deterministic baseline trainer or emit MONAI/nnU-Net backend requests;
5. export runtime model packages and point reconstruction/UCA services at those packages via `configs/models/*.yaml` or environment variables.


## Training interfaces

The repository now ships offline dataset export, MONAI Label server-task descriptors, MONAI/nnU-Net backend adapters, and an nnU-Net raw dataset conversion pipeline. The desktop runtime remains import-safe when those optional research dependencies are not installed.


## Reconstruction closure profiles

The reconstruction/assessment mainline now supports two explicit closure profiles instead of treating no-weight execution as an implicit fallback:

- `weighted_runtime` (default): allows exported runtime packages plus research-only degradations such as `quality_only_rows`, `all_rows_fallback`, `registration_prior_curve`, and `curve_window_fallback`.
- `preweight_deterministic`: measured-only preweight profile activated with `SPINE_RECONSTRUCTION_PROFILE=preweight_deterministic`. This profile only accepts `authoritative_measured_rows` and fail-closes when measured evidence is insufficient.

The profile state is emitted into `reconstruction_summary.json`, `assessment_summary.json`, and `export/session_report.json` via `runtime_profile`, `profile_release_state`, `closure_mode`, `closure_verdict`, `provenance_purity`, `source_contamination_flags`, `hard_blockers`, `soft_review_reasons`, `profile_config_path`, and `profile_load_error`.

Prior-assisted outputs are now physically separated from authoritative artifacts. When those sidecars exist, canonical `spine_curve.json` and `cobb_measurement.json` are rewritten as authoritative placeholders instead of carrying contaminated geometry:

- `derived/reconstruction/prior_assisted_curve.json`
- `derived/assessment/prior_assisted_cobb.json`

Training-bridge outputs are separated from runtime-authoritative artifacts:

- `derived/training_bridge/model_ready_input_index.json`

## Measured-pose reconstruction contract

The reconstruction mainline no longer treats scan progress as a proxy for probe pose. `derived/sync/frame_sync_index.json` now records whether each ultrasound frame has:

- a measured robot pose,
- acceptable temporal alignment to the ultrasound timestamp,
- a valid calibration bundle, and
- a valid patient-frame definition.

`derived/reconstruction/reconstruction_input_index.json` carries the normalized measured pose (`robot_pose_mm_rad`) and the transformed patient-frame pose (`patient_pose_mm_rad`). When those facts are missing the session explicitly degrades to manual-review / fallback modes instead of synthesizing an authoritative pose chain.

`derived/reconstruction/coronal_vpi.npz` is now built from pose-resampled ultrasound pixels. It stores contribution metadata (`row_geometry`, `contributing_frames`, `contribution_map`) so downstream assessment can explain which recorded frames contributed to the projection.

## Packaged runtime models and benchmark gates

Runtime identity is now explicit for both projection/VPI models and the raw-frame anatomy-point mainline. In particular, `configs/models/frame_anatomy_keypoint_runtime.yaml` no longer points at an inline baseline; it points at an exported-weight package under `models/frame_anatomy_keypoint/` that contains:

- `model_meta.json` with package identity and release state,
- `parameters.json` with runtime thresholds,
- `frame_anatomy_keypoint_weights.npz` with exported point templates, and
- `benchmark_manifest.json` with release-gate evidence.

The default config enforces a benchmark gate before the raw-frame runtime adapter is considered loadable. Missing weight files, missing benchmark manifests, or benchmark thresholds below the configured gate cause the package load to fail and the reconstruction chain degrades explicitly instead of silently claiming a release-ready model.

Use the benchmark helpers to evaluate either assessment outputs or frame-level anatomy packages:

```bash
python scripts/run_assessment_benchmark.py --session-dir <session_dir>
python scripts/run_assessment_benchmark.py --spec-file <cases.json>
python scripts/run_frame_anatomy_benchmark.py --runtime configs/models/frame_anatomy_keypoint_runtime.yaml --manifest models/frame_anatomy_keypoint/generated/frame_anatomy_training_manifest.json
```

The bundled `frame_anatomy_keypoint` package is an exported research package trained and benchmarked on repository-local synthetic fixtures. It is therefore a genuine exported-weight runtime package with explicit gates, but it is **not** a clinical claim or a substitute for phantom/HIL/retrospective validation.


## Environment readiness manifest

The runtime doctor now emits an explicit readiness manifest that separates static/sandbox readiness from real live-runtime verification. `scripts/doctor_runtime.py --manifest-only --write-manifest <path>` must not be interpreted as proof that HIL or robot-side validation has already passed.

## Control authority capability claims

- 控制权不再只表示“谁持有租约”，还会显式记录当前 owner 已拿到的 capability claims。
- 写命令按 `hardware_lifecycle_write / session_freeze_write / nrt_motion_write / rt_motion_write / recovery_write / fault_injection_write / plan_compile / runtime_validation` 收口。
- `validate_scan_plan` 是 canonical 的 plan precheck/read-contract 命令；兼容别名 `compile_scan_plan` 仍会走 capability guard，但不会被提升为写命令或强制占用控制租约。

## Scan-plan adapter pipeline

- preview / execution / rescan plan 在 planner 输出后统一进入 adapter pipeline。
- 当前 pipeline 固定执行：`resolve_frames -> surface_constraints -> safety_limits -> time_parameterization -> plan_digest`。
- adapter evidence 会写入 `scan_plan.validation_summary.adapter_pipeline`，用于后续 session freeze / rationale / replay 审计。


## Session-product materialization contract

Headless/session read APIs now operate in **materialized-only** mode for session-intelligence products. Missing lineage / release / governance artifacts are reported as `not_materialized` and must be regenerated through `SessionService.refresh_session_intelligence()` (or the equivalent finalize/export path) rather than being created on demand by a GET/read surface.


真实环境验证必须提供 `scripts/package_live_evidence_bundle.py` 生成的归档证据包；`scripts/write_verification_report.py --live-evidence-bundle ...` 现在会校验证据包是否真实存在且结构完整，单独给一个路径字符串不再被当成 live-controller proof。
