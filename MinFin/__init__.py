"""
MinFin energy-finance toolkit.

Prefer explicit imports, e.g. ``from MinFin.data_processor import load_excel_data``.
This module re-exports common notebook entry points.
"""

from MinFin.data_processor import (
    detect_workbook_format,
    emission_savings_series_from_investment_plan,
    get_funding_envelope,
    input_extractor,
    load_excel_data,
    process_funding_baseline,
    read_financing_baseline,
    read_infrastructure_input,
    WORKBOOK_FORMAT_AUTO,
    WORKBOOK_FORMAT_LEGACY,
    WORKBOOK_FORMAT_PURE_INPUT,
)
from MinFin.financing_baseline import (
    financing_baseline_extractor,
    financing_baseline_stats,
    get_exchange_rates,
)
from MinFin.high_level_dashboard import hd, high_level_dashboard

__all__ = [
    "WORKBOOK_FORMAT_AUTO",
    "WORKBOOK_FORMAT_LEGACY",
    "WORKBOOK_FORMAT_PURE_INPUT",
    "detect_workbook_format",
    "emission_savings_series_from_investment_plan",
    "financing_baseline_extractor",
    "financing_baseline_stats",
    "get_exchange_rates",
    "get_funding_envelope",
    "hd",
    "high_level_dashboard",
    "input_extractor",
    "load_excel_data",
    "process_funding_baseline",
    "read_financing_baseline",
    "read_infrastructure_input",
]
