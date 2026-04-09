# PROFILE_MATRIX

| profile   | live sdk | lab port | write commands | strict authority | evidence seal | HIL expected | sandbox |
|-----------|----------|----------|----------------|------------------|---------------|--------------|---------|
| dev       | optional | yes      | yes            | no               | relaxed       | no           | yes     |
| lab       | optional | yes      | yes            | yes              | strong        | optional     | yes     |
| research  | yes      | optional | yes            | yes              | strong        | recommended  | yes     |
| clinical  | yes      | no       | yes            | yes              | strict        | required     | no      |
| review    | no       | yes      | no             | no               | strict        | no           | no      |


- headless review may use `mock` **only** for read-only evidence / replay / contract inspection flows; write commands remain blocked by deployment profile policy.

Headless 默认运行面由 `spine_ultrasound_ui.services.runtime_mode_policy` 统一解析；`scripts/start_headless.sh` 通过 `scripts/resolve_headless_backend.py` 读取该权威决策，避免脚本默认值漂移。
