"""Kenya reference workbook paths for Excel vs Python parity tests."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Default local paths (override with MINFIN_KENYA_XLSM / MINFIN_KENYA_PY_OUTPUT).
DEFAULT_KENYA_XLSM = Path(
    os.environ.get(
        "MINFIN_KENYA_XLSM",
        Path.home() / "Downloads" / "Kenya MINFin Energy Financing - Moderate.xlsm",
    )
)
DEFAULT_KENYA_PY_OUTPUT = REPO_ROOT / "minfin_output" / "minfin_technology_output_in_osemosys_way.xlsx"

if os.environ.get("MINFIN_KENYA_PY_OUTPUT"):
    DEFAULT_KENYA_PY_OUTPUT = Path(os.environ["MINFIN_KENYA_PY_OUTPUT"])

PARITY_REPORT_PATH = REPO_ROOT / "minfin_output" / "kenya_excel_parity_report.csv"
PARITY_SUMMARY_PATH = REPO_ROOT / "minfin_output" / "kenya_excel_parity_summary.txt"
PARITY_XLSX_PATH = REPO_ROOT / "minfin_output" / "kenya_excel_parity_report.xlsx"

# Projection years compared when Excel and Python both carry values.
DEFAULT_PARITY_YEARS = list(range(2025, 2071))
DEFAULT_PARITY_DECIMALS = 4


def kenya_reference_files_available() -> bool:
    return DEFAULT_KENYA_XLSM.is_file() and DEFAULT_KENYA_PY_OUTPUT.is_file()


def require_kenya_reference_files():
    if not DEFAULT_KENYA_XLSM.is_file():
        raise FileNotFoundError(f"Kenya Excel reference not found: {DEFAULT_KENYA_XLSM}")
    if not DEFAULT_KENYA_PY_OUTPUT.is_file():
        raise FileNotFoundError(f"Python output not found: {DEFAULT_KENYA_PY_OUTPUT}")
