"""Smoke tests: new notebook-extracted modules import without side effects."""


def test_additional_workflow_modules_import():
    from MinFin.definitions_io import Technology, load_technologies_from_dataframe
    from MinFin.disag_tables import build_disag_table, DisagLookupConfig
    from MinFin.funding_allocation import InvestmentAllocator, TechnologyStats
    from MinFin.investment_needs_extra import filter_data, cal_weighted_avg
    from MinFin.market_revenue import aggregate_market_revenue_stacks, split_market_revenue
    from MinFin.high_level_dashboard import hd, high_level_dashboard
    from MinFin.notebook_dashboard import NotebookHighLevelDashboard
    from MinFin.plotting_notebook import stacked_area_fig, plot_technology_cashflow_waterfall
    from MinFin.repayment_extras import _calc_debt_logic
    from MinFin.technology_sheet_io import TECH_START_ROWS, extract_tech_data_relative

    assert TECH_START_ROWS["Biomass"] == 83
    assert hd is high_level_dashboard
    assert NotebookHighLevelDashboard is high_level_dashboard
    assert callable(extract_tech_data_relative)
    assert callable(_calc_debt_logic)
    assert callable(load_technologies_from_dataframe)
    assert callable(build_disag_table)
    assert DisagLookupConfig().scenario == "S1"
    assert callable(cal_weighted_avg)
    assert callable(stacked_area_fig)
    assert callable(plot_technology_cashflow_waterfall)
    assert callable(split_market_revenue)
    assert callable(aggregate_market_revenue_stacks)
