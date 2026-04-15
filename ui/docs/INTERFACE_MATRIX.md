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
| `AuthoritativeGovernanceProjection` | `RuntimeGovernanceProjectionService` | Desktop view-state, status presenters, runtime doctor, task tree, session summary | Read-only projection of `control_authority`, `final_verdict`, and `authoritative_runtime_envelope`. Consumers may not re-adjudicate the runtime truth. |
| `final_verdict` | `cpp_robot_core` command contract (`validate_scan_plan`, `query_final_verdict`; backend canonical API: `resolve_final_verdict(read_only=...)`) | Desktop runtime verdict kernel, API bridge, headless review | Python advisory report may enrich presentation but may not overrule it. |
| `EvidenceEnvelope` | session intelligence / evidence seal services | replay, diagnostics, export | Freeze-point and lineage governed artifacts. |

| `RuntimeGovernanceQuerySurface` | `RuntimeGovernanceProjectionService` | Control-plane snapshot, UI projection, runtime doctor, task tree | Dedicated read-only query surface for governance facts. Consumers must not bypass it to re-adjudicate runtime truth. |
| `AuthorityMetadataV1` | `session/authority_metadata_v1.schema.json` | Assessment/reconstruction/read surfaces | Additive authority metadata carried by exported session products so degraded or prior-assisted outputs are never rendered as runtime-authoritative. |
