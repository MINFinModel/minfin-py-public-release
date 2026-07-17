"""Foreign-exchange helpers shared across financing baseline, tariffs, and market revenue."""

from __future__ import annotations

import random
from typing import Any, Iterable, Optional

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

# Country-code aliases seen across MACRO / EXISTING INFRASTRUCTURE sheets.
CURRENCY_ALIASES: dict[str, tuple[str, ...]] = {
    "ZK": ("ZK", "ZMW"),
    "ZMW": ("ZMW", "ZK"),
}

# ``{year: {currency: rate}}`` when MACRO / sheet rates are not used
exchange_rates_by_year: dict = {}
for year in range(2010, 2080):
    exchange_rates_by_year[year] = {
        currency: round(base_rates[currency] * round(1 + random.uniform(-0.05, 0.05)), 5)
        for currency in currency_list
    }


def normalize_currency_code(code: Any, available: Optional[Iterable[str]] = None) -> str:
    """Return *code* as-is, or an alias that exists in *available* (e.g. ZMW ↔ ZK)."""
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return ""
    text = str(code).strip()
    if not text or text.lower() in {"nan", "none"}:
        return ""
    if available is None:
        return text
    avail = {str(a).strip() for a in available}
    if text in avail:
        return text
    for alt in CURRENCY_ALIASES.get(text, ()):
        if alt in avail:
            return alt
    return text


def get_exchange_rates(
    target_currency,
    currency_series,
    year_series,
    rates_by_year=None,
):
    """
    Convert volumes using year and original currency to *target_currency*.

    *rates_by_year* is optional ``{year: {currency: rate}}`` (e.g. from MACROECONOMIC).
    Conversion uses whatever currency codes appear in *currency_series* and in the
    rate table for that year — not a fixed whitelist — so historical rows in CNY /
    ZMW / etc. convert when MACRO has matching (or aliased) rates.
    """
    rd = rates_by_year if rates_by_year is not None else exchange_rates_by_year
    years = pd.to_numeric(pd.Series(year_series), errors="coerce")
    currencies = pd.Series(currency_series).astype(str).str.strip()
    years.index = pd.Series(year_series).index
    currencies.index = years.index

    out = pd.Series(index=years.index, dtype="float64")
    tgt_raw = str(target_currency).strip() if target_currency is not None else ""

    for idx in years.index:
        y = years.loc[idx]
        if pd.isna(y):
            continue
        y = int(y)
        year_rates = rd.get(y)
        if not year_rates:
            continue
        available = list(year_rates.keys())
        src = normalize_currency_code(currencies.loc[idx], available)
        tgt = normalize_currency_code(tgt_raw, available)
        src_rate = year_rates.get(src)
        tgt_rate = year_rates.get(tgt)
        if src_rate is None or tgt_rate is None:
            continue
        src_rate = float(src_rate)
        if src_rate == 0:
            continue
        out.loc[idx] = float(tgt_rate) / src_rate
    return out


def fx_rate_lookup(currency_code: str, exchange_rates: Any) -> float:
    """Look up FX for a single currency code; supports dict-like *exchange_rates*."""
    try:
        code = normalize_currency_code(
            currency_code,
            list(exchange_rates.keys()) if hasattr(exchange_rates, "keys") else None,
        )
        if isinstance(exchange_rates, dict):
            return float(exchange_rates.get(code, exchange_rates.get(currency_code, 1.0)))
        if hasattr(exchange_rates, "get"):
            return float(exchange_rates.get(code, exchange_rates.get(currency_code, 1.0)))
    except Exception:
        pass
    return 1.0


def fx_to_dashboard_currency(currency, year, dash_curr, exchange_rates):
    """Ratio dashboard_currency / currency for a year in a wide year × currency table."""
    if exchange_rates is None or dash_curr is None or year not in exchange_rates.index:
        return 1.0
    available = list(exchange_rates.columns)
    src = normalize_currency_code(currency, available)
    tgt = normalize_currency_code(dash_curr, available)
    if src not in exchange_rates.columns or tgt not in exchange_rates.columns:
        return 1.0
    rx = float(exchange_rates.loc[year, src])
    rd = float(exchange_rates.loc[year, tgt])
    return rd / rx if rx else 0.0


def macro_rates_dict_from_exchange_wide(wide: pd.DataFrame) -> dict:
    """``{year: {currency: rate}}`` for :func:`get_exchange_rates`."""
    d: dict = {}
    for year, row in wide.iterrows():
        d[int(year)] = {str(k).strip(): float(v) for k, v in row.dropna().items()}
    return d
