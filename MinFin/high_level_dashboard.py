from dataclasses import dataclass

from .data_processor import get_funding_envelope, process_funding_baseline
from .excel_io import year_columns_from_index
from .utils import cal_equity_needs, cal_loan_needs
from typing import Union


class InProgressError(Exception):
    """Raised when functionality is still under development."""
    pass

@dataclass
class CapitalInjection:
    money_from: str = "domestic public"
    start_year: int = 2024
    volume: float = 100.0
    duration: int = 3
    type: str = "grant"

@dataclass
class EconomicParameters:
    income_elasticity_of_energy_demand: float = 0.5
    cagr_of_real_energy_price: float = 0.02
    gdp_growth_rate: float = 0.03

    @classmethod
    def from_dict(cls, kwargs):
        return cls(**kwargs)
@dataclass
class Scenarios:
    financial_instrument_type: str = "Grant"
    scenario: str = "NetZero"
    capital_injection: Union[bool, CapitalInjection] = False  # False means no capital injection; if needed, pass a CapitalInjection instance
    
    @classmethod
    def from_dict(cls, kwargs):
        return cls(**kwargs)
    
    def __post_init__(self):

        if self.capital_injection is True:
            raise ValueError(
                "When capital_injection is True, please pass in a CapitalInjection instance."
            )

