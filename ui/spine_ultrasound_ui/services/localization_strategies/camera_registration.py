
from __future__ import annotations

from spine_ultrasound_ui.services.localization_strategies.base import GuidanceLocalizationStrategy, LocalizationStrategyContract


class CameraRegistrationStrategy(GuidanceLocalizationStrategy):
    contract = LocalizationStrategyContract(
        version='camera_backed_registration_v3',
        source_type='camera_only',
        source_label='camera_backed_registration',
        detail_template='实验 {exp_id} 使用相机 guidance runtime 生成 session-freeze 引导合同。',
    )
