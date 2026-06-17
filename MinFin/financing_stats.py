"""Historical financing baseline statistics and technology requirement tables."""

from __future__ import annotations

import pandas as pd

class financing_baseline_stats:
    def __init__(self, financing_baseline_extractor, repayment_schedule):
        self.repayment_schedule = repayment_schedule.copy()
        self.historical = financing_baseline_extractor.get_historical()        
        # Fill multiple columns at once
        cols_to_copy = ['Financing Source', 'Type of Finance', 'Volume in USD', 'Term', 'Grace period']
        self.repayment_schedule.loc[:, cols_to_copy] = self.historical[cols_to_copy]

                
        self.repayment_schedule['Interest rate'] = self.historical['Rate']
        # self.repayment_schedule['Financing Source'] = self.historical['Financing Source']
        # self.repayment_schedule['Type of Finance'] = self.historical['Type of Finance']
        # self.repayment_schedule['Volume in USD'] = self.historical['Volume in USD']
        # self.repayment_schedule['Term'] = self.historical['Term']
        # self.repayment_schedule['Grace period'] = self.historical['Grace period']
        self.cols = ['Volume (USD)', 'Interest rate', 'Term', 'Grace period', 'Average Annual Payment']#, 'Average Annual Discounted Payment',	'Total Discounted Payment']
        self.rows = ['Total financing volumes',
                'Conc_IFI',
                'Conc_DPS',
                'Comm_Intl',
                'Comm_Dom',
                ]
    def cal_summary_stats(self):
        cols = self.cols
        rows = self.rows
        repayment_schedule = self.repayment_schedule
        
        df_summary_stats = pd.DataFrame(columns=cols,index=rows)
        for row in rows:
            # Calculate 'Volume (USD)' for 'Commercial Domestic Finance (Comm Dom)'
            df_summary_stats.loc[row, 'Volume (USD)'] = self.historical[
                self.historical['Financing Source'] == row
            ]['Volume in USD'].sum()
        
        for row in rows[1:]:
            for col in cols[1:]:
                weighted_data = repayment_schedule[
                (repayment_schedule['Financing Source'] == row)
                ][col]* repayment_schedule[
                (repayment_schedule['Financing Source'] == row)  
                ][ "Volume in USD"]  
                df_summary_stats.loc[row, col] = weighted_data.sum() / repayment_schedule[
                (repayment_schedule['Financing Source'] == row) 
                ][ "Volume in USD"].sum() 
        
            debt_share = repayment_schedule[
                    (repayment_schedule['Financing Source'] == row)
                    ][repayment_schedule['Type of Finance'] == 'Loan']['Volume in USD'].sum() / repayment_schedule[
                    (repayment_schedule['Financing Source'] == row) 
                    ][ "Volume in USD"].sum()
            df_summary_stats.loc[row, 'Debt Share'] = debt_share
            df_summary_stats.loc[row, 'Equity Share'] = 1 - debt_share
        df_summary_stats.loc[rows[0], 'Volume (USD)'] = df_summary_stats['Volume (USD)'].sum()    
        
        return df_summary_stats
    
    def cal_equity_debt_stats(self,type_of_finance='Equity'):
        cols = self.cols
        rows = self.rows
        repayment_schedule = self.repayment_schedule
        df = pd.DataFrame(columns=cols,index=rows)
        for row in rows[1:]:
            # Calculate 'Volume (USD)' for 'Commercial Domestic Finance (Comm Dom)'
            df.loc[row, 'Volume (USD)'] = self.historical[
                (self.historical['Financing Source'] == row) & (self.historical['Type of Finance'] == type_of_finance)
            ]['Volume in USD'].sum()
            
        df.loc[rows[0], 'Volume (USD)'] = df['Volume (USD)'].sum()
        # repayment_schedule['Interest rate'] = self.historical['Rate']
        # repayment_schedule['Financing Source'] = self.historical['Financing Source']
        # repayment_schedule['Type of Finance'] = self.historical['Type of Finance']
        # repayment_schedule['Volume in USD'] = self.historical['Volume in USD']
        # repayment_schedule['Term'] = self.historical['Term']
        # repayment_schedule['Grace period'] = self.historical['Grace period']
        for row in rows[1:]:
            for col in cols[1:]:
                
                weighted_data = repayment_schedule[
                (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)
                ][col]* repayment_schedule[
                (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)
                ][ "Volume in USD"]  
                
                denominator = repayment_schedule[
                    (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)
                ][ "Volume in USD"].sum()
                if denominator == 0:
                    df.loc[row, col] = 0
                else:
                    df.loc[row, col] = weighted_data.sum() / denominator
                 
                if df.loc[row, col] == float('inf'):
                    print("inf",repayment_schedule[
                (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)
                ][ "Volume in USD"].sum(),weighted_data.sum())  
                    print(repayment_schedule[
                (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)
                ][col])
                    print(repayment_schedule[
                (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)
                ][ "Volume in USD"])
                    
                # Select the correct volume column based on currency condition
                volume_column = "Volume in USD"
                
            if type_of_finance in ["Loan", "loan"]:
                market_element  = repayment_schedule[
            (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)& ( self.historical['Schedule'] != 'Equity')
            ]['Market Element']* repayment_schedule[
            (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)& ( self.historical['Schedule'] != 'Equity')
            ][ "Volume in USD"]/ repayment_schedule[
                (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)
                ][ "Volume in USD"].sum() 
            
                df.loc[row, 'Market Element'] = market_element.sum()
                df.loc[row, 'Grant Element'] = 1 - df.loc[row, 'Market Element']
                # Compute weighted sum
                # numerator = (filtered_df[volume_column] * repayment_schedule[col]).sum()
                
                # Compute total volume sum
                # denominator = filtered_df[volume_column].sum()
                
                # Avoid division by zero
                # df.loc[row, col] = numerator / denominator if denominator != 0 else 0    
        return df
    def add_weighted_average(self,df):
        cols = df.columns
        rows = self.rows
        for index, col in enumerate(cols[1:]):
            # #print(index,col)
            df.iloc[0, index+1] = (df[col][1:]*df['Volume (USD)'][1:]).sum()/df['Volume (USD)'][1:].sum()
            #  #print(df.iloc[1, index+1])
        return df
    def get_repayment_statistics(self):
        # #print(self.cal_summary_stats().columns)
        df_summary = self.add_weighted_average(self.cal_summary_stats())
        df_equity = self.add_weighted_average(self.cal_equity_debt_stats())
        df_debt = self.add_weighted_average(self.cal_equity_debt_stats(type_of_finance='Loan'))
        df_final = pd.concat(
        [df_summary, df_equity, df_debt], 
        axis=0, 
        keys=['Summary', 'Equity', 'Debt']  # adding hierarchical index
        )
        return df_final  
        
    def get_institution_shares(self):
        rows = ["Bilateral Agency",
                "Multilateral Agency",
                "Foreign Government",
                "National Government",
                "Domestic Public Sector",
                "Climate Funds",
                "Commercial Bank",
                "Private Equity Fund"
                ]
        repayment_schedule = self.repayment_schedule
        df_institution_shares = pd.DataFrame(index=rows)

        for row in rows:   
            df_institution_shares.loc[row, 'Share'] = repayment_schedule[(self.historical['Financial Institution'] == row) 
                ][ "Volume in USD"].sum()/ repayment_schedule.loc[:, "Volume in USD"].sum() 
            df_institution_shares.loc[row, 'Market Element'] = repayment_schedule[(self.historical['Financial Institution'] == row) & (self.historical['Schedule'] != 'Equity')
                ][ "Market Element"].mean()#/ repayment_schedule.loc[:, "Volume in USD"].sum() 
            if repayment_schedule.loc[(self.historical['Financial Institution'] == row), "Volume in USD"].sum() != 0:
                df_institution_shares.loc[row, 'Debt Share'] = repayment_schedule[(self.historical['Financial Institution'] == row) & (self.historical['Schedule'] != 'Equity')
                    ][ "Volume in USD"].sum()/ repayment_schedule.loc[(self.historical['Financial Institution'] == row), "Volume in USD"].sum()
                df_institution_shares.loc[row, 'Equity Share'] = repayment_schedule[(self.historical['Financial Institution'] == row) & (self.historical['Schedule'] == 'Equity')
                    ][ "Volume in USD"].sum()/ repayment_schedule.loc[(self.historical['Financial Institution'] == row), "Volume in USD"].sum()
                
        return df_institution_shares
    
    def get_financing_sector_shares(self):
        rows = ["Public",
                "Private",
                "Comm_Dom",
                "Comm_Intl",
                "Conc_DPS",
                "Conc_IFI",
                ]
        repayment_schedule = self.repayment_schedule
        df_financing_sector_shares = pd.DataFrame(index=rows)
        # #print(self.historical.columns)
        for row in rows: 
            
            df_financing_sector_shares.loc[row,'Share'] = repayment_schedule[(self.historical['Financing Sector'] == row) | (self.historical['Financing Source'] == row)
            ][ "Volume in USD"].sum()/ repayment_schedule.loc[ :,"Volume in USD"].sum() 
        
        df_financing_sector_shares.loc["Domestic","Share"] = df_financing_sector_shares.loc["Comm_Dom", "Share"] + df_financing_sector_shares.loc["Conc_DPS", "Share"]
        df_financing_sector_shares.loc["International","Share"] = df_financing_sector_shares.loc["Comm_Intl", "Share"] + df_financing_sector_shares.loc["Conc_IFI", "Share"]
        df_financing_sector_shares.drop(["Comm_Dom", "Comm_Intl", "Conc_DPS", "Conc_IFI"], inplace=True)
        return df_financing_sector_shares   
    
    def get_technology_stats(self):
        rows = self.historical['Technology'].unique()
        repayment_schedule = self.repayment_schedule
        df_technology_stats = pd.DataFrame(index=rows)
        
        for row in rows:
            df_technology_stats.loc[row, 'IRR'] = self.historical[(self.historical['Technology'] == row)& (self.historical['Schedule'] == 'Equity')
                ][ "Rate"].mean()
            df_technology_stats.loc[row, 'Volume of Finance'] = self.historical[(self.historical['Technology'] == row)
                ][ "Volume in USD"].sum()
            df_technology_stats.loc[row, 'Interest Rate'] = self.historical[(self.historical['Technology'] == row)& (self.historical['Schedule'] != 'Equity')
                ][ "Rate"].mean()
            df_technology_stats.loc[row, 'Debt Share'] = self.historical[(self.historical['Technology'] == row)&(self.historical['Schedule'] != 'Equity')
                ][ "Volume in USD"].sum()/df_technology_stats.loc[row, 'Volume of Finance']
            df_technology_stats.loc[row, 'Equity Share'] = self.historical[(self.historical['Technology'] == row)&(self.historical['Schedule'] == 'Equity')
                ][ "Volume in USD"].sum()/df_technology_stats.loc[row, 'Volume of Finance']
            
        df_technology_stats.fillna(0, inplace=True)
        df_technology_stats.loc[:, 'WACC'] = df_technology_stats.loc[:, 'IRR'] * df_technology_stats.loc[:, 'Equity Share'] + df_technology_stats.loc[:, 'Interest Rate'] * df_technology_stats.loc[:, 'Debt Share']
        df_technology_stats.index.name = "Technology"
        return df_technology_stats
    
    def get_technology_financing_requirement(self):
        """
        Calculate financing requirement metrics for each technology broken down by source.
        
        Returns:
        -------
        DataFrame
            Multi-level indexed DataFrame with financing requirements by technology and source
            First level: Source (Conc_IFI, Conc_DPS, etc.)
            Second level: Metric (Debt Equity Share, Average interest rate, etc.)
        """
        # Get unique technologies and sources
        technologies = self.historical['Technology'].unique()
        sources = ["Conc_IFI", "Conc_DPS", "Comm_Intl", "Comm_Dom", "Average"]
        
        # Metrics to calculate
        metrics = [
            'Debt Equity Share',
            'Average interest rate', 
            'Average grace period (years)', 
            'Average term of loan (years)',
            'Average grant element'
        ]
        
        # Create a dictionary to store DataFrames for each source
        result_dict = {}
        
        # First process each regular source (excluding "Average")
        for source in sources[:-1]:  # Skip "Average" for now
            # Create a nested dictionary for metrics under this source
            source_metrics = {}
            
            # Process each metric for this source
            for metric in metrics:
                # Create DataFrame for this metric and source
                metric_df = pd.DataFrame(index=technologies, 
                                        columns=['Debt', 'Equity', 'Total'])
                
                # Process each technology for this source and metric
                for tech in technologies:
                    tech_data = self.historical[self.historical['Technology'] == tech]
                    
                    if tech_data.empty:
                        continue
                        
                    # Filter for this source
                    source_data = tech_data[tech_data['Financing Source'] == source]
                    
                    if source_data.empty:
                        continue
                    
                    # Total volume for this technology and source
                    total_volume = source_data['Volume in USD'].sum()
                    
                    # Calculate debt and equity volumes
                    debt_volume = source_data[source_data['Type of Finance'] == 'Loan']['Volume in USD'].sum()
                    equity_volume = source_data[source_data['Type of Finance'] == 'Equity']['Volume in USD'].sum()
                    
                    # Skip if no volume data
                    if total_volume == 0:
                        continue
                    
                    # Calculate shares
                    debt_share = debt_volume / total_volume if total_volume > 0 else 0
                    equity_share = equity_volume / total_volume if total_volume > 0 else 0
                    
                    # Process based on metric type
                    if metric == 'Debt Equity Share':
                        metric_df.loc[tech, 'Debt'] = debt_share * 100
                        metric_df.loc[tech, 'Equity'] = equity_share * 100
                        metric_df.loc[tech, 'Total'] = 100.0
                    
                    elif metric == 'Average interest rate':
                        # Debt interest rate (weighted by volume)
                        if debt_volume > 0:
                            debt_interest = (source_data[source_data['Type of Finance'] == 'Loan']['Rate'] * 
                                           source_data[source_data['Type of Finance'] == 'Loan']['Volume in USD']).sum() / debt_volume
                            metric_df.loc[tech, 'Debt'] = debt_interest * 100
                        
                        # Equity interest rate (weighted by volume)
                        if equity_volume > 0:
                            equity_interest = (source_data[source_data['Type of Finance'] == 'Equity']['Rate'] * 
                                             source_data[source_data['Type of Finance'] == 'Equity']['Volume in USD']).sum() / equity_volume
                            metric_df.loc[tech, 'Equity'] = equity_interest * 100
                        
                        # Total weighted average
                        metric_df.loc[tech, 'Total'] = (
                            (debt_interest * debt_volume if debt_volume > 0 else 0) + 
                            (equity_interest * equity_volume if equity_volume > 0 else 0)
                        ) / total_volume * 100
                    
                    elif metric == 'Average grace period (years)':
                        # Grace period is only for debt
                        if debt_volume > 0:
                            grace_period = (source_data[source_data['Type of Finance'] == 'Loan']['Grace period'] * 
                                          source_data[source_data['Type of Finance'] == 'Loan']['Volume in USD']).sum() / debt_volume
                            metric_df.loc[tech, 'Debt'] = grace_period
                            metric_df.loc[tech, 'Total'] = grace_period * debt_share
                        
                        metric_df.loc[tech, 'Equity'] = 0.0  # No grace period for equity
                    
                    elif metric == 'Average term of loan (years)':
                        debt_term = 0
                        equity_term = 0
                        
                        # Term for debt
                        if debt_volume > 0:
                            debt_term = (source_data[source_data['Type of Finance'] == 'Loan']['Term'] * 
                                       source_data[source_data['Type of Finance'] == 'Loan']['Volume in USD']).sum() / debt_volume
                            metric_df.loc[tech, 'Debt'] = debt_term
                        
                        # Term for equity
                        if equity_volume > 0:
                            equity_term = (source_data[source_data['Type of Finance'] == 'Equity']['Term'] * 
                                         source_data[source_data['Type of Finance'] == 'Equity']['Volume in USD']).sum() / equity_volume
                            metric_df.loc[tech, 'Equity'] = equity_term
                        
                        # Total weighted average
                        metric_df.loc[tech, 'Total'] = (
                            (debt_term * debt_volume if debt_volume > 0 else 0) + 
                            (equity_term * equity_volume if equity_volume > 0 else 0)
                        ) / total_volume
                    
                    elif metric == 'Average grant element':
                        # Grant element is only for debt
                        if debt_volume > 0:
                            # Match historical data with repayment schedule
                            debt_data_ids = source_data[source_data['Type of Finance'] == 'Loan'].index
                            
                            # Get grant elements from repayment schedule for these IDs
                            grant_elements = []
                            for idx in debt_data_ids:
                                if idx < len(self.repayment_schedule):
                                    grant_element = self.repayment_schedule.loc[idx, 'Grant Element']
                                    volume = source_data.loc[idx, 'Volume in USD']
                                    if isinstance(grant_element, (int, float)) and not pd.isna(grant_element):
                                        grant_elements.append((grant_element, volume))
                            
                            # Calculate weighted average
                            if grant_elements:
                                total_grant_element = sum(ge * vol for ge, vol in grant_elements)
                                total_volume_with_ge = sum(vol for _, vol in grant_elements)
                                weighted_grant_element = total_grant_element / total_volume_with_ge if total_volume_with_ge > 0 else 0
                                
                                metric_df.loc[tech, 'Debt'] = weighted_grant_element * 100
                                metric_df.loc[tech, 'Total'] = weighted_grant_element * debt_share * 100
                            
                        metric_df.loc[tech, 'Equity'] = float('nan')  # No grant element for equity
                
                # Store this metric's DataFrame in the source_metrics dictionary
                source_metrics[metric] = metric_df
            
            # Combine all metrics for this source into a DataFrame and add it to result_dict
            source_df = pd.concat(source_metrics, names=['Metric'])
            result_dict[source] = source_df
        
        # Now handle the "Average" source - calculating overall averages
        source_metrics = {}
        
        for metric in metrics:
            avg_metric_df = pd.DataFrame(index=technologies, columns=['Debt', 'Equity', 'Total'])
            
            for tech in technologies:
                # Get all data for this technology across all sources
                tech_data = self.historical[self.historical['Technology'] == tech]
                
                if tech_data.empty:
                    continue
                
                total_volume = tech_data['Volume in USD'].sum()
                if total_volume == 0:
                    continue
                
                # Calculate weighted averages across all sources
                # This varies by metric
                if metric == 'Debt Equity Share':
                    debt_volume = tech_data[tech_data['Type of Finance'] == 'Loan']['Volume in USD'].sum()
                    equity_volume = tech_data[tech_data['Type of Finance'] == 'Equity']['Volume in USD'].sum()
                    
                    debt_share = debt_volume / total_volume
                    equity_share = equity_volume / total_volume
                    
                    avg_metric_df.loc[tech, 'Debt'] = debt_share * 100
                    avg_metric_df.loc[tech, 'Equity'] = equity_share * 100
                    avg_metric_df.loc[tech, 'Total'] = 100.0
                
                elif metric == 'Average interest rate':
                    debt_volume = tech_data[tech_data['Type of Finance'] == 'Loan']['Volume in USD'].sum()
                    equity_volume = tech_data[tech_data['Type of Finance'] == 'Equity']['Volume in USD'].sum()
                    
                    debt_interest = 0
                    equity_interest = 0
                    
                    if debt_volume > 0:
                        debt_interest = (tech_data[tech_data['Type of Finance'] == 'Loan']['Rate'] * 
                                       tech_data[tech_data['Type of Finance'] == 'Loan']['Volume in USD']).sum() / debt_volume
                        avg_metric_df.loc[tech, 'Debt'] = debt_interest 
                    
                    if equity_volume > 0:
                        equity_interest = (tech_data[tech_data['Type of Finance'] == 'Equity']['Rate'] * 
                                         tech_data[tech_data['Type of Finance'] == 'Equity']['Volume in USD']).sum() / equity_volume
                        avg_metric_df.loc[tech, 'Equity'] = equity_interest 
                    
                    avg_metric_df.loc[tech, 'Total'] = (
                        (debt_interest * debt_volume if debt_volume > 0 else 0) + 
                        (equity_interest * equity_volume if equity_volume > 0 else 0)
                    ) / total_volume * 100 if total_volume > 0 else 0
                
                elif metric == 'Average grace period (years)':
                    debt_volume = tech_data[tech_data['Type of Finance'] == 'Loan']['Volume in USD'].sum()
                    if debt_volume > 0:
                        grace_period = (tech_data[tech_data['Type of Finance'] == 'Loan']['Grace period'] * 
                                      tech_data[tech_data['Type of Finance'] == 'Loan']['Volume in USD']).sum() / debt_volume
                        avg_metric_df.loc[tech, 'Debt'] = grace_period
                        avg_metric_df.loc[tech, 'Total'] = grace_period * debt_volume / total_volume
                    
                    avg_metric_df.loc[tech, 'Equity'] = 0.0
                
                elif metric == 'Average term of loan (years)':
                    debt_volume = tech_data[tech_data['Type of Finance'] == 'Loan']['Volume in USD'].sum()
                    equity_volume = tech_data[tech_data['Type of Finance'] == 'Equity']['Volume in USD'].sum()
                    
                    debt_term = 0
                    equity_term = 0
                    
                    if debt_volume > 0:
                        debt_term = (tech_data[tech_data['Type of Finance'] == 'Loan']['Term'] * 
                                   tech_data[tech_data['Type of Finance'] == 'Loan']['Volume in USD']).sum() / debt_volume
                        avg_metric_df.loc[tech, 'Debt'] = debt_term
                    
                    if equity_volume > 0:
                        equity_term = (tech_data[tech_data['Type of Finance'] == 'Equity']['Term'] * 
                                     tech_data[tech_data['Type of Finance'] == 'Equity']['Volume in USD']).sum() / equity_volume
                        avg_metric_df.loc[tech, 'Equity'] = equity_term
                    
                    avg_metric_df.loc[tech, 'Total'] = (
                        (debt_term * debt_volume if debt_volume > 0 else 0) + 
                        (equity_term * equity_volume if equity_volume > 0 else 0)
                    ) / total_volume if total_volume > 0 else 0
                
                elif metric == 'Average grant element':
                    debt_volume = tech_data[tech_data['Type of Finance'] == 'Loan']['Volume in USD'].sum()
                    if debt_volume > 0:
                        # Match historical data with repayment schedule for all sources
                        debt_data_ids = tech_data[tech_data['Type of Finance'] == 'Loan'].index
                        
                        # Get grant elements
                        grant_elements = []
                        for idx in debt_data_ids:
                            if idx < len(self.repayment_schedule):
                                grant_element = self.repayment_schedule.loc[idx, 'Grant Element']
                                volume = tech_data.loc[idx, 'Volume in USD']
                                if isinstance(grant_element, (int, float)) and not pd.isna(grant_element):
                                    grant_elements.append((grant_element, volume))
                        
                        if grant_elements:
                            total_grant_element = sum(ge * vol for ge, vol in grant_elements)
                            total_volume_with_ge = sum(vol for _, vol in grant_elements)
                            weighted_grant_element = total_grant_element / total_volume_with_ge if total_volume_with_ge > 0 else 0
                            
                            avg_metric_df.loc[tech, 'Debt'] = weighted_grant_element * 100
                            debt_share = debt_volume / total_volume
                            avg_metric_df.loc[tech, 'Total'] = weighted_grant_element * debt_share * 100
                    
                    avg_metric_df.loc[tech, 'Equity'] = float('nan')
            
            # Store this metric's average DataFrame in the source_metrics dictionary
            source_metrics[metric] = avg_metric_df
        
        # Combine all metrics for the "Average" source and add to result_dict
        avg_source_df = pd.concat(source_metrics, names=['Metric'])
        result_dict["Average"] = avg_source_df
        
        # Combine all sources into a multi-level DataFrame
        final_result = pd.concat(result_dict, names=['Source'])
        
        # Sort the MultiIndex to fix the PerformanceWarning
        final_result = final_result.sort_index()
        
        return final_result
    
    def get_technology_summary_table(self):
        """
        Generate a summary table of financing metrics organized by technology.
        
        Returns:
        -------
        DataFrame
            A table with technologies as rows and financing metrics as columns.
            Includes debt/equity shares, interest rates, terms, and other key metrics.
        """
        # Get technology financing requirement data
        tech_financing = self.get_technology_financing_requirement()
        
        # Get the list of unique technologies
        technologies = self.historical['Technology'].unique()
        
        # Create a new DataFrame for the summary table
        summary = pd.DataFrame(index=technologies)
        
        # Extract data from the "Average" source (which has aggregated metrics)
        avg_data = tech_financing.xs('Average', level='Source')
        
        # Add debt/equity shares
        summary['Debt Share (%)'] = avg_data.xs('Debt Equity Share', level='Metric')['Debt']
        summary['Equity Share (%)'] = avg_data.xs('Debt Equity Share', level='Metric')['Equity']
        
        # Add interest rates
        summary['Debt Interest Rate (%)'] = avg_data.xs('Average interest rate', level='Metric')['Debt']
        summary['Equity Return Rate (%)'] = avg_data.xs('Average interest rate', level='Metric')['Equity']
        summary['Combined Interest Rate (%)'] = avg_data.xs('Average interest rate', level='Metric')['Total']
        
        # Add loan terms
        summary['Loan Term (years)'] = avg_data.xs('Average term of loan (years)', level='Metric')['Debt']
        summary['Grace Period (years)'] = avg_data.xs('Average grace period (years)', level='Metric')['Debt']
        
        # Add grant element
        summary['Grant Element (%)'] = avg_data.xs('Average grant element', level='Metric')['Debt']
        
        # Calculate Weighted Average Cost of Capital (WACC)
        summary['WACC (%)'] = (summary['Debt Interest Rate (%)'] * summary['Debt Share (%)'] / 100 + 
                             summary['Equity Return Rate (%)'] * summary['Equity Share (%)'] / 100)
        
        # Add volume data from technology stats
        tech_stats = self.get_technology_stats()
        summary['Volume of Finance (USD)'] = tech_stats['Volume of Finance']
        
        # Set technology as the index name
        summary.index.name = "Technology"
        
        return summary
    
    def get_technology_financing_by_source(self, technology=None, metric='all'):
        """
        Generate a table showing how a specific technology is financed across different sources,
        or how a specific metric varies across technologies and sources.
        
        Parameters:
        ----------
        technology : str, optional
            Filter for a specific technology. If None, includes all technologies.
        metric : str, optional
            Filter for a specific metric. Default is 'all' which includes all metrics.
            Options: 'all', 'Debt Equity Share', 'Average interest rate', 
                    'Average grace period (years)', 'Average term of loan (years)',
                    'Average grant element'
                    
        Returns:
        -------
        DataFrame
            A table showing financing data by source, filtered by technology and/or metric as specified.
        """
        # Define valid metrics
        valid_metrics = [
            'Debt Equity Share',
            'Average interest rate', 
            'Average grace period (years)', 
            'Average term of loan (years)',
            'Average grant element'
        ]
        
        # Get technology financing requirement data
        tech_financing = self.get_technology_financing_requirement()
        
        # Filter by technology if specified
        if technology is not None:
            if technology not in self.historical['Technology'].unique():
                raise ValueError(f"Technology '{technology}' not found in data")
            tech_financing = tech_financing.xs(technology, level=2, drop_level=False)
        
        # Filter by metric if specified
        if metric != 'all':
            if metric not in valid_metrics:
                raise ValueError(f"Metric '{metric}' not valid. Choose from: {valid_metrics} or 'all'")
            tech_financing = tech_financing.xs(metric, level='Metric')
        
        # Reorganize data for better presentation
        # If we have a specific technology and specific metric (not 'all'), we can reshape
        if technology is not None and metric != 'all':
            result = tech_financing.droplevel(2)  # Drop the technology level since it's redundant
            return result
        
        return tech_financing
    
    