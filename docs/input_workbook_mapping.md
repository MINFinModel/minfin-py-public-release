# Legacy vs pure-input workbook mapping

This document compares the **legacy** template (`MINFin Energy Example Input File.xlsm` and structurally similar `.xlsm` files) with the **pure-input** template (`MINFin Python Input File.xlsx`). It reflects how the Python code in this repository reads each layout.

**Definitions**

- **Legacy** — Original multi-sheet workbook with `Definitions`, `New Infrastructure (Input)`, `Technology Disag (S1)`, `Financing Baseline`, `Funding Baseline`, etc.
- **Pure input** — Long-form sheets such as `INVESTMENT PLAN`, `PPA REVENUE`, `WHOLESALE REVENUE`, `OTHER REVENUE`; detected when the file has `INVESTMENT PLAN` and no `Definitions` sheet (`detect_workbook_format` → `pure_input`).

---

## 1. Sheet-level mapping

| Legacy (.xlsm) | Pure input (.xlsx) | Notes |
|----------------|---------------------|--------|
| **Definitions** | **TECHNOLOGY REGISTER** + **MACROECONOMIC** + empty placeholders in code | Technologies, some currencies; several blocks that lived on `Definitions` are returned as empty frames in `load_excel_data(..., workbook_format=pure_input)` or sourced from the two sheets above. |
| **New Infrastructure (Input)** | **INVESTMENT PLAN** | Wide OSeMOSYS-style grid → long table; use `input_extractor(..., workbook_format=WORKBOOK_FORMAT_PURE_INPUT, file_path=...)` instead of a wide `DataFrame`. |
| **Technology Disag (S1)** | **PPA REVENUE** + **WHOLESALE REVENUE** + **OTHER REVENUE** | Field-level mapping: `PURE_INPUT_STATIC_FIELD_SOURCES` in `MinFin/technology_sheet_io.py`. |
| **Financing Baseline** | **EXISTING INFRASTRUCTURE** | **Semantic match:** historic financing instruments and flows that the legacy workbook puts on **Financing Baseline** (especially the “historical baseline” block) are represented in the pure-input file as **long-form rows** on **EXISTING INFRASTRUCTURE** (e.g. Technology, Year, Financing Source, Type of Finance, Volume of Finance, Currency, Rate, Term, Grace period, Schedule). **`financing_baseline_extractor.from_workbook(file_path)`** maps that sheet (plus **MACROECONOMIC** for exchange rates) into the same extractor API as the legacy wide sheet. `read_financing_baseline()` still returns `None` for pure input because there is no single wide sheet to load. **NEW INFRASTRUCTURE** holds forward-looking cost-of-capital / instrument parameters, not the same table as the legacy historic block. |
| **Funding Baseline** | *None* | Not present; `OTHER REVENUE` (e.g. grants) is not a full substitute for the legacy funding-baseline sheet used by `process_funding_baseline`. |
| **Investment Needs** | **INVESTMENT PLAN** (e.g. `Capital Cost` variable) | Legacy had a dedicated sheet; pure input embeds investment needs in the long plan. |
| **Technology Disag (S2)** | *No second Disag sheet* | If the model used S2, there is no equivalent second tab. |
| **Visualisation Dashboard** | *None* | Dashboard only; not part of the pure-input data file. |
| **High Level Dashboard** | *None* | Same as above. |

---

## 2. Technology Disag–style fields → pure-input `Variable` names

These correspond to `DEFAULT_FIELD_RELATIVE_POSITIONS` / `extract_tech_data_pure_input` in `technology_sheet_io.py`.

| Logical field (legacy grid) | Pure-input sheet | `Variable` |
|----------------------------|------------------|------------|
| `total_grant_amount` | OTHER REVENUE | Grants |
| `ppa_currency` | — | Not stored as a year series in the new file; API uses a **zero row** for compatibility. |
| `ppa_contracted_generation` | PPA REVENUE | PPA Contracted Generation |
| `ppa_standard_offtaker_share` | PPA REVENUE | Standard Off-taker Share |
| `ppa_direct_offtaker_tariff` | PPA REVENUE | Direct Off-taker Tariff |
| `ppa_standard_tariff` | PPA REVENUE | Standard Off-taker Tariff |
| `ppa_contracted_capacity` | PPA REVENUE | PPA Contracted Capacity |
| `ppa_capacity_fee` | PPA REVENUE | PPA Capacity Fee |
| `ppa_penalty_tariff` | PPA REVENUE | PPA Penalty Tariff |
| `redispatch_compensation_price` | PPA REVENUE | Redispatch Compensation Price |
| `corporate_tax_rate` | OTHER REVENUE | Corporate Tax Rate |
| `receivables` | OTHER REVENUE | Receivables |
| `liabilities` | OTHER REVENUE | Liabilities |
| Dynamic offtaker **share** / **wholesale price** | WHOLESALE REVENUE | Share of Off-take; Wholesale Price (row order aligned with `generate_share_configs` offsets 38 / 44). |

