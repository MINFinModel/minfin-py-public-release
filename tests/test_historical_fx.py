"""Historical FX conversion from sheet currencies + MACRO rates."""

from __future__ import annotations

import pandas as pd

from MinFin.fx import get_exchange_rates, normalize_currency_code
from MinFin.financing_baseline import financing_baseline_extractor


def test_normalize_currency_zwm_zk_alias():
    assert normalize_currency_code("ZMW", ["ZK", "USD"]) == "ZK"
    assert normalize_currency_code("ZK", ["ZMW", "USD"]) == "ZMW"
    assert normalize_currency_code("CNY", ["ZK", "USD", "CNY"]) == "CNY"


def test_get_exchange_rates_uses_historical_codes_not_whitelist():
    rates = {
        2020: {"USD": 1.0, "ZK": 20.0, "CNY": 7.0},
        2021: {"USD": 1.0, "ZK": 22.0, "CNY": 7.2},
    }
    hist = pd.DataFrame(
        {
            "Year": [2020, 2020, 2021],
            "Currency": ["CNY", "ZMW", "USD"],
            "Volume of Finance": [70.0, 40.0, 10.0],
        }
    )
    to_usd = get_exchange_rates("USD", hist["Currency"], hist["Year"], rates)
    # CNY 70 -> USD: 70 * (1/7) = 10
    assert abs(float(to_usd.iloc[0]) - (1.0 / 7.0)) < 1e-9
    # ZMW aliased to ZK: 40 * (1/20) factor
    assert abs(float(to_usd.iloc[1]) - (1.0 / 20.0)) < 1e-9
    assert abs(float(to_usd.iloc[2]) - 1.0) < 1e-9

    to_zk = get_exchange_rates("ZK", hist["Currency"], hist["Year"], rates)
    assert abs(float(to_zk.iloc[1]) - 1.0) < 1e-9  # ZMW→ZK identity via alias


def test_add_columns_converts_mixed_historical_currencies():
    rates = {2015: {"USD": 1.0, "ZK": 10.0, "CNY": 5.0, "EUR": 0.8, "JPY": 100.0}}
    hist = pd.DataFrame(
        {
            "Year": [2015, 2015, 2015],
            "Currency": ["CNY", "ZMW", "EUR"],
            "Volume of Finance": [50.0, 100.0, 8.0],
            "Term": [10, 10, 10],
        }
    )
    fb = financing_baseline_extractor(
        pd.DataFrame(),
        currency="ZK",
        foreign_currency="USD",
        starting_year=2024,
        macro_rates_dict=rates,
        historical_from_existing=hist,
    )
    out = fb.historical
    assert "Volume in ZK" in out.columns
    assert "Volume in USD" in out.columns
    # CNY 50 → ZK: 50 * (10/5) = 100
    assert abs(float(out.loc[0, "Volume in ZK"]) - 100.0) < 1e-6
    # ZMW 100 → ZK via alias: 100
    assert abs(float(out.loc[1, "Volume in ZK"]) - 100.0) < 1e-6
    # EUR 8 → USD: 8 * (1/0.8) = 10
    assert abs(float(out.loc[2, "Volume in USD"]) - 10.0) < 1e-6
