# Configuration directories

## Base runtime configs
- `base/` and top-level runtime YAML/JSON files remain the canonical desktop/runtime configuration set.

## Training configs
- `training/lamina_center_training.yaml`: deterministic baseline trainer.
- `training/lamina_center_training_monai.yaml`: MONAI-backed lamina segmentation/keypoint request.
- `training/lamina_center_training_nnunet.yaml`: nnU-Net-backed lamina segmentation request.
- `training/uca_training.yaml`: deterministic UCA ranking baseline.
- `training/uca_training_monai.yaml`: MONAI-backed UCA ranking request.
- `training/frame_anatomy_keypoint_training.yaml`: exported raw-frame anatomy-point package build config.

## Runtime model configs
The files in `models/` point runtime inference services at exported model
packages. They are optional and keep the desktop runtime import-safe when no
training frameworks are installed.


Runtime configs now default to repository-local model packages under `../../models/*`. Most of them remain deterministic research baselines. The raw-frame anatomy-point config is different: it requires an exported-weight package plus a passing benchmark manifest before the runtime adapter will load it.

- `models/frame_anatomy_keypoint_runtime.yaml`: exported-weight runtime package for per-frame raw-ultrasound anatomical point inference, with benchmark-gate thresholds and required release state.

- `models/frame_anatomy_keypoint_preweight.json`: deterministic no-weight runtime config used by the `preweight_deterministic` measured-only profile.


Profile loading now emits `profile_config_path` and `profile_load_error` metadata into reconstruction/assessment artifacts. When a weighted runtime session degrades into prior-assisted geometry, canonical `spine_curve.json` and `cobb_measurement.json` are preserved as authoritative placeholders while the contaminated payloads are written to dedicated sidecars.
