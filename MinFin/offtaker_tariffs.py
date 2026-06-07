"""Offtaker, tariff, and generation-purchase utilities (extracted from minfin_notebook workflow)."""

import numpy as np
import pandas as pd

from MinFin.fx import fx_to_dashboard_currency as _get_fx_to_dash

# ---------------------------------------------------------------------------
# 1. Segment classification constants and helpers
# ---------------------------------------------------------------------------

SEGMENT_MAP = {
    "Generation": 1,
    "Transmission": 2,
    "Distribution": 3,
    "Export": 4,
    "Exports": 4,
}

UPSTREAM_CATEGORY_BY_NUM = {
    1: "Generation",
    2: "Transmission",
    3: "Distribution",
    4: "Exports",
}


def _classify_segment(text) -> int:
    """Map Classification or Category text to a segment number (Generation=1, Trans=2, Dist=3, Export=4)."""
    if pd.isna(text) or not str(text).strip():
        return 0
    s = str(text).strip().lower()
    if "generation" in s and "export" not in s:
        return 1
    if "transmission" in s:
        return 2
    if "distribution" in s:
        return 3
    if "export" in s:
        return 4
    return 0


def _get_tech_class(tech_name: str, df_technologies: pd.DataFrame) -> str:
    """Return the technology's Classification from ``df_technologies``."""
    row = df_technologies[df_technologies["Technology"] == tech_name]
    if row.empty:
        return ""
    return row["Classification"].values[0]


def _get_offtaker_share_columns(
    tech_name: str,
    upstream_category: str,
    organized_offtaker: pd.DataFrame,
    tech_dataframes: dict,
) -> list:
    """
    From ``organized_offtaker`` and the current tech's columns, return
    ``[(offtaker_name, share_col_name), ...]``.
    ``upstream_category``: upstream segment name, e.g. ``"Generation"``.
    """
    mask = (
        organized_offtaker["Category"].str.strip().str.lower() == upstream_category.lower()
    ) & (
        organized_offtaker["Name"].str.strip().str.lower() != "exported from:"
    )
    offtakers = organized_offtaker.loc[mask, ["Name", "Currency"]].drop_duplicates()

    df = tech_dataframes.get(tech_name)
    if df is None:
        return []

    out = []
    for _, row in offtakers.iterrows():
        name, curr = row["Name"], row["Currency"]
        base = (
            str(name)
            .lower()
            .replace(" ", "_")
            .replace(":", "")
            .replace("-", "_")
        )
        share_col = f"{base}_share_{curr}"
        if share_col in df.columns:
            out.append((name, share_col))
    return out

def _get_export_techs(tech_dataframes: dict, df_technologies: pd.DataFrame) -> list:
    """Technology names whose Classification is Exports (for ExportGen)."""
    return [
        t for t in tech_dataframes
        if _classify_segment(_get_tech_class(t, df_technologies)) == 4
    ]
    
def _compute_export_gen(
    export_techs: list,
    df_generation_tech_sums: pd.DataFrame,
    year: int,
) -> float:
    """ExportGen: sum of generation over export technologies (PJ → GWh)."""
    total = 0.0
    for t in export_techs:
        if t in df_generation_tech_sums.columns and year in df_generation_tech_sums.index:
            total += df_generation_tech_sums.loc[year, t]
    return total * 1000 / 3.6


# ---------------------------------------------------------------------------
# 2. Main path: single-year Generation Purchased (offtaker-weighted)
# ---------------------------------------------------------------------------


def _slug(name):
    return str(name).lower().replace(" ", "_").replace(":", "").replace("-", "_")


def _empty_result(return_breakdown):
    if return_breakdown:
        return 0.0, 0.0, {}
    return 0.0, 0.0


def _upstream_totals(upstream_techs, tech_dataframes, year):
    """Upstream totals: (total_wholesale, total_ppa)."""
    tw, tp = 0.0, 0.0
    for t in upstream_techs:
        if year not in tech_dataframes[t].index:
            continue
        td = tech_dataframes[t]
        tw += td.loc[year, "whole_sale_generation"]
        tp += td.loc[year, "ppa_met_generation"] * td.loc[year, "ppa_standard_offtaker_share"]
    return tw, tp


