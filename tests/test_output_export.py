"""Tests for raw technology parameter export helpers."""

import pandas as pd

from MinFin.output_export import (
    ECONOMY_DIM,
    RAW_INPUT_COLUMNS,
    build_technology_output_raw_table,
    build_technology_parameter_raw_table,
    compute_existing_financing_requirement_by_year,
    compute_financing_baseline_by_year,
)


def test_build_technology_parameter_raw_table_flattens_all_tech_data():
    all_tech_data = {
        "Biomass": {
            "total_grant_amount": {"values": [10.0, 11.5], "unit": "Million USD"},
            "ppa_currency": {"values": [0, 0], "unit": "Currency"},
            "ppa_contracted_generation": {"values": [0, 0], "unit": "GWh/Year"},
        },
        "Wind": {
            "receivables": {"values": [2.0, 0.0], "unit": "Million USD"},
        },
    }

    df = build_technology_parameter_raw_table(
        all_tech_data=all_tech_data,
        years=[2025, 2026],
        scenario="Net Zero",
    )

    assert list(df.columns) == RAW_INPUT_COLUMNS
    assert len(df) == 4
    assert set(df["Variable"]) == {"total_grant_amount", "receivables"}
    assert set(df["Dim1"]) == {"Biomass", "Wind"}
    assert set(df["Dim2"]) == {2025, 2026}
    assert set(df["Scenario"]) == {"Net Zero"}
    assert df.loc[df["Variable"] == "total_grant_amount", "Dim3"].iat[0] == "Million USD"


def test_build_technology_output_raw_table_includes_computed_and_financing_rows():
    tech_dataframes = {
        "Biomass": pd.DataFrame(
            {
                "total_generation": [100.0, 110.0],
                "cashflow": [5.0, 6.0],
                "ppa_contracted_generation": [0, 0],
            },
            index=[2025, 2026],
        ),
    }
    all_tech_data = {
        "Biomass": {
            "ppa_contracted_generation": {"values": [50.0, 55.0], "unit": "GWh/Year"},
            "receivables": {"values": [0, 0], "unit": "Million USD"},
        }
    }
    financing_requirement_by_tech = {
        "Biomass": pd.DataFrame(
            {"2025": [1.0], "2026": [2.0]},
            index=["Loans (Comm_Intl)"],
        ),
    }

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        all_tech_data=all_tech_data,
        financing_requirement_by_tech=financing_requirement_by_tech,
        years=[2025, 2026],
    )

    variables = set(df["Variable"])
    assert "total_generation" in variables
    assert "cashflow" in variables
    assert "ppa_contracted_generation" in variables
    assert "Loans (Comm_Intl)" in variables
    assert "receivables" in variables
    assert "cashflow" in variables


def test_build_technology_output_raw_table_skips_ppa_for_distribution():
    df_technologies = pd.DataFrame(
        {
            "Technology": ["Distribution"],
            "Classification": ["Distribution"],
        }
    )
    tech_dataframes = {
        "Distribution": pd.DataFrame(
            {
                "total_generation": [10.0, 12.0],
                "total_ppa_revenue": [0.0, 0.0],
                "ppa_contracted_generation": [0.0, 0.0],
                "power_purchased": [3.0, 4.0],
            },
            index=[2025, 2026],
        ),
    }
    all_tech_data = {
        "Distribution": {
            "ppa_contracted_generation": {"values": [0, 0], "unit": "GWh/Year"},
            "corporate_tax_rate": {"values": [0.3, 0.3], "unit": ""},
        }
    }

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        all_tech_data=all_tech_data,
        df_technologies=df_technologies,
        years=[2025, 2026],
    )

    variables = set(df["Variable"])
    assert "total_generation" in variables
    assert "power_purchased" in variables
    assert "corporate_tax_rate" in variables
    assert "total_ppa_revenue" not in variables
    assert "ppa_contracted_generation" not in variables


def test_build_technology_output_raw_table_exports_zero_core_variables():
    tech_dataframes = {
        "Biomass": pd.DataFrame(
            {
                "investment_need": [0.0, 0.0],
                "cashflow": [0.0, 0.0],
                "total_ppa_revenue": [10.0, 12.0],
            },
            index=[2025, 2026],
        ),
    }
    all_tech_data = {
        "Biomass": {
            "ppa_contracted_generation": {"values": [50.0, 55.0], "unit": "GWh/Year"},
        }
    }

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        all_tech_data=all_tech_data,
        years=[2025, 2026],
    )

    variables = set(df["Variable"])
    assert "investment_need" in variables
    assert "cashflow" in variables
    assert "total_ppa_revenue" in variables