---

## 3. New Infrastructure blocks → `INVESTMENT PLAN` variables

| `input_extractor` block (legacy wide sheet) | `Variable` in INVESTMENT PLAN |
|---------------------------------------------|------------------------------|
| `capital_cost` | Capital Cost |
| `elec_production` (electricity production) | ActualGeneration |
| `opex` | OPEX |
| `potential_generation` | PotentialGeneration |
| `ffe` (Fossil Fuel Expenditure) | **Missing** — the pure-input file has no FFE series; the code returns a **zero matrix** with the same shape as `capital_cost` for API compatibility with `load_osemosys_input`. |
| Other “3) Other Inputs” style series (aggregated) | Emissions, Carbon Price; variable OPEX rolled up for `variable_cost`, etc. (`_pure_input_other_input_series` in `data_processor.py`). |
| Emission savings (LC − NZ CO₂) when using pure input | **Emissions Savings** — read per year from INVESTMENT PLAN (prefer `Scenario == "Net Zero"`); `emission_savings_series_from_investment_plan` and `cal_invest_needs(..., pure_input_file_path=...)` instead of differencing scenario summaries. |

---

## 4. Gaps: present in legacy, missing or not equivalent in pure input

1. **Whole sheets with no equivalent (or equivalent only after adaptation)**
   - **Financing Baseline** (as a **sheet name and Excel layout**) — absent in pure input. **Content** that overlapped the legacy historic-financing area is on **EXISTING INFRASTRUCTURE**; the legacy **exchange-rate block** at the top of Financing Baseline is read from **MACROECONOMIC** via `financing_baseline_extractor.from_workbook`.
   - **Funding Baseline** — As used with `process_funding_baseline`.
   - **Visualisation Dashboard** / **High Level Dashboard** — Dashboards in the legacy file only.
   - **Technology Disag (S2)** — No second Disag sheet in the pure-input file.

2. **Definitions-derived tables** (returned empty or partial in `load_excel_data` for pure input)
   - Name/description style blocks: `df_param_constraints`, `df_investment_needs`, `df_financing_baseline`, `df_funding_baseline`, `df_scenarios` (as separate definition lists).
   - **consumer_segments** — No single replacement sheet; wholesale long data partly replaces the role of consumer-driven column generation.

3. **New Infrastructure / OSeMOSYS**
   - **Fossil Fuel Expenditure (FFE)** as a proper time series — **not** in INVESTMENT PLAN.

4. **Scenarios**
   - Example files often contain only **Net Zero** rows under `Scenario`. If **Least Cost** rows are absent, `least_cost` blocks are empty; downstream totals are aligned with `reindex(..., fill_value=0)` to avoid length mismatches.

5. **Other workbooks / sheets referenced in some notebooks** (not in the pure-input xlsx)
   - e.g. **OSeMOSYS (Input)**, **FFRM (Input)** — not in the current `MINFin Python Input File.xlsx` sheet list.

---

## 5. Present in pure input but not as separate legacy “input sheets”

- **NEW INFRASTRUCTURE** — Cost of capital, debt/equity, instrument structure by technology (parameter-style; complements but does not replace the legacy **Financing Baseline** historic grid).
- **EXISTING INFRASTRUCTURE** — Line-level existing financing; **this is where the Financing Baseline–style historic financing content is carried** in the pure-input template. It is wired through `historical_from_existing_infrastructure` and `financing_baseline_extractor.from_workbook` (see `MinFin/financing_baseline.py`).
- **COVER** — Model metadata.
- **MACROECONOMIC** — Exchange rates, GDP, discount rate, etc.

---

## Related code

| Purpose | Module / symbol |
|--------|-----------------|
| Detect layout | `detect_workbook_format`, `WORKBOOK_FORMAT_PURE_INPUT` — `MinFin.data_processor` |
| Wide infra sheet | `read_infrastructure_input` — `None` for pure input |
| Financing Baseline (legacy sheet) | `read_financing_baseline` — `None` for pure input (no wide sheet). Historic financing + rates: `financing_baseline_extractor.from_workbook` → **EXISTING INFRASTRUCTURE** + **MACROECONOMIC** |
| Blocks from INVESTMENT PLAN | `_build_input_blocks_from_pure_input_file`, `input_extractor` |
| Disag / revenue fields | `extract_tech_data_pure_input`, `PURE_INPUT_STATIC_FIELD_SOURCES` — `MinFin.technology_sheet_io` |
| definitions-style dict | `load_excel_data(file_path, workbook_format="auto")` |

For questions or to extend mapping (e.g. row/cell level for one specific legacy sheet), specify the sheet name and version of the file.
