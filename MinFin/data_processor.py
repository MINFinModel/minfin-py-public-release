"""
Excel ingestion: workbook detection, definitions loading, infrastructure blocks, funding baseline.

Implementation is split across :mod:`workbook_format`, :mod:`pure_input_blocks`,
:mod:`infrastructure_extractor`, and :mod:`excel_io`; this module re-exports the public API.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from MinFin.excel_io import read_long_sheet, year_columns_from_dataframe
from MinFin.infrastructure_extractor import input_extractor
from MinFin.pure_input_blocks import (
    build_input_blocks_from_pure_input_file,
    emission_savings_series_from_investment_plan,
)
from MinFin.workbook_format import (
    WORKBOOK_FORMAT_AUTO,
    WORKBOOK_FORMAT_CHOICES,
    WORKBOOK_FORMAT_LEGACY,
    WORKBOOK_FORMAT_PURE_INPUT,
    WORKBOOK_FORMAT_PYTHON,
    detect_workbook_format,
    normalize_workbook_format,
)

_normalize_workbook_format = normalize_workbook_format


CONSUMER_SEGMENT_CATEGORIES = ("Generation", "Transmission", "Distribution", "Exports")


def get_melted_currency_df():
    years = np.arange(2000, 2080)

    # Define some example currencies
    currencies = ["EUR", "GBP", "JPY", "CNY", "INR", "AUD", "CAD"]

    # Generate synthetic exchange rates with a simulated yearly change
    np.random.seed(42)  # For reproducibility
    base_rates = {
        'USD': 1#, "EUR": 1.1, "GBP": 1.3, "JPY": 110, "CNY": 6.5, "INR": 74, "AUD": 1.4, "CAD": 1.25
    }
    base_rates["KES"] = 1

    # Simulate yearly fluctuations for KES (small changes)
    fluctuations = np.cumsum(np.random.normal(0, 0.01, len(years)))  # Simulated yearly change
    # Create a DataFrame to store the exchange rates
    exchange_rates = pd.DataFrame({"Year": years})
    exchange_rates["KES"] = base_rates["KES"]# * (1 + fluctuations)
    # exchange_rates["USD"] = base_rates["USD"]
    # Simulate yearly fluctuations in exchange rates
    for currency, base_rate in base_rates.items():
        fluctuations = np.cumsum(np.random.normal(0, 0.01, len(years)))  # Simulated yearly change
        exchange_rates[currency] = base_rate #* (1 + fluctuations)
    exchange_rates
    melted = exchange_rates.melt(id_vars=["Year"], var_name="Currency", value_name="Exchange Rate")
    
    return melted


def read_infrastructure_input(file_path, workbook_format: str = WORKBOOK_FORMAT_AUTO) -> Optional[pd.DataFrame]:
    """
    Load the wide OSeMOSYS-style **New Infrastructure (Input)** sheet. Only defined for the legacy
    .xlsm; the pure-input workbook (MINFin Python Input File.xlsx) has no equivalent sheet—use
    ``input_extractor(..., workbook_format=WORKBOOK_FORMAT_PURE_INPUT, file_path=...)`` and the INVESTMENT
    PLAN data instead. Returns None for the pure_input format.
    """
    if workbook_format == WORKBOOK_FORMAT_AUTO:
        workbook_format = detect_workbook_format(file_path)
    else:
        workbook_format = normalize_workbook_format(workbook_format)
    if workbook_format == WORKBOOK_FORMAT_PURE_INPUT:
        return None
    return pd.read_excel(file_path, sheet_name="New Infrastructure (Input)", engine="openpyxl")


def read_financing_baseline(
    file_path, workbook_format: str = WORKBOOK_FORMAT_AUTO
) -> Optional[pd.DataFrame]:
    """
    Read the **Financing Baseline** sheet (legacy .xlsm) used by :class:`MinFin.financing_baseline.financing_baseline_extractor`
    (fixed row/column layout: exchange block + historic instrument block).

    The pure-input workbook has **no** sheet named *Financing Baseline* or with the same **wide layout**.
    The **historic financing content** that the legacy model places on Financing Baseline is instead provided
    as **long-form** rows on **EXISTING INFRASTRUCTURE**; forward-looking instrument parameters are on
    **NEW INFRASTRUCTURE**; exchange-rate style inputs appear on **MACROECONOMIC**. Use
    ``financing_baseline_extractor.from_workbook(file_path)`` to build the extractor for either layout (legacy
    sheet or pure-input sheets). This function still returns ``None`` for pure input because there is no
    wide **Financing Baseline** sheet to return as a single ``DataFrame``.
    """
    if workbook_format == WORKBOOK_FORMAT_AUTO:
        workbook_format = detect_workbook_format(file_path)
    else:
        workbook_format = normalize_workbook_format(workbook_format)
    if workbook_format == WORKBOOK_FORMAT_PURE_INPUT:
        return None
    return pd.read_excel(file_path, sheet_name="Financing Baseline", engine="openpyxl")


def _clean_definition_text(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def _category_from_classification(classification) -> str:
    text = _clean_definition_text(classification).lower()
    if "generation" in text and "export" not in text:
        return "Generation"
    if "transmission" in text:
        return "Transmission"
    if "distribution" in text:
        return "Distribution"
    if "export" in text:
        return "Exports"
    return ""


def _series_has_values(row: pd.Series, year_cols: list) -> bool:
    if not year_cols:
        return False
    values = pd.to_numeric(row.reindex(year_cols), errors="coerce").fillna(0.0)
    return bool((values != 0).any())


def _read_consumer_segments_from_wholesale_revenue(
    file_path: str,
    df_technologies_classification: pd.DataFrame,
) -> pd.DataFrame:
    """
    Reconstruct the legacy ``Definitions`` consumer-segments block from pure-input
    ``WHOLESALE REVENUE`` rows.

    In the pure-input workbook, offtaker/segment metadata lives on long-table
    ``Share of Off-take`` and ``Wholesale Price`` rows. Only rows with a non-zero
    share or price series are material to the downstream wholesale calculations;
    blank placeholder slots are intentionally ignored so they do not replace the
    no-share fallback with a 0% offtaker split.
    """
    columns = ["Name", "Currency", "Type", "Offtaker"]
    try:
        wholesale = read_long_sheet(file_path, "WHOLESALE REVENUE")
    except (ValueError, KeyError, FileNotFoundError):
        return pd.DataFrame(columns=columns)

    required = {"Variable", "Technology", "Currency", "Name", "Off-taker"}
    if not required.issubset(set(wholesale.columns)):
        return pd.DataFrame(columns=columns)

    year_cols = year_columns_from_dataframe(wholesale)
    valid_vars = {"Share of Off-take", "Wholesale Price"}
    rows = wholesale[wholesale["Variable"].isin(valid_vars)].copy()
    rows = rows[rows["Technology"].notna() & rows["Currency"].notna()]
    if rows.empty:
        return pd.DataFrame(columns=columns)

    rows["_has_values"] = rows.apply(lambda r: _series_has_values(r, year_cols), axis=1)
    material_keys = rows.loc[
        rows["_has_values"], ["Technology", "Currency", "Name", "Off-taker"]
    ].drop_duplicates()
    if material_keys.empty:
        return pd.DataFrame(columns=columns)

    classification = (
        df_technologies_classification.dropna(subset=["Technology"])
        .drop_duplicates(subset=["Technology"], keep="first")
        .set_index("Technology")["Classification"]
        .to_dict()
    )

    items: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    material_keys = material_keys.sort_values(["Technology", "Name", "Off-taker"], na_position="last")
    for _, row in material_keys.iterrows():
        technology = _clean_definition_text(row["Technology"])
        category = _category_from_classification(classification.get(technology, ""))
        if not category:
            continue
        name = _clean_definition_text(row["Name"]) or _clean_definition_text(row["Off-taker"])
        currency = _clean_definition_text(row["Currency"])
        offtaker = _clean_definition_text(row["Off-taker"])
        if not name or not currency:
            continue
        key = (category, name, currency, offtaker)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "Category": category,
                "Name": name,
                "Currency": currency,
                "Type": category[:-1] if category == "Exports" else category,
                "Offtaker": offtaker,
            }
        )

    output_rows: list[dict] = []
    for category in CONSUMER_SEGMENT_CATEGORIES:
        output_rows.append({"Name": category, "Currency": "", "Type": "", "Offtaker": ""})
        for item in items:
            if item["Category"] == category:
                output_rows.append({col: item[col] for col in columns})
    return pd.DataFrame(output_rows, columns=columns)


def _load_excel_data_pure_input_workbook(file_path: str) -> dict:
    """
    Map MINFin Python Input File.xlsx sheets to the same keys as legacy ``load_excel_data``.

    - ``df_technologies`` / ``df_technologies_classification``: **TECHNOLOGY REGISTER** (header row 4),
      then filtered by the parent technology list on **NEW INFRASTRUCTURE** so that sheet is the
      authoritative source for "which technologies exist".
    - ``df_currencies``: **MACROECONOMIC** exchange block (rows with Parameter containing ``Currency`` / Foreign / Local).
    - Other definition lists are not in this workbook: returned as empty DataFrames with the same columns
      as the legacy output so existing notebooks can run with minimal changes.
    """
    tr = pd.read_excel(file_path, sheet_name="TECHNOLOGY REGISTER", header=4, engine="openpyxl")
    tr = tr.loc[:, [c for c in tr.columns if not str(c).startswith("Unnamed:")]]
    if "Technology" in tr.columns:
        tr = tr[tr["Technology"].notna() & (tr["Technology"].astype(str).str.strip() != "")]
    for col in ("Name", "Description", "Technology", "Classification"):
        if col not in tr.columns:
            tr[col] = "" if col != "Description" else ""
    tr = tr.copy()
    tr["Sector"] = ""
    tr = tr.fillna("")
    # NEW INFRASTRUCTURE is the source of truth for "which technologies exist" in pure input.
    # Adding/removing a row in NEW INFRASTRUCTURE removes the technology from df_technologies as well.
    try:
        from MinFin.technology_sheet_io import new_infrastructure_technology_list
        nia_techs = set(new_infrastructure_technology_list(file_path))
    except Exception:
        nia_techs = set()
    # TECHNOLOGY REGISTER in pure input has two blocks:
    #   1. "Financing Technologies"  -> parent tech only (Name == ""), used for financing classification
    #   2. "Investment Plan Technologies" -> OSeMOSYS code in Name (e.g. PWRBIO), parent in Technology
    # Legacy df_technologies has one row per OSeMOSYS Name; drop the empty-Name parent rows so
    # downstream lookups like ``df_technologies[Technology==X]["Name"].values`` return real codes.
    df_technologies = tr[["Name", "Description", "Technology", "Classification", "Sector"]]
    df_technologies = df_technologies[df_technologies["Name"].astype(str).str.strip() != ""].reset_index(drop=True)
    if nia_techs:
        df_technologies = df_technologies[df_technologies["Technology"].isin(nia_techs)].reset_index(drop=True)
    # Classification map keeps both blocks (parent rows are valid for classification lookups), then filtered.
    df_technologies_classification = tr[["Technology", "Classification"]].loc[
        lambda x: (x["Technology"] != "")
    ].drop_duplicates(subset=["Technology"], keep="first")
    if nia_techs:
        df_technologies_classification = df_technologies_classification[
            df_technologies_classification["Technology"].isin(nia_techs)
        ]
    # Currencies: MACROECONOMIC, column 1 = Parameter, 2 = code
    mac = pd.read_excel(file_path, sheet_name="MACROECONOMIC", header=None, engine="openpyxl")
    cur_rows = []
    for i in range(mac.shape[0]):
        p = mac.iloc[i, 1] if mac.shape[1] > 1 else None
        code = mac.iloc[i, 2] if mac.shape[1] > 2 else None
        p = str(p).strip() if pd.notna(p) else ""
        if p in ("Foreign Currency", "Local Currency", "Currency") and pd.notna(code):
            c = str(code).strip()
            if c:
                cur_rows.append({"Code": c, "Currency": c})
    df_currencies = pd.DataFrame(cur_rows).drop_duplicates().reset_index(drop=True)
    if df_currencies.empty:
        df_currencies = pd.DataFrame(columns=["Code", "Currency"])
    # Empty placeholders (same structure as legacy)
    df_param_constraints = pd.DataFrame(columns=["Name", "Description"])
    df_investment_needs = pd.DataFrame(columns=["Name", "Description"])
    df_financing_baseline = pd.DataFrame(columns=["Name", "Description"])
    df_funding_baseline = pd.DataFrame(columns=["Name", "Description"])
    df_scenarios = pd.DataFrame(columns=["Name", "Description"])
    consumer_segments = _read_consumer_segments_from_wholesale_revenue(
        file_path, df_technologies_classification
    )
    # Classification map (match legacy)
    classification_map = df_technologies_classification.set_index("Technology")["Classification"]
    df_technologies = df_technologies.copy()
    m = df_technologies["Technology"].map(classification_map)
    df_technologies["Classification"] = m
    return {
        "df_param_constraints": df_param_constraints,
        "df_investment_needs": df_investment_needs,
        "df_financing_baseline": df_financing_baseline,
        "df_funding_baseline": df_funding_baseline,
        "df_scenarios": df_scenarios,
        "df_currencies": df_currencies,
        "df_technologies": df_technologies,
        "df_technologies_classification": df_technologies_classification,
        "consumer_segments": consumer_segments,
    }


def _load_excel_data_legacy(file_path) -> dict:
    df_definitions_full = pd.read_excel(file_path, sheet_name="Definitions", engine="openpyxl")
    
    def _extract_section(df, row_start, row_end, col_start, col_end, 
                        columns, fill_method="fillna", fill_value=""):
        """
        Helper function to extract and process a section from the DataFrame.
        
        Parameters:
        -----------
        df : DataFrame
            Source DataFrame
        row_start, row_end : int
            Row range (end is exclusive)
        col_start, col_end : int
            Column range (end is exclusive)
        columns : list
            Column names for the extracted DataFrame
        fill_method : str
            Either "fillna" or "dropna"
        fill_value : str
            Value to fill NaN with (only used if fill_method="fillna")
        """
        section = df.iloc[row_start:row_end, col_start:col_end]
        
        if fill_method == "fillna":
            section = section.fillna(fill_value)
        elif fill_method == "dropna":
            section = section.dropna()
        
        section = section.reset_index(drop=True)
        section.columns = columns
        return section
    
    # Define extraction configurations
    extraction_configs = [
        {
            "name": "df_param_constraints",
            "row_range": (23, 34),
            "col_range": (1, 3),
            "columns": ["Name", "Description"],
            "fill_method": "fillna"
        },
        {
            "name": "df_investment_needs",
            "row_range": (37, 45),
            "col_range": (1, 3),
            "columns": ["Name", "Description"],
            "fill_method": "dropna"
        },
        {
            "name": "df_financing_baseline",
            "row_range": (58, 91),
            "col_range": (1, 3),
            "columns": ["Name", "Description"],
            "fill_method": "fillna"
        },
        {
            "name": "df_funding_baseline",
            "row_range": (48, 56),
            "col_range": (1, 3),
            "columns": ["Name", "Description"],
            "fill_method": "fillna"
        },
        {
            "name": "df_scenarios",
            "row_range": (23, 26),
            "col_range": (4, 6),
            "columns": ["Name", "Description"],
            "fill_method": "fillna"
        },
        {
            "name": "df_currencies",
            "row_range": (58, 69),
            "col_range": (4, 6),
            "columns": ["Code", "Currency"],
            "fill_method": "fillna"
        },
        {
            "name": "df_technologies",
            "row_range": (23, 74),
            "col_range": (8, 13),
            "columns": ["Name", "Description", "Technology", "Classification", "Sector"],
            "fill_method": "fillna"
        },
        {
            "name": "df_technologies_classification",
            "row_range": (23, 74),
            "col_range": (14, 18),
            "columns": ["Technology", "Classification"],
            "fill_method": "fillna"
        },
        {
            "name": "consumer_segments",
            "row_range": (76, 97),
            "col_range": (8, 12),
            "columns": ["Name", "Currency", "Type", "Offtaker"],
            "fill_method": "fillna"
        }
    ]
    
    # Extract all sections
    extracted_data = {}
    for config in extraction_configs:
        df = _extract_section(
            df_definitions_full,
            config["row_range"][0], config["row_range"][1],
            config["col_range"][0], config["col_range"][1],
            config["columns"],
            config["fill_method"]
        )
        extracted_data[config["name"]] = df
    
    # Post-process technologies_classification
    df_technologies_classification = extracted_data["df_technologies_classification"]
    df_technologies_classification = df_technologies_classification[
        df_technologies_classification["Technology"] != ""
    ]
    extracted_data["df_technologies_classification"] = df_technologies_classification
    
    # Post-process technologies: map Classification
    df_technologies = extracted_data["df_technologies"]
    classification_map = df_technologies_classification.set_index("Technology")["Classification"]
    df_technologies["Classification"] = df_technologies.dropna()["Technology"].map(classification_map)
    extracted_data["df_technologies"] = df_technologies
    
    # Return dictionary - names come directly from extraction_configs
    return {config["name"]: extracted_data[config["name"]] for config in extraction_configs}


def load_excel_data(file_path, workbook_format: str = WORKBOOK_FORMAT_AUTO) -> dict:
    """
    Load definition-style tables from the workbook. Use ``workbook_format`` to switch layouts.

    Parameters
    ----------
    file_path : str
        Path to ``MINFin Energy Example Input File.xlsm`` (legacy) or ``MINFin Python Input File.xlsx`` (pure input).
    workbook_format : str
        'auto' — use :func:`detect_workbook_format` (INVESTMENT PLAN + no Definitions ⇒ pure_input).
        'legacy' — **Definitions** sheet (and **New Infrastructure (Input)** read separately).
        'pure_input' — **TECHNOLOGY REGISTER**, **MACROECONOMIC** (currencies), empty placeholders for other tables. The name ``'python'`` is accepted as a deprecated alias.

    Returns
    -------
    dict
        Same keys as before: ``df_param_constraints``, ``df_investment_needs``, ``df_financing_baseline``,
        ``df_funding_baseline``, ``df_scenarios``, ``df_currencies``, ``df_technologies``,
        ``df_technologies_classification``, ``consumer_segments``.
    """
    if workbook_format == WORKBOOK_FORMAT_AUTO:
        workbook_format = detect_workbook_format(file_path)
    else:
        workbook_format = normalize_workbook_format(workbook_format)
    if workbook_format == WORKBOOK_FORMAT_PURE_INPUT:
        return _load_excel_data_pure_input_workbook(file_path)
    if workbook_format == WORKBOOK_FORMAT_LEGACY:
        return _load_excel_data_legacy(file_path)
    raise ValueError(
        f"workbook_format must be one of {WORKBOOK_FORMAT_CHOICES} (or the alias 'python' for pure_input), got {workbook_format!r}"
    )


def process_funding_baseline(df_funding_baseline_full,melted_currency_df=get_melted_currency_df()):
    """
    Load FFRM Input data for Oil, Gas, and Coal into a structured DataFrame.
    
    Parameters:
    df_ffrm_full (DataFrame): The full FFRM (Input) sheet from the Excel file.

    Returns:
    DataFrame: A merged DataFrame containing all energy types with multi-level column names.
    """
    # starting_cols = {'Oil': 1, 'Gas': 4, 'Coal': 7}  # Define starting columns
    starting_row = 9

    # Extract relevant section
    df = df_funding_baseline_full.iloc[starting_row:starting_row+150, 0:9].copy()  # +3 to ensure all columns
    df.columns = df_funding_baseline_full.iloc[starting_row-1, 0:9].fillna(0).tolist()
    
    df.reset_index(drop=True, inplace=True)

    # Merge all energy types into a single DataFrame
    # df_final = pd.concat(df, axis=1)
    
    # Remove duplicate Year columns (keep only one)
    df_final = df#df_final.loc[:, ~df_final.columns.duplicated()]
    df_final = df_final.drop(columns=["Exchange Rate"], errors="ignore").fillna(0)  # Remove existing exchange rate column if present
    # print(exchange_rates.melt(id_vars=["Year"], var_name="Currency", value_name="Exchange Rate"))
    # Merge funding baseline with exchange rates based on Year and Currency
    
    if "Year" in melted_currency_df.columns:
        df_final = df_final.merge(melted_currency_df, on=["Year", "Currency"], how="left")
    else:
        # Assume index contains years, reset index to column for merging
        temp_currency_df = melted_currency_df.reset_index().rename(columns={melted_currency_df.index.name or "index": "Year"})
        df_final = df_final.merge(temp_currency_df, on=["Year", "Currency"], how="left")
    
    mask = df_final["Type"] != "Grant"

    df_final.loc[mask, "volume_in_usd"] = (
        df_final.loc[mask, "Volume (Million)"] *
        df_final.loc[mask, "Govt Share"] /
        df_final.loc[mask, "Exchange Rate"]
    )

    df_final.loc[~mask, "volume_in_usd"] = (
        df_final.loc[~mask, "Volume (Million)"] /
        df_final.loc[~mask, "Exchange Rate"]
    )
    return df_final

def preprocess_data_for_cagr(col):
    '''
    Preprocess the data for CAGR calculation.The logic is in line with MinFin Engergy 251203.xlsm sheet "Definitions" CAGR of annual growth rate.
    '''
    s = pd.to_numeric(col, errors="coerce")
    # Exclude 'average' or other non-numeric years from calculation
    years = pd.to_numeric([y for y in col.index if str(y).lower() != "average"], errors="coerce")
    pos = s[s > 0]
    if len(pos) < 2:
        return pd.Series(dtype=float)
    s = s.loc[pos.index.min():pos.index.max()]
   
    return s

def cal_annual_cagr(col):
    '''
    Calculate the annual CAGR of a given column. The logic is in line with MinFin Engergy 251203.xlsm sheet "Definitions" CAGR of annual growth rate.
    '''
    s = preprocess_data_for_cagr(col)
    if s.empty:
        return 0.0
    ratios = s.div(s.shift(1)).iloc[1:]

    ratios = ratios.replace([np.inf, -np.inf], np.nan).dropna()  # IFERROR(...,0)
    return ratios.mean() - 1                    # AVERAGE(...) - 1

def cal_period_cagr(col):
    '''
    Calculate the period CAGR of a given column. The logic is in line with MinFin Engergy 251203.xlsm sheet "Definitions" CAGR of annual growth rate.
    '''
    s = preprocess_data_for_cagr(col)
    if s.empty:
        return 0.0
    return (s.iloc[-1] / s.iloc[0]) ** (1/( s.index.max() - s.index.min())) - 1

def log_reg_growth_rate(col):
    '''
    This is in line with MinFin Engergy 251203.xlsm sheet.
    '''
    s = preprocess_data_for_cagr(col)
    if s.empty:
        return 0.0
    s = s[s > 0]
    y = s.values.astype(float)
    x = s.index.astype(float)
    ln_y = np.log(y)

    # Linear regression ln(y) = a + b x
    b, a = np.polyfit(x, ln_y, 1)

    return float(np.exp(b) - 1)

def get_funding_envelope(df_funding_baseline):
    funding_types = ["Budget","SOE Gen.", "Grant"]

    # Filter relevant data
    df_filtered = df_funding_baseline[df_funding_baseline["Type"].isin(funding_types)]
    # Pivot: Sum values for each funding type across years
    df_funding_envelope = df_filtered.pivot_table(index="Type", columns="Year", values="volume_in_usd", aggfunc="sum")

    # Transpose: Make years as columns (match the image format)
    df_funding_envelope = df_funding_envelope.T
    # Calculate the yearly average (mean) across all years for each funding type
    df_funding_envelope_deep_copy = df_funding_envelope.copy()
    # Calculate the annual growth rate (year-over-year percentage change)
    df_funding_envelope.loc["Annual Average"] = df_funding_envelope_deep_copy.apply(
        lambda s: (p := s.fillna(0) > 0).any() and s.loc[p.idxmax():p.iloc[::-1].idxmax()].mean() or 0
    )
    df_funding_envelope.loc["Annual CAGR"] = df_funding_envelope_deep_copy.apply(
    cal_annual_cagr, axis=0
    )
    df_funding_envelope.loc["Period CAGR"] = df_funding_envelope_deep_copy.apply(
    cal_period_cagr, axis=0
    )
    df_funding_envelope.loc["Log Reg Growth Rate"] = df_funding_envelope_deep_copy.apply(
    log_reg_growth_rate, axis=0
    )
    

    return df_funding_envelope.fillna(0)
