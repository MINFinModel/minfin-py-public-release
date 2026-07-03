import pandas as pd

from MinFin.technology_sheet_io import (
    DEFAULT_FIELD_RELATIVE_POSITIONS,
    extract_tech_data_pure_input,
    infer_technology_disag_start_rows,
)


def test_infer_technology_disag_start_rows_skips_navigation_labels():
    df = pd.DataFrame(
        {
            0: ["Go To", None, None, "6. - To Top", None, None],
            1: ["Wind", None, None, "Wind", None, "Investment Need (Million USD)"],
            2: [0.1, None, None, None, None, 1.0],
        }
    )

    starts = infer_technology_disag_start_rows(df, ["Wind"])

    assert starts == {"Wind": 4}


def test_pure_input_ppa_currency_uses_currency_column_without_code_whitelist(tmp_path):
    path = tmp_path / "pure_input_currency.xlsx"
    years = [2025, 2026]
    ppa = pd.DataFrame(
        [
            {
                "Variable": "Standard Off-taker Tariff",
                "Scenario": "Net Zero",
                "Technology": "Test Tech",
                "Currency": "XYZ",
                "Unit": "local/kWh",
                2025: 1.0,
                2026: 2.0,
            }
        ],
        columns=["Variable", "Scenario", "Technology", "Currency", "Unit", *years],
    )
    other = pd.DataFrame(
        columns=["Variable", "Scenario", "Technology", "Currency", "Unit", *years]
    )
    wholesale = pd.DataFrame(
        columns=[
            "Variable",
            "Scenario",
            "Technology",
            "Currency",
            "Name",
            "Off-taker",
            "Unit",
            *years,
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        ppa.to_excel(writer, sheet_name="PPA REVENUE", startrow=3, index=False)
        other.to_excel(writer, sheet_name="OTHER REVENUE", startrow=3, index=False)
        wholesale.to_excel(writer, sheet_name="WHOLESALE REVENUE", startrow=3, index=False)

    data = extract_tech_data_pure_input(
        str(path), "Test Tech", DEFAULT_FIELD_RELATIVE_POSITIONS
    )

    assert data["ppa_currency"]["unit"] == "XYZ"
    assert data["ppa_currency"]["values"].tolist() == ["XYZ", "XYZ"]
