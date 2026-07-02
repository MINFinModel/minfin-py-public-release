"""Compare Python technology output exports against Excel Technology Disag blocks."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

# Excel row label (Technology Disag col B) -> Python export ``Variable`` name.
EXCEL_LABEL_TO_PYTHON_VARIABLE: dict[str, str] = {
    "Cashflows (Million USD)": "cashflow",
    "Total Generation (GWh/Year)": "total_generation",
    "Total PPA Revenue (Million USD)": "total_ppa_revenue",
    "PPA Met Generation (GWh/Year)": "ppa_met_generation",
    "PPA Contracted Generation (GWh/Year)": "ppa_contracted_generation",
    "PPA Standard Tariff (KES/kWh)": "ppa_standard_tariff",
    "PPA Standard Tariff (USD/kWh)": "ppa_standard_tariff",
    "PPA Standard Offtaker Share (%)": "ppa_standard_offtaker_share",
    "PPA Direct Offtaker Share (%)": "ppa_direct_offtaker_share",
    "PPA Direct Offtaker Tariff (KES/kWh)": "ppa_direct_offtaker_tariff",
    "PPA Direct Offtaker Tariff (USD/kWh)": "ppa_direct_offtaker_tariff",
    "PPA Penalty Tariff (KES/kWh)": "ppa_penalty_tariff",
    "PPA Penalty Tariff (USD/kWh)": "ppa_penalty_tariff",
    "PPA Contracted Capacity (MW)": "ppa_contracted_capacity",
    "PPA Capacity Fee (Million KES/MW)": "ppa_capacity_fee",
    "PPA Capacity Fee (Million USD/MW)": "ppa_capacity_fee",
    "OPEX (Million USD)": "opex",
    "Corporate Tax Expense (Million USD)": "corporate_tax_expenses",
    "Corporate Tax Rate %": "corporate_tax_rate",
    "Financing Requirement (Million USD)": "Financing Requirement",
    "Investment Need (Million USD)": "capital_cost",
    "Existing Financing Requirement (Million USD)": "Existing Financing Requirement",
    "Total Grant Amount (Million USD)": "total_grant_amount",
    "Wholesale Generation (GWh/Year)": "whole_sale_generation",
    "Total Wholesale Revenue (Million USD)": "total_wholesale_revnue",
    "Sale Price (USD/kWh)": "sale_price",
    "Receivables (Million USD)": "receivables",
    "Liabilities (Million USD)": "liabilities",
    "Redispatch Compensation ( Million KES)": "redispatch_compensation",
    "Redispatch Compensation ( Million USD)": "redispatch_compensation",
    "Redispatch Compensation Price (KES/kWh)": "redispatch_compensation_price",
    "Redispatch Compensation Price (USD/kWh)": "redispatch_compensation_price",
    "Generation Purchased (GWh/Year)": "power_purchased",
    "Transmission Purchased (GWh/Year)": "power_purchased",
    "Tariff (USD/KWh)": "tariff",
    "Capacity Purchased (MW)": "capacity_purchased",
    "Capacity Tariff (USD/MW)": "capacity_tariff",
    "Power Purchase Cost (Million  USD)": "power_purchase_cost",
    "Cost (Million USD)": "power_purchase_cost",
    "Loans (Comm_Intl)": "Loans (Comm_Intl)",
    "Loans (Comm_Dom)": "Loans (Comm_Dom)",
    "Loans (Conc_IFI)": "Loans (Conc_IFI)",
    "Loans (Conc_DPS)": "Loans (Conc_DPS)",
    "Equity (Comm_Intl)": "Equity (Comm_Intl)",
    "Equity (Comm_Dom)": "Equity (Comm_Dom)",
    "Equity (Conc_IFI)": "Equity (Conc_IFI)",
    "Equity (Conc_DPS)": "Equity (Conc_DPS)",
}

# Variables expected to match Excel after rounding (PPA / generation path).
STRICT_PARITY_VARIABLES: frozenset[str] = frozenset(
    {
        "total_generation",
        "ppa_met_generation",
        "ppa_contracted_generation",
        "total_ppa_revenue",
        "ppa_standard_tariff",
        "ppa_standard_offtaker_share",
        "opex",
        "weighted_wacc",
    }
)

# Reported in the parity CSV but not asserted (known or under investigation).
DOCUMENTED_DIVERGENCE_VARIABLES: frozenset[str] = frozenset(
    {
        "cashflow",
        "corporate_tax_expenses",
        "investment_need",
        "Existing Financing Requirement",
        "Financing Requirement",
        "Loans (Comm_Intl)",
        "Loans (Comm_Dom)",
        "Loans (Conc_IFI)",
        "Loans (Conc_DPS)",
        "Equity (Comm_Intl)",
        "Equity (Comm_Dom)",
        "Equity (Conc_IFI)",
        "Equity (Conc_DPS)",
        "capital_cost",
        "power_purchased",
        "tariff",
        "power_purchase_cost",
    "ppa_direct_offtaker_share",
    "receivables",
    "sale_price",
    "total_wholesale_revnue",
    "capacity_tariff",
    "whole_sale_generation",
    "redispatch_compensation",
    "corporate_tax_rate",
    "total_grant_amount",
    "liabilities",
    "ppa_capacity_fee",
    "ppa_contracted_capacity",
    "ppa_penalty_tariff",
    "ppa_direct_offtaker_tariff",
}
)

PARITY_REPORT_COLUMNS = [
    "technology",
    "excel_label",
    "variable",
    "year",
    "excel_value",
    "python_value",
    "rounded_excel",
    "rounded_python",
    "difference",
    "status",
]


@dataclass(frozen=True)
class ParitySummary:
    match: int = 0
    mismatch: int = 0
    missing_python: int = 0
    missing_excel: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.match + self.mismatch + self.missing_python + self.missing_excel + self.skipped


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", str(label).strip())


def round_for_parity(value, *, decimals: int = 3):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return round(float(value), decimals)


def values_equal_at_precision(
    excel_value,
    python_value,
    *,
    decimals: int = 3,
) -> bool:
    if excel_value is None or (isinstance(excel_value, float) and math.isnan(excel_value)):
        return python_value is None or (
            isinstance(python_value, float) and math.isnan(python_value)
        )
    if python_value is None or (isinstance(python_value, float) and math.isnan(python_value)):
        return False
    if isinstance(excel_value, str) or isinstance(python_value, str):
        return str(excel_value).strip() == str(python_value).strip()
    tolerance = 10 ** (-decimals)
    return abs(float(excel_value) - float(python_value)) <= tolerance + 1e-12


def discover_technology_disag_blocks(
    technology_disag: pd.DataFrame,
    *,
    technology_names: Optional[Iterable[str]] = None,
) -> dict[str, int]:
    """Return {technology: start_row} for detailed per-technology blocks."""
    names = set(technology_names or [])
    blocks: dict[str, int] = {}
    for i in range(technology_disag.shape[0]):
        label = technology_disag.iloc[i, 1]
        if pd.isna(label):
            continue
        tech = _normalize_label(label)
        if technology_names is not None and tech not in names:
            continue
        if tech in blocks:
            continue
        window = technology_disag.iloc[i + 1 : i + 25, 1].astype(str)
        if window.str.contains("Investment Need", case=False, na=False).any() or window.str.contains(
            "Cashflows", case=False, na=False
        ).any():
            blocks[tech] = i
    return blocks


def _year_column_index(year: int, start_year: int = 2025) -> int:
    return 2 + (int(year) - start_year)


def technology_disag_year_columns(
    technology_disag: pd.DataFrame,
    *,
    start_year: int = 2025,
    search_rows: int = 10,
) -> dict[int, int]:
    """Map Excel column index -> projection year for Technology Disag data columns.

    Prefer an explicit year header row when present; otherwise columns from index 2
  onward are ``start_year``, ``start_year + 1``, … (Kenya workbook layout).
    """
    for row_idx in range(min(search_rows, technology_disag.shape[0])):
        mapping: dict[int, int] = {}
        for col_idx in range(2, technology_disag.shape[1]):
            header = technology_disag.iloc[row_idx, col_idx]
            try:
                year = int(float(header))
            except (TypeError, ValueError):
                continue
            if 1990 < year < 2100:
                mapping[col_idx] = year
        if mapping and 2025 in mapping.values():
            return mapping

    return {
        col_idx: start_year + (col_idx - 2)
        for col_idx in range(2, technology_disag.shape[1])
    }


def _is_block_boundary(label: str, *, after_start: bool) -> bool:
    if not after_start:
        return False
    return "Go To" in label or "To Top" in label


def _is_technology_block_header(
    technology_disag: pd.DataFrame,
    row_idx: int,
) -> bool:
    """True when ``row_idx`` is the technology title row of a Disag detail block."""
    label = technology_disag.iloc[row_idx, 1]
    if pd.isna(label):
        return False
    tech = _normalize_label(label)
    if not tech or tech in EXCEL_LABEL_TO_PYTHON_VARIABLE:
        return False
    if "(" in tech or "Million" in tech or "Go To" in tech or "To Top" in tech:
        return False
    end = min(row_idx + 25, technology_disag.shape[0])
    if row_idx + 1 >= end:
        return False
    window = technology_disag.iloc[row_idx + 1 : end, 1].astype(str)
    return (
        window.str.contains("Investment Need", case=False, na=False).any()
        or window.str.contains("Cashflows", case=False, na=False).any()
    )


def extract_block_series(
    technology_disag: pd.DataFrame,
    start_row: int,
    *,
    year_columns: Optional[dict[int, int]] = None,
    start_year: int = 2025,
) -> dict[str, dict[int, object]]:
    """Extract {excel_label: {year: value}} for one technology block."""
    if year_columns is None:
        year_columns = technology_disag_year_columns(technology_disag, start_year=start_year)

    series: dict[str, dict[int, object]] = {}
    for i in range(start_row + 1, min(start_row + 90, technology_disag.shape[0])):
        raw_label = technology_disag.iloc[i, 1]
        if pd.isna(raw_label):
            continue
        label = _normalize_label(raw_label)
        if _is_technology_block_header(technology_disag, i):
            break
        if _is_block_boundary(label, after_start=i > start_row + 5):
            break
        if label not in EXCEL_LABEL_TO_PYTHON_VARIABLE:
            continue
        if label.startswith("Local Currency") or label.startswith("Foreign Currency"):
            continue
        year_values: dict[int, object] = {}
        for col_idx, year in year_columns.items():
            if year < start_year:
                continue
            year_values[year] = technology_disag.iloc[i, col_idx]
        series[label] = year_values
    return series


def extract_wacc_top_table(
    technology_disag: pd.DataFrame,
    *,
    technology_names: Optional[Iterable[str]] = None,
) -> dict[str, float]:
    """WACC from the summary rows at the top of Technology Disag (percent)."""
    names = set(technology_names or [])
    out: dict[str, float] = {}
    for i in range(min(30, technology_disag.shape[0])):
        label = technology_disag.iloc[i, 1]
        if pd.isna(label):
            continue
        tech = _normalize_label(label)
        if names and tech not in names:
            continue
        wacc = technology_disag.iloc[i, 2]
        try:
            value = float(wacc)
        except (TypeError, ValueError):
            continue
        if math.isnan(value):
            continue
        # Top table stores WACC as a fraction; export uses percent.
        out[tech] = value * 100.0 if value <= 1.0 else value
    return out


def build_technology_disag_parity_report(
    excel_path: str | Path,
    python_output_path: str | Path,
    *,
    years: Optional[Iterable[int]] = None,
    decimals: int = 3,
    sheet_name: str = "Technology Disag",
) -> pd.DataFrame:
    """Compare Excel Technology Disag per-technology blocks to Python long output."""
    excel_path = Path(excel_path)
    python_output_path = Path(python_output_path)
    td = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
    py = pd.read_excel(python_output_path)

    if years is None:
        year_set = {int(y) for y in py["year"].dropna().unique() if int(y) >= 2025}
        years = sorted(year_set)
    else:
        years = sorted({int(y) for y in years})

    py_techs = set(py["technology"].dropna().astype(str).unique()) - {"Economy"}
    blocks = discover_technology_disag_blocks(td, technology_names=py_techs)
    year_columns = technology_disag_year_columns(td)

    records: list[dict] = []

    def append_row(
        *,
        technology: str,
        excel_label: str,
        variable: str,
        year: Optional[int],
        excel_value,
        python_value,
        status: str,
    ) -> None:
        ex_r = round_for_parity(excel_value, decimals=decimals)
        py_r = round_for_parity(python_value, decimals=decimals)
        diff = None
        if isinstance(ex_r, (int, float)) and isinstance(py_r, (int, float)):
            diff = py_r - ex_r
        records.append(
            {
                "technology": technology,
                "excel_label": excel_label,
                "variable": variable,
                "year": year,
                "excel_value": excel_value,
                "python_value": python_value,
                "rounded_excel": ex_r,
                "rounded_python": py_r,
                "difference": diff,
                "status": status,
            }
        )

    for tech, start_row in sorted(blocks.items()):
        block = extract_block_series(td, start_row, year_columns=year_columns)
        for excel_label, year_map in block.items():
            variable = EXCEL_LABEL_TO_PYTHON_VARIABLE[excel_label]
            for year in years:
                if year not in year_map:
                    continue
                excel_value = year_map[year]
                if pd.isna(excel_value):
                    continue
                try:
                    excel_numeric = float(excel_value)
                except (TypeError, ValueError):
                    append_row(
                        technology=tech,
                        excel_label=excel_label,
                        variable=variable,
                        year=year,
                        excel_value=excel_value,
                        python_value=None,
                        status="skipped_non_numeric",
                    )
                    continue
                if math.isnan(excel_numeric):
                    continue

                py_rows = py[
                    (py["Variable"] == variable)
                    & (py["technology"] == tech)
                    & (py["year"] == year)
                ]
                if py_rows.empty:
                    append_row(
                        technology=tech,
                        excel_label=excel_label,
                        variable=variable,
                        year=year,
                        excel_value=excel_numeric,
                        python_value=None,
                        status="missing_python",
                    )
                    continue

                python_value = float(py_rows["ResultValue"].iat[0])
                if values_equal_at_precision(excel_numeric, python_value, decimals=decimals):
                    status = "match"
                else:
                    status = "mismatch"
                append_row(
                    technology=tech,
                    excel_label=excel_label,
                    variable=variable,
                    year=year,
                    excel_value=excel_numeric,
                    python_value=python_value,
                    status=status,
                )

    # WACC (scalar per technology)
    wacc_excel = extract_wacc_top_table(td, technology_names=py_techs)
    for tech, excel_wacc in wacc_excel.items():
        py_rows = py[(py["Variable"] == "weighted_wacc") & (py["technology"] == tech)]
        if py_rows.empty:
            append_row(
                technology=tech,
                excel_label="WACC (top table)",
                variable="weighted_wacc",
                year=None,
                excel_value=excel_wacc,
                python_value=None,
                status="missing_python",
            )
            continue
        python_wacc = float(py_rows["ResultValue"].iat[0])
        status = "match" if values_equal_at_precision(excel_wacc, python_wacc, decimals=decimals) else "mismatch"
        append_row(
            technology=tech,
            excel_label="WACC (top table)",
            variable="weighted_wacc",
            year=None,
            excel_value=excel_wacc,
            python_value=python_wacc,
            status=status,
        )

    if not records:
        return pd.DataFrame(columns=PARITY_REPORT_COLUMNS)

    report = pd.DataFrame(records, columns=PARITY_REPORT_COLUMNS)
    return report.sort_values(
        ["status", "technology", "variable", "year"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)


def summarize_parity_report(report: pd.DataFrame) -> ParitySummary:
    counts = report["status"].value_counts().to_dict() if not report.empty else {}
    return ParitySummary(
        match=int(counts.get("match", 0)),
        mismatch=int(counts.get("mismatch", 0)),
        missing_python=int(counts.get("missing_python", 0)),
        missing_excel=int(counts.get("missing_excel", 0)),
        skipped=int(counts.get("skipped_non_numeric", 0)),
    )


def format_parity_summary(report: pd.DataFrame, *, decimals: int = 3) -> str:
    """Human-readable summary of match/mismatch counts."""
    summary = summarize_parity_report(report)
    lines = [
        f"Parity summary (rounded to {decimals} decimals):",
        f"  match={summary.match} mismatch={summary.mismatch} "
        f"missing_python={summary.missing_python} skipped={summary.skipped} total={summary.total}",
    ]
    if report.empty:
        lines.append("  (empty report)")
        return "\n".join(lines)

    mismatches = report[report["status"] == "mismatch"]
    if not mismatches.empty:
        lines.append("Mismatches by variable:")
        for variable, count in mismatches["variable"].value_counts().items():
            lines.append(f"  {variable}: {count}")
    matches = report[report["status"] == "match"]
    if not matches.empty:
        lines.append("Matches by variable:")
        for variable, count in matches["variable"].value_counts().items():
            lines.append(f"  {variable}: {count}")
    return "\n".join(lines)


def parity_summary_dataframes(
    report: pd.DataFrame,
    *,
    decimals: int = 3,
) -> dict[str, pd.DataFrame]:
    """Build tabular summaries for Excel export."""
    summary = summarize_parity_report(report)
    overview = pd.DataFrame(
        [
            {"metric": "decimals", "value": decimals},
            {"metric": "match", "value": summary.match},
            {"metric": "mismatch", "value": summary.mismatch},
            {"metric": "missing_python", "value": summary.missing_python},
            {"metric": "missing_excel", "value": summary.missing_excel},
            {"metric": "skipped", "value": summary.skipped},
            {"metric": "total", "value": summary.total},
        ]
    )

    by_status_variable = (
        report.groupby(["status", "variable"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["status", "count", "variable"], ascending=[True, False, True])
    )

    mismatch_by_tech = (
        report[report["status"] == "mismatch"]
        .groupby(["technology", "variable"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "technology", "variable"], ascending=[False, True, True])
    )

    return {
        "Overview": overview,
        "By_Status_Variable": by_status_variable,
        "Mismatch_By_Tech": mismatch_by_tech,
    }


def export_parity_report_workbook(
    report: pd.DataFrame,
    output_path: str | Path,
    *,
    decimals: int = 3,
) -> Path:
    """Write parity comparisons to a multi-sheet Excel workbook."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_sheets = parity_summary_dataframes(report, decimals=decimals)
    mismatches = report[report["status"] == "mismatch"].copy()
    missing_python = report[report["status"] == "missing_python"].copy()

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_sheets["Overview"].to_excel(writer, sheet_name="Overview", index=False)
        summary_sheets["By_Status_Variable"].to_excel(
            writer, sheet_name="By_Status_Variable", index=False
        )
        summary_sheets["Mismatch_By_Tech"].to_excel(
            writer, sheet_name="Mismatch_By_Tech", index=False
        )
        mismatches.to_excel(writer, sheet_name="Mismatches", index=False)
        missing_python.to_excel(writer, sheet_name="Missing_Python", index=False)
        report.to_excel(writer, sheet_name="All_Comparisons", index=False)

    return output_path
