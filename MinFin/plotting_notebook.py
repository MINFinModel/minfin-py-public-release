"""Plotly / seaborn helpers used by the additional_input notebook workflow."""

from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns


def fmt_million_usd(x, pos):
    s = f"{abs(x):,.0f}"
    if x < 0:
        return f"(${s})"
    return f"${s}"


def plot_metric_time_series(
    df: pd.DataFrame,
    selected_rows: list,
    title: str,
    xlabel: str = "Year",
    ylabel: str = "Amount (Million USD)",
    legend_title: str = "Metric",
    fig_size: tuple = (8, 3),
):
    df_plot = df.loc[selected_rows].T.reset_index().rename(columns={"index": "Year"})
    df_long = df_plot.melt(id_vars="Year", var_name="Metric", value_name="Value")
    df_long["Year"] = df_long["Year"].astype(int)
    sns.set(style="whitegrid")
    plt.figure(figsize=fig_size)
    ax = sns.lineplot(data=df_long, x="Year", y="Value", hue="Metric", marker="o", linewidth=2)
    ax.set_title(title, fontsize=16)
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    plt.legend(title=legend_title, fontsize=12, title_fontsize=14)
    plt.show()


def plot_co2_emissions_scenarios(df_emissions: pd.DataFrame):
    df_plot = df_emissions.reset_index().rename(columns={"index": "Year"})
    df_long = df_plot.melt(id_vars="Year", var_name="Scenario", value_name="Emissions")
    df_long["Year"] = df_long["Year"].astype(int)
    fig = px.line(
        df_long,
        x="Year",
        y="Emissions",
        color="Scenario",
        title="Projected CO₂ Emissions by Scenario",
        labels={"Emissions": "Mt CO₂", "Year": "Year"},
    )
    fig.update_traces(selector=dict(name="Emissions Savings"), line=dict(dash="dash", color="gray", width=2))
    fig.update_traces(selector=dict(name="Least Cost"), line=dict(color="blue", width=2))
    fig.update_traces(selector=dict(name="Net Zero"), line=dict(color="orange", width=2))
    fig.update_layout(template="plotly_white")
    fig.show()


DEFAULT_STACK_COLOR_MAP = {
    "Government Budget": "#ecf0a2",
    "Cashflows": "#c4da4b",
    "Capital Injection": "#c4da4b",
    "Carbon Credits": "#008080",
}


def stacked_area_fig(
    df_stack_plot: pd.DataFrame,
    stacked_cols: list,
    width: int = 800,
    height: int = 600,
    color_map: Optional[dict] = None,
    title: str = "",
    line_plots: bool = True,
):
    color_map = color_map or DEFAULT_STACK_COLOR_MAP
    df_area = df_stack_plot.melt(
        id_vars="Year", value_vars=stacked_cols, var_name="Source", value_name="Value"
    )
    fig = px.area(
        df_area,
        x="Year",
        y="Value",
        color="Source",
        color_discrete_map=color_map,
        title=title,
        labels={"Value": "Million US$", "Year": "Year", "Source": ""},
        template="plotly_white",
    )
    if line_plots:
        fig.add_trace(
            go.Scatter(
                x=df_stack_plot["Year"],
                y=df_stack_plot["Financing Requirement"],
                mode="lines+markers",
                name="Financing Requirement",
                line=dict(color="red", width=2),
                marker=dict(color="red", size=5),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_stack_plot["Year"],
                y=df_stack_plot["Funding Availability"],
                mode="lines+markers",
                name="Funding Availability",
                line=dict(color="darkgreen", width=2),
                marker=dict(color="darkgreen", size=5),
            )
        )
    fig.update_layout(
        xaxis=dict(range=[2024, 2071], tickangle=-45),
        yaxis=dict(tickformat=",", title="Million US$"),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="center", x=0.2),
        width=width,
        height=height,
    )
    return fig


def plot_funding_shortfall_bar_interactive(
    df: pd.DataFrame,
    row_label: str = "Funding shortfall",
    title: str = "Projected Funding Shortfall in Absolute Terms",
):
    df_bar = df.loc[row_label, :].T.reset_index().rename(columns={"index": "Year", row_label: "Value"})
    data = {"Year": list(df_bar["Year"]), "Value": list(df_bar["Value"])}
    df_bar = pd.DataFrame(data)
    fig = px.bar(df_bar, x="Year", y="Value", title=title, labels={"Value": "Million US$", "Year": "Year"})
    fig.update_traces(marker_color="green")
    fig.update_layout(
        template="plotly_white",
        xaxis=dict(range=[df_bar["Year"].min(), df_bar["Year"].max()], title="Year"),
        yaxis=dict(title="Million US$"),
    )
    fig.show()


def single_bar_plot(
    df_plot: pd.DataFrame,
    x: str,
    y: str,
    color_map: dict,
    title: str = "",
    labels: str = "",
    width: int = 800,
    height: int = 600,
):
    del labels
    fig = px.bar(
        df_plot,
        x=x,
        y=y,
        color="Financier",
        orientation="h",
        barmode="stack",
        color_discrete_map=color_map,
        title=title,
    )
    if max(df_plot[x]) < 1:
        fig.update_layout(
            xaxis=dict(range=[0, 1], tickformat=".0%"),
            width=width,
            height=height,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        )
    else:
        fig.update_layout(
            width=width,
            height=height,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        )
    return fig


