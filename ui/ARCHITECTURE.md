# Spine Ultrasound Platform Architecture

## Final principle
- Official xCore SDK is used only inside `cpp_robot_core`.
- Python UI never enters the 1 ms real-time loop.
- Free-space motion uses SDK non-real-time motion.
- Contact scanning defaults to Cartesian impedance.
- External pressure sensing is auxiliary; robot state remains the primary contact signal.
- ROS2 is optional and never becomes the real-time control owner.
- `cpp_robot_core` is the single execution-state authority.
- `SdkRobotFacade` is the live-binding authority for the official SDK and is frozen to the xMate3 / xMateRobot / 6-axis mainline.
- Session manifest is the single source of truth for replay/export inputs.
- Runtime command metadata is defined once in `schemas/runtime_command_manifest.json`; Python catalog and C++ registry are generated/validated from that manifest.
- FastAPI composition is app-state scoped through `ApiRuntimeContainer`; module-level singleton fallback is not part of the mainline runtime model.

## Identity contract
- `robot_model = xmate3`
- `sdk_robot_class = xMateRobot`
- `axis_count = 6`
- `preferred_link = wired_direct`
- `rt_mode = cartesianImpedance`
- Any other model/class/axis combination is rejected during runtime/profile validation.

## Execution units
1. `cpp_robot_core`: single control authority for the robot.
2. `spine_ultrasound_ui`: research platform, GUI, experiment orchestration, imaging and assessment.
3. `ros2_bridge` (optional): mirror and integration layer only.

## Layered responsibilities
### SDK-native layer
ROKAE xCore SDK primitives, robot state, NRT motion, RT motion, planner, model, collision, soft limits, logs.

### Robot abstraction layer
`SdkRobotFacade`, `RobotStateHub`, `NrtMotionService`, `RtMotionService`, `SafetyService`.

### Scan control layer
`ContactObserver`, `TrajectoryCompiler`, `ScanSupervisor`, `RecoveryManager`.

### Experiment and data layer
`ExperimentManager`, `SessionManifest`, `SyncRecorder`, `ReplayService`, `ExportService`.

### Research application layer
PySide6 GUI, `AppController`, quality monitoring, reconstruction, assessment, reporting.


## Authoritative / Advisory / Unavailable
- authoritative_final_verdict 只能来自运行时权威内核。
- advisory_precheck 仅作辅助说明，不得合成为最终裁决。
- unavailable 表示权威路径缺失或不可达。

## Control-plane authority envelope
- `authoritative_runtime_envelope` is the canonical additive contract for control authority, applied runtime config, session freeze, plan digest and final runtime verdict.
- Python backends may normalize and project that envelope, but they may not fabricate a parallel authority snapshot.
- `AppController` remains a UI/application façade; dependency assembly now lives in an internal composition root and session state/materialization are split into dedicated services.


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
- `device_readiness` now cross-checks `source_frame_set`, guidance plugin registry completeness, and review approval state instead of relying on optimistic constants alone.
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



## Closure-profile architecture

The postprocess mainline separates authoritative runtime artifacts from both prior-assisted and training-bridge artifacts. Two explicit closure profiles exist:

- `weighted_runtime`: exported-package capable, degradation-tolerant research runtime.
- `preweight_deterministic`: measured-only profile that blocks when authoritative measured rows are unavailable.

The authoritative path writes `derived/reconstruction/reconstruction_input_index.json`, `derived/reconstruction/spine_curve.json`, and `derived/assessment/cobb_measurement.json`. Prior-assisted sidecars are isolated to `derived/reconstruction/prior_assisted_curve.json` and `derived/assessment/prior_assisted_cobb.json`. When those sidecars exist, canonical `spine_curve.json` and `cobb_measurement.json` are rewritten as authoritative placeholders so contaminated geometry never occupies the authoritative artifact name. Training-bridge artifacts are isolated to `derived/training_bridge/model_ready_input_index.json`.

This keeps runtime-authoritative evidence, prior-assisted outputs, and model-preparation outputs from sharing the same namespace or closure semantics.

## Authoritative scoliosis measurement stack

The reconstruction/assessment pipeline is split into four phases:

1. **Dataset export**: locked sessions are exported into patient/session case trees for lamina-center and UCA annotation.
2. **Lamina-aware reconstruction**: synchronized US evidence is transformed into coronal-VPI projections, bone masks, lamina candidates, and an authoritative spine curve.
3. **Primary assessment**: vertebra pairing and tilt estimation drive `lamina_center_cobb` measurement artifacts plus QA overlays.
4. **Auxiliary assessment**: ranked VPI slices and bone-feature masks drive a secondary `uca_auxiliary` measurement used for agreement checks and manual-review escalation.

This stack preserves the original session/report contracts while replacing the old curve-only measurement path with a landmark-aware authoritative path.


## Offline annotation / training interface

The runtime application and the offline training stack are explicitly separated:

