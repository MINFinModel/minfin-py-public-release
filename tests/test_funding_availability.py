"""Tests for the funding-availability composition helpers."""

import pandas as pd

from MinFin.high_level_dashboard import (
    CapitalInjection,
    FUNDING_AVAILABILITY_COMPONENTS,
    capital_injection_inflow_by_year,
    compute_funding_availability,
)


def test_compute_funding_availability_sums_components():
    years = [2025, 2026]
    df = compute_funding_availability(
        years,
        cashflows=pd.Series([10.0, 20.0], index=years),
        liabilities_payments=pd.Series([1.0, 2.0], index=years),
        carbon_credits=pd.Series([5.0, 6.0], index=years),
        capital_injection=pd.Series([3.0, 0.0], index=years),
        government_budget=pd.Series([100.0, 100.0], index=years),
    )

    assert list(df.index) == list(FUNDING_AVAILABILITY_COMPONENTS) + ["Total"]
    # Total = gov budget + liabilities + cashflows + capital injection + carbon credits
    assert df.loc["Total", 2025] == 100.0 + 1.0 + 10.0 + 3.0 + 5.0
    assert df.loc["Total", 2026] == 100.0 + 2.0 + 20.0 + 0.0 + 6.0


def test_government_budget_is_reserved_and_defaults_to_zero():
    years = [2025, 2026]
    df = compute_funding_availability(
        years,
        cashflows=pd.Series([10.0, 20.0], index=years),
        liabilities_payments=pd.Series([1.0, 2.0], index=years),
        carbon_credits=pd.Series([5.0, 6.0], index=years),
    )

    assert (df.loc["Government Budget", :] == 0.0).all()
    assert (df.loc["Capital Injection", :] == 0.0).all()
    assert df.loc["Total", 2025] == 0.0 + 1.0 + 10.0 + 0.0 + 5.0


def test_capital_injection_spreads_over_duration():
    years = list(range(2024, 2029))
    ci = CapitalInjection(start_year=2025, volume=300.0, duration=3)
    inflow = capital_injection_inflow_by_year(ci, years)

    assert inflow.loc[2024] == 0.0
    assert inflow.loc[2025] == 100.0
    assert inflow.loc[2026] == 100.0
    assert inflow.loc[2027] == 100.0
    assert inflow.loc[2028] == 0.0

    df = compute_funding_availability(years, capital_injection=ci)
    assert df.loc["Capital Injection", 2025] == 100.0
    assert df.loc["Total", 2025] == 100.0


def test_compute_funding_availability_aligns_partial_year_index():
    years = [2025, 2026, 2027]
    # cashflows only covers two of the three years; missing year -> 0
    df = compute_funding_availability(
        years,
        cashflows=pd.Series([10.0, 20.0], index=[2025, 2026]),
    )
    assert df.loc["Cashflows", 2027] == 0.0
    assert df.loc["Total", 2025] == 10.0
