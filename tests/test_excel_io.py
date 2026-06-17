"""Tests for shared Excel year-column helpers."""

from pathlib import Path

import pandas as pd

from MinFin.excel_io import (
    load_workbook_variable_units,
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