def plot_market_element_by_financier(
    df: pd.DataFrame,
    color_map: dict,
    title: str = "Market Elements of Finance for Energy Investments 2010-2024 by Financier",
):
    df_bar = pd.DataFrame({"Financier": list(df.index), "Value": list(df["Market Element"])})
    fig = px.bar(
        df_bar,
        x="Financier",
        y="Value",
        title=title,
        color="Financier",
        color_discrete_map=color_map,
        category_orders={"Financier": list(color_map.keys())},
        labels={"Value": "Million US$", "Financier": "Financier"},
    )
    fig.update_layout(template="plotly_white", yaxis=dict(title="Million US$"))
    return fig


def debt_equity_plot(df: pd.DataFrame, title: str, width: int = 800, height: int = 600):
    df_melted = df.melt(
        id_vars=["Financier"], value_vars=["Debt Share", "Equity Share"], var_name="Type", value_name="Share"
    )
    fig = px.bar(
        df_melted,
        x="Share",
        y="Financier",
        color="Type",
        orientation="h",
        title=title,
        color_discrete_map={"Debt Share": "#ffc000", "Equity Share": "#2f5597"},
    )
    fig.update_layout(
        xaxis_title="Percentage",
        yaxis_title="",
        xaxis=dict(tickformat=".0%", showgrid=True),
        barmode="stack",
        legend_title_text="",
        width=width,
        height=height,
    )
    return fig


COL_INCREASE = "#b8e6b8"
COL_DECREASE = "#f5b8c8"
COL_TOTAL_CASH = "#2ca02c"
CONNECTOR = dict(line=dict(color="rgba(0,0,0,0.45)", width=1))


def get_year_row_for_waterfall(df: pd.DataFrame, year: int) -> pd.Series:
    """Return one row for *year*; index may be int or string."""
    idx = df.index
    if year not in idx and str(year) in idx:
        year = str(year)
    return df.loc[year]


def plot_technology_cashflow_waterfall(
    tech_name: str,
    year: int,
    tech_dataframes: dict,
    financing_requirement_by_tech: dict,
    existing_financing_repayment=None,
    width: int = 900,
    height: int = 560,
):
    """Waterfall chart for one technology and year (operating items through financing)."""
    df = tech_dataframes[tech_name]
    row = get_year_row_for_waterfall(df, int(year))

    revenue = float(row.get("total_ppa_revenue", 0) + row.get("total_wholesale_revnue", 0))
    receivables = float(row.get("receivables", 0))
    elec_cost = -float(row.get("power_purchase_cost", 0))
    corp_tax = -float(row.get("corporate_tax_expenses", 0))
    opex = -float(row.get("opex", 0))

    fr = financing_requirement_by_tech[tech_name]
    ycol = year if year in fr.columns else str(year)
    fin_req = float(fr.loc["Financing Requirement", ycol])

    idx = list(fr.index)
    loan_rows = [r for r in idx if str(r).startswith("Loans")]
    equity_rows = [r for r in idx if str(r).startswith("Equity")]
    loans_sum = float(fr.loc[loan_rows, ycol].sum()) if loan_rows else 0.0
    equity_sum = float(fr.loc[equity_rows, ycol].sum()) if equity_rows else 0.0

    if existing_financing_repayment is None:
        existing_financing_repayment = 0.0
    existing = -float(existing_financing_repayment)
    liabilities = -float(row.get("liabilities", 0))

    x_labels = [
        "Revenue",
        "Receivables",
        "Electricity Purchase Cost",
        "Corporate Tax Expense",
        "OPEX",
        "Cashflows",
        "Financing Requirement",
        "Loans",
        "Equity",
        "Existing Financing",
        "Liabilities",
    ]
    measure = [
        "absolute",
        "relative",
        "relative",
        "relative",
        "relative",
        "total",
        "total",
        "relative",
        "relative",
        "relative",
        "relative",
    ]
    cashflows_total = revenue + receivables + elec_cost + corp_tax + opex
    y = [
        revenue,
        receivables,
        elec_cost,
        corp_tax,
        opex,
        cashflows_total,
        fin_req,
        -loans_sum,
        -equity_sum,
        existing,
        liabilities,
    ]
    text = []
    for m, v in zip(measure, y):
        if m == "total":
            text.append(f"${v:,.0f}")
        else:
            text.append(f"${v:+,.0f}" if v != 0 else "$0")

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measure,
            x=x_labels,
            textposition="outside",
            text=text,
            y=y,
            connector=CONNECTOR,
            increasing={"marker": {"color": COL_INCREASE}},
            decreasing={"marker": {"color": COL_DECREASE}},
            totals={"marker": {"color": COL_TOTAL_CASH}},
        )
    )
    fig.update_layout(
        title=f"Technology Cashflow — {tech_name} ({year})",
        template="plotly_white",
        width=width,
        height=height,
        showlegend=False,
        yaxis=dict(title="Million US$", showgrid=True, gridcolor="lightgray", zeroline=True),
        xaxis=dict(tickangle=-35, title=""),
        plot_bgcolor="white",
    )
    return fig
