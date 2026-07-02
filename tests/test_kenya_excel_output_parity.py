"""Parity tests: Python technology output vs Kenya Excel Technology Disag reference.

Requires the Kenya reference workbook and a generated Python output file.
Skips when files are absent (e.g. CI). Locally, defaults to:

- ``~/Downloads/Kenya MINFin Energy Financing - Moderate.xlsm``
- ``minfin_output/minfin_technology_output_in_osemosys_way.xlsx``

Override with env vars ``MINFIN_KENYA_XLSM`` and ``MINFIN_KENYA_PY_OUTPUT``.

After running, inspect:

- ``minfin_output/kenya_excel_parity_report.csv`` — every technology / variable / year
- ``minfin_output/kenya_excel_parity_summary.txt`` — match vs mismatch counts
"""

from __future__ import annotations

import pytest

from MinFin.excel_technology_disag_compare import (
    DOCUMENTED_DIVERGENCE_VARIABLES,
    STRICT_PARITY_VARIABLES,
    build_technology_disag_parity_report,
    export_parity_report_workbook,
    format_parity_summary,
    summarize_parity_report,
)
from tests.kenya_reference_paths import (
    DEFAULT_KENYA_PY_OUTPUT,
    DEFAULT_KENYA_XLSM,
    DEFAULT_PARITY_DECIMALS,
    DEFAULT_PARITY_YEARS,
    PARITY_REPORT_PATH,
    PARITY_SUMMARY_PATH,
    PARITY_XLSX_PATH,
    kenya_reference_files_available,
    require_kenya_reference_files,
)

pytestmark = pytest.mark.skipif(
    not kenya_reference_files_available(),
    reason=(
        "Kenya reference files not found. Set MINFIN_KENYA_XLSM and "
        "MINFIN_KENYA_PY_OUTPUT or place files at default paths."
    ),
)

CORE_TECHNOLOGIES = ("Solar PV", "Battery", "Geothermal", "Wind")
REVENUE_PATH_VARIABLES = (
    "total_generation",
    "total_ppa_revenue",
    "ppa_standard_tariff",
    "ppa_met_generation",
    "opex",
)


@pytest.fixture(scope="module")
def parity_report():
    require_kenya_reference_files()
    report = build_technology_disag_parity_report(
        DEFAULT_KENYA_XLSM,
        DEFAULT_KENYA_PY_OUTPUT,
        years=DEFAULT_PARITY_YEARS,
        decimals=DEFAULT_PARITY_DECIMALS,
    )
    PARITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(PARITY_REPORT_PATH, index=False)
    PARITY_SUMMARY_PATH.write_text(
        format_parity_summary(report, decimals=DEFAULT_PARITY_DECIMALS),
        encoding="utf-8",
    )
    return report


def test_kenya_parity_writes_full_report(parity_report):
    assert len(parity_report) > 1000
    assert PARITY_REPORT_PATH.is_file()
    assert PARITY_SUMMARY_PATH.is_file()
    assert set(parity_report["status"].unique()) <= {
        "match",
        "mismatch",
        "missing_python",
        "missing_excel",
        "skipped_non_numeric",
    }


def test_kenya_parity_summary_statistics(parity_report, capsys):
    summary = summarize_parity_report(parity_report)
    assert summary.match > 0
    assert summary.mismatch > 0
    print(format_parity_summary(parity_report, decimals=DEFAULT_PARITY_DECIMALS))
    captured = capsys.readouterr()
    assert "match=" in captured.out
    assert "mismatch=" in captured.out


def test_kenya_parity_catalog_covers_all_mapped_variables(parity_report):
    """Report must list both matches and mismatches across technologies and years."""
    assert parity_report["technology"].nunique() >= 10
    assert parity_report["variable"].nunique() >= 20
    assert parity_report["status"].isin(["match", "mismatch"]).any()

    mismatches = parity_report[parity_report["status"] == "mismatch"]
    matches = parity_report[parity_report["status"] == "match"]
    assert not mismatches.empty
    assert not matches.empty

    # No unclassified mismatch buckets.
    unexpected = set(mismatches["variable"]) - STRICT_PARITY_VARIABLES - DOCUMENTED_DIVERGENCE_VARIABLES
    assert not unexpected, f"Add to DOCUMENTED_DIVERGENCE_VARIABLES: {sorted(unexpected)}"


@pytest.mark.parametrize("technology", CORE_TECHNOLOGIES)
def test_kenya_parity_core_technologies_revenue_path_2030(parity_report, technology):
    subset = parity_report[
        (parity_report["technology"] == technology)
        & (parity_report["year"] == 2030)
        & (parity_report["variable"].isin(REVENUE_PATH_VARIABLES))
    ]
    assert not subset.empty, f"No revenue-path rows for {technology} 2030"
    bad = subset[subset["status"] != "match"]
    if not bad.empty:
        pytest.fail(
            f"{technology} 2030 revenue-path mismatches:\n{bad.to_string(index=False)}\n"
            f"See {PARITY_REPORT_PATH}"
        )


@pytest.mark.parametrize("variable", sorted(STRICT_PARITY_VARIABLES))
def test_kenya_parity_strict_variables_match_except_zero_excel(parity_report, variable):
    """Strict metrics must match when Excel carries a non-zero value."""
    subset = parity_report[parity_report["variable"] == variable]
    if variable != "weighted_wacc":
        assert not subset.empty, f"No rows for {variable}"

    if variable == "weighted_wacc":
        mismatches = subset[subset["status"] == "mismatch"]
    else:
        mismatches = subset[
            (subset["status"] == "mismatch")
            & (subset["excel_value"].fillna(0).astype(float) != 0)
        ]

    if mismatches.empty:
        return

    examples = mismatches.head(10)[
        ["technology", "year", "excel_value", "python_value", "difference"]
    ].to_string(index=False)
    pytest.fail(
        f"{variable}: {len(mismatches)} mismatches at {DEFAULT_PARITY_DECIMALS} decimals "
        f"(non-zero Excel).\nFirst examples:\n{examples}\nFull report: {PARITY_REPORT_PATH}"
    )
