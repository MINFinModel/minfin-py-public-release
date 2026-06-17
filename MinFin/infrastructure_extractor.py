"""Legacy and pure-input infrastructure / OSeMOSYS block extraction."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from MinFin.excel_io import read_investment_plan_long, year_columns_from_dataframe
from MinFin.pure_input_blocks import (
    build_input_blocks_from_pure_input_file,
    pure_input_other_input_series,
)
from MinFin.workbook_format import (
    WORKBOOK_FORMAT_LEGACY,
    WORKBOOK_FORMAT_PURE_INPUT,
    normalize_workbook_format,
)


class input_extractor:
    def __init__(
        self,
        scenario,
        workbook_format: str = WORKBOOK_FORMAT_LEGACY,
        file_path: Optional[str] = None,
    ) -> None:
        self.scenario = scenario
        self.workbook_format = normalize_workbook_format(workbook_format)
        self.file_path = file_path
        if self.workbook_format == WORKBOOK_FORMAT_PURE_INPUT and not file_path:
            raise ValueError(
                "file_path is required when workbook_format is 'pure_input' (or alias 'python')"
            )
        self.starting_rows = {"net_zero": 137, "least_cost": 137}
        self.starting_cols = {
            "least_cost": {"variable_cost": 4, "fixed_cost": 6, "co2_emission": 18}
        }
        self.starting_cols["net_zero"] = {
            key: value - 1 for key, value in self.starting_cols["least_cost"].items()
        }
        self.starting_cols[scenario]["carbon_price"] = 16
        self.starting_cols[scenario]["carbon_credit_price"] = 20

    def get_other_inputs(self, name_of_input, df_input_full):
        if self.workbook_format == WORKBOOK_FORMAT_PURE_INPUT:
            if not self.file_path:
                raise ValueError("file_path is required for pure-input workbook get_other_inputs")
            df = read_investment_plan_long(self.file_path)
            yc = year_columns_from_dataframe(df)[:46]
            if name_of_input in ["year", "years", "y"]:
                return pd.DataFrame({0: [int(float(c)) for c in yc]})
            o = pure_input_other_input_series(self.file_path, self.scenario, yc, n_years=46)
            return pd.DataFrame({0: o[name_of_input]})

        starting_row = self.starting_rows[self.scenario]
        starting_col = self.starting_cols[self.scenario]
        if name_of_input in ["year", "years", "y"]:
            return df_input_full.iloc[starting_row : starting_row + 46, 0:1]
        input_df = df_input_full.iloc[
            starting_row : starting_row + 46,
            starting_col[name_of_input] : starting_col[name_of_input] + 1,
        ]
        input_df.fillna(0, inplace=True)
        input_df.reset_index(drop=True, inplace=True)
        return input_df

    @staticmethod
    def filter_valid_cols(df, header_row):
        header_row = header_row.apply(
            lambda x: (
                np.nan
                if isinstance(x, str) and not x.strip()
                else x.strip() if isinstance(x, str) else x
            )
        )
        num_named_cols = header_row.notna().sum()
        df = df.iloc[:, :num_named_cols]
        df.columns = list(header_row.iloc[:num_named_cols])
        df.reset_index(drop=True, inplace=True)
        return df

    @staticmethod
    def _build_cost_df(df_input_full, starting_row, col_start, col_end, df_year, n_rows=56):
        df = df_input_full.iloc[starting_row : starting_row + n_rows, col_start:col_end]
        header_row = df_input_full.iloc[starting_row - 1, col_start:col_end]
        df = input_extractor.filter_valid_cols(df, header_row)
        df = df.fillna(0)
        df = pd.concat([df_year, df], axis=1)
        total_row = pd.DataFrame(df.iloc[:, 1:].sum()).T
        total_row.insert(0, "Year", "Total")
        return pd.concat([df, total_row], ignore_index=True)

    @staticmethod
    def _build_input_blocks(
        scenario,
        df_input_full,
        workbook_format: str = WORKBOOK_FORMAT_LEGACY,
        file_path: Optional[str] = None,
    ):
        workbook_format = normalize_workbook_format(workbook_format)
        if workbook_format == WORKBOOK_FORMAT_PURE_INPUT:
            if not file_path:
                raise ValueError("file_path is required to load blocks from a pure-input workbook")
            return build_input_blocks_from_pure_input_file(scenario, file_path)
        starting_rows = {"net_zero": 9, "least_cost": 73}
        starting_row = starting_rows[scenario]
        n_rows = 56
        df_year = (
            df_input_full.iloc[starting_row : starting_row + n_rows, 0]
            .reset_index(drop=True)
            .to_frame(name="Year")
        )
        capital_start_col = 1
        capital_end_col = 51
        ffe_start_col = capital_end_col + 1
        ffe_end_col = ffe_start_col + 20
        elec_production_start_col = ffe_end_col + 2
        elec_production_end_col = elec_production_start_col + 50
        op_start_col = elec_production_end_col + 1
        op_end_col = op_start_col + 50
        potential_generation_start_col = op_end_col + 1
        potential_generation_end_col = potential_generation_start_col + 50
        block_specs = {
            "capital_cost": (capital_start_col, capital_end_col),
            "ffe": (ffe_start_col, ffe_end_col),
            "elec_production": (elec_production_start_col, elec_production_end_col),
            "opex": (op_start_col, op_end_col),
            "potential_generation": (potential_generation_start_col, potential_generation_end_col),
        }
        blocks = {}
        for name, (col_start, col_end) in block_specs.items():
            blocks[name] = input_extractor._build_cost_df(
                df_input_full, starting_row, col_start, col_end, df_year, n_rows=n_rows
            )
        return blocks

    @staticmethod
    def load_block_for(
        scenario,
        df_input_full,
        block_name,
        workbook_format: str = WORKBOOK_FORMAT_LEGACY,
        file_path: Optional[str] = None,
    ):
        blocks = input_extractor._build_input_blocks(
            scenario, df_input_full, workbook_format, file_path
        )
        return blocks[block_name]

    @staticmethod
    def load_all_blocks_for(
        scenario,
        df_input_full,
        workbook_format: str = WORKBOOK_FORMAT_LEGACY,
        file_path: Optional[str] = None,
    ):
        return input_extractor._build_input_blocks(
            scenario, df_input_full, workbook_format, file_path
        )

    @staticmethod
    def load_all_for(
        scenario,
        df_input_full,
        workbook_format: str = WORKBOOK_FORMAT_LEGACY,
        file_path: Optional[str] = None,
    ):
        blocks = input_extractor.load_all_blocks_for(
            scenario, df_input_full, workbook_format, file_path
        )
        return (
            blocks["capital_cost"],
            blocks["ffe"],
            blocks["elec_production"],
            blocks["opex"],
            blocks["potential_generation"],
        )

    @staticmethod
    def load_osemosys_input(
        scenario,
        df_input_full,
        workbook_format: str = WORKBOOK_FORMAT_LEGACY,
        file_path: Optional[str] = None,
    ):
        blocks = input_extractor.load_all_blocks_for(
            scenario, df_input_full, workbook_format, file_path
        )
        for k, v in blocks.items():
            if "Year" in v.columns:
                blocks[k] = v.set_index("Year")
        return blocks["capital_cost"], blocks["ffe"], blocks["elec_production"]

    def load(self, df_input_full, block_name):
        blocks = input_extractor._build_input_blocks(
            self.scenario,
            df_input_full,
            self.workbook_format,
            self.file_path,
        )
        if "Year" in blocks[block_name].columns:
            return blocks[block_name].set_index("Year")
        import warnings

        warnings.warn(
            f"'Year' column not found in block '{block_name}'. Returning block unmodified."
        )
        return blocks[block_name]

    def load_all(self, df_input_full):
        return input_extractor.load_all_for(
            self.scenario, df_input_full, self.workbook_format, self.file_path
        )

    def get_all_other_inputs(self, df_input_full):
        totals = pd.DataFrame()
        for name in self.starting_cols[self.scenario].keys():
            totals[name] = self.get_other_inputs(name, df_input_full)
        years = self.get_other_inputs("year", df_input_full)
        totals.set_index(years.iloc[:, 0], inplace=True)
        since = years.iloc[0, 0]
        cc = self.cal_total_capital(df_input_full, since_year=since)["total_capital"]
        ap = self.cal_total_elec_production(df_input_full, since_year=since)[
            "annual_elec_production"
        ]
        totals["capital_cost"] = cc.reindex(totals.index, fill_value=0).values
        totals["total_cost"] = (
            totals["capital_cost"] + totals["variable_cost"] + totals["fixed_cost"]
        )
        totals["annual_elec_production"] = ap.reindex(totals.index, fill_value=0).values
        totals["cost_of_elec_in_pj"] = totals["total_cost"] / totals["annual_elec_production"]
        totals["cost_of_elec"] = totals["cost_of_elec_in_pj"] / 3.6
        totals["cost_of_co2"] = totals["co2_emission"] * totals["carbon_price"]
        totals.index.name = None
        return totals

    def get_totals(self, df_input_full):
        return self.get_all_other_inputs(df_input_full)

    def calc_total_for_block(
        self, df_input_full, block_name, since_year=2025, total_col_name=None
    ):
        import warnings

        df_block = self.load(df_input_full, block_name).copy()
        if "Year" in df_block.columns:
            df_block["Year"] = pd.to_numeric(df_block["Year"], errors="coerce")
        elif df_block.index.name == "Year" or (
            df_block.index.names and "Year" in df_block.index.names
        ):
            df_block.index = pd.to_numeric(df_block.index, errors="coerce")
            df_block["Year"] = df_block.index
        else:
            warnings.warn(
                "No 'Year' column or index found. Adding 'Year' based on the current index."
            )
            df_block["Year"] = df_block.index
        df_filtered = df_block[df_block["Year"] >= since_year]
        total = df_filtered.iloc[:, :-1].sum(axis=1).to_frame()
        if total_col_name is None:
            total_col_name = f"total_{block_name}"
        total.columns = [total_col_name]
        return total

    def cal_total_capital(self, df_input_full, since_year=2025):
        return self.calc_total_for_block(
            df_input_full,
            block_name="capital_cost",
            since_year=since_year,
            total_col_name="total_capital",
        )

    def cal_total_elec_production(self, df_input_full, since_year=2025):
        return self.calc_total_for_block(
            df_input_full,
            block_name="elec_production",
            since_year=since_year,
            total_col_name="annual_elec_production",
        )
