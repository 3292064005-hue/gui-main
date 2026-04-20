# Deployment Source Policy

## Purpose

This document defines the authoritative runtime-source boundary for the spine UI mainline.
The goal is to ensure that preview, session lock, and execution-write surfaces do not silently
mix simulated, replay, and live inputs under the same operational claim.

## Source tiers

- `live`: measured hardware-backed guidance or force facts.
- `replay`: recorded/replayed evidence, valid for review and some lab workflows.
- `simulated`: synthetic or mock inputs, valid only for development preview.
- `unknown`: unclassified source, treated conservatively.

## Deployment profiles

### dev
- Preview: allowed for live/replay/simulated.
- Session lock: allowed.
- Execution write: allowed.
- Contract-shell writes: allowed.
- Semantics: local iteration only.

### lab
- Preview: allowed for live/replay/simulated.
- Session lock: blocked when guidance is simulated.
- Execution write: allowed.
- Contract-shell writes: allowed.
- Semantics: controlled bring-up and rehearsal.

### research
- Preview: requires live guidance.
- Session lock: requires live guidance and live force.
- Execution write: requires live guidance and live force.
- Contract-shell writes: forbidden.
- Semantics: real execution with strong evidence boundary.

### clinical
- Preview: requires live guidance.
- Session lock: requires live guidance and live force.
- Execution write: requires live guidance and live force.
- Contract-shell writes: forbidden.
- Semantics: strict execution and audit surface.

### review
- Preview: allowed, including replay and simulated evidence.
- Session lock: not intended.
- Execution write: forbidden.
- Contract-shell writes: forbidden.
- Semantics: read-only review and offline analysis.

## Export placeholder boundary

Dataset export keeps a deterministic directory contract, but placeholder files are **not**
authoritative evidence. Every exported case writes `export_manifest.json` with:

- `artifact_states`
- `integrity_state`
- `placeholder_artifact_count`
- `claim_boundary`

Consumers must read the manifest instead of inferring truth from file presence alone.

## Migration notes

1. Existing exporters remain directory-compatible.
2. New consumers should switch to `export_manifest.json` as the source of truth.
3. Session-lock callers must provide guidance/source-frame facts that can be classified.
4. Desktop surfaces should use capability/page contracts instead of unconditional tab exposure.

## Rollback

If this boundary needs temporary rollback for local debugging:

1. use `SPINE_DEPLOYMENT_PROFILE=dev`, or
2. use `SPINE_DEPLOYMENT_PROFILE=lab` for controlled rehearsal.

Research and clinical profiles must not be rolled back to contract-shell writes.