- `spine_ultrasound_ui/services/datasets/*` exports locked sessions into patient/session case trees.
- `spine_ultrasound_ui/training/datasets/*` loads those exports for lamina-center and UCA training.
- `spine_ultrasound_ui/training/trainers/*` produces deterministic baseline training results and model-package metadata.
- `spine_ultrasound_ui/training/exporters/model_export_service.py` turns training results into runtime-consumable packages.
- `spine_ultrasound_ui/training/runtime_adapters/*` are the only bridge back into runtime reconstruction/assessment services.

This preserves the mainline rule that MONAI Label, nnU-Net, or any future heavy training dependency must not become a direct dependency of the UI runtime process.


## Offline training and annotation boundary

The repository separates clinical runtime code from annotation/training code:

- `services/datasets/` exports authoritative session artifacts into offline datasets.
- `tools/monai_label_app/` defines the repository-owned MONAI Label skeleton.
- `training/` contains dataset adapters, training specs, trainer facades, backend request adapters, model exporters, and runtime adapters.
- runtime reconstruction/assessment services consume exported model packages only; they never import MONAI Label or nnU-Net directly.


## Offline annotation and training boundary

`tools/monai_label_app/` now contains both packaging manifests and server-side task handlers for `lamina_center` and `uca_auxiliary`.
`spine_ultrasound_ui/training/exporters/nnunet_dataset_export_service.py` owns nnU-Net raw dataset conversion.
Heavyweight dependencies remain outside the desktop runtime; runtime code only consumes exported model packages through adapters.

## Control authority capability claims

- 控制权不再只表示“谁持有租约”，还会显式记录当前 owner 已拿到的 capability claims。
- 写命令按 `hardware_lifecycle_write / session_freeze_write / nrt_motion_write / rt_motion_write / recovery_write / fault_injection_write / plan_compile / runtime_validation` 收口。
- `validate_scan_plan` 是 canonical 的 plan precheck/read-contract 命令；兼容别名 `compile_scan_plan` 仍会经过 capability guard，但不会升级为写命令，也不会隐式占用控制租约。

## Scan-plan adapter pipeline

- preview / execution / rescan plan 在 planner 输出后统一进入 adapter pipeline。
- 当前 pipeline 固定执行：`resolve_frames -> surface_constraints -> safety_limits -> time_parameterization -> plan_digest`。
- adapter evidence 会写入 `scan_plan.validation_summary.adapter_pipeline`，用于后续 session freeze / rationale / replay 审计。


## Session intelligence read policy

Session-intelligence artifacts (lineage, resume, release, governance, evidence seal, and related products) are now governed by a **materialized-only read policy**. `SessionFinalizeService` / `SessionService.refresh_session_intelligence()` is the sole supported materialization phase. Read surfaces may report `not_materialized` or `legacy_fallback_only`, but they must not regenerate session-intelligence artifacts as a side effect.


## Canonical backend authority surface

Runtime-owned governance facts are read through explicit backend methods instead of scraping nested control-plane projections. The canonical read surface is:

- `resolve_authoritative_runtime_envelope()`
- `resolve_control_authority()`
- `resolve_final_verdict(..., read_only=...)`

API/headless/core/mock backends all implement the same surface. Canonical methods are strict: they may return runtime-published facts or explicit unavailable/degraded payloads, but they must not synthesize stronger authority/envelope/verdict truth from Python-side control-plane caches. The system API exposes matching read endpoints, and backend link snapshots now copy the runtime-owned envelope/authority/verdict to the top level so UI consumers can avoid re-interpreting nested compatibility payloads.

## Typed runtime command contracts

`schemas/runtime_command_manifest.json` remains the single source of truth. In addition to the existing Python catalog and generated C++ registry include, the repository now exports a typed contract document to `spine_ultrasound_ui/contracts/generated/runtime_command_contracts.json`.

The typed contract surface is consumed by:

- `runtime_payload_validator.py`
- `ipc_protocol.protocol_schema()`
- repository gates (`check_protocol_sync.py`)

This keeps payload validation, protocol export, and generated artifacts aligned without duplicating manual command-field tables.



## Runtime command typed contracts

`schemas/runtime_command_manifest.json` now drives three generated surfaces:

- Python typed contract document: `spine_ultrasound_ui/contracts/generated/runtime_command_contracts.json`
- C++ command registry include: `cpp_robot_core/include/robot_core/generated_command_manifest.inc`
- C++ typed request/response/guard include: `cpp_robot_core/include/robot_core/generated_runtime_command_contracts.inc`

The C++ dispatcher validates payloads against the generated typed request contract before handler dispatch, validates guard contracts (lane + allowed runtime states) before invoking the handler, and validates the typed reply-envelope contract before returning a response. Response contracts and guard contracts are therefore enforced instead of remaining generation-only metadata, while Python, protocol export, and C++ stay aligned on one manifest-backed source of truth.

## RT purity gate

`python scripts/check_rt_purity_gate.py` is part of `scripts/verify_mainline.sh`.

The gate scans RT-sensitive C++ sources and rejects forbidden hot-path work such as:

- JSON construction/parsing
- filesystem writes or recorder appends
- console logging/formatting
- heap-style dynamic allocation on RT-sensitive paths
- RT-adjacent command/telemetry loop regressions in `command_server.cpp` and `telemetry_publisher.cpp`

This gate is static proof only. It does not replace HIL/live-controller timing validation.
