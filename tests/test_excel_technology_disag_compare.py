"""Unit tests for Technology Disag parity helpers (no Kenya files required)."""

import pandas as pd

from MinFin.excel_technology_disag_compare import (
    round_for_parity,
    values_equal_at_precision,
)


def test_round_for_parity_three_decimals():
    assert round_for_parity(1.23456, decimals=3) == 1.235
    assert round_for_parity(None, decimals=3) is None


def test_values_equal_within_three_decimal_rounding():
    assert values_equal_at_precision(41.35743779870651, 41.35743779837565, decimals=3)
    assert not values_equal_at_precision(7.5519, 7.1467, decimals=3)
    assert values_equal_at_precision(156.7815, 156.78150000000002, decimals=3)


def test_values_equal_rejects_material_difference_at_four_decimals():
    assert not values_equal_at_precision(
        0.01226574120247373,
        0.01165245414235004,
        decimals=4,
    )


def test_discover_blocks_on_minimal_frame():
    from MinFin.excel_technology_disag_compare import discover_technology_disag_blocks

    td = pd.DataFrame(
        [
            [None, None, None, None, None],
            [None, None, 2025, 2026, 2027],
            [None, "Solar PV", None, None, None],
            [None, "Investment Need (Million USD)", 10.0, 20.0, 30.0],
            [None, "Cashflows (Million USD)", 1.0, 2.0, 3.0],
        ]
    )
    blocks = discover_technology_disag_blocks(td, technology_names={"Solar PV"})
    assert blocks == {"Solar PV": 2}


def test_extract_block_series_stops_at_next_technology_header():
    from MinFin.excel_technology_disag_compare import extract_block_series

    td = pd.DataFrame(
        [
            [None, None, 2025, 2026],
            [None, "Biomass", None, None],
            [None, "Investment Need (Million USD)", 0.0, 25.0],
            [None, "Cashflows (Million USD)", 1.0, 2.0],
            [None, "Geothermal", None, None],
            [None, "Investment Need (Million USD)", 278.0, 544.0],
            [None, "Cashflows (Million USD)", 3.0, 4.0],
        ]
    )
    series = extract_block_series(td, 1)
    assert series["Investment Need (Million USD)"][2026] == 25.0
    assert series["Investment Need (Million USD)"][2025] == 0.0
