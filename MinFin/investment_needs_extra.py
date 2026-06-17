"""Investment need aggregation helpers (least cost / net zero, FFRM placeholders)."""

from __future__ import annotations

from collections import defaultdict
from typing import List, Optional

import numpy as np
import pandas as pd

from .definitions_io import Technology
from .index_alignment import ensure_year_index

DEFAULT_SINCE_YEAR = 2025


def filter_data(data: pd.DataFrame, since_year: int = DEFAULT_SINCE_YEAR) -> pd.DataFrame:
    """Restrict rows to years >= *since_year* and return a year-indexed frame when possible."""
    if data is None:
        return pd.DataFrame()
    if data.empty:
        return data.copy()

    frame = ensure_year_index(data.copy())
    year_index = pd.to_numeric(frame.index, errors="coerce")
    valid_years = year_index.notna()
    if valid_years.any():
        keep = valid_years & (year_index >= since_year)
        filtered = frame.loc[keep]
        filtered.index = year_index[keep].astype(int)
        filtered.index.name = "Year"
        return filtered

    if "Year" in frame.columns:
        frame["Year"] = pd.to_numeric(frame["Year"], errors="coerce")
        frame = frame[frame["Year"] >= since_year]
        return ensure_year_index(frame)

    return frame


def aggregate_by_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Aggregate columns by renaming with *mapping* then summing duplicate names."""
    tmp = df.rename(columns=mapping)
    tmp = tmp.T.groupby(level=0).sum().T
    return filter_data(tmp)


def get_tech_cls_map(technologies: List[Technology]) -> dict:
    return {tech.name: tech.classification for tech in technologies}


def cal_invest_needs(
    technologies: List[Technology],
    least_cost_summary: pd.DataFrame,
    net_zero_summary: pd.DataFrame,
    df_ffe_least_cost: pd.DataFrame,
    df_ffe_net_zero: pd.DataFrame,
    full_cap_cost_least_cost: pd.DataFrame,
    full_cap_cost_net_zero: pd.DataFrame,
    df_technologies: pd.DataFrame,
    *,
    pure_input_file_path: Optional[str] = None,
):
    """Build investment-need tables from OSeMOSYS / FFRM–style inputs.

    If *pure_input_file_path* is set, ``emission_savings`` is read from **INVESTMENT PLAN**
    (``emission_savings_series_from_investment_plan``) instead of ``least_cost_summary - net_zero_summary`` CO2.
    """
    df_emission_savings = pd.DataFrame(index=net_zero_summary.index)
    if pure_input_file_path:
        from MinFin.data_processor import emission_savings_series_from_investment_plan

        df_emission_savings["emission_savings"] = emission_savings_series_from_investment_plan(
            pure_input_file_path, net_zero_summary.index
        )
    else:
        df_emission_savings["emission_savings"] = (
            least_cost_summary["co2_emission"] - net_zero_summary["co2_emission"]
        )

    filtered_least_cost = filter_data(df_ffe_least_cost)
    filtered_net_zero = filter_data(df_ffe_net_zero)
    fossil_fuel_savings = filtered_least_cost - filtered_net_zero
    fossil_fuel_no_earnings = fossil_fuel_savings.drop(columns=["Total"], errors="ignore").copy()
    fossil_fuel_no_earnings.iloc[:, :] = fossil_fuel_no_earnings.map(lambda x: max(x, 0))

    years = pd.to_numeric(fossil_fuel_savings.index, errors="coerce")
    if years.isna().any():
        raise ValueError(
            "Could not align years to fossil fuel savings rows. "
            "Ensure FFE frames share a Year column or a Year-named index, "
            "and least-cost vs net-zero FFE shapes are compatible."
        )

    fossil_fuel_savings = fossil_fuel_savings.copy()
    fossil_fuel_savings.index = years.astype(int)
    fossil_fuel_savings.index.name = "Year"
    fossil_fuel_savings["expenditure"] = fossil_fuel_no_earnings.sum(axis=1)

    tech_list = ["Oil", "Gas", "Coal"]
    total_cols = [(tech, tech) for tech in tech_list]
    cols = total_cols + [("Total", "Total")]
    n = len(fossil_fuel_savings.index)
    df_financing_needs_ffr = pd.DataFrame(
        0.0,
        index=fossil_fuel_savings.index,
        columns=pd.MultiIndex.from_tuples(cols),
    )
    df_financing_needs_ffr.insert(0, ("General", "Year"), df_financing_needs_ffr.index)
    df_financing_needs_ffr.loc[:, ("Total", "Total")] = df_financing_needs_ffr.loc[:, total_cols].sum(axis=1)

    tech_category_map = get_tech_cls_map(technologies)
    name_to_tech_map = df_technologies.set_index("Name")["Technology"].to_dict()

    df_cap_by_class_lc = aggregate_by_mapping(full_cap_cost_least_cost, tech_category_map)
    df_cap_by_tech_lc = aggregate_by_mapping(full_cap_cost_least_cost, name_to_tech_map)
    df_cap_by_class_nz = aggregate_by_mapping(full_cap_cost_net_zero, tech_category_map)
    df_cap_by_tech_nz = aggregate_by_mapping(full_cap_cost_net_zero, name_to_tech_map)

    df_category_sum_lc = get_category_sum(df_cap_by_class_lc, df_cap_by_tech_lc)
    df_category_sum_nz = get_category_sum(df_cap_by_class_nz, df_cap_by_tech_nz)
    return (
        df_cap_by_class_lc,
        df_cap_by_tech_lc,
        df_cap_by_class_nz,
        df_cap_by_tech_nz,
        df_emission_savings,
        df_financing_needs_ffr.set_index(("General", "Year"), drop=False),
        fossil_fuel_savings,
    )


def get_category_sum(by_class: pd.DataFrame, by_tech: pd.DataFrame) -> pd.DataFrame:
    """Concatenate class and technology capital tables on a shared year index."""
    return pd.concat([ensure_year_index(by_class), ensure_year_index(by_tech)], axis=1)


def cal_weighted_avg(data: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """Weighted row-wise average."""
    return ((weights * data).sum(axis=1) / weights.sum(axis=1).replace(0, np.nan)).fillna(0)


def aggregate_tech_production(df: pd.DataFrame, technologies: list) -> pd.DataFrame:
    """Sum generation columns by technology name using *technologies* name→code mapping."""
    source = ensure_year_index(df)
    code_to_name = {t.name: t.technology for t in technologies}
    name_to_cols: dict[str, list] = defaultdict(list)
    for col in source.columns:
        if col in code_to_name:
            name_to_cols[code_to_name[col]].append(col)
    return pd.DataFrame(
        {name: source[cols].sum(axis=1) for name, cols in name_to_cols.items()},
        index=source.index,
    )
