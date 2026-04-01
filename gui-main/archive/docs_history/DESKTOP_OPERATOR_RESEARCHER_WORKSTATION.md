# Desktop Operator / Researcher Workstation

## Scope
- Single computer workstation only
- Two workspaces only: operator and researcher
- Single clinical mainline only: xMate ER3 + xCore SDK C++ + external force sensor + camera registration + ultrasound acquisition + scoliosis assessment

## Operator workspace
The operator workspace is the execution workstation. It owns readiness validation, patient registration confirmation, scan protocol confirmation, live contact monitoring, recovery visibility, rescan recommendations, and export readiness.

### Operator panels
- SystemReadinessPanel
- PatientRegistrationPanel
- ScanProtocolPanel
- LockFreezePanel
- ProbeContactPanel
- RecoveryStatusPanel
- UltrasoundQualityPanel
- RescanRecommendationPanel
- ExportCenterPanel

### Operator rules
- Only the operator workspace may issue write commands
- All write commands still pass backend role-gate validation
- UI is ordered around execution flow, not generic monitoring

## Researcher workspace
The researcher workspace is the analysis workstation. It owns replay, frame sync, command trace, compare/trends, assessment review, diagnostics, artifact dependencies, and annotation-aware review.

### Researcher panels
- SessionOverviewPanel
- SessionComparePanel
- TrendAnalysisPanel
- AssessmentReviewDesk
- FrameSyncPanel
- CommandTracePanel
- QaPackPanel
- ArtifactExplorerPanel
- ArtifactDependencyPanel
- DiagnosticsSummaryPanel

### Researcher rules
- Researcher workspace is read-only for execution
- Researcher actions are limited to review, replay, diagnostics, annotation and analysis
- Write commands are blocked both in the frontend and backend

## Event-driven product refresh
The workstation now consumes product update events over telemetry topics rather than relying only on full polling. Important topics include:
- session_product_update
- artifact_ready
- report_updated
- replay_updated
- quality_updated
- alarms_updated
- compare_updated
- trends_updated
- diagnostics_updated
- qa_pack_updated
- command_trace_updated
- assessment_updated

Operator and researcher workspaces subscribe to different topic sets to reduce unnecessary refresh load.

## Current convergence goals
1. Keep execution truth in the C++ runtime only
2. Keep session/product truth in the backend only
3. Keep the frontend strictly contract-driven
4. Keep operator and researcher capabilities separated by policy
