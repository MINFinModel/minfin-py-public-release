"""Detailed repayment and interest-cost calculations (extracted from minfin_notebook workflow)."""


import numpy as np
import pandas as pd
def _calc_debt_logic(inv_series, rate, term, grace, fin_share, years,interest_only=False):
    """
    Pixel-level match to the Excel debt formulas.
    inv_series: raw investment series (sourcefinFC).
    fin_share: financing share.
    """
    results = pd.Series(0.0, index=years)
    inv_map = inv_series.to_dict()
    repay_period = term - grace

    for curryear in years:
        # --- PART 1: Principal portion ---
        # Excel: SUMIFS(sourcefinFC, yearsarray, ">="&(curryear-ROUNDDOWN(term,0)+1), yearsarray, "<="&(curryear-ROUNDUP(grace,0)))
        f_term = int(np.floor(term))
        c_grace = int(np.ceil(grace))
        mask_body = (inv_series.index >= (curryear - f_term + 1)) & (inv_series.index <= (curryear - c_grace))
        sum_ifs_val = inv_series[mask_body].sum()
        
        # Adjustment 1 (end decimal): XLOOKUP(curryear-ROUNDUP(term)+1, ...) * (term-floor_term)
        c_term = int(np.ceil(term))
        p_end_val = inv_map.get(curryear - c_term + 1, 0.0) * (term - np.floor(term))
        
        # Adjustment 2 (grace decimal): XLOOKUP(curryear-floor_grace, ...) * (1-IF(frac==0,1,frac))
        f_grace = int(np.floor(grace))
        g_frac = grace - f_grace
        g_inner_if = g_frac if g_frac != 0 else 1.0
        p_grace_val = inv_map.get(curryear - f_grace, 0.0) * (1.0 - g_inner_if)
        
        # Total principal = fin_share * (body + adj1 + adj2) / repay_period
        # (Excel uses -PMT(0, term-grace, SUM), equivalent to SUM/repay_period here.)
        if repay_period != 0:
            total_p = (fin_share * (sum_ifs_val + p_end_val + p_grace_val)) / repay_period
        else:
            total_p = 0.0

        # --- PART 2: Interest portion ---
        # 1. Window total investment: SUMPRODUCT(sourcefinFC, yearsarray <= curryear, yearsarray >= curryear - term)
        mask_window = (inv_series.index <= curryear) & (inv_series.index >= (curryear - term))
        window_inv_sum = inv_series[mask_window].sum()
        
        # 2. Principal repaid in window: step logic grace+1, +2, +3 as in Excel
        # step = (curryear - inv_year) - grace
        total_repaid_in_window = 0.0
        for inv_y, val in inv_series[mask_window].items():
            step = (curryear - inv_y) - grace
            # Excel condition: step > 0 AND step <= repay_period
            if step > 0:
                repaid_units = min(step, repay_period)
                total_repaid_in_window += (val / repay_period) * repaid_units
        
        # Interest = fin_share * (window investment - principal repaid in window) * rate
        total_i = (fin_share * (window_inv_sum - total_repaid_in_window)) * rate

        if interest_only == True:
            results[curryear] = total_i
        # Total: principal + interest
        else:
            results[curryear] = total_p + total_i

    return results

def _calc_equity_logic(inv_series, eirr, life, years):
    """Mathematical engine for Equity (Dividends)"""
    flow = pd.Series(0.0, index=years)
    for curr_year in years:
        start_window = curr_year - np.floor(life)
        past_inv = inv_series[(years > start_window) & (years <= curr_year)]
        flow[curr_year] = past_inv.sum() * eirr
    return flow
