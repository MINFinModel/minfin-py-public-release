"""Tests for raw technology parameter export helpers."""

import pandas as pd
import pytest

from MinFin.output_export import (
    ECONOMY_DIM,
    RAW_INPUT_COLUMNS,
    build_technology_output_raw_table,
    build_technology_parameter_raw_table,
    compute_existing_financing_requirement_by_technology,
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
    assert set(df["technology"]) == {"Biomass", "Wind"}
    assert set(df["year"]) == {2025, 2026}
    assert set(df["Scenario"]) == {"Net Zero"}
    assert df.loc[df["Variable"] == "total_grant_amount", "unit"].iat[0] == "Million USD"


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

    assert df.loc[df["Variable"] == "ppa_contracted_generation", "unit"].iat[0] == "GWh/Year"
    assert df.loc[df["Variable"] == "cashflow", "unit"].iat[0] == "Mn USD"


def test_build_technology_output_raw_table_uses_dashboard_units_for_computed_tariffs():
    tech_dataframes = {
        "Distribution": pd.DataFrame(
            {
                "tariff": [0.1],
                "sale_price": [0.2],
                "capacity_tariff": [1.5],
            },
            index=[2030],
        ),
    }
    all_tech_data = {
        "Distribution": {
            "ppa_standard_tariff": {"values": [12.0], "unit": "KES/kWh"},
            "ppa_capacity_fee": {"values": [120.0], "unit": "Mn KES/MW"},
        }
    }
    df_technologies = pd.DataFrame(
        {"Technology": ["Distribution"], "Classification": ["Distribution"]}
    )

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        all_tech_data=all_tech_data,
        df_technologies=df_technologies,
        years=[2030],
    )

    units = df.set_index("Variable")["unit"].to_dict()
    assert units["tariff"] == "USD/kWh"
    assert units["sale_price"] == "USD/kWh"
    assert units["capacity_tariff"] == "Mn USD/MW"


def test_build_technology_output_raw_table_units_local_source_rows_separately():
    tech_dataframes = {
        "Battery": pd.DataFrame(
            {
                "local_currency_debt_comm_dom": [11.0],
                "foreign_currency_debt_comm_intl": [2.0],
                "cashflow": [5.0],
            },
            index=[2032],
        ),
    }
    financing_requirement_by_tech = {
        "Battery": pd.DataFrame({2032: [0.5]}, index=["Loans (Comm_Dom)"]),
    }

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        financing_requirement_by_tech=financing_requirement_by_tech,
        variable_units={"capital_cost": "Mn USD", "total_grant_amount": "Mn USD"},
        years=[2032],
        local_currency_code="KES",
        foreign_currency_code="USD",
    )

    units = df.set_index("Variable")["unit"].to_dict()
    assert units["local_currency_debt_comm_dom"] == "Mn KES"
    assert units["foreign_currency_debt_comm_intl"] == "Mn USD"
    assert units["Loans (Comm_Dom)"] == "Mn USD"


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

    economy_rows = df[df["technology"] == ECONOMY_DIM]
    # Existing financing requirement is now reported per technology, not at the economy level.
    assert set(economy_rows["Variable"]) == {"financing_baseline"}
    assert economy_rows.loc[
        economy_rows["Variable"] == "financing_baseline", "ResultValue"
    ].tolist() == [1.0, 4.0, 5.0]
    assert economy_rows["unit"].iat[0] == "Mn USD"


def test_compute_existing_financing_requirement_by_technology_disaggregates_totals():
    repayment_schedule = pd.DataFrame(
        {
            2024: [1.0, 2.0, 4.0],
            2025: [10.0, 20.0, 40.0],
            2026: [100.0, 200.0, 400.0],
            "Volume in USD": [5.0, 6.0, 7.0],
        }
    )
    technology = pd.Series(["Solar", "Solar", "Wind"])

    by_tech = compute_existing_financing_requirement_by_technology(
        repayment_schedule, technology, years=[2025, 2026]
    )

    assert list(by_tech.columns) == [2025, 2026]
    assert 2024 not in by_tech.columns
    assert by_tech.loc["Solar", 2025] == 30.0
    assert by_tech.loc["Wind", 2025] == 40.0
    assert by_tech.loc["Solar", 2026] == 300.0

    economy = compute_existing_financing_requirement_by_year(
        repayment_schedule, years=[2025, 2026]
    )
    assert by_tech.sum(axis=0).loc[2025] == economy.loc[2025]
    assert by_tech.sum(axis=0).loc[2026] == economy.loc[2026]


def test_compute_existing_financing_requirement_by_technology_applies_alias_map():
    repayment_schedule = pd.DataFrame(
        {
            2025: [10.0, 20.0, 40.0],
            2026: [100.0, 200.0, 400.0],
            "Volume in USD": [5.0, 6.0, 7.0],
        }
    )
    # Historic labels use register descriptions; map them to the parent model names.
    technology = pd.Series(["Onshore Wind", "Onshore Wind", "Solar PV"])
    alias_map = {"Onshore Wind": "Wind", "Solar PV": "Solar PV"}

    by_tech = compute_existing_financing_requirement_by_technology(
        repayment_schedule, technology, years=[2025, 2026], technology_map=alias_map
    )

    assert set(by_tech.index) == {"Wind", "Solar PV"}
    assert "Onshore Wind" not in by_tech.index
    assert by_tech.loc["Wind", 2025] == 30.0
    assert by_tech.loc["Solar PV", 2026] == 400.0


