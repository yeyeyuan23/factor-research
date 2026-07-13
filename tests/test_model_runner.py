import json

import pytest

from pb_roe.models.runner import _load_frozen_features


def test_load_frozen_features_preserves_frozen_order(tmp_path) -> None:
    path = tmp_path / "frozen_factor_selection.json"
    path.write_text(
        json.dumps(
            {
                "config_fingerprint": "abc",
                "selected_features": ["momentum_z", "paper_score_z"],
            }
        )
    )

    selected, _ = _load_frozen_features(
        path,
        ["paper_score_z", "roe_z", "momentum_z"],
        "abc",
    )

    assert selected == ["momentum_z", "paper_score_z"]


def test_load_frozen_features_rejects_stale_config(tmp_path) -> None:
    path = tmp_path / "frozen_factor_selection.json"
    path.write_text(json.dumps({"config_fingerprint": "old", "selected_features": ["bp_z"]}))

    with pytest.raises(ValueError, match="does not match"):
        _load_frozen_features(path, ["bp_z"], "new")
