"""Workbook layout detection and format constants for MinFin input files."""

from __future__ import annotations

import pandas as pd

# How MinFin input workbooks are laid out. Use with load_excel_data(..., workbook_format=...).
# "legacy"     — MINFin Energy Example Input File (.xlsm): Definitions + New Infrastructure (Input).
# "pure_input" — MINFin Python Input File.xlsx: INVESTMENT PLAN (long) + TECHNOLOGY REGISTER, etc.
WORKBOOK_FORMAT_LEGACY = "legacy"
WORKBOOK_FORMAT_PURE_INPUT = "pure_input"
WORKBOOK_FORMAT_AUTO = "auto"
# Deprecated name for the same mode; still accepted and normalized to PURE_INPUT.
WORKBOOK_FORMAT_PYTHON = "python"
WORKBOOK_FORMAT_CHOICES = (WORKBOOK_FORMAT_LEGACY, WORKBOOK_FORMAT_PURE_INPUT, WORKBOOK_FORMAT_AUTO)


def normalize_workbook_format(workbook_format: str) -> str:
    """Map the deprecated name ``python`` to ``pure_input`` (same workbook layout)."""
    if workbook_format in (WORKBOOK_FORMAT_PYTHON, "python"):
        return WORKBOOK_FORMAT_PURE_INPUT
    return workbook_format


def detect_workbook_format(file_path: str) -> str:
    """
    Return :data:`WORKBOOK_FORMAT_PURE_INPUT` if the file matches the pure-input layout
    (INVESTMENT PLAN present, no Definitions), else :data:`WORKBOOK_FORMAT_LEGACY`.
    """
    try:
        with pd.ExcelFile(file_path, engine="openpyxl") as xls:
            names = set(xls.sheet_names)
    except (OSError, ValueError):
        return WORKBOOK_FORMAT_LEGACY
    if "INVESTMENT PLAN" in names and "Definitions" not in names:
        return WORKBOOK_FORMAT_PURE_INPUT
    return WORKBOOK_FORMAT_LEGACY
