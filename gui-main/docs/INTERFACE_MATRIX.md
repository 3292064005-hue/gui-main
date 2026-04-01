# Interface Matrix

| Layer | Owns robot control? | Reads SDK directly? | Runs RT loop? | Writes experiment data? |
|---|---:|---:|---:|---:|
| cpp_robot_core | Yes | Yes | Yes | No |
| spine_ultrasound_ui/services/robot_core_client.py | No | No | No | No |
| spine_ultrasound_ui/core/experiment_manager.py | No | No | No | Yes |
| spine_ultrasound_ui/imaging/* | No | No | No | Yes |
| ros2_bridge (optional) | No | No | No | Optional |


## Runtime contract

| Contract | Producer | Primary consumers | Notes |
|---|---|---|---|
| `ControlPlaneSnapshot` | headless / backend control-plane aggregator | Desktop, Web, replay, evidence | Canonical governance snapshot. |
| `final_verdict` | `cpp_robot_core` command contract (`compile_scan_plan`, `query_final_verdict`) | Desktop runtime verdict kernel, API bridge, headless review | Python advisory report may enrich presentation but may not overrule it. |
| `EvidenceEnvelope` | session intelligence / evidence seal services | replay, diagnostics, export | Freeze-point and lineage governed artifacts. |
