def evaluate_quality(image_quality: float, feature_confidence: float) -> dict:
    need_resample = image_quality < 0.7 or feature_confidence < 0.6
    return {
        "need_resample": need_resample,
        "quality_score": (image_quality + feature_confidence) / 2.0,
    }
