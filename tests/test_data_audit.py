from dataclasses import replace

from pb_roe.data.audit import audit_bundle
from pb_roe.data.providers.fixture import fixture_bundle


def test_fixture_bundle_passes_audit() -> None:
    report = audit_bundle(
        fixture_bundle(),
        announcement_threshold=0.95,
        membership_expected_size=5,
        membership_as_of="2023-12-29",
    )

    assert report.passed
    assert all(check.passed for check in report.checks if check.severity == "error")


def test_membership_shortfall_fails_audit() -> None:
    report = audit_bundle(
        fixture_bundle(),
        membership_expected_size=10,
        membership_threshold=0.80,
        membership_as_of="2023-12-29",
    )

    failed_ids = {check.check_id for check in report.checks if not check.passed}
    assert "universe_membership.coverage" in failed_ids


def test_membership_coverage_checks_every_signal_date() -> None:
    bundle = fixture_bundle()
    membership = bundle.universe_membership.copy()
    membership.loc[membership.index[0], "member_to"] = "2023-06-01"

    report = audit_bundle(
        replace(bundle, universe_membership=membership),
        membership_expected_size=5,
        membership_threshold=0.90,
        membership_as_of=["2023-05-31", "2023-12-29"],
    )

    failed_ids = {check.check_id for check in report.checks if not check.passed}
    assert "universe_membership.coverage" in failed_ids


def test_future_effective_date_fails_audit() -> None:
    bundle = fixture_bundle()
    fundamentals = bundle.fundamentals.copy()
    fundamentals.loc[0, "effective_date"] = "2020-01-01"

    report = audit_bundle(replace(bundle, fundamentals=fundamentals))

    failed_ids = {check.check_id for check in report.checks if not check.passed}
    assert "fundamentals.effective_after_period" in failed_ids


def test_suspended_vendor_price_mismatch_does_not_fail_ohlc_audit() -> None:
    bundle = fixture_bundle()
    prices = bundle.prices.copy()
    prices.loc[0, ["open", "high", "low"]] = 11.0
    prices.loc[0, "close"] = 10.0
    prices.loc[0, "volume"] = None
    prices.loc[0, "is_suspended"] = True

    report = audit_bundle(replace(bundle, prices=prices))

    check = next(check for check in report.checks if check.check_id == "prices.ohlc_logic")
    assert check.passed


def test_tradable_missing_volume_fails_ohlc_audit() -> None:
    bundle = fixture_bundle()
    prices = bundle.prices.copy()
    prices.loc[0, "volume"] = None

    report = audit_bundle(replace(bundle, prices=prices))

    failed_ids = {check.check_id for check in report.checks if not check.passed}
    assert "prices.ohlc_logic" in failed_ids


def test_factor_coverage_reports_first_continuous_passing_month() -> None:
    bundle = fixture_bundle()
    report = audit_bundle(
        bundle,
        factor_coverage_threshold=0.80,
        factor_signal_dates=["2023-03-31", "2023-06-30", "2023-09-29"],
    )

    check = next(
        check for check in report.checks if check.check_id == "fundamentals.factor_coverage"
    )
    assert check.passed
    assert "first continuous passing month" in check.details