def _weighted_components(tech_df, year, offtaker_share_pairs, total_wholesale, total_ppa):
    """(wholesale_component, ppa_component, breakdown_wholesale, breakdown_ppa)."""
    if not offtaker_share_pairs:
        return total_wholesale, total_ppa, {"(no shares)": total_wholesale}, {"(no shares)": total_ppa}
    wc, pc, bw, bp = 0.0, 0.0, {}, {}
    for name, share_col in offtaker_share_pairs:
        s = float(tech_df.loc[year, share_col]) if share_col in tech_df.columns else 0.0
        w = s * total_wholesale
        p = s * total_ppa
        wc += w
        pc += p
        bw[name], bp[name] = w, p
    return wc, pc, bw, bp


def _get_offtaker_tariff_columns(tech_name, upstream_category, organized_offtaker, tech_dataframes):
    mask = (organized_offtaker["Category"].str.strip().str.lower() == upstream_category.lower()) & (organized_offtaker["Name"].str.strip().str.lower() != "exported from:")
    offtakers = organized_offtaker.loc[mask, ["Name", "Currency"]].drop_duplicates()
    df = tech_dataframes.get(tech_name)
    if df is None:
        return []
    return [
        (r["Name"], f"{_slug(r['Name'])}_share_{r['Currency']}", f"{_slug(r['Name'])}_sale_price_{r['Currency']}", r["Currency"])
        for _, r in offtakers.iterrows()
        if f"{_slug(r['Name'])}_share_{r['Currency']}" in df.columns and f"{_slug(r['Name'])}_sale_price_{r['Currency']}" in df.columns
    ]


def _average_tariff(tech_name, tech_df, year, upstream_techs, upstream_category,
                    total_upstream_wholesale, wholesale_component, ppa_component,
                    tech_dataframes, organized_offtaker, exchange_rates, dash_curr):
    denom = wholesale_component + ppa_component
    if denom <= 0:# or exchange_rates is None or dash_curr is None:
        return 0.0

    num_total = 0.0
    
    # 1) Wholesale leg: if offtaker tariff columns exist, use buyer share × tariff × FX
    offtaker_pairs = _get_offtaker_tariff_columns(tech_name, upstream_category, organized_offtaker, tech_dataframes)
    if offtaker_pairs:
        num_wholesale = total_upstream_wholesale * sum(
            (float(tech_df.loc[year, sc]) if sc in tech_df.columns else 0.0)
            * (float(tech_df.loc[year, tc]) if tc in tech_df.columns else 0.0)
            * _get_fx_to_dash(curr, year, dash_curr, exchange_rates)
            for _, sc, tc, curr in offtaker_pairs
        )
    else:
        # 2) Fallback: upstream tech sale_price × whole_sale_generation
        num_wholesale = 0.0
        for t in upstream_techs:
            if year not in tech_dataframes[t].index:
                continue
            td = tech_dataframes[t]
            gwh = td.loc[year, "whole_sale_generation"]
            price = td.loc[year, "sale_price"] if "sale_price" in td.columns else 0.0
            curr = str(td.loc[year, "ppa_currency"]) if "ppa_currency" in td.columns else "USD"
            fx = _get_fx_to_dash(curr, year, dash_curr, exchange_rates)
            num_wholesale += gwh * price * fx

    # 3) PPA leg: upstream ppa_met × ppa_standard_offtaker_share × ppa_standard_tariff × FX
    num_ppa = 0.0
    for t in upstream_techs:
        if year not in tech_dataframes[t].index:
            continue
        td = tech_dataframes[t]
        g = td.loc[year, "ppa_met_generation"]
        sh = td.loc[year, "ppa_standard_offtaker_share"]
        price = td.loc[year, "ppa_standard_tariff"]
        curr = str(td.loc[year, "ppa_currency"]) if "ppa_currency" in td.columns else "USD"
        fx = _get_fx_to_dash(curr, year, dash_curr, exchange_rates)
        num_ppa += g * sh * price * fx

    return (num_wholesale + num_ppa) / denom