def test_build_technology_output_raw_table_exports_financing_rows_when_zero():
    tech_dataframes = {
        "Biomass": pd.DataFrame({"cashflow": [1.0, 2.0]}, index=[2025, 2026]),
    }
    financing_requirement_by_tech = {
        "Biomass": pd.DataFrame(
            {"2025": [0.0], "2026": [0.0]},
            index=["Loans (Comm_Intl)"],
        ),
    }

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        financing_requirement_by_tech=financing_requirement_by_tech,
        years=[2025, 2026],
    )

    assert "Loans (Comm_Intl)" in set(df["Variable"])


def test_build_technology_output_raw_table_uses_workbook_units():
    tech_dataframes = {
        "Biomass": pd.DataFrame(
            {
                "cashflow": [5.0, 6.0],
                "ppa_contracted_generation": [50.0, 55.0],
            },
            index=[2025, 2026],
        ),
    }
    all_tech_data = {
        "Biomass": {
            "ppa_contracted_generation": {"values": [50.0, 55.0], "unit": "GWh/Year"},
            "ppa_standard_tariff": {"values": [0.1, 0.1], "unit": "KES/kWh"},
            "total_grant_amount": {"values": [1.0, 2.0], "unit": "Mn USD"},
        }
    }
    variable_units = {
        "capital_cost": "Mn USD",
        "total_grant_amount": "Mn USD",
        "cashflow": "Mn USD",
    }

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        all_tech_data=all_tech_data,
        variable_units=variable_units,
        years=[2025, 2026],
    )

    assert df.loc[df["Variable"] == "ppa_contracted_generation", "Dim3"].iat[0] == "GWh/Year"
    assert df.loc[df["Variable"] == "cashflow", "Dim3"].iat[0] == "Mn USD"


def test_compute_financing_baseline_and_existing_requirement_from_repayment_schedule():
    repayment_schedule = pd.DataFrame(
        {
            2024: [1.0, 2.0],
            2025: [10.0, 20.0],
            2026: [100.0, 200.0],
            "Volume in USD": [50.0, 60.0],
        }
    )

    baseline = compute_financing_baseline_by_year(repayment_schedule)
    assert baseline.loc[2024] == 3.0
    assert baseline.loc[2025] == 30.0
    assert baseline.loc[2026] == 300.0

    existing = compute_existing_financing_requirement_by_year(
        repayment_schedule, years=[2025, 2026]
    )
    assert 2024 not in existing.index
    assert existing.loc[2025] == 30.0
    assert existing.loc[2026] == 300.0


def test_build_technology_output_raw_table_includes_economy_financing_metrics():
    tech_dataframes = {
        "Biomass": pd.DataFrame({"cashflow": [1.0, 2.0]}, index=[2025, 2026]),
    }
    repayment_schedule = pd.DataFrame(
        {
            2024: [1.0],
            2025: [4.0],
            2026: [5.0],
            "Volume in USD": [10.0],
        }
    )

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        repayment_schedule=repayment_schedule,
        years=[2025, 2026],
        variable_units={"total_grant_amount": "Mn USD"},
    )

    economy_rows = df[df["Dim1"] == ECONOMY_DIM]
    assert set(economy_rows["Variable"]) == {
        "financing_baseline",
        "existing_financing_requirement",
    }
    assert economy_rows.loc[
        economy_rows["Variable"] == "financing_baseline", "ResultValue"
    ].tolist() == [1.0, 4.0, 5.0]
    assert economy_rows.loc[
        economy_rows["Variable"] == "existing_financing_requirement", "ResultValue"
    ].tolist() == [4.0, 5.0]
    assert economy_rows["Dim3"].iat[0] == "Mn USD"


def test_build_technology_output_raw_table_excludes_ffe_investment_block():
    tech_dataframes = {
        "Biomass": pd.DataFrame({"cashflow": [1.0]}, index=[2025]),
    }
    investment_blocks = {
        "capital_cost": pd.DataFrame(
            {"PWRBIO": [100.0]},
            index=[2025],
        ),
        "ffe": pd.DataFrame(
            {"PWRBIO": [999.0]},
            index=[2025],
        ),
    }
    df_technologies = pd.DataFrame(
        {"Technology": ["Biomass"], "Name": ["PWRBIO"]}
    )

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        investment_blocks=investment_blocks,
        df_technologies=df_technologies,
        years=[2025],
    )

    variables = set(df["Variable"])
    assert "capital_cost" in variables
    assert "ffe" not in variables
