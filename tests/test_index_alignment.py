"""Tests for year-index alignment helpers."""

import warnings

import pandas as pd
import pytest

from MinFin.index_alignment import (
    align_series_to_index,
    apply_investment_to_tech_dataframes,
    assign_series_column,
    ensure_year_index,
    warn_on_index_mismatch,
)
from MinFin.investment_needs_extra import filter_data, get_category_sum


def test_ensure_year_index_from_year_column():
    frame = pd.DataFrame({"Year": [2025, 2026], "Biomass": [10.0, 20.0]})
    result = ensure_year_index(frame)
    assert result.index.tolist() == [2025, 2026]
    assert "Year" not in result.columns


def test_filter_data_returns_year_index():
    frame = pd.DataFrame({"Year": [2024, 2025, 2026], "Biomass": [1.0, 2.0, 3.0]})
    result = filter_data(frame, since_year=2025)
    assert result.index.tolist() == [2025, 2026]
    assert result.loc[2025, "Biomass"] == 2.0


def test_warn_on_index_mismatch_emits_warning():
    with pytest.warns(UserWarning, match="Year index mismatch"):
        warn_on_index_mismatch([0, 1, 2], [2025, 2026, 2027], context="test")


def test_assign_series_column_aligns_by_year():
    tech_df = pd.DataFrame(index=[2025, 2026, 2027])
    capital = pd.Series([10.0, 20.0], index=[2025, 2026])
    assign_series_column(tech_df, "investment_need", capital, context="Biomass investment_need")
    assert tech_df.loc[2025, "investment_need"] == 10.0
    assert tech_df.loc[2027, "investment_need"] == 0.0


def test_apply_investment_to_tech_dataframes_populates_columns():
    tech_dataframes = {"Biomass": pd.DataFrame(index=[2025, 2026])}
    category = pd.DataFrame({"Biomass": [100.0, 200.0]}, index=[2025, 2026])
    apply_investment_to_tech_dataframes(tech_dataframes, category, grant_share=0.05)
    assert tech_dataframes["Biomass"].loc[2025, "total_grant_amount"] == 5.0
    assert tech_dataframes["Biomass"].loc[2025, "investment_need"] == 95.0


def test_assign_series_column_warns_on_misaligned_indices():
    tech_df = pd.DataFrame(index=[2025, 2026])
    bad = pd.Series([1.0, 2.0], index=[0, 1])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assign_series_column(tech_df, "investment_need", bad, context="Biomass investment_need")
    assert any("Year index mismatch" in str(item.message) for item in caught)


def test_get_category_sum_keeps_year_index():
    by_class = pd.DataFrame({"Year": [2025, 2026], "ClassA": [1.0, 2.0]})
    by_tech = pd.DataFrame({"Year": [2025, 2026], "Biomass": [10.0, 20.0]})
    result = get_category_sum(by_class, by_tech)
    assert result.index.tolist() == [2025, 2026]
