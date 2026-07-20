"""Local / foreign / display currency codes from MACROECONOMIC."""

from __future__ import annotations

import pandas as pd

from MinFin.financing_baseline import (
    financing_baseline_extractor,
    macroeconomic_currency_codes,
    macroeconomic_display_currency,
)


def _write_macro_workbook(path, *, local: str, foreign: str, display: str | None = "USD"):
    years = [2025, 2026]
    # Rows match pure-input MACROECONOMIC layout used by exchange_rates_wide_from_macroeconomic
    if display is None:
        display_row = [None, "Display Currency", None, None, *[None] * len(years)]
    else:
        display_row = [None, "Display Currency", None, None, display, *[None] * (len(years) - 1)]
    rows = [
        [None] * (4 + len(years)),
        [None] * (4 + len(years)),
        [None] * (4 + len(years)),
        [None] * (4 + len(years)),
        [None, "Parameter", "Code", "Unit", *years],
        [None, "1. Exchange Rates", None, None, *[None] * len(years)],
        display_row,
        [None, "Foreign Currency", foreign, "LCU/USD", 1.0, 1.0],
        [None, "Local Currency", local, "LCU/USD", 30.0, 31.0],
    ]
    mac = pd.DataFrame(rows)
    existing = pd.DataFrame(
        {
            "Technology": pd.Series(dtype=str),
            "Year": pd.Series(dtype=float),
            "Financing Source": pd.Series(dtype=str),
            "Volume of Finance": pd.Series(dtype=float),
            "Currency": pd.Series(dtype=str),
            "Rate": pd.Series(dtype=float),
            "Term": pd.Series(dtype=float),
            "Grace period": pd.Series(dtype=float),
            "Schedule": pd.Series(dtype=str),
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        mac.to_excel(writer, sheet_name="MACROECONOMIC", header=False, index=False)
        # header=4 for EXISTING INFRASTRUCTURE reader
        pd.DataFrame([[None] * 8] * 4).to_excel(
            writer, sheet_name="EXISTING INFRASTRUCTURE", header=False, index=False
        )
        existing.to_excel(writer, sheet_name="EXISTING INFRASTRUCTURE", startrow=4, index=False)
        # Minimal sheets so detect_workbook_format sees pure input
        for sheet in (
            "COVER",
            "TECHNOLOGY REGISTER",
            "INVESTMENT PLAN",
            "NEW INFRASTRUCTURE",
            "PPA REVENUE",
            "WHOLESALE REVENUE",
            "OTHER REVENUE",
        ):
            pd.DataFrame({"x": [1]}).to_excel(writer, sheet_name=sheet, index=False)


def test_macroeconomic_currency_codes(tmp_path):
    path = tmp_path / "macro.xlsx"
    _write_macro_workbook(path, local="TRY", foreign="USD")
    assert macroeconomic_currency_codes(str(path)) == ("TRY", "USD")


def test_macroeconomic_display_currency_defaults_to_usd(tmp_path):
    path = tmp_path / "no_display.xlsx"
    _write_macro_workbook(path, local="ZK", foreign="USD", display=None)
    assert macroeconomic_display_currency(str(path)) == "USD"


def test_macroeconomic_display_currency_reads_time_independent(tmp_path):
    path = tmp_path / "display_eur.xlsx"
    _write_macro_workbook(path, local="TRY", foreign="USD", display="EUR")
    assert macroeconomic_display_currency(str(path)) == "EUR"


def test_from_workbook_reads_local_foreign_currency(tmp_path):
    path = tmp_path / "pure.xlsx"
    _write_macro_workbook(path, local="TRY", foreign="USD", display="USD")
    fb = financing_baseline_extractor.from_workbook(str(path))
    assert fb.currency == "TRY"
    assert fb.foreign_currency == "USD"
    assert fb.display_currency == "USD"
    ex = fb.get_exchange_rates_by_year()
    assert "TRY" in ex.columns and "USD" in ex.columns


def test_from_workbook_reads_display_currency(tmp_path):
    path = tmp_path / "display.xlsx"
    _write_macro_workbook(path, local="ZK", foreign="USD", display="EUR")
    fb = financing_baseline_extractor.from_workbook(str(path))
    assert fb.display_currency == "EUR"
