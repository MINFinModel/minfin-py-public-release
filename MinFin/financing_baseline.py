import math

import numpy as np
import pandas as pd

from MinFin.fx import (
    currency_list,
    exchange_rates_by_year,
    get_exchange_rates,
    macro_rates_dict_from_exchange_wide,
)
from MinFin.utils import pmt

# Canonical repayment Schedule names (from the Excel "Financing Baseline" formula) keyed by a
# lowercase lookup. Accepts both legacy labels and the pure-input EXISTING INFRASTRUCTURE labels
# (e.g. "Lump Sum Principal" -> "Lump Sum on Principal").
_SCHEDULE_ALIASES = {
    "equity": "Equity",
    "equal principal payments (epp)": "Equal Principal Payments (EPP)",
    "epp": "Equal Principal Payments (EPP)",
    "epp with grace on principal": "EPP with Grace on Principal",
    "epp with grace years for principal": "EPP with Grace on Principal",
    "epp with grace on principal & interest": "EPP with Grace on Principal & Interest",
    "epp with grace on principal and interest": "EPP with Grace on Principal & Interest",
    "lump sum on principal": "Lump Sum on Principal",
    "lump sum principal": "Lump Sum on Principal",
    "lump sum on principal & interest": "Lump Sum on Principal & Interest",
    "lump sum on principal and interest": "Lump Sum on Principal & Interest",
    "lump sum principal and interest": "Lump Sum on Principal & Interest",
    "lump sum principal & interest": "Lump Sum on Principal & Interest",
    "annuity": "Annuity",
    "annuity with grace on principal": "Annuity with Grace on Principal",
    "annuity with grace on principal & interest": "Annuity with Grace on Principal & Interest",
    "annuity with grace on principal and interest": "Annuity with Grace on Principal & Interest",
}


def _normalize_schedule(scenario):
    """Return the canonical Schedule name, or None for blank/unrecognised values."""
    if scenario is None:
        return None
    key = str(scenario).strip().lower()
    if key in ("", "nan", "0"):
        return None
    return _SCHEDULE_ALIASES.get(key)


def historical_from_existing_infrastructure(ex: pd.DataFrame) -> pd.DataFrame:
    """
    Map **EXISTING INFRASTRUCTURE** (header row 4) onto the same column layout as the legacy
    *Financing Baseline* historical block (before ``add_columns_for_other_currencies``).

    Pure-input columns: Technology, Year, Financing Source, Volume of Finance,
    Currency, Rate, Term, Grace period, Schedule.
    Optional (no longer required from sheet): Type of Finance; Financing Sector /
    Financial Institution / Origin of Finance are left unset for downstream stats that only need source + amounts.
    """
    df = ex.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, [c for c in df.columns if not c.startswith("Unnamed")]]
    for col in ("Technology", "Year", "Financing Source", "Volume of Finance", "Currency"):
        if col not in df.columns:
            raise ValueError(f"EXISTING INFRASTRUCTURE missing required column: {col}")
    out = pd.DataFrame()
    uid = df.index.astype(str)
    out["Name of Project"] = (
        df["Technology"].astype(str) + " | " + df["Year"].astype(str) + " | " + uid
    )
    out["Name of Financier"] = ""
    out["Sector"] = np.nan
    out["Technology"] = df["Technology"]
    out["Source"] = np.nan
    out["Year"] = pd.to_numeric(df["Year"], errors="coerce").fillna(0).astype(int)
    out["Financing Source"] = df["Financing Source"]
    # Optional classification columns (omit from template or leave blank).
    # out["Type of Finance"] = df["Type of Finance"]
    # out["Financing Sector"] = ...
    # out["Financial Institution"] = ...
    # out["Origin of Finance"] = ...
    if "Type of Finance" in df.columns:
        out["Type of Finance"] = df["Type of Finance"].astype(str)
    else:
        out["Type of Finance"] = "Loan"
    # Match legacy ``get_historical`` column names (stripped); keep nan unless sheet adds columns later.
    out["Financing Sector"] = df["Financing Sector"].astype(object) if "Financing Sector" in df.columns else np.nan
    out["Financial Institution"] = (
        df["Financial Institution"].astype(object) if "Financial Institution" in df.columns else np.nan
    )
    out["Origin of Finance"] = df["Origin of Finance"].astype(object) if "Origin of Finance" in df.columns else np.nan
    out["Volume of Finance"] = pd.to_numeric(df["Volume of Finance"], errors="coerce").fillna(0.0)
    out["Currency"] = df["Currency"].fillna("USD").astype(str)
    out["Volume in GHS"] = np.nan
    out["Volume in USD"] = np.nan
    out["Exchange Rate"] = np.nan
    out["Rate"] = pd.to_numeric(df.get("Rate", np.nan), errors="coerce").fillna(0.0)
    out["Term"] = pd.to_numeric(df.get("Term", np.nan), errors="coerce").fillna(0.0)
    out["Maturity"] = np.nan
    out["Grace period"] = pd.to_numeric(df.get("Grace period", np.nan), errors="coerce").fillna(0.0)
    out["Schedule"] = df.get("Schedule", "").fillna("").astype(str)
    return out


