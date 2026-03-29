"""Technology Disag sheet extraction: relative row offsets and per-tech DataFrames."""

from __future__ import annotations

from typing import Optional, Union

import pandas as pd

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
                "unit": "GHS/kWh",
                "type": "price",
            }
            count += 1
    return configs


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
