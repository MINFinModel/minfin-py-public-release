"""Tests for PPA revenue FX conversion helpers."""

import pandas as pd
import pytest

from MinFin.offtaker_tariffs import (
    apply_network_receivables,
    compute_capacity_purchased_series,
    compute_generation_purchased_series,
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


def test_network_generation_and_capacity_tariffs_convert_to_usd():
    exchange_rates = pd.DataFrame({2030: {"KES": 120.0, "USD": 1.0}}).T
    df_technologies = pd.DataFrame(
        {
            "Technology": ["Solar PV", "Transmission", "Distribution"],
            "Classification": ["Generation", "Transmission", "Distribution"],
        }
    )
    tech_dataframes = {
        "Solar PV": pd.DataFrame(
            {
                "whole_sale_generation": [0.0],
                "ppa_met_generation": [100.0],
                "ppa_standard_offtaker_share": [1.0],
                "ppa_standard_tariff": [12.0],
                "ppa_currency": ["KES"],
                "ppa_contracted_capacity": [10.0],
                "ppa_capacity_fee": [120.0],
            },
            index=[2030],
        ),
        "Transmission": pd.DataFrame(index=[2030]),
        "Distribution": pd.DataFrame(index=[2030]),
    }
    organized_offtaker = pd.DataFrame(columns=["Category", "Name", "Currency"])

    _gp, tariff = compute_generation_purchased_series(
        "Transmission",
        tech_dataframes,
        pd.DataFrame(index=[2030]),
        df_technologies,
        organized_offtaker,
        exchange_rates=exchange_rates,
        dash_curr="USD",
    )
    cap, fee = compute_capacity_purchased_series(
        "Transmission",
        tech_dataframes,
        df_technologies,
        exchange_rates=exchange_rates,
        dash_curr="USD",
    )

    assert tariff.loc[2030] == pytest.approx(0.1)
    assert cap.loc[2030] == pytest.approx(10.0)
    assert fee.loc[2030] == pytest.approx(1.0)


def test_apply_network_receivables_links_transmission_and_distribution():
    df_technologies = pd.DataFrame(
        {
            "Technology": ["Transmission", "Distribution"],
            "Classification": ["Transmission", "Distribution"],
        }
    )
    tech_dataframes = {
        "Transmission": pd.DataFrame({"power_purchase_cost": [5.0]}, index=[2030]),
        "Distribution": pd.DataFrame(index=[2030]),
    }

    apply_network_receivables(tech_dataframes, df_technologies)

    assert tech_dataframes["Transmission"].loc[2030, "receivables"] == 5.0
    assert tech_dataframes["Distribution"].loc[2030, "receivables"] == -5.0


def test_apply_network_receivables_preserves_pure_input_values():
    df_technologies = pd.DataFrame(
        {
            "Technology": ["Transmission", "Distribution"],
            "Classification": ["Transmission", "Distribution"],
        }
    )
    tech_dataframes = {
        "Transmission": pd.DataFrame(
            {"power_purchase_cost": [5.0], "receivables": [2.0]},
            index=[2030],
        ),
        "Distribution": pd.DataFrame({"receivables": [-2.0]}, index=[2030]),
    }

    apply_network_receivables(tech_dataframes, df_technologies)

    assert tech_dataframes["Transmission"].loc[2030, "receivables"] == 2.0
    assert tech_dataframes["Distribution"].loc[2030, "receivables"] == -2.0


def test_apply_network_receivables_can_preserve_zero_input_values():
    df_technologies = pd.DataFrame(
        {
            "Technology": ["Transmission", "Distribution"],
            "Classification": ["Transmission", "Distribution"],
        }
    )
    tech_dataframes = {
        "Transmission": pd.DataFrame(
            {"power_purchase_cost": [5.0], "receivables": [0.0]},
            index=[2030],
        ),
        "Distribution": pd.DataFrame({"receivables": [0.0]}, index=[2030]),
    }

    apply_network_receivables(
        tech_dataframes,
        df_technologies,
        preserve_zero_existing=True,
    )

    assert tech_dataframes["Transmission"].loc[2030, "receivables"] == 0.0
    assert tech_dataframes["Distribution"].loc[2030, "receivables"] == 0.0
