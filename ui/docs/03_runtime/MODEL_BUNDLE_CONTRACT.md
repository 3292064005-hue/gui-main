---
category: spec
authority: canonical
audience: runtime developers, model integrators, reviewers
owner: repository
status: active
---

# Model Bundle Contract

Runtime-consumable AI packages must carry `bundle_manifest.json` alongside `model_meta.json` and `parameters.json`.

Required top-level keys:
- `bundle_id`
- `bundle_version`
- `runtime_profile`
- `artifacts.weights_path`
- `artifacts.entrypoint`
- `compatibility.robot_models`
- `compatibility.runtime_modes`
- `metrics`

Legacy packages without `bundle_manifest.json` remain readable through the compatibility loader, but new exports must emit the bundle manifest.