def compute_generation_purchased(
    tech_name: str,
    year: int,
    tech_dataframes: dict,
    df_generation_tech_sums: pd.DataFrame,
    df_technologies: pd.DataFrame,
    organized_offtaker: pd.DataFrame,
    export_source: str = "Generation",
    return_breakdown: bool = False,
    exchange_rates: pd.DataFrame = None,
    dash_curr: str = "USD",
):
    """GenePurchase (GWh/year) and AverageTariff; returns (gp, tariff) or (gp, tariff, breakdown)."""
    tech_class_num = _classify_segment(_get_tech_class(tech_name, df_technologies))
    upstream_num = tech_class_num - 1
    if upstream_num < 1:
        return _empty_result(return_breakdown)

    upstream_techs = [t for t in tech_dataframes if _classify_segment(_get_tech_class(t, df_technologies)) == upstream_num]
    tech_df = tech_dataframes.get(tech_name)
    if not upstream_techs or tech_df is None:
        return _empty_result(return_breakdown)

    export_techs = _get_export_techs(tech_dataframes, df_technologies)
    if tech_class_num == 4:
        val = _compute_export_gen(export_techs, df_generation_tech_sums, year)
        if return_breakdown:
            return val, 0.0, {"ExportGen": val, "average_tariff": 0.0}
        return val, 0.0

    upstream_category = UPSTREAM_CATEGORY_BY_NUM.get(upstream_num, "")
    offtaker_share_pairs = _get_offtaker_share_columns(tech_name, upstream_category, organized_offtaker, tech_dataframes)
    total_wholesale, total_ppa = _upstream_totals(upstream_techs, tech_dataframes, year)
    wholesale_component, ppa_component, bw, bp = _weighted_components(tech_df, year, offtaker_share_pairs, total_wholesale, total_ppa)

    export_deduction = _compute_export_gen(export_techs, df_generation_tech_sums, year) if tech_class_num == _classify_segment(export_source) + 1 else 0.0
    gene_purchase = wholesale_component + ppa_component - export_deduction
    average_tariff = _average_tariff(tech_name,tech_df, year, upstream_techs, upstream_category, total_wholesale, wholesale_component, ppa_component, tech_dataframes, organized_offtaker, exchange_rates, dash_curr)

    if return_breakdown:
        return gene_purchase, average_tariff, {"wholesale": wholesale_component, "ppa": ppa_component, "export_deduction": export_deduction, "by_offtaker_wholesale": bw, "by_offtaker_ppa": bp, "average_tariff": average_tariff}
    return gene_purchase, average_tariff

def compute_capacity_purchased_and_avg_fee(
    tech_name: str,
    year: int,
    tech_dataframes: dict,
    df_technologies: pd.DataFrame,
    exchange_rates: pd.DataFrame = None,
    dash_curr: str = None,
    cap_gwh_col: str = "ppa_contracted_capacity",
    cap_fee_col: str = "ppa_capacity_fee",
    ppa_currency_col: str = "ppa_currency",
) -> tuple:
    """
    Excel-aligned: returns
    1) Total capacity purchased CapGWh = SUM(OfftakerCheck * CapGWhArray)
    2) Average capacity fee (capacity-weighted, in dashboard currency) =
       SUM(OfftakerCheck * CapFee * CapGWh * PPAFX) / SUM(OfftakerCheck * CapGWh)
    For Exports, capacity purchased and average fee are both 0.
    """
    tech_class_num = _classify_segment(_get_tech_class(tech_name, df_technologies))
    if tech_class_num == 4:
        return 0.0, 0.0
    upstream_num = tech_class_num - 1
    if upstream_num < 1:
        return 0.0, 0.0

    def _fx(currency):
        if exchange_rates is None or dash_curr is None or currency not in exchange_rates.columns or dash_curr not in exchange_rates.columns or year not in exchange_rates.index:
            return 1.0
        rx = float(exchange_rates.loc[year, currency])
        rd = float(exchange_rates.loc[year, dash_curr])
        return rd / rx if rx else 0.0

    sum_cap_gwh = 0.0
    sum_fee_times_cap = 0.0

    for t in tech_dataframes:
        if _classify_segment(_get_tech_class(t, df_technologies)) != upstream_num:
            continue
        df = tech_dataframes[t]
        if year not in df.index:
            continue
        if cap_gwh_col not in df.columns or cap_fee_col not in df.columns:
            continue
        gwh = float(df.loc[year, cap_gwh_col])
        fee = float(df.loc[year, cap_fee_col])
        curr = str(df.loc[year, ppa_currency_col]) if ppa_currency_col in df.columns else "USD"
        fx = _fx(curr)
        sum_cap_gwh += gwh
        sum_fee_times_cap += fee * gwh * fx

    if sum_cap_gwh <= 0:
        return sum_cap_gwh, 0.0
    avg_fee = sum_fee_times_cap / sum_cap_gwh
    return sum_cap_gwh, avg_fee

