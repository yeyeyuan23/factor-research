import pandas as pd

from pb_roe.data.providers.early_paper import (
    apply_membership_adjustment,
    parse_initial_csi300_members,
    parse_july_2005_adjustment,
)


def test_initial_members_and_july_adjustment_reconstruct_300_stocks() -> None:
    initial_codes = [f"000{index:03d}" for index in range(1, 300)] + ["600001"]
    initial_html = (
        '<div id="article">指数代码 000300 '
        + " ".join(initial_codes)
        + "</div>"
    ).encode()
    removed_codes = initial_codes[:14]
    added_codes = [f"002{index:03d}" for index in range(1, 15)]
    adjustment_html = (
        '<div id="article">'
        + " ".join(
            value for pair in zip(removed_codes, added_codes, strict=True) for value in pair
        )
        + "</div>"
    ).encode()

    initial = parse_initial_csi300_members(initial_html)
    removed, added = parse_july_2005_adjustment(adjustment_html)
    adjusted = apply_membership_adjustment(initial, removed, added)

    assert len(initial) == 300
    assert len(adjusted) == 300
    assert not set(removed) & set(adjusted)
    assert set(added) <= set(adjusted)


def test_early_report_period_mapping_uses_quarter_end() -> None:
    periods = [
        pd.Timestamp(year, quarter * 3, 1) + pd.offsets.MonthEnd(0)
        for year, quarter in [(2005, 1), (2005, 2), (2005, 3)]
    ]

    assert periods == list(pd.to_datetime(["2005-03-31", "2005-06-30", "2005-09-30"]))
