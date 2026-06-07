"""Technology Disag sheet extraction: relative row offsets and per-tech DataFrames."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Union

import numpy as np
import pandas as pd

from MinFin.excel_io import read_long_sheet, unit_from_workbook_row, year_columns_from_dataframe
from MinFin.workbook_format import WORKBOOK_FORMAT_PURE_INPUT, detect_workbook_format

# Default anchors for "Technology Disag (S1)" layout (matches MINFin Energy workbook structure).
TECH_START_ROWS: dict[str, int] = {
    "Biomass": 83,
    "CSP": 154,
    "Geothermal": 225,
    "Hydropower": 296,
    "Direct Hydro": 367,
    "Nuclear": 438,
    "Solar PV": 509,
    "Direct Solar": 580,
    "Imports": 651,
    "Wind": 722,
    "Coal": 793,
    "Gas": 864,
    "Direct Oil": 935,
    "Oil": 1006,
    "Transmission": 1077,
    "Distribution": 1148,
    "Energy Exports": 1219,
}

# Pure-input workbook (``MINFin Python Input File.xlsx``): static fields map to long-table Variable names.
PURE_INPUT_STATIC_FIELD_SOURCES: dict[str, tuple[str, str]] = {
    "total_grant_amount": ("OTHER REVENUE", "Grants"),
    "ppa_contracted_generation": ("PPA REVENUE", "PPA Contracted Generation"),
    "ppa_standard_offtaker_share": ("PPA REVENUE", "Standard Off-taker Share"),
    "ppa_direct_offtaker_tariff": ("PPA REVENUE", "Direct Off-taker Tariff"),
    "ppa_standard_tariff": ("PPA REVENUE", "Standard Off-taker Tariff"),
    "ppa_contracted_capacity": ("PPA REVENUE", "PPA Contracted Capacity"),
    "ppa_capacity_fee": ("PPA REVENUE", "PPA Capacity Fee"),
    "ppa_penalty_tariff": ("PPA REVENUE", "PPA Penalty Tariff"),
    "redispatch_compensation_price": ("PPA REVENUE", "Redispatch Compensation Price"),
    "corporate_tax_rate": ("OTHER REVENUE", "Corporate Tax Rate"),
    "receivables": ("OTHER REVENUE", "Receivables"),
    "liabilities": ("OTHER REVENUE", "Liabilities"),
}

DEFAULT_FIELD_RELATIVE_POSITIONS: dict[str, dict] = {
    "total_grant_amount": {"offset": 22, "unit": "Million USD"},
    "ppa_currency": {"offset": 25, "unit": "Currency"},
    "ppa_contracted_generation": {"offset": 26, "unit": "GWh/Year"},
    "ppa_standard_offtaker_share": {"offset": 27, "unit": "%"},
    "ppa_direct_offtaker_tariff": {"offset": 29, "unit": "USD/kWh"},
    "ppa_standard_tariff": {"offset": 30, "unit": "USD/kWh"},
    "ppa_contracted_capacity": {"offset": 31, "unit": "MW"},
    "ppa_capacity_fee": {"offset": 32, "unit": "Million USD/MW"},
    "ppa_penalty_tariff": {"offset": 33, "unit": "USD/kWh"},
    "redispatch_compensation_price": {"offset": 35, "unit": "USD/kWh"},
    "corporate_tax_rate": {"offset": 55, "unit": ""},
    "receivables": {"offset": 57, "unit": "Million USD"},
    "liabilities": {"offset": 58, "unit": "Million USD"},
}


def generate_share_configs(
    tech_name: str,
    organized_offtaker: pd.DataFrame,
    tech_to_class_map: dict[str, str],
    share_start_offset: int = 38,
    price_start_offset: int = 44,
) -> dict:
    """Build dynamic share / sale_price field configs from offtaker rows for one technology."""
    configs: dict = {}
    filtered_df = organized_offtaker[
        organized_offtaker["Category"].str.lower().apply(
            lambda x: x in tech_to_class_map[tech_name].lower()
        )
    ]
    count = 0
    for _, row in filtered_df.iterrows():
        if str(row.get("Category", "")).strip().lower() != "exports":
            name = row["Name"]
            base_slug = name.lower().replace(" ", "_").replace(":", "").replace("-", "_")
            share_key = f"{base_slug}_share_{row['Currency']}"
            configs[share_key] = {
                "offset": share_start_offset + count,
                "unit": "%",
                "type": "share",
            }
            price_key = f"{base_slug}_sale_price_{row['Currency']}"
            configs[price_key] = {
                "offset": price_start_offset + count,
                "unit": "",
                "type": "price",
            }
            count += 1
    return configs


@lru_cache(maxsize=8)
def _read_pure_input_long_sheet(file_path: str, sheet: str) -> pd.DataFrame:
    return read_long_sheet(file_path, sheet)


def pure_input_tech_sheets() -> tuple[str, str, str]:
    """Return (PPA, WHOLESALE, OTHER) sheet names for the pure-input workbook."""
    return ("PPA REVENUE", "WHOLESALE REVENUE", "OTHER REVENUE")


def use_pure_input_tech_extraction(file_path: str) -> bool:
    """True if *file_path* is the long-table workbook (no Technology Disag sheet)."""
    return detect_workbook_format(file_path) == WORKBOOK_FORMAT_PURE_INPUT


def new_infrastructure_technology_list(file_path: str) -> list[str]:
    """Return parent technology names from **NEW INFRASTRUCTURE** column B (rows starting at 6).

    The pure-input workbook treats this sheet as the authoritative list of technologies that have
    financing parameters. Use it to drive ``df_technologies`` filtering, the financing-config loop,
    and ``InvestmentAllocator`` rather than relying on TECHNOLOGY REGISTER, so removing a tech from
    NEW INFRASTRUCTURE removes it everywhere downstream.
    """
    raw = pd.read_excel(file_path, sheet_name="NEW INFRASTRUCTURE", header=None, engine="openpyxl")
    techs: list[str] = []
    seen: set[str] = set()
    for v in raw.iloc[5:, 1].tolist():
        if pd.isna(v):
            continue
        s = str(v).strip()
        if s and s not in seen:
            seen.add(s)
            techs.append(s)
    return techs


def technology_disag_s1_from_new_infrastructure(file_path: str) -> pd.DataFrame:
    """
    Build a ``Technology Disag (S1)``-shaped frame from **NEW INFRASTRUCTURE** in the pure-input workbook.

    Layout (header rows 2/3/4 = Source / Category / Parameter; technologies in column B from row 5):
    - Sources: ``Comm_Intl``, ``Comm_Dom``, ``Conc_IFI``, ``Conc_DPS``.
    - Categories: ``Debt``, ``Equity``, ``Financing Shares``, ``Foreign Currency Shares``.
    - Parameters: ``Interest Rate``, ``Grace Period``, ``Loan Term``, ``Rate of Return``, ``Project Life``,
      ``Debt Share``, ``Equity Share``, ``Share of Finance``, ``Debt``, ``Equity``.

    Returns a frame whose ``index`` is the technology name and whose ``columns`` are a 3-level
    ``MultiIndex`` named ``(Source, Category, Parameter)`` — i.e. the same shape as ``technology_disag_s1_data``
    in legacy notebooks, so all the existing ``IndexSlice`` / ``cal_weighted_avg`` / ``InvestmentAllocator``
    code paths work unchanged.
    """
    raw = pd.read_excel(file_path, sheet_name="NEW INFRASTRUCTURE", header=None, engine="openpyxl")
    src = pd.Series(raw.iloc[2, :].values).ffill().fillna("").astype(str).str.strip()
    cat = pd.Series(raw.iloc[3, :].values).ffill().fillna("").astype(str).str.strip()
    par = raw.iloc[4, :].fillna("").astype(str).str.strip()
    keep = [
        i
        for i in range(raw.shape[1])
        if src.iloc[i] not in ("", "Technologies") and par.iloc[i] != ""
    ]
    if not keep:
        raise ValueError("NEW INFRASTRUCTURE: could not locate Source/Category/Parameter header block")
    body = raw.iloc[5:, :].copy()
    body = body.dropna(how="all", axis=0)
    tech_index = body.iloc[:, 1].astype(str).str.strip()
    valid = tech_index.notna() & (tech_index != "") & (tech_index.str.lower() != "nan")
    body = body.loc[valid]
    tech_index = tech_index.loc[valid]
    out = body.iloc[:, keep].copy()
    out.columns = pd.MultiIndex.from_arrays(
        [src.iloc[keep].tolist(), cat.iloc[keep].tolist(), par.iloc[keep].tolist()],
        names=["Source", "Category", "Parameter"],
    )
    out.index = tech_index.values
    out = out.apply(pd.to_numeric, errors="coerce")
    return out


def _year_columns_ppa_style(df: pd.DataFrame) -> list:
    return year_columns_from_dataframe(df)


def _row_to_year_array(row, year_cols: list) -> np.ndarray:
    if row is None or len(year_cols) == 0:
        return np.array([], dtype=float)
    out = np.empty(len(year_cols), dtype=float)
    for i, c in enumerate(year_cols):
        v = row.get(c, 0) if hasattr(row, "get") else row[c] if c in row.index else 0
        out[i] = 0.0 if pd.isna(v) else float(v)
    return out


def extract_tech_data_pure_input(
    file_path: str,
    tech_name: str,
    field_positions: dict,
    scenario: str = "Net Zero",
    share_start_offset: int = 38,
    price_start_offset: int = 44,
) -> dict:
    """
    Build the same structure as :func:`extract_tech_data_relative` from the pure-input workbook:
    **PPA REVENUE**, **WHOLESALE REVENUE**, **OTHER REVENUE** (header row 3), keyed by
    :data:`PURE_INPUT_STATIC_FIELD_SOURCES` and the dynamic share/price blocks (offsets from
    :func:`generate_share_configs`).

    * ``ppa_currency`` is not stored as a time series in the new file; a zero row is returned for API parity.
    """
    ppa = _read_pure_input_long_sheet(file_path, "PPA REVENUE")
    oth = _read_pure_input_long_sheet(file_path, "OTHER REVENUE")
    wsl = _read_pure_input_long_sheet(file_path, "WHOLESALE REVENUE")
    year_cols = _year_columns_ppa_style(ppa)
    if not year_cols:
        return {}

    sh_w = wsl[
        (wsl["Variable"] == "Share of Off-take")
        & (wsl["Technology"] == tech_name)
        & (wsl["Scenario"] == scenario)
    ].sort_values(["Name", "Off-taker"], na_position="last")
    pr_w = wsl[
        (wsl["Variable"] == "Wholesale Price")
        & (wsl["Technology"] == tech_name)
        & (wsl["Scenario"] == scenario)
    ].sort_values(["Name", "Off-taker"], na_position="last")

    tech_data: dict = {}
    n = len(year_cols)
    z = np.zeros(n, dtype=float)

    for field_name, finfo in field_positions.items():
        fallback_unit = finfo.get("unit", "")
        t = finfo.get("type")
        if t == "share":
            idx = finfo["offset"] - share_start_offset
            row = sh_w.iloc[idx] if 0 <= idx < len(sh_w) else None
            fallback_unit = fallback_unit or "%"
        elif t == "price":
            idx = finfo["offset"] - price_start_offset
            row = pr_w.iloc[idx] if 0 <= idx < len(pr_w) else None
        elif field_name == "ppa_currency":
            row = None
        elif field_name in PURE_INPUT_STATIC_FIELD_SOURCES:
            sheet, var = PURE_INPUT_STATIC_FIELD_SOURCES[field_name]
            src = ppa if sheet == "PPA REVENUE" else oth
            sub = src[
                (src["Variable"] == var)
                & (src["Technology"] == tech_name)
                & (src["Scenario"] == scenario)
            ]
            row = sub.iloc[0] if len(sub) else None
        else:
            row = None

        if field_name == "ppa_currency":
            values = z.copy()
        elif row is not None:
            values = _row_to_year_array(row, year_cols)
        else:
            values = z.copy()

        unit = unit_from_workbook_row(row, fallback_unit)
        tech_data[field_name] = {"values": values, "unit": unit}
    return tech_data


def extract_tech_data_relative(
    df_full: pd.DataFrame,
    sheet_name: str,
    tech_name: str,
    start_row: int,
    field_positions: dict,
) -> dict:
    """Extract yellow-input fields using relative row offsets from *start_row*."""
    del sheet_name, tech_name  # kept for API compatibility with notebook callers
    tech_data: dict = {}
    for field_name, field_info in field_positions.items():
        absolute_row = start_row + field_info["offset"] - 1
        if absolute_row < len(df_full):
            values = df_full.fillna(0).iloc[absolute_row, 2:].values
            tech_data[field_name] = {"values": values, "unit": field_info["unit"]}
    return tech_data


def convert_tech_data_to_dataframes(
    all_tech_data: dict,
    column_names: Optional[Union[list, range]] = None,
) -> dict:
    """Convert nested *all_tech_data* dict to one DataFrame per technology (years as index)."""
    tech_dataframes: dict[str, pd.DataFrame] = {}
    for tech_name, tech_data in all_tech_data.items():
        data_dict = {fn: fi["values"] for fn, fi in tech_data.items()}
        max_cols = max((len(v) for v in data_dict.values()), default=0)
        cols = column_names[:max_cols] if column_names is not None else range(max_cols)
        tech_dataframes[tech_name] = pd.DataFrame(
            {k: v[: len(cols)] for k, v in data_dict.items()},
            index=cols,
        )
    return tech_dataframes
