
from __future__ import annotations

from spine_ultrasound_ui.services.localization_strategies.base import GuidanceLocalizationStrategy, LocalizationStrategyContract


class UltrasoundRegistrationStrategy(GuidanceLocalizationStrategy):
    contract = LocalizationStrategyContract(
        version='ultrasound_landmark_registration_v4',
        source_type='ultrasound_augmented_guidance',
        source_label='ultrasound_landmark_registration',
        detail_template='实验 {exp_id} 使用超声地标增强 guidance 合同，并保留相机预扫证据链。',
    )