class high_level_dashboard:
    def __init__(
        self,
        repayment_statistics,
        economic_params: EconomicParameters,
        scenario: Scenarios,
        start_year=2025,
        df_funding_baseline_full=None,
        least_cost_summary=None,
        net_zero_summary=None,
        financing_summary=None,
    ):
        self.rows = {
            'Debt Equity Share':0,
            'Average interest rate':'Interest rate',
            'Average grace period':"Grace period",
            'Average term of loan':"Term", 
            'Average grant element':"Grant Element"
        }
        self.years = list(range(start_year, 2071))
        self.cols = ['Debt','Equity','Summary']
        self.repayment_statistics = repayment_statistics
        self.sectors = ['Conc_IFI', 'Conc_DPS', 'Comm_Intl', 'Comm_Dom']
        self.economic_params = economic_params  
        self.financial_instrument_type = scenario.financial_instrument_type
        self.scenario = scenario
        self.funding_baseline_full = df_funding_baseline_full
        self.least_cost_summary = least_cost_summary
        self.net_zero_summary = net_zero_summary
        self.financing_summary = financing_summary
    def get_financing_requirements(self,sector):
        repayment_statistics = self.repayment_statistics
        df_financing_requirements = pd.DataFrame(index=self.rows, columns=self.cols)
        rows = self.rows
        cols = self.cols
        for col in cols:
            for row in rows.keys():
                if not row == "Debt Equity Share":
                    df_financing_requirements.loc[row,col] = repayment_statistics.loc[(col,sector),rows[row]]
                # df_financing_requirements['Equity'] = repayment_statistics.loc[('Equity',sector),'Term']
                # df_financing_requirements['Total'] = repayment_statistics.loc[('Summary',sector),'Grace period']

        summary_row = list(rows.keys())[0]
        for col in cols:
            if not col in ['Summary']:
                df_financing_requirements.loc[summary_row,col] = repayment_statistics.loc[(cols[-1],sector),col+' Share']
            else:
                df_financing_requirements.loc[summary_row,col] = df_financing_requirements.loc[summary_row,:].sum()
        
        df_financing_requirements_projected = df_financing_requirements.copy()
        return pd.concat([df_financing_requirements,df_financing_requirements_projected],axis=1,keys=["Historical","Projected"])
    
    def get_full_financing_requirement(self):
        sectors = self.sectors
        
        df_list = [self.get_financing_requirements(sector) for sector in sectors]

        df_financing_requirements = pd.concat(df_list, keys=sectors)

        return df_financing_requirements
    def get_funding_availability_lever(self,df_funding_envelope=None):
        if df_funding_envelope is None:
            df_funding_baseline_full = self.funding_baseline_full
            df_funding_baseline = process_funding_baseline(df_funding_baseline_full)
            df_funding_envelope = get_funding_envelope(df_funding_baseline)
        df_funding_availability = pd.DataFrame(columns=["Historical","Projected"])    
        rows = [
            "CAGR of government spending",
            "CAGR of international grants",
            "CAGR of SOE internal cash generation",
            "Income elasticity of energy demand",
            "CAGR of real energy price"
        ]

        df_funding_availability.loc[rows[0],"Historical"] = df_funding_envelope.loc["Annual CAGR","Budget"]
        df_funding_availability.loc[rows[1],"Historical"] = df_funding_envelope.loc["Annual CAGR","Grant"]
        df_funding_availability.loc[rows[3],"Historical"] = self.economic_params.income_elasticity_of_energy_demand
        df_funding_availability.loc[rows[4],"Historical"] = self.economic_params.cagr_of_real_energy_price
        df_funding_availability.loc[rows[2],"Historical"] = self.cal_cagr_soe_international_cash_generation()
        
        df_funding_availability["Projected"] = df_funding_availability["Historical"].copy()
        
        
        return df_funding_availability

    def cal_cagr_soe_international_cash_generation(self):
        return (1 + self.economic_params.income_elasticity_of_energy_demand * self.economic_params.gdp_growth_rate) * (1 + self.economic_params.cagr_of_real_energy_price) - 1

    def get_financing_source_shares(self):
        repayment_statistics = self.repayment_statistics
        sectors = self.sectors
        df_financing_source_shares = pd.DataFrame(index=sectors, columns=["Historical","Projected"])
        total = repayment_statistics.loc[("Summary","Total financing volumes"),"Volume (USD)"]
        for sector in sectors:
            df_financing_source_shares.loc[sector,"Historical"] = repayment_statistics.loc[("Summary",sector),"Volume (USD)"]/total
        df_financing_source_shares["Projected"] = df_financing_source_shares["Historical"].copy()
        return df_financing_source_shares
    
    def get_projected_average(self):
        rows = {
            'Debt Equity Share':0,
            'Average interest rate':'Interest rate',
            'Average grace period':"Grace period",
            'Average term of loan':"Term", 
            'Average grant element':"Grant Element"
        }
        # df_financing_repayments.head()
        projected_financing = self.get_full_financing_requirement()["Projected"]
        projected_weights = self.get_financing_source_shares()["Projected"]

        projected_averages=pd.DataFrame()
        for metric in rows.keys():
            for type in ["Debt","Equity"]:
                if metric in ["Debt Equity Share"]:
                    mask = projected_financing.xs(metric, level=1)[type]*projected_weights
                else:
                    weights = projected_weights.copy()*projected_financing.xs("Debt Equity Share", level=1)[type]

                    mask = projected_financing.xs(metric, level=1)[type]*weights /weights.sum()
                
                projected_averages.loc[metric,type] = mask.sum()
                    
        return projected_averages

    def get_funding_availability_full(
        self,
        df_funding_envelope=None,
        financing_summary=None,
        fossil_fuel_savings=None,
        df_grants_with_ffs_carbon=None,
    ):
        """Primary funding availability table (Government Budget, Cashflows, Carbon rows, etc.)."""
        del fossil_fuel_savings, df_grants_with_ffs_carbon
        if df_funding_envelope is None:
            df_funding_baseline_full = self.funding_baseline_full
            df_funding_baseline = process_funding_baseline(df_funding_baseline_full)
            df_funding_envelope = get_funding_envelope(df_funding_baseline)
        if financing_summary is None:
            financing_summary = self.financing_summary
        df_funding_availability_lever = self.get_funding_availability_lever(df_funding_envelope)
        cols = self.years
        rows = [
            "Government Budget",
            "Liabilities Payments",
            "Cashflows",
            "Capital Injection",
            "Carbon Credits",
            "Carbon Credit Price",
            "Net CO2 Emissions Savings",
            "CO2 Emissions Base Scenario",
            "CO2 Emissions Net Zero Scenario",
        ]
        df_funding_availability_full = pd.DataFrame(index=rows, columns=cols)

        if self.scenario.capital_injection:
            capital_injection = self.scenario.capital_injection
            df_funding_availability_full.loc[rows[3], :] = [
                capital_injection.volume / capital_injection.duration
                if year in range(capital_injection.start_year, capital_injection.start_year + 3)
                else 0
                for year in cols
            ]
        else:
            df_funding_availability_full.loc[rows[3], :] = 0

        if self.scenario.capital_injection and self.scenario.capital_injection.type in [
            "Government Budget",
            "Government budget",
            "government budget",
        ]:
            rate = df_funding_availability_lever.loc["CAGR of government spending", "Projected"]
            df_funding_availability_full.loc[rows[0], :] = [
                df_funding_envelope.loc["Annual Average", "Budget"] * (1 + rate) ** i for i in range(len(cols))
            ]
            df_funding_availability_full.loc[rows[0], :] -= df_funding_availability_full.loc[rows[3], :]
        else:
            rate = df_funding_availability_lever.loc["CAGR of government spending", "Projected"]
            df_funding_availability_full.loc[rows[0], :] = [
                df_funding_envelope.loc["Annual Average", "Budget"] * (1 + rate) ** i for i in range(len(cols))
            ]

        df_funding_availability_full.loc[rows[2], :] = financing_summary.loc["Cashflows", :]
        df_carbon_saving = self.get_co2_savings(self.least_cost_summary, self.net_zero_summary)
        df_funding_availability_full.loc[rows[4], :] = df_carbon_saving.loc["Carbon credit", :]
        df_funding_availability_full.loc[rows[5], :] = df_carbon_saving.loc["Carbon credit price", :]
        df_funding_availability_full.loc[rows[6], :] = df_carbon_saving.loc["Net CO2 Saving", :]
        df_funding_availability_full.loc[rows[7], :] = df_carbon_saving.loc["Least cost", :]
        df_funding_availability_full.loc[rows[8], :] = df_carbon_saving.loc["Net zero", :]
        df_funding_availability_full.loc["Total", :] = df_funding_availability_full.loc[rows[0:5], :].sum(axis=0)
        return df_funding_availability_full

    def get_funding_availability_full_legacy(self,df_funding_envelope=None,fossil_fuel_savings=None,df_grants_with_ffs_carbon=None):
        if df_funding_envelope is None:
            df_funding_baseline_full = self.funding_baseline_full
            df_funding_baseline = process_funding_baseline(df_funding_baseline_full)
            df_funding_envelope = get_funding_envelope(df_funding_baseline)
        financial_instrument=self.financial_instrument_type
        df_funding_availability_lever = self.get_funding_availability_lever(df_funding_envelope)
        cols = self.years
        rows = [
            "Government spending",
            "Debt Write-off",
            "SOE internal cash generation",
            "Capital Injection",
            "Fossil Fuel Expenditure Savings",
            "International Project Grants",
            "Additional Project Grants",
            "Carbon Credits",
            # "Carbon Credit Price"
        ]
        df_funding_availability_full = pd.DataFrame(index=rows,columns=cols)
        
        #If there is captital injection or not
        if self.scenario.capital_injection:
            capital_injection = self.scenario.capital_injection
            # raise InProgressError("This feature is still in progress.")
            df_funding_availability_full.loc[rows[3],:]= [capital_injection.volume/capital_injection.duration if year in range(capital_injection.start_year,capital_injection.start_year+3) else 0 for year in cols]
        else:
            df_funding_availability_full.loc[rows[3],:]= 0
        
        
        if self.scenario.capital_injection and self.scenario.capital_injection.type in ["Government Budget","Government budget","government budget"]:
            # raise InProgressError("This feature is still in progress.")
            rate = df_funding_availability_lever.loc["CAGR of government spending","Projected"]
            df_funding_availability_full.loc[rows[0],:] = [df_funding_envelope.loc["Annual Average","Budget"]*(1+rate)**i for i in range(len(cols))]
            df_funding_availability_full.loc[rows[0],:] -= df_funding_availability_full.loc[rows[3],:]
        else:
            rate = df_funding_availability_lever.loc["CAGR of government spending","Projected"]
            df_funding_availability_full.loc[rows[0],:] = [df_funding_envelope.loc["Annual Average","Budget"]*(1+rate)**i for i in range(len(cols))]
            
        
        if financial_instrument in ["Debt Write-Off","Debt write-off","debt write-off"]:
            raise InProgressError("This feature is still in progress.")
        else:
            df_funding_availability_full.loc[rows[1],:]=0
        
            
        rate = df_funding_availability_lever.loc["CAGR of SOE internal cash generation","Projected"]
        df_funding_availability_full.loc[rows[2],:]= [df_funding_envelope.loc["Annual Average","SOE Gen."]*(1+rate)**i for i in range(len(cols))]
        
        df_funding_availability_full.loc[rows[4],:] = fossil_fuel_savings.loc[:,"expenditure"]
        rate =df_funding_availability_lever.loc["CAGR of international grants","Projected"] 
        df_funding_availability_full.loc[rows[5],:] = [df_funding_envelope.loc["Annual Average","Grant"]*(1+rate)**i for i in range(len(cols))]
        if financial_instrument in ["Grant","grant"]:
            df_funding_availability_full.loc[rows[6],:] = df_grants_with_ffs_carbon.loc["Annual Grant Requirement Considering FF and Carbon Savings"]
        elif financial_instrument in ["Grant and Loan","grant and loan","Grant and loan","Grant Loan"]:
            raise InProgressError("This feature is still in progress.")
        else:
            df_funding_availability_full.loc[rows[6],:] = 0
        df_funding_availability_full.loc[rows[7],:] = self.get_co2_savings_legacy(self.least_cost_summary,self.net_zero_summary).loc["Carbon price",:]
        
        df_funding_availability_full.loc["Total",:]= df_funding_availability_full.copy().sum(axis=0)-df_funding_availability_full.loc[rows[3],:]
        
        return df_funding_availability_full
    
    
        
    def get_funding_sources(self,dashboard_summary):
        cols = self.years
        rows = [
            "Total Funding",
            "Multilateral Development Bank concessional loans",
            "National Development Bank concessional loans",
            "International commercial loans",
            "Domestic commercial loans",
        ]
        # dashboard_summary= self.get_summary(df_funding_availability_full,df_invest_need_summary,needs_of_different_scenario,repayment_schedule)
        df_funding_sources = pd.DataFrame(index = rows, columns=cols)
        df_funding_sources.loc[rows[0],:] = dashboard_summary.loc["Investment needs",:]
        shares = self.get_financing_source_shares()
        for i,row in enumerate(rows[1:]):
            df_funding_sources.loc[row,:] =shares.loc[self.sectors[i],"Projected"]*dashboard_summary.loc["Investment needs",:]
        return df_funding_sources
        
    def get_existing_financing(self, repayment_schedule):
        year_cols = [
            col for col in repayment_schedule.columns if str(col).isdigit() and int(col) in self.years
        ]
        repayments = repayment_schedule[year_cols].T.sum(axis=1)
        repayments.index = repayments.index.astype(int)
        return repayments.sort_index()

    def get_repayments(self,repayment_schedule,df_invest_need_summary,df_funding_envelope):
        cols = self.years
        rows = ["Existing finance payments (Million USD)",
                "Financing payments for construction of new energy",
                "Financing Payments for retirement of old fossil fuel technologies",
                "Capital Injection Repayment (Million USD)",
            ]
        
        year_cols = year_columns_from_index(
            repayment_schedule.columns, since_year=self.years[0]
        )
        existing_finance_payments = repayment_schedule[year_cols].sum()
        
        df_repayments = pd.DataFrame(index=rows, columns=cols)
        df_repayments.loc[rows[0],:] = existing_finance_payments
        df  = self.get_net_zero_financing_needs_full(df_invest_need_summary,df_funding_envelope)
        
        df_repayments.loc[rows[1],:] =df.loc["Financing Requirements",:] *df_invest_need_summary.loc[:,"Net Zero"]/df.loc["Investment needs",:]
        df_repayments.loc[rows[2],:] = df.loc["Financing Requirements",:]-df_repayments.loc[rows[1],:]
        if self.scenario.capital_injection and self.scenario.capital_injection.type.lower() in ["Loan", "loan","Equity"]:
            projected_average =  self.get_projected_average()["Debt"]
            
            df_repayments.loc[rows[3],:] = [self.cal_injection_repayments(year,projected_average) for year in cols]
        else:
            df_repayments.loc[rows[3],:] = 0

        return df_repayments
    
    def cal_injection_repayments(self,year,projected_average):
        """
        Simulates Excel formula:
        =IFERROR(
            IF(AND(year >= start_year, year < (start_year + term), OR(financing_type="Loan", financing_type="Equity")),
                (volume / (term - (grace_period - 1)) + volume * interest_rate * ((1 + interest_rate) ** term)),
                0
            ),
            0
            )
        
        Parameters:
        year: Current year (corresponds to Excel cell B70)
        start_year: Starting year (corresponds to C48)
        duration: Duration (corresponds to C49, not used in formula)
        volume: Funding amount (corresponds to C50)
        term: Term (corresponds to C36)
        grace_period: Grace period (corresponds to C35)
        interest_rate: Interest rate (corresponds to C34)
        financing_type: Financing type, should be "Loan" or "Equity" (corresponds to C51)
        
        Returns:
        Formula calculation result (float), returns 0 if conditions are not met or in case of error
        """
        start_year = self.scenario.capital_injection.start_year
        volume = self.scenario.capital_injection.volume
        term = projected_average.loc["Average term of loan"]
        grace_period = projected_average.loc["Average grace period"]
        interest_rate = projected_average.loc["Average interest rate"]
        
        try:
            # Condition check: year is within [start_year, start_year + term) and financing type is "Loan" or "Equity"
            if year >= start_year and year < (start_year + term):
                result = (volume / (term - (grace_period - 1))) + (volume * interest_rate * ((1 + interest_rate) ** term))
            else:
                result = 0
        except Exception:
            result = 0
        return result

    def get_debt_stock(self,dashboard_summary,nz_needs):
        cols = self.years
        rows = self.sectors
        debt_share = self.get_full_financing_requirement().loc[:,("Projected","Debt")]
        df_debt_stock = pd.DataFrame(index=rows, columns=cols)
        for sector in rows:
            df_debt_stock.loc[sector,:] = debt_share.loc[(sector,"Debt Equity Share"),] * dashboard_summary.loc["Investment needs",:]*self.get_financing_source_shares().loc[sector,"Projected"]
            
            values = pd.DataFrame(index=[0],columns=cols) 
            for i,year in enumerate(cols):
                # Formula: current period = (previous period + constant) * factor
                if i == 0:
                    next_value = df_debt_stock.loc[sector, year] * (1+ debt_share.loc[(sector,"Average interest rate")])-nz_needs.loc["Debt: "+sector,year]
                else:    
                    next_value = (values.loc[0,year-1] + df_debt_stock.loc[sector, year]) * (1+ debt_share.loc[(sector,"Average interest rate")])-nz_needs.loc["Debt: "+sector,year]
                
                values.loc[0,year] = next_value
            df_debt_stock.loc[sector, :] =values.loc[0,:]# df_debt_stock.loc[sector, :]*(1+ debt_share.loc[(sector,"Average interest rate")]) -nz_needs.loc["Debt: "+sector,:]    
        df_debt_stock.loc["Total",:] = df_debt_stock.sum(axis=0)
        return df_debt_stock
    
    def get_financing_needs_scenario(self,df_data_source,df_funding_envelope=None):
            
        cols = self.years
        if df_funding_envelope is None:
            df_funding_baseline_full = self.funding_baseline_full
            df_funding_baseline = process_funding_baseline(df_funding_baseline_full)
            df_funding_envelope = get_funding_envelope(df_funding_baseline)
        rows = ["Investment needs","Grant covered","Financing needs"]
        df_investment_needs = pd.DataFrame(index=rows, columns=cols)
        df_investment_needs.loc[rows[0], :] = df_data_source#.values#df_data_source.set_index("Year",drop=True).drop(columns=categories_to_exclude).sum(axis=1)
        
        growth_rate = self.get_funding_availability_lever(df_funding_envelope).loc[ "CAGR of international grants","Projected"]
        df_investment_needs.loc[rows[1],:] = [df_funding_envelope.loc["Annual Average","Grant"] * (1 + growth_rate) ** (year - cols[0]) for year in cols]
        # df_category_sum_lc.set_index("Year",drop=True).drop(columns=categories_to_exclude).sum(axis=1)
        
        df_investment_needs.loc[rows[2],:] = df_investment_needs.loc[rows[0],:].copy() - df_investment_needs.loc[rows[1],:].copy()
        
        # compute_excel_value(df, interest_rate, term, grace, coef1, coef2):
        source_shares = self.get_financing_source_shares()["Projected"]
        for f in ["Debt","Equity"]:
            for sector in self.sectors:
                levers = self.get_financing_requirements(sector)
            
                if self.financial_instrument_type in ["Grant element","grant element","Grant Element"]:
                    raise ValueError("Should do soemthing else for grant element, haven't finished")
                else:    
                    rate = levers.loc["Average interest rate",("Projected",f)]
                term = levers.loc["Average term of loan",("Projected",f)]
                grace_period = levers.loc["Average grace period",("Projected",f)]
                debt_share = levers.loc["Debt Equity Share",("Projected",f)]
                if f == "Debt":
                    cal_needs = cal_loan_needs
                else:
                    cal_needs = cal_equity_needs
                repayment_sch = cal_needs(df_investment_needs.loc[rows[2],:].to_frame().T,rate, term, grace_period, debt_share,source_shares[sector])
                df_investment_needs.loc[f+": "+sector,:] = repayment_sch
        df_investment_needs.loc["Financing Requirements",:] = df_investment_needs.loc[~df_investment_needs.index.isin(rows[0:3:2])].sum(axis=0)
        new_index = [idx for idx in df_investment_needs.index]
        return df_investment_needs.loc[new_index]
    def get_net_zero_financing_needs_full(self,df_invest_need_summary,df_funding_envelope):
        return self.get_financing_needs_scenario(df_invest_need_summary.loc[:,"Total financing"],df_funding_envelope)
    def get_least_cost_financing_needs_full(self,df_invest_need_summary,df_funding_envelope):
        return self.get_financing_needs_scenario(df_invest_need_summary.loc[:,"Least Cost"],df_funding_envelope)
    @staticmethod
    def get_additional_investment_needs(least_cost_needs,net_zero_needs):
        additional = net_zero_needs - least_cost_needs
        
        return additional.iloc[0:2]
    @staticmethod
    def get_co2_savings_legacy(least_cost_summary,net_zero_summary):
        df_co2_savings = pd.DataFrame()
        df_list = [ 
            least_cost_summary['co2_emission']-net_zero_summary['co2_emission'], 
            least_cost_summary['co2_emission'],
            net_zero_summary['co2_emission'],
            (least_cost_summary['co2_emission']-net_zero_summary['co2_emission'])*least_cost_summary['carbon_price'],
        ]
        return pd.concat(df_list,axis=1,keys=["Net CO2 Saving","Least cost", "Net zero","Carbon price"]).T

    @staticmethod
    def get_co2_savings(least_cost_summary, net_zero_summary):
        df_list = [
            (least_cost_summary["co2_emission"] - net_zero_summary["co2_emission"])
            * least_cost_summary["carbon_credit_price"],
            least_cost_summary["carbon_credit_price"],
            least_cost_summary["co2_emission"] - net_zero_summary["co2_emission"],
            least_cost_summary["co2_emission"],
            net_zero_summary["co2_emission"],
        ]
        return pd.concat(
            df_list,
            axis=1,
            keys=[
                "Carbon credit",
                "Carbon credit price",
                "Net CO2 Saving",
                "Least cost",
                "Net zero",
            ],
        ).T
    def get_gdp_projection(self,current_gdp=50000,growth_rate=0.05):
        return pd.DataFrame([current_gdp*(1+growth_rate)**i for i in range(len(self.years))],index=self.years,columns=["GDP"]) 
    def get_gdp_percentage(self,dashboard_summary):
        gdp = self.get_gdp_projection(5000,0).loc[:,"GDP"]
        cols = self.years
        rows = ['Financing',"Funding"]
        df_gdp_percentage = pd.DataFrame(index=rows,columns=cols)
        df_gdp_percentage.loc[rows[0],:] = dashboard_summary.loc["Financing requirement",:]/gdp
        df_gdp_percentage.loc[rows[1],:] = dashboard_summary.loc["Funding availability",:]/gdp
        return df_gdp_percentage
        
    def get_summary(self,df_funding_availability_full,df_invest_need_summary,needs_of_different_scenario,repayment_schedule):
        funding_available = df_funding_availability_full.loc["Total",:]
        if self.scenario.scenario in ["NetZero","LeastCost","Incremental"]:
            
            investment_need = df_invest_need_summary[self.scenario.scenario ]["Total"]
            financing_requirement = needs_of_different_scenario[self.scenario.scenario].loc["Financing Requirements"]
            
        else:
            #We may remove this if else and just set the default scenario as NetZero
            raise InProgressError("This feature is still in progress.")
        investment_need.index = self.years
        year_cols = year_columns_from_index(
            repayment_schedule.columns, since_year=self.years[0]
        )
        existing_finance_payments = repayment_schedule[year_cols].sum()
        financing_requirement = financing_requirement+existing_finance_payments
        # df_result = pd.concat(
        #     [
        #         investment_need,
        #         funding_available,
        #         financing_requirement,
        #         financing_requirement - funding_available
        #     ],
        #     keys=["Investment needs","Funding Availability","Financing requirement","Funding shortfall"],
        #     axis=0  # Default is also 0, written here for clarity
        # )

        # # Then rename columns for the concatenated df_result (ensure column count matches self.years length)
        # df_result.columns = self.years

        return pd.DataFrame({
                    "Investment needs": investment_need,
                    "Funding availability": funding_available,
                    "Financing requirement": financing_requirement,
                    "Funding shortfall": financing_requirement - funding_available
                }).T


hd = high_level_dashboard
