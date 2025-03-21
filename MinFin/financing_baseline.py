import time
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
    根据年份和原货币，获取对应的汇率，并转换为目标货币。
    
    参数：
    year_series: 包含年份的 Pandas Series
    currency_series: 包含原货币的 Pandas Series
    target_currency: 目标货币（如 USD）
    
    返回：
    Pandas Series，包含对应的汇率
    """
    # print(year_series)
    year_series = year_series.astype(int)  # 确保年份是整数
    mask = year_series.isin(exchange_rates_by_year.keys()) & currency_series.isin(currency_list)
    # print(mask)
    rates = year_series[mask].map(lambda y: exchange_rates_by_year[y]).combine(currency_series[mask], lambda rates_dict, c: rates_dict.get(c, None))
    target_rates = year_series[mask].map(lambda y: exchange_rates_by_year[y].get(target_currency, 1))
    return  target_rates/rates

class financing_baseline_extractor:
    def __init__(self,df_financing_baseline_full,currency='KES',starting_year=2024,number_of_payments_per_annum=1) -> None:
        self.currency = currency
        self.starting_year = starting_year
        self.foreign_currency = 'USD'
        self.discount_rate = 5.33/100 #'High Level Dashboard'!E34
        self.number_of_payments_per_annum = number_of_payments_per_annum
        self.starting_rows = {'exchange_rate': 36,'historical baseline': 46}
        self.starting_cols = {'historical baseline':0}
        # {'least_cost': {'variable_cost': 4, 'fixed_cost': 6, 'annual_elec_production': 10,'co2_emission':18}}
        # self.starting_cols['net_zero']= { key:value-1 for key,value in self.starting_cols['least_cost'].items()}
        # self.starting_cols[scenario]['carbon_price'] = 16
        self.df_financing_baseline_full = df_financing_baseline_full
        self.historical = self.get_historical()
        
        
        
    def get_historical(self):
        df_financing_baseline_full=self.df_financing_baseline_full
        starting_row = self.starting_rows['historical baseline']
        starting_col = self.starting_cols['historical baseline']
        # 获取第一行作为列名
        new_columns = df_financing_baseline_full.iloc[starting_row, starting_col:starting_col+20].values
        
        # 提取数据（跳过列名行）
        df_historical = df_financing_baseline_full.iloc[starting_row+1:starting_row+400, starting_col:starting_col+20].copy()
        
        # 重新设置列名
        df_historical.columns = [x.strip() for x in new_columns]        
        df_historical = df_historical.drop(columns=["Volume in KES", "Volume in USD", "Exchange Rate","Maturity"], errors='ignore').dropna(how='all', axis=0)#.dropna(how='all', axis=1)
        df_historical = self.add_columns_for_other_currencies(df_historical, exchange_rates_by_year)
        return df_historical.dropna(how='all', axis=0).reset_index(drop=True)#.dropna(how='all', axis=1)
    
    def add_columns_for_other_currencies(self, df, exchange_rates_by_year):
        """
        计算财务数据，并添加：
        - volume of finance in currency
        - volume of finance in foreign currency
        - exchange rate to currency
        - exchange rate to foreign currency
        
        参数：
        df: 包含交易数据的 DataFrame
        exchange_rates: 货币汇率 DataFrame，包含 base_currency 到其他货币的汇率
        base_currency: 基准货币，默认 KES
        foreign_currency: 外币，通常是 USD
        """
        base_currency=self.currency
        foreign_currency=self.foreign_currency

        # 1. 获取当前货币的汇率（相对于 base_currency）
        # df[f"exchange rate to {base_currency}"] = df["Currency"].apply(lambda row: get_exchange_rate(row, "Currency", "Year"))

        # # 2. 获取当前货币的汇率（相对于 foreign_currency）
        # df[f"Exchange rate to {foreign_currency}"] = df[f"exchange rate to {base_currency}"].apply(lambda row: get_exchange_rate(row, foreign_currency, "Year"))

        # 3. 计算 volume of finance in currency
        df[f"Volume in {base_currency}"] = df["Volume of Finance"] *get_exchange_rates(base_currency,df["Currency"],df["Year"])

        # 4. 计算 volume of finance in foreign currency（通常 USD）
        df[f"Volume in {foreign_currency}"] = df["Volume of Finance"] *get_exchange_rates(foreign_currency,df["Currency"],df["Year"])
        df[f"Exchange Rate to {base_currency}"] = get_exchange_rates(base_currency,df["Currency"],df["Year"])
        df[f"Exchange Rate to {foreign_currency}"] = get_exchange_rates(foreign_currency,df["Currency"],df["Year"])
        df["Maturity"] = df["Term"]-self.starting_year+df["Year"]
        
        return df
    
    def cal_repayment_schedule(self,df):
        df=df.reset_index(drop=True)
        years =  list(range(2010, 2071))
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
            # print(df['Volume in KES'])
            for project_id in df.index:
                # print( 2020 in list(df_repayment.loc[df_repayment['Project ID'] == project_id,'repay_years'])[0])
                # print('==',list(df_repayment.loc[df_repayment['Project ID'] == project_id,'repay_years'])[0])
                repay_years = list(df_repayment.loc[df_repayment['Project ID'] == project_id,'repay_years'])[0]
                if year in repay_years:
                    if year == repay_years[-1]:
                        df_repayment.loc[df_repayment['Project ID'] == project_id,year] = self.cal_repayment_value(df.loc[project_id,"Rate"],df['Volume of Finance'],df.loc[project_id,"Schedule"],year,repay_years,term=df.loc[project_id,'Term'],grace_period=df.loc[project_id,'Grace period']) 
                    else:
                        df_repayment.loc[df_repayment['Project ID'] == project_id,year] = self.cal_repayment_value(df.loc[project_id,"Rate"],df['Volume of Finance'],df.loc[project_id,"Schedule"],year,repay_years,term=df.loc[project_id,'Term'],grace_period=df.loc[project_id,'Grace period']) 
                else:
                    df_repayment.loc[df_repayment['Project ID'] == project_id,year] = 0
            # df_repayment.loc[df_repayment[year] == year] = df['Volume in KES'] * (1 + df['Rate']) ** df['Maturity']
            
        df_repayment['Sum of Repayment'] = df_repayment[years].sum(axis=1).astype(float)
        # print("============================================")
        df_repayment['Market Element'] = self.cal_market_element()
        df_repayment['Grant Element'] = self.cal_grant_element()
        # print('term',df['Term'].astype(float),df['Term'].astype(float).replace(0,100000))
        df_repayment['Average Annual Payment']= df_repayment['Sum of Repayment'] /df['Term'].astype(float)#.replace(0,100000)
        df_repayment['Average Annual Payment'] = df_repayment['Average Annual Payment'].replace([np.inf, -np.inf], np.nan).fillna(0)
        return df_repayment.reset_index(drop=True)
    def cal_repayment_value(self,interest_rate,volume,scenario,year,repay_years,term=0,grace_period=0):
        # print(type(scenario),scenario)
        # print(type(interest_rate),interest_rate)
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
        
        elif scenario in ['Equal Principal Payments (EPP)']:    
                        
            return -self.calculate_annuity_payment(interest_rate, term-grace_period+1, volume, fv=0)
        elif scenario in ['EPP with Grace Years for Principal and on Interest']:
            if year <= repay_years[0]+grace_period:
                return volume * interest_rate
            else:
                return -self.calculate_annuity_payment(interest_rate, term-grace_period+1, volume, fv=0)
        else:
            return None
            
    def get_discount_rate_for_grant_ele(self):
        # discount_rate = historical['Rate'].max(historical.loc[:,'Type of Finance']=='Loan')
        # 先筛选出 'Type of Finance' 为 'Loan' 的行
        loan_data = self.historical[self.historical['Type of Finance'] == 'Loan']
        # 检查是否存在 'Loan' 类型的融资
        if not loan_data.empty:
            # 如果存在，计算 'Rate' 列的最大值
            discount_rate = loan_data['Rate'].max()
        else:
            # 如果不存在，使用默认值 10%
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
        # print(interest_rate,grace_period,loan_term)
        term2 = 1 - ((factor1 - factor2) / denominator)

        epp_grant_element = pd.DataFrame(term1 * term2)
        lump_grant_element = pd.DataFrame(1-(1+interest_rate*(loan_term + grace_period))/(1+self.get_discount_rate_for_grant_ele())**(loan_term + grace_period))
        equity = 'equity'
        grant_element = pd.DataFrame(columns=['Grant Element'])
        
        factor = pd.DataFrame([1 if "EPP" in t else 0 for t in financing_schedule_type])
        # print(factor)
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
            # print('Equity')
            return "Equity"        
        
    # def cal_general_repayment_statistics(self):
    #     self.weighte_averages = self.cal_weighted_average()
    #     return self.weighte_averages
    

class financing_baseline_stats:
    def __init__(self, financing_baseline_extractor, repayment_schedule):
        self.repayment_schedule = repayment_schedule.copy()
        self.historical = financing_baseline_extractor.get_historical()        
        # 一次性填充多个列
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
                
                df.loc[row, col] = weighted_data.sum() / repayment_schedule[
                (repayment_schedule['Financing Source'] == row) & (repayment_schedule['Type of Finance'] == type_of_finance)
                ][ "Volume in USD"].sum() 
                
                 
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
            # print(index,col)
            df.iloc[0, index+1] = (df[col][1:]*df['Volume (USD)'][1:]).sum()/df['Volume (USD)'][1:].sum()
            #  print(df.iloc[1, index+1])
        return df
    def get_repayment_statistics(self):
        # print(self.cal_summary_stats().columns)
        df_summary = self.add_weighted_average(self.cal_summary_stats())
        df_equity = self.add_weighted_average(self.cal_equity_debt_stats())
        df_debt = self.add_weighted_average(self.cal_equity_debt_stats(type_of_finance='Loan'))
        df_final = pd.concat(
        [df_summary, df_equity, df_debt], 
        axis=0, 
        keys=['Summary', 'Equity', 'Debt']  # 添加的层级索引
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
        # print(self.historical.columns)
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