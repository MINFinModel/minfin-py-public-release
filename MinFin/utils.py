import math
import pandas as pd

def pmt(rate, nper, pv):
    """
    Simulates Excel's PMT function, without considering final value and payments at the beginning of period.
    If rate is 0, returns pv/nper, otherwise returns pv * rate*(1+rate)**nper/((1+rate)**nper - 1)
    """
    if rate == 0:
        return -pv / nper
    return -pv * rate * (1 + rate)**nper / ((1 + rate)**nper - 1)

def cal_loan_needs(df, interest_rate, term, grace, coef1, coef2):
    """
    Parameters:
      df: A DataFrame with a single row, columns are years (e.g., 2025, 2026, ...), values are amounts for each year
      interest_rate: Corresponds to C10 (interest rate)
      term: Corresponds to C12 (term), can be non-integer
      grace: Corresponds to C11 (grace period), can be non-integer
      coef1: Corresponds to C53
      coef2: Corresponds to C9

    Returns:
      A Series with years as index (sorted in ascending order), values as calculation results
    """
    # Calculate commonly used intermediate variables in the formula
    nper_total = term - grace + 1
    floor_term = math.floor(term)
    frac_term = term - floor_term
    floor_grace = math.floor(grace)
    ceil_grace = math.ceil(grace)
    frac_grace = grace - floor_grace

    # Assume df has only one row, extract the data (amounts)
    amounts = list(df.iloc[0])
    # Convert DataFrame column names (years) to a numeric list
    years = [float(col) for col in df.columns]

    # Store calculation results for each year
    results = {}

    for g in years:
        # ---------------------
        # First term: -PMT(interest_rate, nper_total, SUMIFS(...))
        # Condition: year is in [ g - floor_term + 1, g - ceil_grace ]
        L1 = g - floor_term + 1
        U1 = g - ceil_grace
        sum_val = sum(amt for yr, amt in zip(years, amounts) if L1 <= yr <= U1)
        try:
            term1 = -pmt(interest_rate, nper_total, sum_val)
        except Exception:
            term1 = 0

        # ---------------------
        # Second term: IFERROR(-PMT(interest_rate, nper_total, (XLOOKUP(...)* (term - floor_term))),0)
        # XLOOKUP search: key2 = g - ROUNDUP(term,0) + 1, which is g - math.ceil(term) + 1
        key2 = g - math.ceil(term) + 1
        if key2 in years:
            idx = years.index(key2)
            lookup_val = amounts.iloc[idx] if isinstance(amounts, pd.Series) else amounts[idx]
            pv2 = lookup_val * frac_term
            term2 = -pmt(interest_rate, nper_total, pv2)
        else:
            term2 = 0

        # ---------------------
        # Third term: IFERROR(-PMT(interest_rate, nper_total, (XLOOKUP(...)* (grace - floor_grace))),0)
        # XLOOKUP search: key3 = g - ROUNDDOWN(grace,0) = g - floor_grace
        key3 = g - floor_grace
        if key3 in years:
            idx = years.index(key3)
            lookup_val = amounts.iloc[idx] if isinstance(amounts, pd.Series) else amounts[idx]
            pv3 = lookup_val * frac_grace
            try:
                term3 = -pmt(interest_rate, nper_total, pv3)
            except Exception:
                term3 = 0
        else:
            term3 = 0

        # ---------------------
        # Fourth term:
        #   ( SUMIFS(amounts, condition: year > g - floor_grace and <= g)
        #     + IFERROR( SUMIF(year, ROUNDDOWN(g - grace,0) + 1, amount) * (1 - (grace - floor_grace)), 0)
        #   ) * interest_rate
        sum_val_4a = sum(amt for yr, amt in zip(years, amounts) if (yr > (g - floor_grace)) and (yr <= g))
        key4 = math.floor(abs(g - grace)) + 1
        if key4 in years:
            idx = years.index(key4)
            lookup_val4 = amounts.iloc[idx] if isinstance(amounts, pd.Series) else amounts[idx]
        else:
            lookup_val4 = 0
        term4 = (sum_val_4a + lookup_val4 * (1 - frac_grace)) * interest_rate

        # Add all terms together, then multiply by coef1 and coef2
        total = coef1 * coef2*(term1 + term2 + term3 + term4)
        results[g] = total

    # Convert to Series and return sorted by year
    result_series = pd.Series(results).sort_index()
    return result_series
    
