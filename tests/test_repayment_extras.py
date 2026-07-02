import pandas as pd

from MinFin.funding_allocation import SourceConfig, TechnologyStats
from MinFin.repayment_extras import calculate_detailed_repayments


def test_local_currency_source_repayments_convert_to_dashboard_usd():
    config = SourceConfig()
    config.fin_share = 1.0
    config.interest_rate = 0.0
    config.grace_period = 0.0
    config.loan_term = 1.0
    config.rate_of_return = 0.0
    config.project_life = 1.0
    config.inv_fc_debt = pd.Series([0.0], index=[2032])
    config.inv_fc_equity = pd.Series([0.0], index=[2032])
    config.inv_lc_debt = pd.Series([60.0], index=[2032])
    config.inv_lc_equity = pd.Series([0.0], index=[2032])
    tech = TechnologyStats(
        name="Battery",
        financing_configs={"Comm_Dom": config},
    )
    exchange_rates = pd.DataFrame(
        {"USD": [1.0], "KES": [3.0]},
        index=[2032],
    )

    result = calculate_detailed_repayments(
        tech,
        exchange_rates,
        years=[2032],
        target_is_local=False,
        local_curr_code="KES",
    )

    assert result.loc["Loans (Comm_Dom)", 2032] == 20.0
