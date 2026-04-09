
from __future__ import annotations

from spine_ultrasound_ui.services.localization_strategies.base import GuidanceLocalizationStrategy, LocalizationStrategyContract


class HybridRegistrationStrategy(GuidanceLocalizationStrategy):
    contract = LocalizationStrategyContract(
        version='hybrid_registration_v4',
        source_type='camera_ultrasound_fusion',
        source_label='camera_backed_registration',
        detail_template='实验 {exp_id} 使用 camera 主引导与 ultrasound 校验联合生成 guidance 合同。',
    )
