# Control Plane Rewrite Wave A

This wave formalizes the first stage of the platform rewrite:

- desktop command provenance now flows through `CommandOrchestrator`
- desktop governance/status projection now flows through `GovernanceCoordinator` and `UiProjectionService`
- session summary export is centralized in `SessionFacade`
- headless control-plane output now includes an explicit deployment profile and a unified control-plane snapshot
- API now exposes `/api/v1/profile` and forwards `x-spine-session-id` into command context

## Why this wave exists

The project already had the correct macro-direction:

- C++ / xCore SDK owns real robot control
- Python desktop owns orchestration, evidence, and review UX
- headless API owns network exposure

But orchestration responsibilities were still concentrated in a few large files. This wave reduces that coupling without changing the core runtime contract.

## New desktop services

- `core/command_orchestrator.py`
- `core/governance_coordinator.py`
- `core/session_facade.py`
- `core/ui_projection_service.py`

## New headless/control-plane services

- `services/deployment_profile_service.py`
- `services/control_plane_snapshot_service.py`
- `services/headless_telemetry_cache.py`
- `services/headless_control_plane_aggregator.py`

## Immediate outcome

The UI, headless API, and backend link summary now share a more explicit control-plane language:

- deployment profile
- control authority
- backend link state
- bridge observability
- config baseline
- SDK alignment
- model precheck

This is still not a substitute for real hardware validation. It is the desktop/headless governance rewrite that prepares the project for the later real-SDK / real-model integration wave.
