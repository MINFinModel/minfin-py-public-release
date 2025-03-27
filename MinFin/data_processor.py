
import pandas as pd
import numpy as np


class osemosys_extractor:
    def __init__(self,scenario) -> None:
        self.scenario = scenario
        self.starting_rows = {'net_zero': 137,'least_cost': 137}
        self.starting_cols = {'least_cost': {'variable_cost': 4, 'fixed_cost': 6, 'annual_elec_production': 10,'co2_emission':18}}
        self.starting_cols['net_zero']= { key:value-1 for key,value in self.starting_cols['least_cost'].items()}
        self.starting_cols[scenario]['carbon_price'] = 16
    def get_cols(self,name_of_cost,df_osemosys_full):
        starting_row = self.starting_rows[self.scenario]
        starting_col = self.starting_cols[self.scenario]
        if name_of_cost in ['year','years','y']:
            years = df_osemosys_full.iloc[starting_row:starting_row+46, 0:1]
            return years
        cost = df_osemosys_full.iloc[starting_row:starting_row+46, starting_col[name_of_cost]:starting_col[name_of_cost]+1]  # A10:AH66 in Million
        cost.reset_index(drop=True, inplace=True)
        return cost
    
    @staticmethod
    def load_osemosys_input(scenario,df_osemosys_full):
        starting_rows = {'net_zero': 9,'least_cost': 73}
        starting_row = starting_rows[scenario]
        # Extract different sections
        df_captial_cost = df_osemosys_full.iloc[starting_row:starting_row+56, 0:34]  # A10:AH66 in Million
        df_captial_cost.columns = ["Year"] + list(df_osemosys_full.iloc[starting_row-1, 1:34])  # Rename columns using the header row
        df_captial_cost.reset_index(drop=True, inplace=True)

        df_captial_cost.iloc[:, 1:] = df_captial_cost.iloc[:, 1:].fillna(0)  # Replace NaN with 0
        # Calculate the total row
        total_row = pd.DataFrame(df_captial_cost.iloc[:, 1:].sum()).T  # Sum all numerical columns and transpose
        total_row.insert(0, "Year", "Total")  # Set the "Year" column to "Total"

        # Append the total row to the DataFrame
        df_captial_cost =pd.concat([df_captial_cost,total_row], ignore_index=True)
        
        df_ffe  = df_osemosys_full.iloc[starting_row:starting_row+56, 35:39]  # A10:AH66 in Million
        df_ffe.columns =  list(df_osemosys_full.iloc[starting_row-1, 35:39])  # Rename columns using the header row
        df_ffe.reset_index(drop=True, inplace=True)
        
        df_ffe.iloc[:, 1:] = df_ffe.iloc[:, 1:].fillna(0)  # Replace NaN with 0

        df_ffe["Total"] = df_ffe.iloc[:, 0:].sum(axis=1)
        df_ffe["Year"] = df_captial_cost["Year"]

        # Calculate the total row
        total_row = pd.DataFrame(df_ffe.iloc[:, 1:].sum()).T  # Sum all numerical columns and transpose
        total_row.iloc[:,-1]= "Total" # Set the "Year" column to "Total"
        df_ffe =pd.concat([df_ffe,total_row], ignore_index=True)
        df_ffe.set_index("Year", inplace=True, drop=False)

        return df_captial_cost, df_ffe

  
    def get_totals(self,df_osemosys_full):
        #Load Variable Cost, Fixed Cose, and Annual Electricity
        # starting_cols = {'least_cost': {'variable_cost': 4, 'fixed_cost': 6, 'elec_production': 10,'co2_emission':18}}
        # starting_cols['net_zero']= { key:value-1 for key,value in starting_cols['least_cost'].items()}
       
        # print(starting_col.keys())
        # Extract different sections
        
        # print(years)
        totals=pd.DataFrame()
        for name in self.starting_cols[self.scenario].keys(): 
            
            totals[name] = self.get_cols(name,df_osemosys_full)

        years = self.get_cols('year',df_osemosys_full)
        totals.set_index(years.iloc[:,0], inplace=True)
        # print(years.iloc[0,0])
        totals['capital_cost'] = self.cal_total_capital(df_osemosys_full,since_year=years.iloc[0,0])["total_capital"].values
        totals['total_cost'] = totals['capital_cost']+totals['variable_cost']+totals['fixed_cost']
        totals['cost_of_elec_in_pj'] = totals['total_cost']/totals['annual_elec_production']
        totals['cost_of_elec'] = totals['cost_of_elec_in_pj']/3.6 #Convert PJ/USD to TWh/USD
        totals['cost_of_co2'] = totals['co2_emission']*totals['carbon_price'] #Convert PJ/USD to TWh/USD
        # totals.reset_index(inplace=True)  # Moves the current index to a column
        totals.index.name = None  # Removes "MINFin" from the index name
        # df_ffe_least_cost.set_index("Year", inplace=True)
        return totals
    def cal_total_capital(self, df_osemosys_full,since_year=2025):
        df_capatial_cost_detail ,df_ffe=self.load_osemosys_input(self.scenario,df_osemosys_full)
        # Convert 'Year' column to numeric (ignoring 'Total' row)
        df_capatial_cost_detail["Year"] = pd.to_numeric(df_capatial_cost_detail["Year"], errors='coerce')
        # df_ffe["Year"] = pd.to_numeric(df_ffe["Year"], errors='coerce')

        # Filter for rows where Year > 2025
        df_filtered = df_capatial_cost_detail[df_capatial_cost_detail["Year"] >= since_year]
        # df_ffe_filtered = df_ffe[df_ffe["Year"]>=since_year]
        # Sum across all columns (excluding 'Year')
        total_captital = df_filtered.iloc[:, 1:].sum(axis=1).to_frame()
        total_captital.columns=["total_capital"]
        # df_stacked = pd.concat([total_captital, df_ffe_filtered], axis=1)  # axis=0 → row-wise
        return total_captital

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