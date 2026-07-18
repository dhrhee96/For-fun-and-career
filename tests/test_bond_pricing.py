from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bond_pricing import (  # noqa: E402
    BondSpec,
    accrued_interest,
    accrued_interest_details,
    price_bond,
    price_bond_clean,
    price_bond_dirty,
)


def test_accrued_interest_is_zero_on_coupon_date():
    spec = BondSpec(
        face_value=10_000,
        coupon_rate=0.04,
        coupon_frequency=2,
        issue_date="2025-01-01",
        maturity_date="2027-01-01",
        settlement_date="2026-01-01",
    )

    details = accrued_interest_details(spec)

    assert accrued_interest(spec) == pytest.approx(0.0)
    assert details["previous_coupon_date"].isoformat() == "2026-01-01"
    assert details["next_coupon_date"].isoformat() == "2026-07-01"
    assert details["elapsed_days"] == 0


def test_accrued_interest_is_about_halfway_through_period():
    spec = BondSpec(
        face_value=10_000,
        coupon_rate=0.04,
        coupon_frequency=2,
        issue_date="2025-01-01",
        maturity_date="2027-01-01",
        settlement_date="2026-04-01",
    )

    assert accrued_interest(spec) == pytest.approx(100.0, rel=0.02)


def test_dirty_price_equals_clean_price_plus_accrued_interest():
    spec = BondSpec(
        face_value=10_000,
        coupon_rate=0.04,
        coupon_frequency=2,
        issue_date="2025-01-01",
        maturity_date="2027-01-01",
        settlement_date="2026-04-01",
    )
    ytm = 0.035

    assert price_bond_dirty(spec, ytm) == pytest.approx(price_bond_clean(spec, ytm) + accrued_interest(spec))


def test_legacy_maturity_years_pricing_still_works():
    spec = BondSpec(face_value=10_000, coupon_rate=0.035, maturity_years=3, coupon_frequency=2)

    assert price_bond(spec, 0.038) == pytest.approx(9915.6942, rel=1e-6)


def test_non_positive_face_value_is_rejected():
    with pytest.raises(ValueError):
        BondSpec(face_value=0, coupon_rate=0.035, maturity_years=3, coupon_frequency=2)
