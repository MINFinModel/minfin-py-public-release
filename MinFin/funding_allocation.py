"""Investment allocation across financing sources (technology disag MultiIndex)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Union

import pandas as pd

from .definitions_io import Technology


class InvestmentAllocator:
    """Maps total investment to channels using technology_disag_s1-style MultiIndex columns."""

    def __init__(self, config_df: pd.DataFrame):
        self.config = config_df
        self.idx = pd.IndexSlice

    def allocate(
        self,
        tech_name: str,
        total_investment: pd.Series,
        source: str,
        instrument: str,
        is_local: bool,
        lc_rate: float,
        fc_rate: float,
    ) -> pd.Series:
        try:
            sof = self.config.loc[tech_name, self.idx[source, "Financing Shares", "Share of Finance"]]
            if instrument == "Debt":
                inst_share = self.config.loc[tech_name, self.idx[source, "Financing Shares", "Debt Share"]]
                fc_ratio = self.config.loc[tech_name, self.idx[source, "Foreign Currency Shares", "Debt"]]
            else:
                inst_share = self.config.loc[tech_name, self.idx[source, "Financing Shares", "Equity Share"]]
                fc_ratio = self.config.loc[tech_name, self.idx[source, "Foreign Currency Shares", "Equity"]]
            sof, inst_share, fc_ratio = [x if pd.notna(x) else 0 for x in [sof, inst_share, fc_ratio]]
            curr_share = (1 - fc_ratio) if is_local else fc_ratio
            if is_local:
                exchange_factor = lc_rate / fc_rate
            else:
                exchange_factor = fc_rate
            return total_investment * (sof * inst_share * curr_share) * exchange_factor
        except KeyError:
            return total_investment * 0


@dataclass
class SourceConfig:
    raw_data: Union[pd.Series, Dict] = field(default_factory=dict)
    fin_share: float = 0.0
    debt_share: float = 0.0
    interest_rate: float = 0.0
    grace_period: float = 0.0
    loan_term: float = 0.0
    rate_of_return: float = 0.0
    project_life: float = 0.0
    fc_debt_ratio: float = 0.0
    fc_equity_ratio: float = 0.0
    inv_fc_debt: pd.Series | None = None
    inv_fc_equity: pd.Series | None = None
    inv_lc_debt: pd.Series | None = None
    inv_lc_equity: pd.Series | None = None

    def __post_init__(self):
        mapping = {
            "fin_share": ("Financing Shares", "Share of Finance"),
            "debt_share": ("Financing Shares", "Debt Share"),
            "interest_rate": ("Debt", "Interest Rate"),
            "grace_period": ("Debt", "Grace Period"),
            "loan_term": ("Debt", "Loan Term"),
            "rate_of_return": ("Equity", "Rate of Return"),
            "project_life": ("Equity", "Project Life"),
            "fc_debt_ratio": ("Foreign Currency Shares", "Debt"),
            "fc_equity_ratio": ("Foreign Currency Shares", "Equity"),
        }
        for attr, key in mapping.items():
            val = self.raw_data.get(key, 0.0)
            setattr(self, attr, val if pd.notna(val) else 0.0)

    def __getitem__(self, key):
        return self.raw_data.get(key, 0.0)

    def get(self, key, default=0.0):
        return self.raw_data.get(key, default)


@dataclass
class TechnologyStats:
    name: str
    investment_needs: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    investment: Any = None  # optional dict from notebook workflow
    revenue: Dict[str, float] = field(default_factory=dict)
    opex: Dict[str, float] = field(default_factory=dict)
    tax: Dict[str, float] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    financing_configs: Dict[str, Any] = field(default_factory=dict)
    tech_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    @classmethod
    def from_technology(cls, tech: Technology, **kwargs):
        """Build stats using the Excel *Technology* code as *name* (notebook compatibility)."""
        return cls(name=tech.technology, **kwargs)

    def add_metric(self, key: str, value: Any):
        self.metrics[key] = value

    def add_financing_source(self, source_name, config_dict):
        self.financing_configs[source_name] = config_dict

    def get_allocation_matrix(
        self,
        allocator: InvestmentAllocator,
        lc_rate: float,
        fc_rate: float,
    ) -> pd.DataFrame:
        sources = allocator.config.columns.get_level_values("Source").unique()
        results = {}
        for loc_label, is_local in [("Local Currency", True), ("Foreign Currency", False)]:
            for inst in ["Debt", "Equity"]:
                for source in sources:
                    col_key = (loc_label, inst, source)
                    results[col_key] = allocator.allocate(
                        tech_name=self.name,
                        total_investment=self.investment_needs,
                        source=source,
                        instrument=inst,
                        is_local=is_local,
                        lc_rate=lc_rate,
                        fc_rate=fc_rate,
                    )
        df = pd.DataFrame(results)
        df.columns.names = ["Currency", "Instrument", "Source"]
        return df

    def apply_allocation(self, allocation_df: pd.DataFrame):
        sources = allocation_df.columns.get_level_values("Source").unique()
        for src in sources:
            config = self.financing_configs.get(src)
            if config:
                if isinstance(config, dict):
                    config = SourceConfig(raw_data=config)
                    self.financing_configs[src] = config
                config.inv_fc_debt = allocation_df.get(("Foreign Currency", "Debt", src), 0)
                config.inv_fc_equity = allocation_df.get(("Foreign Currency", "Equity", src), 0)
                config.inv_lc_debt = allocation_df.get(("Local Currency", "Debt", src), 0)
                config.inv_lc_equity = allocation_df.get(("Local Currency", "Equity", src), 0)
