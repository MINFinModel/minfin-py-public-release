"""Foreign-exchange helpers shared across financing baseline, tariffs, and market revenue."""

from __future__ import annotations

import random
from typing import Any

import pandas as pd

currency_list = [
    "KES", "USD", "EUR", "GBP", "JPY", "CNY", "INR", "AUD", "CAD",
    "OT4", "OT5", "OT6", "OT7", "OT8",
]
base_rates = {
    "KES": 2,
    "USD": 3.0,
    "EUR": 1.08,
    "GBP": 1.36,
    "JPY": 0.007,
    "CNY": 0.42,
    "INR": 0.036,
    "AUD": 2.0,
    "CAD": 2.2,
    "OT4": 1.0,
    "OT5": 1.0,
    "OT6": 1.0,
    "OT7": 1.0,
    "OT8": 1.0,
}

# ``{year: {currency: rate}}`` when MACRO / sheet rates are not used
exchange_rates_by_year: dict = {}
for year in range(2010, 2080):
    exchange_rates_by_year[year] = {
        currency: round(base_rates[currency] * round(1 + random.uniform(-0.05, 0.05)), 5)
        for currency in currency_list
    }


def get_exchange_rates(
    target_currency,
    currency_series,
    year_series,
    rates_by_year=None,
):
    """
    Convert volumes using year and original currency to *target_currency*.

    *rates_by_year* is optional ``{year: {currency: rate}}`` (e.g. from MACROECONOMIC).
    """
    rd = rates_by_year if rates_by_year is not None else exchange_rates_by_year
    year_series = year_series.astype(int)
    mask = year_series.isin(rd.keys()) & currency_series.isin(currency_list)
    rates = year_series[mask].map(lambda y: rd[y]).combine(
        currency_series[mask], lambda rates_dict, c: rates_dict.get(c, None)
    )
    target_rates = year_series[mask].map(lambda y: rd[y].get(target_currency, 1))
    return target_rates / rates


def fx_rate_lookup(currency_code: str, exchange_rates: Any) -> float:
    """Look up FX for a single currency code; supports dict-like *exchange_rates*."""
    try:
        if isinstance(exchange_rates, dict):
            return float(exchange_rates.get(currency_code, 1.0))
        if hasattr(exchange_rates, "get"):
            return float(exchange_rates.get(currency_code, 1.0))
    except Exception:
        pass
    return 1.0


def fx_to_dashboard_currency(currency, year, dash_curr, exchange_rates):
    """Ratio dashboard_currency / currency for a year in a wide year × currency table."""
    if (
        exchange_rates is None
        or dash_curr is None
        or currency not in exchange_rates.columns
        or dash_curr not in exchange_rates.columns
        or year not in exchange_rates.index
    ):
        return 1.0
    rx = float(exchange_rates.loc[year, currency])
    rd = float(exchange_rates.loc[year, dash_curr])
    return rd / rx if rx else 0.0


def macro_rates_dict_from_exchange_wide(wide: pd.DataFrame) -> dict:
    """``{year: {currency: rate}}`` for :func:`get_exchange_rates`."""
    d: dict = {}
    for year, row in wide.iterrows():
        d[int(year)] = {k: float(v) for k, v in row.dropna().items()}
    return d