def test_build_technology_output_raw_table_existing_financing_per_technology():
    tech_dataframes = {
        "Solar": pd.DataFrame({"cashflow": [1.0, 2.0]}, index=[2025, 2026]),
    }
    repayment_schedule = pd.DataFrame(
        {
            2024: [1.0, 4.0],
            2025: [10.0, 40.0],
            2026: [100.0, 400.0],
            "Volume in USD": [5.0, 7.0],
        }
    )
    existing_by_tech = compute_existing_financing_requirement_by_technology(
        repayment_schedule, pd.Series(["Solar", "Wind"]), years=[2025, 2026]
    )

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        repayment_schedule=repayment_schedule,
        existing_financing_by_technology=existing_by_tech,
        years=[2025, 2026],
    )

    existing_rows = df[df["Variable"] == "existing_financing_requirement"]
    # Split per technology, never emitted at the economy level.
    assert set(existing_rows["technology"]) == {"Solar", "Wind"}
    assert ECONOMY_DIM not in set(existing_rows["technology"])
    assert existing_rows.loc[
        existing_rows["technology"] == "Wind", "ResultValue"
    ].tolist() == [40.0, 400.0]
    # financing_baseline stays an economy-level series.
    baseline_rows = df[df["Variable"] == "financing_baseline"]
    assert set(baseline_rows["technology"]) == {ECONOMY_DIM}


def test_build_technology_output_raw_table_includes_weighted_financing_summary():
    tech_dataframes = {
        "Biomass": pd.DataFrame({"cashflow": [1.0, 2.0]}, index=[2025, 2026]),
    }
    technology_financing_summary = pd.DataFrame(
        {
            "Loan Term (years)": [12.0],
            "Grace Period (years)": [3.0],
            "Combined Interest Rate (%)": [6.5],
            "Equity Return Rate (%)": [11.0],
            "WACC (%)": [8.2],
        },
        index=pd.Index(["Biomass"], name="Technology"),
    )

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        technology_financing_summary=technology_financing_summary,
        years=[2025, 2026],
    )

    summary_rows = df[df["Variable"].str.startswith("weighted_")]
    assert set(summary_rows["Variable"]) == {
        "weighted_grace_period",
        "weighted_loan_term",
        "weighted_interest_rate",
        "weighted_rate_of_return_on_equity",
        "weighted_wacc",
    }
    assert (summary_rows["technology"] == "Biomass").all()
    assert summary_rows["year"].isna().all()
    assert df.loc[df["Variable"] == "weighted_wacc", "ResultValue"].iat[0] == 8.2
    assert df.loc[df["Variable"] == "weighted_wacc", "unit"].iat[0] == "%"


def test_build_technology_output_raw_table_includes_gdp_share_metrics():
    tech_dataframes = {
        "Biomass": pd.DataFrame({"cashflow": [1.0, 2.0]}, index=[2025, 2026]),
    }
    economy_metrics = {
        "financing_requirement_share_of_gdp": pd.Series(
            [0.01, 0.02], index=[2025, 2026]
        ),
        "funding_availability_share_of_gdp": pd.Series(
            [0.03, 0.04], index=[2025, 2026]
        ),
    }

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        economy_metrics=economy_metrics,
        years=[2025, 2026],
    )

    economy_rows = df[df["technology"] == ECONOMY_DIM]
    assert {
        "financing_requirement_share_of_gdp",
        "funding_availability_share_of_gdp",
    } <= set(economy_rows["Variable"])
    fr = economy_rows[economy_rows["Variable"] == "financing_requirement_share_of_gdp"]
    assert fr["ResultValue"].tolist() == [0.01, 0.02]
    assert fr["unit"].iat[0] == "share of GDP"


def test_technology_financing_summary_from_weighted_averages():
    from MinFin.output_export import technology_financing_summary_from_weighted_averages

    weighted_averages = pd.DataFrame(
        {
            ("Debt", "Interest Rate"): [0.06],
            ("Debt", "Grace Period"): [3.0],
            ("Debt", "Loan Term"): [12.0],
            ("Equity", "Rate of Return"): [0.11],
            ("Financing Shares", "Debt Share"): [0.7],
            ("Financing Shares", "Equity Share"): [0.3],
            ("Weighted Cost of Capital", "WACC"): [0.075],
        },
        index=pd.Index(["Solar PV"], name="Technology"),
    )

    summary = technology_financing_summary_from_weighted_averages(weighted_averages)
    assert summary.loc["Solar PV", "Grace Period (years)"] == 3.0
    assert summary.loc["Solar PV", "Loan Term (years)"] == 12.0
    assert summary.loc["Solar PV", "Equity Return Rate (%)"] == pytest.approx(11.0)
    assert summary.loc["Solar PV", "Combined Interest Rate (%)"] == pytest.approx(
        (0.06 * 0.7 + 0.11 * 0.3) * 100
    )
    assert summary.loc["Solar PV", "WACC (%)"] == pytest.approx(7.5)


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


def test_build_technology_output_raw_table_reports_gross_capital_and_investment_need():
    tech_dataframes = {
        "Solar PV": pd.DataFrame({"investment_need": [95.0]}, index=[2025]),
    }
    investment_blocks = {
        "capital_cost": pd.DataFrame({"PWRSOL": [100.0]}, index=[2025]),
    }
    df_technologies = pd.DataFrame(
        {"Technology": ["Solar PV"], "Name": ["PWRSOL"]}
    )

    df = build_technology_output_raw_table(
        tech_dataframes=tech_dataframes,
        investment_blocks=investment_blocks,
        df_technologies=df_technologies,
        years=[2025],
    )

    values = df.set_index("Variable")["ResultValue"].to_dict()
    assert values["investment_need"] == 95.0
    assert values["capital_cost"] == 100.0
