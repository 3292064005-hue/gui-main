# Canonical Module Registry

P2 收口后，仓库只允许以下 canonical 导入面：

| 旧 shim / 别名 | canonical 路径 |
| --- | --- |
| `spine_ultrasound_ui.compat` | `tests.runtime_compat` |
| `spine_ultrasound_ui.core.event_bus` | `spine_ultrasound_ui.core.ui_local_bus` |
| `spine_ultrasound_ui.services.runtime_event_platform` | `spine_ultrasound_ui.services.event_bus` / `spine_ultrasound_ui.services.event_replay_bus` |
| `spine_ultrasound_ui.services.sdk_unit_contract` | `spine_ultrasound_ui.utils.sdk_unit_contract` |
| `spine_ultrasound_ui.core_pipeline.shm_client` | `spine_ultrasound_ui.services.transport.shm_client` |

约束：

1. 不允许重新引入 shim 文件。
2. 不允许在任何正式代码路径中导入旧 shim。
3. `enable_runtime_compat()` 只允许从 `tests.runtime_compat` 获取。
4. `scripts/check_canonical_imports.py` 是该约束的自动审计入口。
