"""Shared helpers for reading MinFin Excel workbooks (long tables and year columns)."""

from __future__ import annotations

import pandas as pd

YEAR_COLUMN_MIN = 2000
YEAR_COLUMN_MAX = 2200

SKIP_NON_YEAR_COLUMNS = frozenset({
    "Unnamed: 0",
    "Variable",
    "Scenario",
    "Technology",
    "Unit",
    "Currency",
    "Name",
    "Off-taker",
})

PURE_INPUT_LONG_HEADER = 3


def year_columns_from_dataframe(df: pd.DataFrame) -> list:
    """Return column labels that represent model years (int or int-like)."""
    year_cols = []
    for c in df.columns:
        if str(c) in SKIP_NON_YEAR_COLUMNS:
            continue
        try:
            y = int(float(c))
        except (TypeError, ValueError):
            continue
        if YEAR_COLUMN_MIN < y < YEAR_COLUMN_MAX:
            year_cols.append(c)
    return year_cols


def year_columns_from_index(index, *, since_year: int | None = None) -> list:
    """Return integer year labels from a DataFrame index or column index."""
    years: list = []
    for col in index:
        if isinstance(col, int):
            if since_year is None or col >= since_year:
                years.append(col)
            continue
        try:
            y = int(col)
            if since_year is None or y >= since_year:
                years.append(y)
        except (TypeError, ValueError):
            continue
    return years


def read_long_sheet(
    file_path: str,
    sheet_name: str,
    *,
    header: int = PURE_INPUT_LONG_HEADER,
) -> pd.DataFrame:
    return pd.read_excel(
        file_path, sheet_name=sheet_name, header=header, engine="openpyxl"
    )


def read_investment_plan_long(file_path: str) -> pd.DataFrame:
    return read_long_sheet(file_path, "INVESTMENT PLAN")


def _clean_unit_value(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return text if text.lower() not in {"nan", "none"} else ""


def unit_from_workbook_row(row, fallback: str = "") -> str:
    """Return the ``Unit`` cell from a long-table row, with an optional fallback."""
    if row is None:
        return fallback
    unit = _clean_unit_value(row.get("Unit") if hasattr(row, "get") else getattr(row, "Unit", None))
    if unit:
        return unit
    return fallback


INVESTMENT_PLAN_EXCEL_TO_PYTHON: dict[str, str] = {
    "Capital Cost": "capital_cost",
    "ActualGeneration": "elec_production",
    "OPEX": "opex",
    "PotentialGeneration": "potential_generation",
    "Emissions": "co2_emission",
    "Emissions Savings": "emission_savings",
    "Carbon Price": "carbon_price",
}

PURE_INPUT_REVENUE_SHEETS = ("PPA REVENUE", "WHOLESALE REVENUE", "OTHER REVENUE")


def load_workbook_variable_units(file_path: str) -> dict[str, str]:
    """Load variable units from the pure-input workbook ``Unit`` column.

    Returns a mapping keyed by both Excel ``Variable`` names and MinFin Python
    field names (e.g. ``Capital Cost`` and ``capital_cost``).
    """
    units: dict[str, str] = {}

    def _store(name: str, unit: str) -> None:
        name = str(name).strip()
        unit = _clean_unit_value(unit)
        if name and unit and name not in units:
            units[name] = unit

    inv = read_investment_plan_long(file_path)
    if "Variable" in inv.columns and "Unit" in inv.columns:
        for variable, unit in (
            inv[["Variable", "Unit"]]
            .dropna(subset=["Variable"])
            .drop_duplicates(subset=["Variable"], keep="first")
            .itertuples(index=False)
        ):
            _store(variable, unit)
            python_name = INVESTMENT_PLAN_EXCEL_TO_PYTHON.get(str(variable).strip())
            if python_name:
                _store(python_name, unit)

    from MinFin.technology_sheet_io import PURE_INPUT_STATIC_FIELD_SOURCES

    for sheet in PURE_INPUT_REVENUE_SHEETS:
        df = read_long_sheet(file_path, sheet)
        if "Variable" not in df.columns or "Unit" not in df.columns:
            continue
        for variable, unit in (
            df[["Variable", "Unit"]]
            .dropna(subset=["Variable"])
            .drop_duplicates(subset=["Variable"], keep="first")
            .itertuples(index=False)
        ):
            _store(variable, unit)
            for python_name, (src_sheet, excel_name) in PURE_INPUT_STATIC_FIELD_SOURCES.items():
                if src_sheet == sheet and excel_name == str(variable).strip():
                    _store(python_name, unit)

    _store("Share of Off-take", "%")
    return units
