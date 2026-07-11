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


def test_future_effective_date_fails_audit() -> None:
    bundle = fixture_bundle()
    fundamentals = bundle.fundamentals.copy()
    fundamentals.loc[0, "effective_date"] = "2020-01-01"

    report = audit_bundle(replace(bundle, fundamentals=fundamentals))

    failed_ids = {check.check_id for check in report.checks if not check.passed}
    assert "fundamentals.effective_after_period" in failed_ids
