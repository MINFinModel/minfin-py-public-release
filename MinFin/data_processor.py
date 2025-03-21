
import pandas as pd
import numpy as np


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
def load_excel_data(file_path):
    df_definitions_full = pd.read_excel(file_path, sheet_name="Definitions", engine="openpyxl")
    
    # Extract different sections
    df_param_constraints = df_definitions_full.iloc[27:38, 1:3].fillna("").reset_index(drop=True)
    df_param_constraints.columns = ["Name", "Description"]
    
    df_financing_baseline = df_definitions_full.iloc[22:55, 4:6].fillna("").reset_index(drop=True)
    df_financing_baseline.columns = ["Name", "Description"]
    
    df_funding_baseline = df_definitions_full.iloc[22:31, 7:9].fillna("").reset_index(drop=True)
    df_funding_baseline.columns = ["Name", "Description"]
    
    df_scenarios = df_definitions_full.iloc[23:25, 1:3].fillna("").reset_index(drop=True)
    df_scenarios.columns = ["Name", "Description"]
    
    df_currencies = df_definitions_full.iloc[33:39, 1:3].fillna("").reset_index(drop=True)
    df_currencies.columns = ["Code", "Currency"]
    
    df_technologies = df_definitions_full.iloc[22:56, 10:13].fillna("").reset_index(drop=True)
    df_technologies.columns = ["Name", "Description", "Classification"]

    return df_param_constraints, df_financing_baseline, df_funding_baseline, df_scenarios, df_currencies, df_technologies

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
    df = df_funding_baseline_full.iloc[starting_row:starting_row+90, 0:9].copy()  # +3 to ensure all columns
    df.columns = df_funding_baseline_full.iloc[starting_row-1, 0:9].fillna(0).tolist()
    
    df.reset_index(drop=True, inplace=True)

    # Merge all energy types into a single DataFrame
    # df_final = pd.concat(df, axis=1)
    
    # Remove duplicate Year columns (keep only one)
    df_final = df#df_final.loc[:, ~df_final.columns.duplicated()]
    df_final = df_final.drop(columns=["Exchange Rate"], errors="ignore")  # Remove existing exchange rate column if present
    # print(exchange_rates.melt(id_vars=["Year"], var_name="Currency", value_name="Exchange Rate"))
    # Merge funding baseline with exchange rates based on Year and Currency
    df_final = df_final.merge(melted_currency_df,on=["Year", "Currency"], how="left")
    df_final["volume_in_usd"] = df_final["Volume (Million)"]*df_final['Govt Share']/df_final['Exchange Rate']
    return df_final

def get_funding_envelope(df_funding_baseline):
    funding_types = ["Budget","SOE Gen.", "Grant"]

    # Filter relevant data
    df_filtered = df_funding_baseline[df_funding_baseline["Type"].isin(funding_types)]

    # Pivot: Sum values for each funding type across years
    df_funding_envelope = df_filtered.pivot_table(index="Type", columns="Year", values="volume_in_usd", aggfunc="sum")

    # Transpose: Make years as columns (match the image format)
    df_funding_envelope = df_funding_envelope.T
    # Calculate the yearly average (mean) across all years for each funding type
    df_funding_envelope.loc["Annual Average"] = df_funding_envelope.fillna(0).mean()

    # Calculate the annual growth rate (year-over-year percentage change)
    df_funding_envelope.loc["Annual Growth Rate"] = (df_funding_envelope.loc[2024].fillna(0)/df_funding_envelope.loc[2010].fillna(0))**(1/(2024-2010))-1 # Convert to percentage
    
    return df_funding_envelope.fillna(0)