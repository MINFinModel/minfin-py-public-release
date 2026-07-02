"""Tests for PPA revenue FX conversion helpers."""

import pandas as pd
import pytest

from MinFin.offtaker_tariffs import (
    compute_redispatch_compensation_mn_usd,
    compute_total_ppa_revenue,
    local_energy_revenue_mn_usd,
)


def _solar_pv_frame():
    index = [2030]
    return pd.DataFrame(
        {
            "ppa_currency": ["KES"],
            "ppa_met_generation": [501.8],
            "ppa_standard_offtaker_share": [1.0],
            "ppa_standard_tariff": [12.7],
            "ppa_direct_offtaker_share": [0.0],
            "ppa_direct_offtaker_tariff": [0.0],
            "total_generation": [501.8],
            "ppa_contracted_generation": [501.8],
            "ppa_penalty_tariff": [0.0],
            "ppa_contracted_capacity": [0.0],
            "ppa_capacity_fee": [0.0],
            "redispatch_compensation_price": [0.0],
        },
        index=index,
    )


def test_local_energy_revenue_mn_usd_kes_to_usd():
    exchange_rates = pd.DataFrame({2030: {"KES": 130.0, "USD": 1.0}}).T
    rev = local_energy_revenue_mn_usd(
        pd.Series([501.8], index=[2030]),
        pd.Series([12.7], index=[2030]),
        exchange_rates,
        "KES",
    )
    assert rev.loc[2030] == pytest.approx(501.8 * 12.7 / 130.0)


def test_compute_total_ppa_revenue_applies_fx():
    exchange_rates = pd.DataFrame({2030: {"KES": 130.0, "USD": 1.0}}).T
    tech_df = _solar_pv_frame()
    rev = compute_total_ppa_revenue(tech_df, exchange_rates)
    assert rev.loc[2030] == pytest.approx(501.8 * 12.7 / 130.0)


def test_compute_total_ppa_revenue_infers_currency_from_unit_hints():
    exchange_rates = pd.DataFrame({2030: {"KES": 130.0, "USD": 1.0}}).T
    tech_df = _solar_pv_frame()
    tech_df["ppa_currency"] = 0.0
    unit_hints = {"ppa_standard_tariff": "KES/kWh"}
    rev = compute_total_ppa_revenue(tech_df, exchange_rates, unit_hints=unit_hints)
    assert rev.loc[2030] == pytest.approx(501.8 * 12.7 / 130.0)


def test_compute_redispatch_compensation_mn_usd_applies_fx():
    exchange_rates = pd.DataFrame({2030: {"KES": 100.0, "USD": 1.0}}).T
    tech_df = _solar_pv_frame()
    tech_df["redispatch_compensation_price"] = 5.0
    comp = compute_redispatch_compensation_mn_usd(
        tech_df, pd.Series([10.0], index=[2030]), exchange_rates
    )
    assert comp.loc[2030] == pytest.approx(10.0 * 5.0 / 100.0)