# ---------------------------------------------------------------------------
# 3. Year-indexed series
# ---------------------------------------------------------------------------


def compute_generation_purchased_series(
    tech_name: str,
    tech_dataframes: dict,
    df_generation_tech_sums: pd.DataFrame,
    df_technologies: pd.DataFrame,
    organized_offtaker: pd.DataFrame,
    years: list = None,
    export_source: str = "Generation",
    return_breakdown: bool = False,
    exchange_rates: pd.DataFrame = None,
    dash_curr: str = None,
):
    """Per-year Generation Purchased and AverageTariff series."""
    if years is None:
        years = tech_dataframes[tech_name].index.astype(int).tolist() if tech_name in tech_dataframes else []

    gp_list, tariff_list = [], []
    breakdowns = [] if return_breakdown else None

    for y in years:
        res = compute_generation_purchased(
            tech_name, y,
            tech_dataframes, df_generation_tech_sums, df_technologies, organized_offtaker,
            export_source=export_source,
            return_breakdown=return_breakdown,
            exchange_rates=exchange_rates,
            dash_curr=dash_curr,
        )
        if return_breakdown:
            gp_list.append(res[0])
            tariff_list.append(res[1])
            breakdowns.append(res[2])
        else:
            gp_list.append(res[0])
            tariff_list.append(res[1])

    gp_series = pd.Series(gp_list, index=years)
    tariff_series = pd.Series(tariff_list, index=years)

    if return_breakdown:
        return gp_series, tariff_series, breakdowns
    return gp_series, tariff_series

def compute_capacity_purchased_series(
    tech_name: str,
    tech_dataframes: dict,
    df_technologies: pd.DataFrame,
    years: list = None,
    exchange_rates: pd.DataFrame = None,
    dash_curr: str = None,
    cap_gwh_col: str = "ppa_contracted_capacity",
    cap_fee_col: str = "ppa_capacity_fee",
    ppa_currency_col: str = "ppa_currency",
) -> tuple:
    """Return (capacity_purchased_series, average_capacity_fee_series)."""
    if years is None:
        years = tech_dataframes[tech_name].index.astype(int).tolist() if tech_name in tech_dataframes else []
    cap_list, fee_list = [], []
    for y in years:
        c, f = compute_capacity_purchased_and_avg_fee(
            tech_name, y, tech_dataframes, df_technologies,
            exchange_rates, dash_curr, cap_gwh_col, cap_fee_col, ppa_currency_col,
        )
        cap_list.append(c)
        fee_list.append(f)
    return pd.Series(cap_list, index=years), pd.Series(fee_list, index=years)


def calc_sale_price(df: pd.DataFrame, er: pd.DataFrame) -> pd.Series:
    """Weighted sale price from ``*_sale_price_*`` and ``*_share_*`` columns and exchange *er*."""
    price_cols = [c for c in df.columns if "_sale_price_" in c]
    parts = {}
    for p in price_cols:
        share = p.replace("_sale_price_", "_share_")
        if share in df.columns:
            curr = p.split("_")[-1]
            parts[p] = df[p] * df[share] / er[curr]
    if not parts:
        return pd.Series(0.0, index=df.index)
    return pd.DataFrame(parts).sum(axis=1).fillna(0)


def flatten_multiindex_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns to single snake_case strings."""
    df = df.copy()
    df.columns = [
        "_".join([str(level).lower() for level in col if str(level)]).replace(" ", "_")
        if isinstance(col, tuple)
        else str(col)
        for col in df.columns.values
    ]
    return df