def cal_equity_needs(df, interest_rate, term, grace, coef1, coef2):
    """
    Parameters:
      df: A DataFrame with a single row,
          column names are years (e.g., 2025, 2026, ...),
          corresponding values are amounts for each year,
          at the same time another row (or another source) provides year information (e.g., B70:AU70).
          For simplicity, assume df's column names are years (corresponding to B70:AU70),
          and df.iloc[0] is the amount data (corresponding to B107:AU107).
      interest_rate: Corresponds to D10 (interest rate)
      term: Corresponds to D12 (term), in the formula nper = term + 1
      coef1: Corresponds to C53
      coef2: Corresponds to D9

    Formula translation:
      = $C$53*$D$9*(
         IFERROR(-PMT(D10, term+1, SUMIFS(amount, year, ">" & (current_year - ROUNDDOWN(term,0)), year, "<=" & current_year)),0)
         +
         IFERROR(-PMT(D10, term+1, SUMIF(year, ROUNDDOWN(current_year-term,0)+1, amount) * (term-ROUNDDOWN(term,0))),0)
         )
    
    Returns:
      A Series with years as index, values as calculation results
    """
    nper = term + 1
    floor_term = math.floor(term)
    frac_term = term - floor_term

    # Assume df's column names are years, convert to float list
    years = [float(col) for col in df.columns]
    amounts = df.iloc[0]

    results = {}

    for current_year in years:
        # ---------------------
        # First part: SUMIFS part
        # Filter condition: year > (current_year - ROUNDDOWN(term,0)) and year <= current_year
        sumifs_val = sum(amt for yr, amt in zip(years, amounts)
                         if (yr > (current_year - floor_term)) and (yr <= current_year))
        try:
            term1 = -pmt(interest_rate, nper, sumifs_val)
        except Exception:
            term1 = 0

        # ---------------------
        # Second part: SUMIF part
        # Condition: year == ROUNDDOWN(current_year - term,0) + 1
        target_year = math.floor(current_year - term) + 1
        sumif_val = 0
        # Here we search by condition, and accumulate if there are multiple matches
        for yr, amt in zip(years, amounts):
            if yr == target_year:
                sumif_val += amt
        try:
            term2 = -pmt(interest_rate, nper, sumif_val * frac_term)
        except Exception:
            term2 = 0

        total = coef1 * coef2 * (term1 + term2)
        results[current_year] = total

    result_series = pd.Series(results).sort_index()
    return result_series

def cal_mirr(cash_flows, finance_rate, reinvest_rate):
    """
    Calculate MIRR (Modified Internal Rate of Return)
    
    :param cash_flows: List of cash flows (the list should include negative investments and positive returns)
    :param finance_rate: Financing rate (discount rate)
    :param reinvest_rate: Reinvestment rate
    :return: MIRR (Modified Internal Rate of Return)
    """
    n = len(cash_flows) - 1  # Calculate number of periods
    # print(cash_flows)
    # Calculate FV (Future Value): compound interest calculation of all positive cash flows
    FV_positive = sum(cash_flows[t] * (1 + reinvest_rate) ** (n - t)
                      for t in cash_flows.index if cash_flows[t] > 0)

    # Calculate PV (Present Value): discount all negative cash flows
    PV_negative = sum(cash_flows[t] / (1 + finance_rate) ** t
                      for t in cash_flows.index if cash_flows[t] < 0)

    # Calculate MIRR
    if PV_negative == 0:  # Avoid division by zero error
        return np.nan
    MIRR = (FV_positive / abs(PV_negative)) ** (1 / n) - 1
    return MIRR

def calc_donor_mirr(grant_amount, annual_cashflows, donor_discount_rate):
    """
    A function example to calculate Donor MIRR.
    
    Parameters:
    - grant_amount: 
    - annual_cashflows: A list (or array) of annual cash flows related to the Donor.
    - donor_discount_rate: Donor discount rate
    
    Returns:
    - MIRR for the donor
    """

    adjusted_cashflows = annual_cashflows.copy()
    adjusted_cashflows.iloc[0] += grant_amount 
    
    # an alternative is to use numpy_financial.mirr for MIRR (requires numpy-financial)
    # !pip install numpy-financial
    donor_mirr = cal_mirr(adjusted_cashflows, finance_rate=donor_discount_rate, reinvest_rate=donor_discount_rate)
       
    return donor_mirr

if __name__ == "__main__":
    data = {'2025': 1000, '2026': 1100, '2027': 1200, '2028': 1300, '2029': 1400, '2030': 1500}
    df_example = pd.DataFrame([data])
    
    interest_rate = 0.05  
    term = 10.5           
    grace = 3.2           
    coef1 = 1.1           
    coef2 = 0.9           