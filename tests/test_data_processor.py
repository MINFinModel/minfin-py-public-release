"""Tests for workbook format detection and data loading helpers."""

import pandas as pd

from MinFin.investment_needs_extra import get_category_sum
from MinFin.data_processor import (
    WORKBOOK_FORMAT_LEGACY,
    WORKBOOK_FORMAT_PURE_INPUT,
    detect_workbook_format,
    input_extractor,
)
from MinFin.workbook_format import normalize_workbook_format


def test_normalize_workbook_format_python_alias():
    assert normalize_workbook_format("python") == WORKBOOK_FORMAT_PURE_INPUT


def test_input_extractor_pure_input_requires_file_path():
    try:
        input_extractor("net_zero", workbook_format=WORKBOOK_FORMAT_PURE_INPUT)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_get_category_sum_uses_year_index():
    by_class = pd.DataFrame({"Year": [2025, 2026], "ClassA": [1.0, 2.0]})
    by_tech = pd.DataFrame({"Year": [2025, 2026], "Biomass": [10.0, 20.0]})
    result = get_category_sum(by_class, by_tech)
    assert result.index.tolist() == [2025, 2026]
    assert result.loc[2025, "Biomass"] == 10.0


def test_detect_workbook_format_legacy_example():
    path = "data/MINFin Energy Example Input File.xlsm"
    try:
        fmt = detect_workbook_format(path)
    except OSError:
        return  # example file not present in CI
    assert fmt == WORKBOOK_FORMAT_LEGACY
