import math
import pandas as pd

def pmt(rate, nper, pv):
    """
    模拟 Excel 中的 PMT 函数，不考虑末值和期初支付。
    如果 rate 为0，则返回 pv/nper，否则返回 pv * rate*(1+rate)**nper/((1+rate)**nper - 1)
    """
    if rate == 0:
        return -pv / nper
    return -pv * rate * (1 + rate)**nper / ((1 + rate)**nper - 1)

def cal_loan_needs(df, interest_rate, term, grace, coef1, coef2):
    """
    参数说明：
      df: 一个 DataFrame，假定只有一行，列名为年份（例如2025,2026, ...），行值为对应年份的金额
      interest_rate: 对应 C10（利率）
      term: 对应 C12（期限），可为非整数
      grace: 对应 C11（宽限期），可为非整数
      coef1: 对应 C53
      coef2: 对应 C9

    返回：
      一个 Series，索引为年份（按升序排列），值为公式计算结果
    """
    # 计算公式中常用的中间变量
    nper_total = term - grace + 1
    floor_term = math.floor(term)
    frac_term = term - floor_term
    floor_grace = math.floor(grace)
    ceil_grace = math.ceil(grace)
    frac_grace = grace - floor_grace

    # 假定 df 只有一行，取出该行数据（金额）
    amounts = list(df.iloc[0])
    # 将 DataFrame 的列名（年份）转换为数字列表
    years = [float(col) for col in df.columns]

    # 用来存放每个年份的计算结果
    results = {}

    for g in years:
        # ---------------------
        # 第一项：-PMT(interest_rate, nper_total, SUMIFS(...))
        # 条件为：年份在 [ g - floor_term + 1, g - ceil_grace ]
        L1 = g - floor_term + 1
        U1 = g - ceil_grace
        sum_val = sum(amt for yr, amt in zip(years, amounts) if L1 <= yr <= U1)
        try:
            term1 = -pmt(interest_rate, nper_total, sum_val)
        except Exception:
            term1 = 0

        # ---------------------
        # 第二项：IFERROR(-PMT(interest_rate, nper_total, (XLOOKUP(...)* (term - floor_term))),0)
        # XLOOKUP 查找：key2 = g - ROUNDUP(term,0) + 1，即 g - math.ceil(term) + 1
        key2 = g - math.ceil(term) + 1
        if key2 in years:
            idx = years.index(key2)
            lookup_val = amounts.iloc[idx] if isinstance(amounts, pd.Series) else amounts[idx]
            pv2 = lookup_val * frac_term
            term2 = -pmt(interest_rate, nper_total, pv2)
        else:
            term2 = 0

        # ---------------------
        # 第三项：IFERROR(-PMT(interest_rate, nper_total, (XLOOKUP(...)* (grace - floor_grace))),0)
        # XLOOKUP 查找：key3 = g - ROUNDDOWN(grace,0) = g - floor_grace
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
        # 第四项：
        #   ( SUMIFS(金额, 条件: 年份 > g - floor_grace 且 <= g)
        #     + IFERROR( SUMIF(年份, ROUNDDOWN(g - grace,0) + 1, 金额) * (1 - (grace - floor_grace)), 0)
        #   ) * interest_rate
        sum_val_4a = sum(amt for yr, amt in zip(years, amounts) if (yr > (g - floor_grace)) and (yr <= g))
        key4 = math.floor(abs(g - grace)) + 1
        if key4 in years:
            idx = years.index(key4)
            lookup_val4 = amounts.iloc[idx] if isinstance(amounts, pd.Series) else amounts[idx]
        else:
            lookup_val4 = 0
        term4 = (sum_val_4a + lookup_val4 * (1 - frac_grace)) * interest_rate

        # 将各项相加，再乘以 coef1 和 coef2
        total = coef1 * coef2*(term1 + term2 + term3 + term4)
        results[g] = total

    # 转换为 Series 并按年份排序返回
    result_series = pd.Series(results).sort_index()
    return result_series
    
def cal_equity_needs(df, interest_rate, term, grace, coef1, coef2):
    """
    参数说明：
      df: 一个 DataFrame，假定只有一行，
          列名为年份（例如：2025, 2026, ...），
          对应的数值为每年的金额，
          同时另一行（或另一来源）提供年份信息（例如 B70:AU70）。
          为简单起见，假设 df 的列名就是年份（对应 B70:AU70），
          且 df.iloc[0] 为金额数据（对应 B107:AU107）。
      interest_rate: 对应 D10（利率）
      term: 对应 D12（期限），公式中 nper = term + 1
      coef1: 对应 C53
      coef2: 对应 D9

    公式翻译：
      = $C$53*$D$9*(
         IFERROR(-PMT(D10, term+1, SUMIFS(金额, 年份, ">" & (当前年份 - ROUNDDOWN(term,0)), 年份, "<=" & 当前年份)),0)
         +
         IFERROR(-PMT(D10, term+1, SUMIF(年份, ROUNDDOWN(当前年份-term,0)+1, 金额) * (term-ROUNDDOWN(term,0))),0)
         )
    
    返回：
      一个 Series，索引为年份，值为计算结果
    """
    nper = term + 1
    floor_term = math.floor(term)
    frac_term = term - floor_term

    # 假设 df 的列名即为年份，转换成浮点数列表
    years = [float(col) for col in df.columns]
    amounts = df.iloc[0]

    results = {}

    for current_year in years:
        # ---------------------
        # 第一部分：SUMIFS 部分
        # 筛选条件：年份 > (当前年份 - ROUNDDOWN(term,0)) 且 年份 <= 当前年份
        sumifs_val = sum(amt for yr, amt in zip(years, amounts)
                         if (yr > (current_year - floor_term)) and (yr <= current_year))
        try:
            term1 = -pmt(interest_rate, nper, sumifs_val)
        except Exception:
            term1 = 0

        # ---------------------
        # 第二部分：SUMIF 部分
        # 条件：年份 == ROUNDDOWN(当前年份 - term,0) + 1
        target_year = math.floor(current_year - term) + 1
        sumif_val = 0
        # 这里我们按条件查找，如果有多个匹配则累加
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



# 示例：假设你有如下的 DataFrame（列名为年份）
if __name__ == "__main__":
    # 构造示例数据，年份从2025到2030，金额随机给出（请替换成实际数据）
    data = {'2025': 1000, '2026': 1100, '2027': 1200, '2028': 1300, '2029': 1400, '2030': 1500}
    df_example = pd.DataFrame([data])
    
    # 参数示例
    interest_rate = 0.05  # 比如 5%
    term = 10.5           # 期限 10.5 年
    grace = 3.2           # 宽限期 3.2 年
    coef1 = 1.1           # 系数 C53
    coef2 = 0.9           # 系数 C9