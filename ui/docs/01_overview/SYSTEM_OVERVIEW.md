---
category: overview
authority: canonical
audience: developers, operators, reviewers
owner: repository
status: active
---

# System Overview

## Formal domains
The formal mainline repository contains these domains:
- `configs/`
- `cpp_robot_core/`
- `spine_ultrasound_ui/`
- `schemas/`
- `scripts/`
- `tests/`
- `docs/`
- `runtime/`

Historical and non-mainline retained material lives under `archive/` and must not be interpreted as current execution or documentation authority.

## High-level architecture
- **C++ runtime core** owns real robot SDK binding, motion authority, execution plan runtime, and final runtime verdicts.
- **Python desktop/headless layer** owns workflow, orchestration, evidence handling, review flows, and UI/backend adaptation.
- **Schemas and runtime artifacts** define the stable contract for evidence, replay, manifests, and model bundles.

## Canonical authority statements
- Real SDK binding is allowed only inside `cpp_robot_core`.
- Desktop, API, and mock layers may project runtime state, but they do not own execution truth.
- Session freeze and runtime envelope are the authoritative cross-layer artifacts.

## Backend surfaces
- `mock`: contract and UI development only.
- `core`: authoritative runtime transport surface.
- `api`: explicit integration/review surface, not a substitute for robot-core truth.

## Robot mainline identity
Current formal robot mainline is restricted to the xMate collaborative path declared in runtime/profile policy. Identity drift across docs, Python, and C++ must be rejected.

## Execution units
1. `cpp_robot_core`: single control authority for robot execution, SDK binding, and runtime verdicts.
2. `spine_ultrasound_ui`: workflow, GUI, evidence handling, review flows, imaging, and assessment.
3. `ros2_bridge` (optional): mirror/integration layer only; it never becomes the real-time control owner.

## Architecture constraints
- `cpp_robot_core` is the single execution-state authority.
- `SdkRobotFacade` is the live-binding authority for the official SDK and is frozen to the xMate collaborative mainline.
- Session manifest and the runtime envelope are the authoritative cross-layer artifacts for replay, export, and execution provenance.

## Mainline identity contract
- `robot_model = xmate3`
- `sdk_robot_class = xMateRobot`
- `axis_count = 6`
- `preferred_link = wired_direct`
- `rt_mode = cartesianImpedance`
- Any other model/class/axis combination is rejected during runtime/profile validation.
