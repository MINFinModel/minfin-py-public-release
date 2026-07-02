import pandas as pd

from MinFin.funding_allocation import InvestmentAllocator, SourceConfig, TechnologyStats


def test_allocation_matrix_accepts_yearly_fx_series():
    columns = pd.MultiIndex.from_tuples(
        [
            ("Comm_Dom", "Financing Shares", "Share of Finance"),
            ("Comm_Dom", "Financing Shares", "Debt Share"),
            ("Comm_Dom", "Financing Shares", "Equity Share"),
            ("Comm_Dom", "Foreign Currency Shares", "Debt"),
            ("Comm_Dom", "Foreign Currency Shares", "Equity"),
        ],
        names=["Source", "Category", "Parameter"],
    )
    config = pd.DataFrame(
        [[1.0, 1.0, 0.0, 0.0, 0.0]],
        index=["Battery"],
        columns=columns,
    )
    allocator = InvestmentAllocator(config)
    tech = TechnologyStats(
        name="Battery",
        investment_needs=pd.Series([10.0, 20.0], index=[2025, 2032]),
        financing_configs={"Comm_Dom": SourceConfig()},
    )
    lc_rates = pd.Series([1.0, 3.0], index=[2025, 2032])
    fc_rates = pd.Series([1.0, 1.0], index=[2025, 2032])

    allocation = tech.get_allocation_matrix(
        allocator,
        lc_rate=lc_rates,
        fc_rate=fc_rates,
    )

    assert allocation.loc[2025, ("Local Currency", "Debt", "Comm_Dom")] == 10.0
    assert allocation.loc[2032, ("Local Currency", "Debt", "Comm_Dom")] == 60.0
    assert allocation.loc[2032, ("Foreign Currency", "Debt", "Comm_Dom")] == 0.0
