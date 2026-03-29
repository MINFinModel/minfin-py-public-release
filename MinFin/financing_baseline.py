import time
import math
import random
import numpy as np
import pandas as pd

currency_list = ["KES", "USD", "EUR", "GBP", "JPY"]
base_rates = {
    "KES": 2,#0.009,
    "USD": 3.0,
    "EUR": 1.08,
    "GBP": 1.36,
    "JPY": 0.007
}
exchange_rates_by_year = pd.DataFrame(columns=currency_list)
for year in range(2010, 2080):
    exchange_rates_by_year[year] = {
        currency: round(base_rates[currency] * round(1 + random.uniform(-0.05, 0.05)), 5) for currency in currency_list
    }
    
def get_exchange_rates(target_currency, currency_series,year_series):
    """
    Get exchange rates based on year and original currency, and convert to target currency.
    
    Parameters:
    year_series: Pandas Series containing years
    currency_series: Pandas Series containing original currencies
    target_currency: Target currency (e.g., USD)
    
    Returns:
    Pandas Series containing corresponding exchange rates
    """
    # #print(year_series)
    year_series = year_series.astype(int)  # Ensure years are integers
    mask = year_series.isin(exchange_rates_by_year.keys()) & currency_series.isin(currency_list)
    # #print(mask)
    rates = year_series[mask].map(lambda y: exchange_rates_by_year[y]).combine(currency_series[mask], lambda rates_dict, c: rates_dict.get(c, None))
    target_rates = year_series[mask].map(lambda y: exchange_rates_by_year[y].get(target_currency, 1))
    return  target_rates/rates

