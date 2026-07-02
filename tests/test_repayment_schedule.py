"""Tests for Excel-faithful repayment Schedule formulas."""

import math

from MinFin.financing_baseline import (
    _normalize_schedule,
    financing_baseline_extractor as FB,
)
from MinFin.utils import pmt


F = 2025


def test_schedule_name_normalization():
    assert _normalize_schedule("Lump Sum Principal") == "Lump Sum on Principal"
    assert _normalize_schedule("EPP with Grace Years for Principal") == "EPP with Grace on Principal"
    assert _normalize_schedule("Equal Principal Payments (EPP)") == "Equal Principal Payments (EPP)"
    assert _normalize_schedule("") is None
    assert _normalize_schedule("Unknown Plan") is None


def test_annuity_matches_pmt():
    pay = [FB._pay_annuity(1000, 0.1, 10, F, y) for y in range(F, F + 11)]
    expected = -pmt(0.1, 10, 1000)
    assert all(abs(p - expected) < 1e-9 for p in pay[:10])
    assert pay[10] == 0.0  # year F+floor(R) gives (R-floor)=0 for integer term


def test_epp_principal_sums_to_volume():
    pay = [FB._pay_epp(1000, 0.1, 10, F, y) for y in range(F, F + 10)]
    principal = sum(1000 / 10 for _ in range(10))
    assert abs(principal - 1000) < 1e-9
    assert abs(pay[0] - (100 + 1000 * 0.1)) < 1e-9
    assert abs(pay[-1] - (100 + 100 * 0.1)) < 1e-9


def test_lump_sum_principal_and_interest_only_last_year():
    pay = [FB._pay_lump_principal_interest(1000, 0.1, 10, F, y) for y in range(F, F + 11)]
    nonzero = [i for i, v in enumerate(pay) if v]
    assert nonzero == [9]
    assert abs(pay[9] - 1000 * (1.1 ** 10)) < 1e-6


def test_annuity_fractional_term_last_partial_year():
    R = 10.5
    pay = [FB._pay_annuity(1000, 0.1, R, F, y) for y in range(F, F + 12)]
    last = -pmt(0.1, R, 1000) * (R - math.floor(R))
    assert abs(pay[10] - last) < 1e-9
    assert pay[11] == 0.0


def test_fx_factor_applied():
    rates = {F: {"USD": 1.0, "KES": 100.0}}
    inst = FB.__new__(FB)  # bypass workbook-dependent __init__
    inst._macro_rates_dict = rates
    factor = inst._repayment_fx_factor("KES", F, "USD", rates)
    assert abs(factor - (1.0 / 100.0)) < 1e-12
    # Unknown currency -> no conversion
    assert inst._repayment_fx_factor("XYZ", F, "USD", rates) == 1.0


def test_fx_factor_uses_excel_two_step_conversion():
    rates = {
        2020: {"USD": 1.0, "KES": 100.0, "EUR": 1.25},
        2025: {"USD": 1.0, "KES": 150.0, "EUR": 1.10},
    }
    inst = FB.__new__(FB)  # bypass workbook-dependent __init__
    inst.currency = "KES"
    inst.foreign_currency = "USD"
    inst._macro_rates_dict = rates

    factor = inst._repayment_fx_factor("EUR", 2025, "USD", rates, start_year=2020)

    assert abs(factor - ((100.0 / 1.25) * (1.0 / 150.0))) < 1e-12
