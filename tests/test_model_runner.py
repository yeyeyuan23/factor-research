import json

import pytest

from pb_roe.models.runner import _load_model_features


def test_load_model_features_preserves_manifest_order(tmp_path) -> None:
    path = tmp_path / "model_feature_manifest.json"
    path.write_text(
        json.dumps(
            {
                "config_fingerprint": "abc",
                "eligible_features": ["momentum_z", "roe_z"],
            }
        )
    )

    selected, _ = _load_model_features(
        path,
        ["paper_score_z", "roe_z", "momentum_z"],
        "abc",
    )

    assert selected == ["momentum_z", "roe_z"]


def test_load_model_features_rejects_stale_config(tmp_path) -> None:
    path = tmp_path / "model_feature_manifest.json"
    path.write_text(json.dumps({"config_fingerprint": "old", "eligible_features": ["bp_z"]}))

    with pytest.raises(ValueError, match="does not match"):
        _load_model_features(path, ["bp_z"], "new")
