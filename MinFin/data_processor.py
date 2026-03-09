
import pandas as pd
import numpy as np
import warnings

class input_extractor:
    def __init__(self,scenario) -> None:
        self.scenario = scenario
        self.starting_rows = {'net_zero': 137,'least_cost': 137}
        self.starting_cols = {'least_cost': {'variable_cost': 4, 'fixed_cost': 6, 'co2_emission':18}}
        self.starting_cols['net_zero']= { key:value-1 for key,value in self.starting_cols['least_cost'].items()}
        self.starting_cols[scenario]['carbon_price'] = 16
    
    def get_other_inputs(self,name_of_input,df_input_full):
        '''
        Get other inputs for a given scenario.
        '''
        starting_row = self.starting_rows[self.scenario]
        starting_col = self.starting_cols[self.scenario]
        if name_of_input in ['year','years','y']:
            years = df_input_full.iloc[starting_row:starting_row+46, 0:1]
            return years
        input_df = df_input_full.iloc[starting_row:starting_row+46, starting_col[name_of_input]:starting_col[name_of_input]+1]  # A10:AH66 in Million
        input_df.fillna(0, inplace=True)
        input_df.reset_index(drop=True, inplace=True)
        return input_df
    
    @staticmethod
    def filter_valid_cols(df, header_row):
        header_row = header_row.apply(
            lambda x: (np.nan if isinstance(x, str) and not x.strip()
                       else x.strip() if isinstance(x, str) else x)
        )
        num_named_cols = header_row.notna().sum()
        df = df.iloc[:, :num_named_cols]
        df.columns = list(header_row.iloc[:num_named_cols])
        df.reset_index(drop=True, inplace=True)
        return df
    
    @staticmethod
    def _build_cost_df(df_input_full, starting_row, col_start, col_end, df_year, n_rows=56):
        """
        Extract a cost block for a given column range and append a 'Total' row.
        """
        # Slice raw values and header row from the Excel sheet
        df = df_input_full.iloc[starting_row:starting_row + n_rows, col_start:col_end]
        header_row = df_input_full.iloc[starting_row - 1, col_start:col_end]

        # Normalise column names and drop unnamed/empty columns
        df = input_extractor.filter_valid_cols(df, header_row)

        # Replace missing values with zero for downstream arithmetic
        df = df.fillna(0)

        # Attach the Year column as the first column
        df = pd.concat([df_year, df], axis=1)

        # Compute and append a 'Total' row across all value columns
        total_row = pd.DataFrame(df.iloc[:, 1:].sum()).T
        total_row.insert(0, "Year", "Total")
        df = pd.concat([df, total_row], ignore_index=True)

        return df
    
    @staticmethod
    def _build_input_blocks(scenario, df_input_full):
        """
        Internal helper to build all input blocks for a given scenario.
        Returns a dict of DataFrames keyed by block name.
        """
        starting_rows = {'net_zero': 9, 'least_cost': 73}
        starting_row = starting_rows[scenario]
        n_rows = 56  # number of data rows per scenario block

        # Shared Year column
        df_year = (
            df_input_full
            .iloc[starting_row:starting_row + n_rows, 0]
            .reset_index(drop=True)
            .to_frame(name="Year")
        )

        # Column ranges
        capital_start_col = 1
        capital_end_col = 51

        ffe_start_col = capital_end_col + 1
        ffe_end_col = ffe_start_col + 20

        elec_production_start_col = ffe_end_col + 2 
        elec_production_end_col = elec_production_start_col + 50

        op_start_col = elec_production_end_col + 1
        op_end_col = op_start_col + 50

        potential_generation_start_col = op_end_col + 1
        potential_generation_end_col = potential_generation_start_col + 50

        block_specs = {
            "capital_cost": (capital_start_col, capital_end_col),
            "ffe": (ffe_start_col, ffe_end_col),
            "elec_production": (elec_production_start_col, elec_production_end_col),
            "opex": (op_start_col, op_end_col),
            "potential_generation": (potential_generation_start_col, potential_generation_end_col),
        }

        blocks = {}
        for name, (col_start, col_end) in block_specs.items():
            blocks[name] = input_extractor._build_cost_df(
                df_input_full,
                starting_row,
                col_start,
                col_end,
                df_year,
                n_rows=n_rows,
            )

        return blocks

    @staticmethod
    def load_block_for(scenario, df_input_full, block_name):
        """
        Return a single input block by name, e.g. 'capital_cost', 'ffe'.
        """
        blocks = input_extractor._build_input_blocks(scenario, df_input_full)
        return blocks[block_name]

    @staticmethod
    def load_all_blocks_for(scenario, df_input_full):
        """
        Return all input blocks as a dict of DataFrames.
        """
        return input_extractor._build_input_blocks(scenario, df_input_full)

    @staticmethod
    def load_all_for(scenario, df_input_full):
        """
        return all input blocks as  DataFrames.
        """
        blocks = input_extractor.load_all_blocks_for(scenario, df_input_full)
        return blocks["capital_cost"], blocks["ffe"], blocks["elec_production"], blocks["opex"], blocks["potential_generation"] 
    
    @staticmethod
    def load_osemosys_input(scenario, df_input_full):
        """
        Legacy name kept for compatibility. Prefer load_input/load_input_blocks.
        """
        blocks = input_extractor.load_all_blocks_for(scenario, df_input_full)
        # Set "Year" column as index for all DataFrames in blocks, if present
        for k, v in blocks.items():
            if "Year" in v.columns:
                blocks[k] = v.set_index("Year")
        return blocks["capital_cost"], blocks["ffe"], blocks["elec_production"]
    
    def load(self, df_input_full, block_name):
        """
        Convenience instance API: load a single block for this extractor's scenario.
        Default block is 'ffe'.
        """
        blocks = input_extractor._build_input_blocks(self.scenario, df_input_full)
        if "Year" in blocks[block_name].columns:
            return blocks[block_name].set_index("Year")
        else:
            import warnings
            warnings.warn(f"'Year' column not found in block '{block_name}'. Returning block unmodified.")
            return blocks[block_name]
    
    def load_all(self, df_input_full):
        return input_extractor.load_all_for(self.scenario, df_input_full)  
    
    def get_all_other_inputs(self,df_input_full):
        totals=pd.DataFrame()
        for name in self.starting_cols[self.scenario].keys(): 
            totals[name] = self.get_other_inputs(name,df_input_full)

        years = self.get_other_inputs('year',df_input_full)
        totals.set_index(years.iloc[:,0], inplace=True)
        #process the data
        totals['capital_cost'] = self.cal_total_capital(df_input_full,since_year=years.iloc[0,0])["total_capital"].values
        totals['total_cost'] = totals['capital_cost']+totals['variable_cost']+totals['fixed_cost']
        totals['annual_elec_production'] = self.cal_total_elec_production(df_input_full,since_year=years.iloc[0,0])["annual_elec_production"].values
        totals['cost_of_elec_in_pj'] = totals['total_cost']/totals['annual_elec_production']
        totals['cost_of_elec'] = totals['cost_of_elec_in_pj']/3.6 #Convert PJ/USD to TWh/USD
        totals['cost_of_co2'] = totals['co2_emission']*totals['carbon_price'] #Convert PJ/USD to TWh/USD
        # totals.reset_index(inplace=True)  # Moves the current index to a column
        totals.index.name = None  # Removes "MINFin" from the index name
        # df_ffe_least_cost.set_index("Year", inplace=True)
        return totals
    def get_totals(self,df_input_full):
        '''
        Remain compatibility with the old function name.
        '''
        return self.get_all_other_inputs(df_input_full)
    def calc_total_for_block(self, df_input_full, block_name, since_year=2025, total_col_name=None):
        """
        Sum all value columns of a given block from since_year onwards.
        """
        df_block = self.load(df_input_full, block_name).copy()

        # Convert Year to numeric for comparison filtering
        import warnings
        if "Year" in df_block.columns:
            df_block["Year"] = pd.to_numeric(df_block["Year"], errors="coerce")
        elif df_block.index.name == "Year" or (df_block.index.names and "Year" in df_block.index.names):
            df_block.index = pd.to_numeric(df_block.index, errors="coerce")
            df_block["Year"] = df_block.index  # 添加year列
        else:
            warnings.warn("No 'Year' column or index found. Adding 'Year' based on the current index.")
            df_block["Year"] = df_block.index

        # Filter data from since_year onwards
        df_filtered = df_block[df_block["Year"] >= since_year]
        # Sum across all columns (excluding 'Year')
        total = df_filtered.iloc[:, 1:].sum(axis=1).to_frame()

        # Set column name
        if total_col_name is None:
            total_col_name = f"total_{block_name}"
        total.columns = [total_col_name]

        return total
    def cal_total_capital(self, df_input_full, since_year=2025):
        # Reuse the general function, specifically for capital_cost
        return self.calc_total_for_block(
            df_input_full,
            block_name="capital_cost",
            since_year=since_year,
            total_col_name="total_capital",
        )
    def cal_total_elec_production(self, df_input_full, since_year=2025):
        # Reuse the general function, specifically for capital_cost
        return self.calc_total_for_block(
            df_input_full,
            block_name="elec_production",
            since_year=since_year,
            total_col_name="annual_elec_production",
        )

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
    """
    Load and extract various data sections from the Definitions sheet of an Excel file.
    
    Parameters:
    -----------
    file_path : str
        Path to the Excel file
        
    Returns:
    --------
    dict
        A dictionary containing DataFrames with keys from extraction_configs.
        Keys: 'df_param_constraints', 'df_investment_needs', 'df_financing_baseline',
              'df_funding_baseline', 'df_scenarios', 'df_currencies', 
              'df_technologies', 'df_technologies_classification'
        
        Usage:
            data = load_excel_data(file_path)
            df_technologies = data['df_technologies']
            # or unpack if needed:
            df_param_constraints, df_investment_needs, ... = data.values()
    """
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