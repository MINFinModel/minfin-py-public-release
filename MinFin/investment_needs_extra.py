"""Investment need aggregation helpers (least cost / net zero, FFRM placeholders)."""

from __future__ import annotations

from collections import defaultdict
from typing import List

import numpy as np
import pandas as pd

from .definitions_io import Technology

DEFAULT_SINCE_YEAR = 2025


def filter_data(data: pd.DataFrame, since_year: int = DEFAULT_SINCE_YEAR) -> pd.DataFrame:
    """Restrict rows to years >= *since_year* using a ``Year`` column or a numeric index."""
    col_to_use = "Year" if "Year" in data.columns else None
    if col_to_use is None:
        data_index_numeric = pd.to_numeric(data.index, errors="coerce")
        return data.loc[data_index_numeric >= since_year]
    data = data.copy()
    data["Year"] = pd.to_numeric(data["Year"], errors="coerce")
    return data[data["Year"] >= since_year]


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
):
    """Build investment-need tables from OSeMOSYS / FFRM–style inputs."""
    df_emission_savings = pd.DataFrame()
    df_emission_savings["emission_savings"] = (
        least_cost_summary["co2_emission"] - net_zero_summary["co2_emission"]
    )

    fossil_fuel_savings = filter_data(df_ffe_least_cost) - filter_data(df_ffe_net_zero)
    fossil_fuel_no_earnings = fossil_fuel_savings.drop(columns=["Total", "Year"], errors="ignore").copy()
    fossil_fuel_no_earnings.iloc[:, :] = fossil_fuel_no_earnings.map(lambda x: max(x, 0))

    filtered_least_cost = filter_data(df_ffe_least_cost)
    if "Year" in filtered_least_cost.columns:
        fossil_fuel_savings["Year"] = filtered_least_cost["Year"].astype(int)
    else:
        fossil_fuel_savings["Year"] = pd.to_numeric(filtered_least_cost.index, errors="coerce").astype(int)
    fossil_fuel_savings["expenditure"] = fossil_fuel_no_earnings.sum(axis=1)
    fossil_fuel_savings = fossil_fuel_savings.set_index("Year")

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

    df_category_sum_lc = pd.concat([df_cap_by_class_lc, df_cap_by_tech_lc], axis=1)
    df_category_sum_nz = pd.concat([df_cap_by_class_nz, df_cap_by_tech_nz], axis=1)
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
    return pd.concat([by_class, by_tech], axis=1)


def cal_weighted_avg(data: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """Weighted row-wise average."""
    return ((weights * data).sum(axis=1) / weights.sum(axis=1).replace(0, np.nan)).fillna(0)


def aggregate_tech_production(df: pd.DataFrame, technologies: list) -> pd.DataFrame:
    """Sum generation columns by technology name using *technologies* name→code mapping."""
    code_to_name = {t.name: t.technology for t in technologies}
    name_to_cols: dict[str, list] = defaultdict(list)
    for col in df.columns:
        if col in code_to_name:
            name_to_cols[code_to_name[col]].append(col)
    return pd.DataFrame({name: df[cols].sum(axis=1) for name, cols in name_to_cols.items()}, index=df.index)
