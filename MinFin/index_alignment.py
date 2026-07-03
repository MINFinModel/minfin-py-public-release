"""Year-index helpers and alignment warnings for time-series DataFrames."""

from __future__ import annotations

import warnings
from typing import Iterable, Optional, Union

import numpy as np
import pandas as pd

YearLike = Union[Iterable, pd.Index, pd.Series]


def ensure_year_index(
    data: pd.DataFrame,
    *,
    year_col: str = "Year",
    drop_year_col: bool = True,
) -> pd.DataFrame:
    """Return a copy with an integer year index when year information is available."""
    if data is None or data.empty:
        return data.copy() if data is not None else pd.DataFrame()

    frame = data.copy()
    if year_col in frame.columns:
        years = pd.to_numeric(frame[year_col], errors="coerce")
        valid = years.notna()
        frame = frame.loc[valid].copy()
        frame.index = years.loc[valid].astype(int)
        if drop_year_col:
            frame = frame.drop(columns=[year_col], errors="ignore")
    else:
        numeric_index = pd.to_numeric(frame.index, errors="coerce")
        valid = numeric_index.notna()
        if valid.any():
            frame = frame.loc[valid].copy()
            frame.index = numeric_index[valid].astype(int)
            frame.index.name = year_col
    return frame


def _as_year_index(index: YearLike) -> pd.Index:
    if isinstance(index, pd.Series):
        values = index.index if index.name is not None else index.to_numpy()
    else:
        values = index
    return pd.Index(pd.to_numeric(values, errors="coerce"))


def warn_on_index_mismatch(
    source_index: YearLike,
    target_index: YearLike,
    *,
    context: str,
    min_overlap: int = 1,
) -> None:
    """Emit a warning when source and target year indices barely overlap."""
    source_years = set(_as_year_index(source_index).dropna().astype(int))
    target_years = set(_as_year_index(target_index).dropna().astype(int))
    overlap = source_years & target_years
    if len(overlap) >= min_overlap:
        return

    source_preview = sorted(source_years)[:5]
    target_preview = sorted(target_years)[:5]
    warnings.warn(
        (
            f"Year index mismatch while aligning {context}: "
            f"source years {source_preview} do not match target years {target_preview}. "
            "Values may be filled with NaN/0 after alignment."
        ),
        category=UserWarning,
        stacklevel=3,
    )


def align_series_to_index(
    series: pd.Series,
    target_index: YearLike,
    *,
    context: str,
    fill_value: float = 0.0,
) -> pd.Series:
    """Align *series* to *target_index*, warning when year indices do not overlap."""
    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    source = ensure_year_index(series.to_frame(name="_value"))["_value"]
    target = _as_year_index(target_index)
    warn_on_index_mismatch(source.index, target, context=context)
    aligned = source.reindex(target, fill_value=fill_value)
    aligned.index = pd.to_numeric(aligned.index, errors="coerce").astype(int)
    return aligned


def assign_series_column(
    frame: pd.DataFrame,
    column: str,
    series: pd.Series,
    *,
    context: str,
    fill_value: float = 0.0,
) -> None:
    """Assign a year-indexed series into *frame* with mismatch warnings."""
    frame[column] = align_series_to_index(
        series,
        frame.index,
        context=context or f"{column}",
        fill_value=fill_value,
    )


def apply_investment_to_tech_dataframes(
    tech_dataframes: dict[str, pd.DataFrame],
    df_category_sum: pd.DataFrame,
    *,
    grant_share: float = 0.0,
) -> None:
    """Populate grant and net investment-need columns using year-aligned category sums.

    When a technology frame already carries ``total_grant_amount`` from the input workbook,
    preserve that workbook series. Otherwise fall back to the legacy percentage shortcut.
    """
    category = ensure_year_index(df_category_sum)
    for tech_name, tech_df in tech_dataframes.items():
        if tech_name not in category.columns:
            continue
        capital = align_series_to_index(
            category[tech_name],
            tech_df.index,
            context=f"{tech_name} capital_cost",
        )
        if "total_grant_amount" in tech_df.columns:
            grant = align_series_to_index(
                pd.to_numeric(tech_df["total_grant_amount"], errors="coerce").fillna(0.0),
                tech_df.index,
                context=f"{tech_name} total_grant_amount",
            )
        else:
            grant = capital * grant_share
        assign_series_column(
            tech_df,
            "total_grant_amount",
            grant,
            context=f"{tech_name} total_grant_amount",
        )
        assign_series_column(
            tech_df,
            "investment_need",
            (capital - grant).clip(lower=0.0),
            context=f"{tech_name} investment_need",
        )
