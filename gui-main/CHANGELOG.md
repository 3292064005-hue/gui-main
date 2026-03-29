# Changelog

## Rewrite round: clinical data products + headless product shell hardening
- Added runtime compatibility layer for headless/test environments without PySide6.
- Added artifact registry and processing step registry to session manifests.
- Added session compare, alarm timeline, and QA pack formal outputs.
- Added artifact JSON schemas under `schemas/` and exposed them via headless API.
- Expanded headless API with quality / alarms / artifacts / compare / qa-pack endpoints.
- Added read-only review mode to the headless adapter and frontend awareness.
- Hardened frontend contracts for expanded force-control and session-product payloads.
- Rewrote convergence docs to match the actual single-mainline architecture.

## 2026-03-28 (rewrite pass 3)
- Removed frontend-generated session identity and tightened Web state to adapter-fed execution/session truth.
- Extended session products with trends, diagnostics, annotations, stronger artifact registry metadata, and manifest freeze fields.
- Added headless read-only endpoints for trends, diagnostics, and annotations; strengthened typed frontend envelopes and session console review panel.
