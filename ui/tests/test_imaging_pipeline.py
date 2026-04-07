import numpy as np

from spine_ultrasound_ui.imaging.assessment import run_assessment
from spine_ultrasound_ui.imaging.feature_extract import run_feature_extract
from spine_ultrasound_ui.imaging.preprocess import run_preprocess
from spine_ultrasound_ui.imaging.reconstruction import run_reconstruction


def test_imaging_pipeline_produces_structured_outputs():
    image = np.zeros((16, 16), dtype=np.uint8)
    image[4:12, 8] = 255
    image[8, 4:12] = 255

    preprocess = run_preprocess(image)
    assert preprocess["image"].shape == (16, 16)
    assert preprocess["stats"]["max"] <= 1.0

    features = run_feature_extract(preprocess)
    assert features["feature_count"] >= 1
    assert 0.0 <= features["confidence"] <= 1.0

    reconstruction = run_reconstruction(preprocess)
    assert reconstruction["curve"]
    assert reconstruction["mesh"]["point_count"] >= 1

    assessment = run_assessment(preprocess)
    assert assessment["point_count"] >= 1
    assert 0.0 <= assessment["confidence"] <= 1.0