class financing_baseline_extractor:
    def __init__(self,df_financing_baseline_full,currency='KES',starting_year=2024,number_of_payments_per_annum=1) -> None:
        self.currency = currency
        self.years = list(range(2010, 2071))
        self.starting_year = starting_year
        self.foreign_currency = 'USD'
        self.discount_rate = 5.33/100 #'High Level Dashboard'!E34
        self.number_of_payments_per_annum = number_of_payments_per_annum
        self.starting_rows = {'exchange_rate': 35,'historical baseline': 49}
        self.starting_cols = {'historical baseline':0,'exchange_rate':2}
        # {'least_cost': {'variable_cost': 4, 'fixed_cost': 6, 'annual_elec_production': 10,'co2_emission':18}}
        # self.starting_cols['net_zero']= { key:value-1 for key,value in self.starting_cols['least_cost'].items()}
        # self.starting_cols[scenario]['carbon_price'] = 16
        self.df_financing_baseline_full = df_financing_baseline_full
        self.historical = self.get_historical()
        
        
    def get_exchange_rates_by_year(self):
        df_financing_baseline_full=self.df_financing_baseline_full
        starting_row = self.starting_rows['exchange_rate']
        starting_col = self.starting_cols['exchange_rate'] 
        new_columns = self.years
        
        # Extract data (skip the column names row)
        df_exchange_rates = df_financing_baseline_full.iloc[starting_row:starting_row+10, starting_col:starting_col+len(new_columns)].copy()
        df_exchange_rates.columns = df_exchange_rates.iloc[0]
        df_exchange_rates = df_exchange_rates.iloc[1:]
        df_exchange_rates.set_index('Currency', inplace=True)
        df_exchange_rates.index.name = "Year"
        df_exchange_rates.columns.name = None  # drop column index name

        
        # df_exchange_rates.columns = new_columns      
        df_result = df_exchange_rates.T.iloc[:].dropna(how='all', axis=0)
        df_result.index = df_result.index.astype(int)
        return df_result
    def get_historical(self):
        df_financing_baseline_full=self.df_financing_baseline_full
        starting_row = self.starting_rows['historical baseline']
        starting_col = self.starting_cols['historical baseline']
        # Get the first row as column names
        new_columns = df_financing_baseline_full.iloc[starting_row, starting_col:starting_col+21].values
        
        # Extract data (skip the column names row)
        df_historical = df_financing_baseline_full.iloc[starting_row+1:starting_row+400, starting_col:starting_col+21].copy()
        
        # Reset column names
        df_historical.columns = [x.strip() for x in new_columns]        
        df_historical = df_historical.drop(columns=["Volume in KES", "Volume in USD", "Exchange Rate","Maturity"], errors='ignore').dropna(how='all', axis=0)#.dropna(how='all', axis=1)
        df_historical = self.add_columns_for_other_currencies(df_historical, exchange_rates_by_year)
        return df_historical.dropna(how='all', axis=0).reset_index(drop=True)#.dropna(how='all', axis=1)
    
    def add_columns_for_other_currencies(self, df, exchange_rates_by_year):
        """
        Calculate financial data and add:
        - volume of finance in currency
        - volume of finance in foreign currency
        - exchange rate to currency
        - exchange rate to foreign currency
        
        Parameters:
        df: DataFrame containing transaction data
        exchange_rates: Currency exchange rate DataFrame, including rates from base_currency to other currencies
        base_currency: Base currency, default KES
        foreign_currency: Foreign currency, usually USD
        """
        base_currency=self.currency
        foreign_currency=self.foreign_currency

        df[f"Volume in {base_currency}"] = df["Volume of Finance"] *get_exchange_rates(base_currency,df["Currency"],df["Year"])

        df[f"Volume in {foreign_currency}"] = df["Volume of Finance"] *get_exchange_rates(foreign_currency,df["Currency"],df["Year"])
        df[f"Exchange Rate to {base_currency}"] = get_exchange_rates(base_currency,df["Currency"],df["Year"])
        df[f"Exchange Rate to {foreign_currency}"] = get_exchange_rates(foreign_currency,df["Currency"],df["Year"])
        df["Maturity"] = df["Term"]-self.starting_year+df["Year"]
        
        return df
    
    def cal_repayment_schedule(self,df):
        df=df.reset_index(drop=True)
        years =  self.years
        df_repayment = pd.DataFrame(columns=years)
        df_repayment['Repayment'] = 0
        df_repayment['Name of Project'] = df['Name of Project']
        
        repay_years_list = []
        # Iterate over each row in the DataFrame
        for index, row in df.fillna(0).iterrows():
            # Calculate the repayment years for each project
            repay_years = list(range(row['Year'], row['Year'] + int(row['Term']+1)))
            repay_years_list.append(repay_years)
        
        # Assign the list of repayment years to the DataFrame
        df_repayment['repay_years'] = repay_years_list
        df_repayment['Project ID'] = df.index
        for year in range(2010, 2071):
            # #print(df['Volume in KES'])
            for project_id in df.index:
                # #print( 2020 in list(df_repayment.loc[df_repayment['Project ID'] == project_id,'repay_years'])[0])
                # #print('==',list(df_repayment.loc[df_repayment['Project ID'] == project_id,'repay_years'])[0])
                repay_years = list(df_repayment.loc[df_repayment['Project ID'] == project_id,'repay_years'])[0]
                if year in repay_years:
                    if year == repay_years[-1]:
                        df_repayment.loc[df_repayment['Project ID'] == project_id,year] = self.cal_repayment_value(df.loc[project_id,"Rate"],df.loc[project_id,'Volume of Finance'],df.loc[project_id,"Schedule"],year,repay_years,term=df.loc[project_id,'Term'],grace_period=df.loc[project_id,'Grace period']) 
                    else:
                        df_repayment.loc[df_repayment['Project ID'] == project_id,year] = self.cal_repayment_value(df.loc[project_id,"Rate"],df.loc[project_id,'Volume of Finance'],df.loc[project_id,"Schedule"],year,repay_years,term=df.loc[project_id,'Term'],grace_period=df.loc[project_id,'Grace period']) 
                else:
                    df_repayment.loc[df_repayment['Project ID'] == project_id,year] = 0
            # df_repayment.loc[df_repayment[year] == year] = df['Volume in KES'] * (1 + df['Rate']) ** df['Maturity']
        
        df_repayment['Sum of Repayment'] = df_repayment[years].sum(axis=1).astype(float)
        # #print("============================================")
        df_repayment['Market Element'] = self.cal_market_element()
        df_repayment['Grant Element'] = self.cal_grant_element()
        # #print('term',df['Term'].astype(float),df['Term'].astype(float).replace(0,100000))
        df_repayment['Average Annual Payment']= df_repayment['Sum of Repayment'] /df['Term'].astype(float)#.replace(0,100000)
        df_repayment['Average Annual Payment'] = df_repayment['Average Annual Payment'].replace([np.inf, -np.inf], np.nan).fillna(0)
        return df_repayment.reset_index(drop=True)
    def cal_repayment_value(self,interest_rate,volume,scenario,year,repay_years,term=0,grace_period=0):
        # #print(type(scenario),scenario)
        # #print(type(interest_rate),interest_rate)
        if scenario in ['Equity']:

             return volume * interest_rate 
        elif scenario in ['Lump Sum Principal']:
            if year == repay_years[-1]:
                return volume * (1+interest_rate) 
            else:
                return volume * interest_rate 
        
        elif scenario in ['Lump Sum Principal and Interest']:
            if year == repay_years[-1]:
                return volume * (1+interest_rate)**term
            else:
                return 0
                    
        elif scenario in ['EPP with Grace Years for Principal']:
            if year < repay_years[0]+grace_period:
                return volume * interest_rate
            else:
                return -self.calculate_annuity_payment(interest_rate, term-grace_period+1, volume, fv=0)
        
        elif scenario in ['Equal Principal Payments (EPP)','Equal Principal Payments (EPP)']:    
                        
            return -self.calculate_annuity_payment(interest_rate, term-grace_period+1, volume, fv=0)
        elif scenario in ['EPP with Grace on Principal & Interest','EPP with Grace on Principal and Interest']:
            payment = self.epp_with_grace_p_and_i_payment(
                interest_rate=interest_rate,
                volume=volume,
                start_year=repay_years[0],
                term=term,
                grace_period=grace_period,
                year=year,
            )
            return payment
        else:
            return None
            
    def get_discount_rate_for_grant_ele(self):
        # discount_rate = historical['Rate'].max(historical.loc[:,'Type of Finance']=='Loan')
        # First filter rows where 'Type of Finance' is 'Loan'
        loan_data = self.historical[self.historical['Type of Finance'] == 'Loan']
        # Check if there are any 'Loan' type finances
        if not loan_data.empty:
            # If exists, calculate the maximum value of the 'Rate' column
            discount_rate = loan_data['Rate'].max()
        else:
            # If not, use default value 10%
            discount_rate = 0.10
        
        return discount_rate
    
    def get_d(self,number_of_payments=None):
        if number_of_payments is None:
            # number_of_payments = self.arguments.get('number_of_payments_per_annum', 1)
            number_of_payments = self.number_of_payments_per_annum
        return (1+self.get_discount_rate_for_grant_ele())**(1/number_of_payments)-1
    
    def cal_grant_element(self,number_of_payments=None):
        if number_of_payments is None:
            # number_of_payments = self.arguments.get('number_of_payments_per_annum', 1)
            number_of_payments = self.number_of_payments_per_annum
        d = self.get_d(number_of_payments)
        
        interest_rate = self.historical['Rate'].dropna().reset_index(drop=True)
        grace_period = self.historical['Grace period'].dropna().reset_index(drop=True) 
        loan_term = self.historical['Term'].dropna().reset_index(drop=True)
        financing_schedule_type = self.historical['Schedule'].dropna()
        
        
        term1 = 1 - interest_rate / (number_of_payments*d)
        
        factor1 = 1 / ((1 + d) ** (number_of_payments * grace_period))
        factor2 = 1 / ((1 + d) ** (number_of_payments * (loan_term + grace_period)))
        denominator = d * number_of_payments * loan_term #+ grace_period) - number_of_payments * grace_period)
        denominator = denominator.where(denominator != 0, 1)
        # #print(interest_rate,grace_period,loan_term)
        term2 = 1 - ((factor1 - factor2) / denominator)

        epp_grant_element = pd.DataFrame(term1 * term2)
        lump_grant_element = pd.DataFrame(1-(1+interest_rate*(loan_term + grace_period))/(1+self.get_discount_rate_for_grant_ele())**(loan_term + grace_period))
        equity = 'equity'
        grant_element = pd.DataFrame(columns=['Grant Element'])
        
        factor = pd.DataFrame([1 if "EPP" in t else 0 for t in financing_schedule_type])
        # #print(factor)
        grant_element['Grant Element'] = epp_grant_element*factor + lump_grant_element*(1-factor)

        grant_element['Grant Element'] = np.where(financing_schedule_type.str.contains("Equity"), "Equity", grant_element['Grant Element'])
        return  grant_element
    def cal_market_element(self,number_of_payments=None):
        return pd.DataFrame([1 - item if isinstance(item, (int, float)) else item for item in self.cal_grant_element(number_of_payments)['Grant Element']])
    
    def cal_discounted_schedule(self,df_repayment,discount_rate,current_year=2024):
        df = self.historical.reset_index(drop=True)
        # years = [package for package in df_repayment.columns if package.isdigit()]
        df_discounted = df_repayment.copy()
        df_discounted.drop(columns=['Repayment','Name of Project','repay_years','Project ID','Sum of Repayment','Average Annual Payment'],inplace=True)
        df_discounted = df_discounted / (1 + discount_rate) ** ((df_discounted.columns - current_year+1) * (df_discounted.columns-current_year>=0))
        df_discounted['Sum of Repayment'] = df_discounted.sum(axis=1).astype(float)
        df_discounted['Average Annual Payment']= df_discounted['Sum of Repayment'] /df['Term'].astype(float)
        return df_discounted
    
    @staticmethod
    def calculate_annuity_payment(rate, nper, pv, fv=0):
        """
        Annuity Payment
        rate: interest rate for each period
        nper: total number of payment periods
        pv: present value (default 0)
        fv: future value (default 0)
        """
        if rate == 0:
            return -(pv + fv) / nper
        else:
            return -(rate * (pv * (1 + rate) ** nper + fv)) / ((1 + rate) ** nper - 1)
    @staticmethod
    def select_grant_element(index,schedule_type,epp_grant_element,lump_grant_element):
        
        if "Equity" in schedule_type:
            # #print('Equity')
            return "Equity"        
        
    # def cal_general_repayment_statistics(self):
    #     self.weighte_averages = self.cal_weighted_average()
    #     return self.weighte_averages
    @staticmethod
    def epp_with_grace_p_and_i_payment(interest_rate, volume, start_year, term, grace_period, year):
        """
        This function calculates the payment for the EPP with Grace on Principal and Interest scenario.
        """
        #print("interest_rate",interest_rate)
        #print("volume",volume)
        #print("start_year",start_year)
        #print("term",term)
        #print("grace_period",grace_period)
        #print("year",year)
        # If not in repayment period: 0
        if year < start_year or year > start_year + math.ceil(term) - 1:
            return 0.0

        # Effective principal after grace period
        effective_volume = volume * (1.0 + interest_rate) ** math.floor(grace_period)

        # 1) First year of repayment: year = ROUNDDOWN(start_year + grace_period, 0)
        if year == math.floor(start_year + grace_period):
            return (
                (effective_volume / (term - grace_period)) * (math.ceil(grace_period) - grace_period)
                + effective_volume * interest_rate
            )

        # 2) Middle years: start_year + grace_period <= year < start_year + term - 1
        if (year >= start_year + grace_period) and (year < start_year + term - 1.0):
            principal_annual = effective_volume / (term - grace_period)
            years_since_start = max(0.0, year - (start_year + grace_period))
            remaining_principal = effective_volume - principal_annual * years_since_start
            return principal_annual + remaining_principal * interest_rate

        # 3) Last year: year = start_year + ROUNDUP(term, 0) - 1
        if year == start_year + math.ceil(term) - 1.0:
            principal_annual = effective_volume / (term - grace_period)
            if term - math.floor(term) == 0.0:
                frac = 1.0
            else:
                frac = term - math.floor(term)
            return principal_annual * frac * (1.0 + interest_rate)

        # Other: 0
        return 0.0
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
    
    