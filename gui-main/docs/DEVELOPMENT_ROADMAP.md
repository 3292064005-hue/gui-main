# Development Roadmap

## Fixed ordering
1. Clinical workflow and session data products
2. RT/device abstraction and safety recovery
3. Web/product shell

## Current convergence status
### Wave 1 — Clinical workflow and session data products
Implemented mainline:
- `AppController -> SessionService -> ExperimentManager`
- formal session manifest freeze
- artifact registry and processing step registry
- quality timeline, alarm timeline, replay index, session report
- session compare and QA pack
- command journal traceability

### Wave 2 — RT/device abstraction and safety
Mainline assumptions kept:
- force-control config remains the single safety config source
- mock and unavailable providers remain the required baseline providers
- alarm/recovery fields remain additive-only

### Wave 3 — Web/product shell
Implemented product shell convergence:
- schema-driven frontend force-control contract
- read-only review mode
- current session report / replay / quality / alarms / artifacts / compare / qa-pack views
- `/ws/telemetry?topics=` filtering

## Exit gates
- no second source of truth
- all public contracts schema-backed
- mock path remains runnable
- local verification remains centered on `./scripts/verify_mainline.sh`
