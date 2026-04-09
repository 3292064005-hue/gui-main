
from __future__ import annotations

from spine_ultrasound_ui.services.localization_strategies.base import GuidanceLocalizationStrategy, LocalizationStrategyContract


class FallbackRegistrationStrategy(GuidanceLocalizationStrategy):
    contract = LocalizationStrategyContract(
        version='fallback_simulated_registration_v4',
        source_type='fallback_simulated',
        source_label='fallback_simulated_registration',
        detail_template='实验 {exp_id} 使用回退 guidance 合同，必须人工复核后才能锁定。',
        fallback_requires_review=True,
    )
