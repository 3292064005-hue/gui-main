
# AppController Dependency Audit

This audit records which collaborators are now owned by the composition root and which ones remain runtime-bound direct constructions inside `AppController`.

## Composition-owned collaborators

The following services must be materialized by `build_app_controller_composition(...)` and injected into `AppController`:

- `ConfigService`
- `RuntimePersistenceService`
- `TelemetryStore`
- `ExperimentManager`
- `SessionService`
- `PlanService`
- `PostprocessService`
- `GuidanceReviewService`
- `SdkCapabilityService`
- `ClinicalConfigService`
- `SdkRuntimeAssetService`
- `RuntimeVerdictKernelService`
- `SessionGovernanceService`
- `BridgeObservabilityService`
- `DeploymentProfileService`
- `ControlPlaneSnapshotService`
- `ViewStateFactory`
- `SessionFacade`
- `UiProjectionService`

## Runtime-bound direct constructions retained in `AppController`

The following collaborators remain direct constructions because they bind live controller state, backend handles, or self-referential projection callbacks at runtime:

- `CommandOrchestrator`
  - Requires the concrete backend instance and the active `SessionService`.
- `GovernanceCoordinator`
  - Aggregates already-materialized services into a runtime coordination object.
- `ControlPlaneReader`
  - Binds the `GovernanceCoordinator`, UI projection service, and `AppController.get_persistence_snapshot` callback.
- `AppRuntimeBridge`
  - Holds a back-reference to the concrete `AppController` façade.

These objects are intentionally retained as runtime-bound adapters. Moving them into the composition root requires extracting host-side protocols for state snapshots and UI callback surfaces; that migration is intentionally out-of-scope for the current patch set to avoid widening the compatibility surface.