def macroeconomic_currency_codes(file_path: str) -> tuple[str | None, str | None]:
    """Return ``(local_currency, foreign_currency)`` codes from **MACROECONOMIC** column C.

    Looks for rows labeled ``Local Currency`` / ``Foreign Currency`` (parameter column B).
    Missing labels yield ``None`` for that side.
    """
    mac = pd.read_excel(file_path, sheet_name="MACROECONOMIC", header=None, engine="openpyxl")
    local: str | None = None
    foreign: str | None = None
    for i in range(mac.shape[0]):
        label = mac.iloc[i, 1]
        if pd.isna(label):
            continue
        label = str(label).strip().lower()
        code = mac.iloc[i, 2]
        if pd.isna(code):
            continue
        code = str(code).strip()
        if not code or code.lower() in {"nan", "none", "code"}:
            continue
        if label == "local currency":
            local = code
        elif label == "foreign currency":
            foreign = code
    return local, foreign


def exchange_rates_wide_from_macroeconomic(file_path: str) -> pd.DataFrame:
    """
    Build a year × currency table from **MACROECONOMIC** (same role as the top of legacy *Financing Baseline*).
    Rows: Foreign Currency, Local Currency, Currency (codes in column C); year columns from header row 4.
    """
    mac = pd.read_excel(file_path, sheet_name="MACROECONOMIC", header=None, engine="openpyxl")
    header_row = 4
    year_cols: list[tuple[int, int]] = []
    for j in range(mac.shape[1]):
        v = mac.iloc[header_row, j]
        try:
            y = int(float(v))
        except (TypeError, ValueError):
            continue
        if 1990 < y < 2100:
            year_cols.append((j, y))
    by_year: dict[int, dict[str, float]] = {}
    for i in range(header_row + 1, mac.shape[0]):
        label = mac.iloc[i, 1]
        if pd.isna(label):
            continue
        label = str(label).strip()
        if label not in ("Foreign Currency", "Local Currency", "Currency"):
            continue
        code = mac.iloc[i, 2]
        if pd.isna(code):
            continue
        code = str(code).strip()
        for j, y in year_cols:
            val = mac.iloc[i, j]
            if pd.notna(val):
                by_year.setdefault(y, {})[code] = float(val)
    if not by_year:
        return pd.DataFrame()
    wide = pd.DataFrame.from_dict(by_year, orient="index").sort_index()
    wide.index.name = None
    # Align to model years; forward-fill so early historic financing years still resolve rates
    wide = wide.reindex(range(2010, 2080)).ffill().bfill()
    return wide


