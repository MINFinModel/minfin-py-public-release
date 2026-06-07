"""Market revenue split (PPA / end-user / wholesale) and Net Zero funding-sources chart."""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple, Union

import pandas as pd
import plotly.graph_objects as go

from MinFin.fx import fx_rate_lookup as fx_rate


def get_row_by_year(df: pd.DataFrame, year: int) -> pd.Series:
    """Return the row for *year*; index may be int or string."""
    y = year if year in df.index else str(year)
    return df.loc[y]


def split_market_revenue(
    df: pd.DataFrame,
    year: int,
    exchange_rates: Any,
) -> Tuple[float, float, float]:
    """
    Split market revenue for one technology-year into:
    PPA total, end-user tariff components, wholesale components.

    Uses the same building block as ``calc_sale_price``:
    ``whole_sale_generation * share * sale_price / FX`` per column pair.
    """
    try:
        row = get_row_by_year(df, year)
    except Exception:
        return 0.0, 0.0, 0.0

    whole_sale_generation = float(row.get("whole_sale_generation", 0) or 0)
    ppa_revenue = float(row.get("total_ppa_revenue", 0) or 0)

    enduser_rev = 0.0
    wholesale_rev = 0.0

    for col in row.index:
        if "_sale_price_" not in str(col):
            continue
        share_col = str(col).replace("_sale_price_", "_share_")
        if share_col not in row.index:
            continue

        share = float(row.get(share_col, 0) or 0)
        price = float(row.get(col, 0) or 0)
        currency = str(col).split("_")[-1]
        fx = fx_rate(currency, exchange_rates)
        component_revenue = whole_sale_generation * share * price / fx if fx else 0.0

        if str(col).startswith("wholesale_sale_price_"):
            wholesale_rev += component_revenue
        else:
            enduser_rev += component_revenue

    return ppa_revenue, enduser_rev, wholesale_rev


def aggregate_market_revenue_stacks(
    tech_dataframes: dict,
    years: Sequence[int],
    exchange_rates: Any,
) -> Tuple[List[float], List[float], List[float]]:
    """Sum *split_market_revenue* across all technologies for each year."""
    ppa: List[float] = []
    enduser: List[float] = []
    wholesale: List[float] = []
    for y in years:
        ppa_y = enduser_y = wholesale_y = 0.0
        for df in tech_dataframes.values():
            p, e, w = split_market_revenue(df, int(y), exchange_rates)
            ppa_y += p
            enduser_y += e
            wholesale_y += w
        ppa.append(ppa_y)
        enduser.append(enduser_y)
        wholesale.append(wholesale_y)
    return ppa, enduser, wholesale


def plot_net_zero_funding_sources_figure(
    years: Sequence[int],
    ppa: Sequence[float],
    enduser: Sequence[float],
    wholesale: Sequence[float],
    financing_requirement: Union[pd.Series, Sequence[float]],
    title: str = "Sources of Funding for the Net Zero Transition",
    width: int = 900,
    height: int = 560,
) -> go.Figure:
    """
    Stacked area (PPA / end-user / wholesale) plus financing requirement line.

    *financing_requirement* is aligned to *years* (Series reindexed or sequence).
    """
    if isinstance(financing_requirement, pd.Series):
        fr = financing_requirement.reindex(years).fillna(0)
        fr_vals = fr.tolist()
    else:
        fr_vals = list(financing_requirement)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(years),
            y=list(ppa),
            name="PPA Revenue",
            stackgroup="one",
            line=dict(width=0),
            fillcolor="#00b050",
            hovertemplate="%{x}<br>PPA Revenue: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(years),
            y=list(enduser),
            name="End-User Tariff Revenue",
            stackgroup="one",
            line=dict(width=0),
            fillcolor="#92d050",
            hovertemplate="%{x}<br>End-User Tariff Revenue: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(years),
            y=list(wholesale),
            name="Wholesale Market Revenue",
            stackgroup="one",
            line=dict(width=0),
            fillcolor="#548235",
            hovertemplate="%{x}<br>Wholesale Market Revenue: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(years),
            y=fr_vals,
            name="Financing Requirement",
            mode="lines",
            line=dict(color="red", width=4),
            hovertemplate="%{x}<br>Financing Requirement: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        template="plotly_white",
        width=width,
        height=height,
        xaxis=dict(title="Year", tickangle=-45),
        yaxis=dict(
            title="Million US$",
            showgrid=True,
            gridcolor="lightgray",
            rangemode="tozero",
        ),
        legend=dict(x=0.02, y=0.98),
        hovermode="x unified",
    )
    return fig
