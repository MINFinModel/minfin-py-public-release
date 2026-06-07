"""Disaggregation lookups and segment rollups for technology cashflow tables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import pandas as pd


def _class_to_segment(cls):
    if pd.isna(cls) or not str(cls).strip():
        return None
    s = str(cls).strip().lower()
    if "generation" in s and "export" not in s:
        return "Generation"
    if "transmission" in s:
        return "Transmission"
    if "distribution" in s:
        return "Distribution"
    if "export" in s:
        return "Exports"
    return None


def sum_tech_params_by_segment(
    tech_dataframes: dict,
    column_name: str,
    tech_to_class_map: dict,
) -> pd.DataFrame:
    """Aggregate *column_name* from each tech DataFrame by high-level segment."""
    segments = ["Generation", "Exports", "Transmission", "Distribution"]
    series_by_segment = {seg: [] for seg in segments}
    for tech_name, df in tech_dataframes.items():
        segment = _class_to_segment(tech_to_class_map.get(tech_name, ""))
        if segment is None or column_name not in df.columns:
            continue
        series_by_segment[segment].append(df[column_name].fillna(0))
    default_index = next(iter(tech_dataframes.values())).index if tech_dataframes else pd.RangeIndex(0)
    result = pd.DataFrame()
    for segment in segments:
        series_list = series_by_segment[segment]
        if series_list:
            result[segment] = pd.concat(series_list, axis=1).sum(axis=1)
        else:
            result[segment] = pd.Series(0.0, index=default_index)
    return result


def _sum_tech_params(tech_dataframes: dict, column_name: str) -> pd.Series:
    """Sum *column_name* across all tech frames; skip frames where the column is missing.

    Some technologies in NEW INFRASTRUCTURE may not get a fully populated frame (e.g. no
    OSeMOSYS row in INVESTMENT PLAN, so no ``cashflow`` / ``opex`` is computed). In that
    case those frames are skipped instead of raising ``KeyError``.
    """
    series = [
        tech_dataframes[t][column_name].fillna(0)
        for t in tech_dataframes
        if column_name in tech_dataframes[t].columns
    ]
    if not series:
        idx = next(iter(tech_dataframes.values())).index if tech_dataframes else pd.RangeIndex(0)
        return pd.Series(0.0, index=idx)
    return pd.concat(series, axis=1).sum(axis=1)


@dataclass
class DisagLookupConfig:
    scenario: str = "S1"
    financing_source: str = ""


def build_disag_table(
    config: DisagLookupConfig,
    disag_data: pd.DataFrame,
    tech_list: Optional[list] = None,
) -> pd.DataFrame:
    """Slice one financing source block from a technology disag MultiIndex table."""
    src = config.financing_source
    tech_list = tech_list or list(disag_data.index)
    if not src:
        return pd.DataFrame(index=tech_list)
    try:
        block = disag_data.loc[:, (src, slice(None), slice(None))].copy()
        block.columns = block.columns.droplevel("Source")
    except (KeyError, TypeError):
        block = pd.DataFrame(index=disag_data.index)
    return block.reindex(tech_list)


def get_row_by_name(
    df: pd.DataFrame, keyword: str, start_year: int, case: bool = False
) -> Union[pd.Series, pd.DataFrame]:
    """Find rows whose index contains *keyword*; align columns to years starting at *start_year*."""
    matched = df[df.index.str.contains(keyword, case=case, na=False)].fillna(0)
    if matched.empty:
        return matched
    num_cols = matched.shape[1]
    matched = matched.copy()
    matched.columns = list(range(start_year, start_year + num_cols))
    if len(matched) == 1:
        s = matched.iloc[0]
        s.name = matched.index[0]
        return s
    lens = matched.index.str.len()
    if lens.nunique() == 1:
        return matched
    kw_len = len(keyword)
    best_i = (np.abs(np.array(lens) - kw_len)).argmin()
    kept = matched.iloc[[best_i]]
    s = kept.iloc[0]
    s.name = kept.index[0]
    return s