def cal_interest_cost(tech_stats, er, years = list(range(2025,2071)),target_is_local=False, local_curr_code='GHS'):
    results = {}
    years = pd.Index(years)
    er = er.loc[min(years):]
    lc_rate, fc_rate = er[local_curr_code], er['USD']
    conv_fc_to_target = (lc_rate / fc_rate) if target_is_local else 1.0
    conv_lc_to_target = 1.0 if target_is_local else (fc_rate / lc_rate)
    # print("USD 2 GHS", conv_fc_to_target,"GHS 2 USD", conv_lc_to_target)
    for src, config in tech_stats.financing_configs.items():
        # Base financing parameters (rate, term, etc.)
        def get_cfg(metric, default=0):
            # Support plain and tuple-key dict layouts
            val = config.get(metric)
            if val is None:  # try tuple keys
                for k, v in config.items():
                    if isinstance(k, tuple) and metric in k: return v
            return val

        # Investment series from config
        # Loan repayment
        inv_fc_debt = config.inv_fc_debt
        inv_lc_debt = config.inv_lc_debt
        # print(inv_fc_debt)
        if (inv_fc_debt.sum() + inv_lc_debt.sum()) >=0:
            rate, term, grace,fin_share = config.interest_rate, config.loan_term, config.grace_period,config.fin_share
            # print( rate, term, grace )
            repay_fc = _calc_debt_logic(inv_fc_debt, rate, term, grace,fin_share, years,interest_only=True) * conv_fc_to_target
            repay_lc = _calc_debt_logic(inv_lc_debt, rate, term, grace,fin_share, years,interest_only=True) *conv_lc_to_target 
            results[f"Loans ({src})"] = (repay_fc + repay_lc).fillna(0)
    
    return pd.DataFrame(results).T.sum()
def calculate_detailed_repayments(tech_stats, er, years = list(range(2025,2071)),target_is_local=False, local_curr_code='GHS'):
    results = {}
    years = pd.Index(years)
    er = er.loc[min(years):]
    lc_rate, fc_rate = er[local_curr_code], er['USD']
    conv_fc_to_target = (lc_rate / fc_rate) if target_is_local else 1.0
    conv_lc_to_target = 1.0 if target_is_local else (fc_rate / lc_rate)
    # print("USD 2 GHS", conv_fc_to_target,"GHS 2 USD", conv_lc_to_target)
    for src, config in tech_stats.financing_configs.items():
        # Base financing parameters (rate, term, etc.)
        def get_cfg(metric, default=0):
            # Support plain and tuple-key dict layouts
            val = config.get(metric)
            if val is None:  # try tuple keys
                for k, v in config.items():
                    if isinstance(k, tuple) and metric in k: return v
            return val

        # Investment series from config
        # Loan repayment
        inv_fc_debt = config.inv_fc_debt
        inv_lc_debt = config.inv_lc_debt
        # print(inv_fc_debt)
        if (inv_fc_debt.sum() + inv_lc_debt.sum()) >=0:
            rate, term, grace,fin_share = config.interest_rate, config.loan_term, config.grace_period,config.fin_share
            # print( rate, term, grace )
            repay_fc = _calc_debt_logic(inv_fc_debt, rate, term, grace,fin_share, years) * conv_fc_to_target
            repay_lc = _calc_debt_logic(inv_lc_debt, rate, term, grace,fin_share, years) #*conv_lc_to_target
            results[f"Loans ({src})"] = (repay_fc + repay_lc).fillna(0)
            if config.loan_term == 0:# To match Excel, make it 0 when data of term is missing.
                results[f"Loans ({src})"] = pd.Series(0.0, index=years)
        # Equity dividends
        inv_fc_equity = config.inv_fc_equity
        inv_lc_equity = config.inv_lc_equity
        # print(src,inv_fc_equity,config.interest_rate)

        if (inv_fc_equity.sum() + inv_lc_equity.sum()) >= 0:
            eirr, life = config.rate_of_return, config.project_life
            
            return_fc = _calc_equity_logic(inv_fc_equity, eirr, life, years) * conv_fc_to_target
            return_lc = _calc_equity_logic(inv_lc_equity, eirr, life, years)# * conv_lc_to_target
            results[f"Equity ({src})"] = (return_fc + return_lc).fillna(0)

    return pd.DataFrame(results).T