"""Tests for shared Excel year-column helpers."""

from pathlib import Path

import pandas as pd

from MinFin.excel_io import (
    load_workbook_variable_units,
    read_annual_gdp,
    year_columns_from_dataframe,
    year_columns_from_index,
)


def test_year_columns_from_dataframe():
    df = pd.DataFrame(columns=["Technology", "Variable", 2025, 2026, "notes"])
    assert year_columns_from_dataframe(df) == [2025, 2026]


def test_year_columns_from_index_since_year():
    cols = pd.Index([2020, 2024, 2025, "Total"])
    assert year_columns_from_index(cols, since_year=2024) == [2024, 2025]


def test_load_workbook_variable_units_reads_input_file():
    file_path = Path("data/MINFin Python Input File.xlsx")
    if not file_path.exists():
        return

    units = load_workbook_variable_units(str(file_path))

    assert units["capital_cost"] == "Mn USD"
    assert units["Capital Cost"] == "Mn USD"
    assert units["ppa_contracted_generation"] == "GWh/Year"
    assert units["PPA Contracted Generation"] == "GWh/Year"
    assert units["total_grant_amount"] == "Mn USD"
    assert units["Share of Off-take"] == "%"


def test_read_annual_gdp_reads_macroeconomic_series():
    file_path = Path("data/MINFin Python Input File.xlsx")
    if not file_path.exists():
        return

    gdp = read_annual_gdp(str(file_path))

    assert not gdp.empty
    assert 2025 in gdp.index
    assert gdp.loc[2025] > 0
    assert gdp.index.is_monotonic_increasing


def test_read_annual_gdp_missing_sheet_returns_empty():
    legacy = Path("data/MINFin Energy Example Input File.xlsm")
    if not legacy.exists():
        return

    gdp = read_annual_gdp(str(legacy))
    assert gdp.empty