class financing_baseline_extractor:
    def __init__(
        self,
        df_financing_baseline_full,
        currency="KES",
        starting_year=2024,
        number_of_payments_per_annum=1,
        *,
        foreign_currency: str = "USD",
        historical_from_existing: pd.DataFrame | None = None,
        exchange_rates_wide: pd.DataFrame | None = None,
        macro_rates_dict: dict | None = None,
    ) -> None:
        self.currency = currency
        self.years = list(range(2010, 2071))
        self.starting_year = starting_year
        self.foreign_currency = foreign_currency
        self.discount_rate = 5.33 / 100  # 'High Level Dashboard'!E34
        self.number_of_payments_per_annum = number_of_payments_per_annum
        self.starting_rows = {"exchange_rate": 35, "historical baseline": 49}
        self.starting_cols = {"historical baseline": 0, "exchange_rate": 2}
        self._exchange_rates_wide = exchange_rates_wide
        self._macro_rates_dict = macro_rates_dict
        self.df_financing_baseline_full = df_financing_baseline_full
        self._historical_is_prebuilt = historical_from_existing is not None
        if historical_from_existing is not None:
            self.historical = self.add_columns_for_other_currencies(
                historical_from_existing.copy(), self._macro_rates_dict
            )
            self.historical = self.historical.dropna(how="all", axis=0).reset_index(drop=True)
        else:
            self.historical = self.get_historical()

    @classmethod
    def from_workbook(
        cls,
        file_path: str,
        currency=None,
        starting_year=2024,
        number_of_payments_per_annum=1,
        foreign_currency=None,
    ):
        """
        Build an extractor from either the legacy **Financing Baseline** sheet or the pure-input workbook
        (**EXISTING INFRASTRUCTURE** + **MACROECONOMIC** exchange block).

        For pure-input workbooks, local/foreign currency codes default to
        **MACROECONOMIC** ``Local Currency`` / ``Foreign Currency`` (column C) when
        *currency* / *foreign_currency* are not passed explicitly.
        """
        from MinFin.data_processor import WORKBOOK_FORMAT_PURE_INPUT, detect_workbook_format

        if detect_workbook_format(file_path) == WORKBOOK_FORMAT_PURE_INPUT:
            ex = pd.read_excel(
                file_path, sheet_name="EXISTING INFRASTRUCTURE", header=4, engine="openpyxl"
            )
            hist = historical_from_existing_infrastructure(ex)
            ex_wide = exchange_rates_wide_from_macroeconomic(file_path)
            macro_d = (
                macro_rates_dict_from_exchange_wide(ex_wide) if len(ex_wide) else None
            )
            local_c, foreign_c = macroeconomic_currency_codes(file_path)
            currency = currency or local_c or "KES"
            foreign_currency = foreign_currency or foreign_c or "USD"
            return cls(
                pd.DataFrame(),
                currency=currency,
                starting_year=starting_year,
                number_of_payments_per_annum=number_of_payments_per_annum,
                foreign_currency=foreign_currency,
                historical_from_existing=hist,
                exchange_rates_wide=ex_wide if len(ex_wide) else None,
                macro_rates_dict=macro_d,
            )
        df_fb = pd.read_excel(file_path, sheet_name="Financing Baseline", engine="openpyxl")
        return cls(
            df_fb,
            currency=currency or "KES",
            starting_year=starting_year,
            number_of_payments_per_annum=number_of_payments_per_annum,
            foreign_currency=foreign_currency or "USD",
        )

    def get_exchange_rates_by_year(self):
        if self._exchange_rates_wide is not None and len(self._exchange_rates_wide):
            df_result = self._exchange_rates_wide.copy()
            df_result.index = df_result.index.astype(int)
            return df_result
        df_financing_baseline_full = self.df_financing_baseline_full
        starting_row = self.starting_rows["exchange_rate"]
        starting_col = self.starting_cols["exchange_rate"]
        new_columns = self.years

        # Extract data (skip the column names row)
        df_exchange_rates = df_financing_baseline_full.iloc[
            starting_row : starting_row + 10, starting_col : starting_col + len(new_columns)
        ].copy()
        df_exchange_rates.columns = df_exchange_rates.iloc[0]
        df_exchange_rates = df_exchange_rates.iloc[1:]
        df_exchange_rates.set_index("Currency", inplace=True)
        df_exchange_rates.index.name = "Year"
        df_exchange_rates.columns.name = None  # drop column index name

        # df_exchange_rates.columns = new_columns
        df_result = df_exchange_rates.T.iloc[:].dropna(how="all", axis=0)
        df_result.index = df_result.index.astype(int)
        return df_result

    def get_historical(self):
        if self._historical_is_prebuilt:
            return self.historical.copy()
        df_financing_baseline_full = self.df_financing_baseline_full
        starting_row = self.starting_rows['historical baseline']
        starting_col = self.starting_cols['historical baseline']
        # Get the first row as column names
        new_columns = df_financing_baseline_full.iloc[starting_row, starting_col:starting_col+21].values
        
        # Extract data (skip the column names row)
        df_historical = df_financing_baseline_full.iloc[starting_row+1:starting_row+400, starting_col:starting_col+21].copy()
        
        # Reset column names
        df_historical.columns = [x.strip() for x in new_columns]        
        df_historical = df_historical.drop(columns=["Volume in KES", "Volume in USD", "Exchange Rate","Maturity"], errors='ignore').dropna(how='all', axis=0)#.dropna(how='all', axis=1)
        df_historical = self.add_columns_for_other_currencies(df_historical, None)
        return df_historical.dropna(how='all', axis=0).reset_index(drop=True)#.dropna(how='all', axis=1)
    
    def add_columns_for_other_currencies(self, df, rates_by_year=None):
        """
        Calculate financial data and add:
        - volume of finance in currency
        - volume of finance in foreign currency
        - exchange rate to currency
        - exchange rate to foreign currency
        
        Parameters:
        df: DataFrame containing transaction data
        rates_by_year: Optional dict ``{year: {currency: rate}}``; defaults to module ``exchange_rates_by_year``.
        """
        base_currency=self.currency
        foreign_currency=self.foreign_currency
        rd = rates_by_year if rates_by_year is not None else exchange_rates_by_year

        df[f"Volume in {base_currency}"] = df["Volume of Finance"] * get_exchange_rates(
            base_currency, df["Currency"], df["Year"], rd
        )

        df[f"Volume in {foreign_currency}"] = df["Volume of Finance"] * get_exchange_rates(
            foreign_currency, df["Currency"], df["Year"], rd
        )
        df[f"Exchange Rate to {base_currency}"] = get_exchange_rates(
            base_currency, df["Currency"], df["Year"], rd
        )
        df[f"Exchange Rate to {foreign_currency}"] = get_exchange_rates(
            foreign_currency, df["Currency"], df["Year"], rd
        )
        df["Maturity"] = df["Term"]-self.starting_year+df["Year"]
        
        return df
    
    def cal_repayment_schedule(
        self,
        df,
        *,
        convert_currency: bool = False,
        dashboard_currency: str | None = None,
        rates_by_year: dict | None = None,
    ):
        """
        Build the per-project repayment schedule (one row per project, one column per year),
        mirroring the Excel "Financing Baseline" formula across all Schedule types.

        Currency handling:
        - ``convert_currency=False`` (default): use ``Volume of Finance`` as-is, i.e. the
          commitment currency. Inputs are USD by default, so this keeps USD amounts.
        - ``convert_currency=True``: multiply each year's payment by the Excel FX ratio
          ``rate(local_currency, start_year) / rate(commitment_currency, start_year)``
          and, for foreign-currency dashboards, ``rate(foreign_currency, payment_year)
          / rate(local_currency, payment_year)``;
          ``dashboard_currency`` defaults to ``self.foreign_currency`` ("USD").
        """
        if dashboard_currency is None:
            dashboard_currency = self.foreign_currency
        df = df.reset_index(drop=True)
        years = self.years
        df_repayment = pd.DataFrame(columns=years)
        df_repayment['Repayment'] = 0
        df_repayment['Name of Project'] = df['Name of Project']

        repay_years_list = []
        for _, row in df.fillna(0).iterrows():
            # Repayment years window: start .. start + ceil(term) (a superset of the paying years;
            # per-Schedule logic zeroes out non-paying years).
            repay_years = list(range(int(row['Year']), int(row['Year']) + int(row['Term'] + 1)))
            repay_years_list.append(repay_years)

        df_repayment['repay_years'] = repay_years_list
        df_repayment['Project ID'] = df.index
        for year in range(2010, 2071):
            for project_id in df.index:
                repay_years = list(df_repayment.loc[df_repayment['Project ID'] == project_id, 'repay_years'])[0]
                if year in repay_years:
                    fx_factor = 1.0
                    if convert_currency:
                        fx_factor = self._repayment_fx_factor(
                            df.loc[project_id, "Currency"],
                            year,
                            dashboard_currency,
                            rates_by_year,
                            start_year=df.loc[project_id, "Year"],
                        )
                    df_repayment.loc[df_repayment['Project ID'] == project_id, year] = self.cal_repayment_value(
                        df.loc[project_id, "Rate"],
                        df.loc[project_id, 'Volume of Finance'],
                        df.loc[project_id, "Schedule"],
                        year,
                        repay_years,
                        term=df.loc[project_id, 'Term'],
                        grace_period=df.loc[project_id, 'Grace period'],
                        fx_factor=fx_factor,
                    )
                else:
                    df_repayment.loc[df_repayment['Project ID'] == project_id, year] = 0
        
        df_repayment['Sum of Repayment'] = df_repayment[years].sum(axis=1).astype(float)
        # #print("============================================")
        df_repayment['Market Element'] = self.cal_market_element()
        df_repayment['Grant Element'] = self.cal_grant_element()
        # #print('term',df['Term'].astype(float),df['Term'].astype(float).replace(0,100000))
        df_repayment['Average Annual Payment']= df_repayment['Sum of Repayment'] /df['Term'].astype(float)#.replace(0,100000)
        df_repayment['Average Annual Payment'] = df_repayment['Average Annual Payment'].replace([np.inf, -np.inf], np.nan).fillna(0)
        return df_repayment.reset_index(drop=True)
    def _repayment_fx_factor(
        self,
        commitment_currency,
        year,
        dashboard_currency,
        rates_by_year=None,
        *,
        start_year=None,
    ):
        """
        Excel repayment FX ratio:
        local(start_year) / commitment(start_year), then foreign(year) / local(year)
        when the dashboard is in foreign currency.
        """
        rd = rates_by_year if rates_by_year is not None else (self._macro_rates_dict or exchange_rates_by_year)
        start_year = year if start_year is None else start_year
        start_rates = rd.get(int(start_year)) if rd else None
        year_rates = rd.get(int(year)) if rd else None
        if not start_rates:
            return 1.0
        local_currency = getattr(self, "currency", "KES")
        foreign_currency = getattr(self, "foreign_currency", "USD")
        local_start = start_rates.get(str(local_currency))
        comm_start = start_rates.get(str(commitment_currency))
        if not local_start or not comm_start:
            return 1.0
        factor = local_start / comm_start
        if str(dashboard_currency) == str(foreign_currency):
            if not year_rates:
                return 1.0
            foreign_year = year_rates.get(str(foreign_currency))
            local_year = year_rates.get(str(local_currency))
            if not foreign_year or not local_year:
                return 1.0
            factor *= foreign_year / local_year
        return factor

    def cal_repayment_value(self, interest_rate, volume, scenario, year, repay_years,
                            term=0, grace_period=0, fx_factor=1.0):
        """
        Single project-year repayment, matching the Excel "Financing Baseline" formula.

        *scenario* is the Schedule type; names are normalised (see ``_SCHEDULE_ALIASES``) so
        legacy and pure-input **EXISTING INFRASTRUCTURE** labels both work. The base payment is
        multiplied by *fx_factor* (Excel's per-year FX ratio; 1.0 keeps the commitment currency).
        Errors return 0.0 (Excel ``IFERROR(..., 0)``).
        """
        try:
            base = self._repayment_base_value(
                interest_rate, volume, scenario, year, repay_years, term, grace_period
            )
        except Exception:
            return 0.0
        if base is None:
            return 0.0
        return base * fx_factor

    def _repayment_base_value(self, interest_rate, volume, scenario, year, repay_years,
                              term=0, grace_period=0):
        canonical = _normalize_schedule(scenario)
        if canonical is None:
            return 0.0
        F = repay_years[0]
        L, Q, R, T, y = float(volume), float(interest_rate), float(term), float(grace_period), float(year)
        if canonical == "Equity":
            return self._pay_equity(L, Q, R, F, y)
        if canonical == "Equal Principal Payments (EPP)":
            return self._pay_epp(L, Q, R, F, y)
        if canonical == "EPP with Grace on Principal":
            return self._pay_epp_grace_p(L, Q, R, T, F, y)
        if canonical == "EPP with Grace on Principal & Interest":
            return self.epp_with_grace_p_and_i_payment(
                interest_rate=Q, volume=L, start_year=F, term=R, grace_period=T, year=y
            )
        if canonical == "Lump Sum on Principal":
            return self._pay_lump_principal(L, Q, R, F, y)
        if canonical == "Lump Sum on Principal & Interest":
            return self._pay_lump_principal_interest(L, Q, R, F, y)
        if canonical == "Annuity":
            return self._pay_annuity(L, Q, R, F, y)
        if canonical == "Annuity with Grace on Principal":
            return self._pay_annuity_grace_p(L, Q, R, T, F, y)
        if canonical == "Annuity with Grace on Principal & Interest":
            return self._pay_annuity_grace_pi(L, Q, R, T, F, y)
        return 0.0

    # --- Per-Schedule payment formulas (L=volume, Q=rate, R=term, T=grace, F=start year, y=year) ---
    @staticmethod
    def _pay_equity(L, Q, R, F, y):
        floor_R = math.floor(R)
        if F <= y <= F + floor_R - 1:
            return L * Q
        if y == F + math.ceil(R) - 1:
            return (R - floor_R) * L * Q
        return 0.0

    @staticmethod
    def _pay_epp(L, Q, R, F, y):
        if R == 0:
            return 0.0
        floor_R = math.floor(R)
        if F <= y < F + floor_R:
            principal = L / R
            remaining = L - principal * max(0.0, y - F)
            return principal + remaining * Q
        if y == F + math.ceil(R) - 1:
            return (L / R) * (R - floor_R) * (1 + Q)
        return 0.0

    @staticmethod
    def _pay_epp_grace_p(L, Q, R, T, F, y):
        denom = R - T
        if denom == 0:
            return 0.0
        floor_R, floor_T = math.floor(R), math.floor(T)
        if F <= y <= F + T - 1:
            return L * Q
        if y == F + floor_T:
            return L * Q + (L / denom) * (1 - (T - floor_T))
        if F + T - 1 < y < F + R - 1:
            principal = L / denom
            remaining = L - principal * max(0.0, y - (F + T))
            return principal + remaining * Q
        if y == F + math.ceil(R) - 1:
            frac = 1.0 if (R - floor_R) == 0 else (R - floor_R)
            return (L / denom) * frac * (1 + Q)
        return 0.0

    @staticmethod
    def _pay_lump_principal(L, Q, R, F, y):
        floor_R = math.floor(R)
        if F <= y < F + R - 1:
            return L * Q
        if y == F + math.ceil(R) - 1:
            frac = 1.0 if (R - floor_R) == 0 else (R - floor_R)
            return L + L * Q * frac
        return 0.0

    @staticmethod
    def _pay_lump_principal_interest(L, Q, R, F, y):
        if y == F + math.ceil(R) - 1:
            return L * (1 + Q) ** R
        return 0.0

    @staticmethod
    def _pay_annuity(L, Q, R, F, y):
        floor_R = math.floor(R)
        if F <= y < F + floor_R:
            return -pmt(Q, R, L)
        if y == F + floor_R:
            return -pmt(Q, R, L) * (R - floor_R)
        return 0.0

    @staticmethod
    def _pay_annuity_grace_p(L, Q, R, T, F, y):
        floor_R = math.floor(R)
        if F <= y < F + T:
            return L * Q
        if F + T <= y < F + floor_R:
            return -pmt(Q, R - T, L)
        if y == F + floor_R:
            return -pmt(Q, R - T, L) * (R - floor_R)
        return 0.0

    @staticmethod
    def _pay_annuity_grace_pi(L, Q, R, T, F, y):
        floor_R = math.floor(R)
        pv = L * (1 + Q) ** T
        if F + T <= y < F + floor_R:
            return -pmt(Q, R - T, pv)
        if y == F + floor_R:
            return -pmt(Q, R - T, pv) * (R - floor_R)
        return 0.0

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
        grant_element["Grant Element"] = epp_grant_element * factor + lump_grant_element * (1 - factor)

        # Do not store the literal "Equity" here — mixing str and float coerces the whole column to object strings.
        grant_element["Grant Element"] = np.where(
            financing_schedule_type.str.contains("Equity", na=False),
            np.nan,
            grant_element["Grant Element"],
        )
        return grant_element
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

from MinFin.financing_stats import financing_baseline_stats
