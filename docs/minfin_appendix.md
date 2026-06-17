# MinFin Model Data Dictionary (Appendix 1 style)

> **Naming convention.** MinFin has two naming layers. **Python key** = the identifier
> used inside the code (e.g. `capital_cost`). **Excel field** = the literal in the
> workbook's `Variable` column (e.g. `Capital Cost`). This table uses the **Python names**
> as primary.
>
> Note: MinFin is a financial post-processing model on top of OSeMOSYS outputs, so
> "Variables" here are *computed* quantities (pandas), not solver decision variables.
> The main dimensionality is **Year × Technology** (no `Region` / `Fuel` / `Mode` as in
> OSeMOSYS).

## 1. Sets / Dimensions

These exist in code as **DataFrame column names, index level names, or list variables**.

| Python name | Form | Values / description |
|-------------|------|----------------------|
| `Year` | column / int header | Model year |
| `Technology` | column | Parent technology name (e.g. `Biomass`) |
| `Name` | column | OSeMOSYS technology code (e.g. `PWRBIO`) |
| `Classification` | column | Technology grouping |
| `Sector` | column | Sector |
| `currency_list` | list (`fx.py`) | `['KES','USD','EUR','GBP','JPY','CNY','INR','AUD','CAD','OT4'…'OT8']` |
| `Currency` / `Code` | column | Currency |
| `net_zero` / `least_cost` | scenario keys | Workbook labels `"Net Zero"` / `"Least Cost"` |
| `Source` | MultiIndex level | `Comm_Intl`, `Comm_Dom`, `Conc_IFI`, `Conc_DPS` |
| `Category` | MultiIndex level | `Debt`, `Equity`, `Financing Shares`, `Foreign Currency Shares` |
| `Parameter` | MultiIndex level | See parameter table B5 |
| `Schedule` | column | `Equity`, `EPP`, `Annuity`, `Lump Sum`, … |
| `Type` | column | `Budget`, `SOE Gen.`, `Grant` |
| `Off-taker` | column | Power offtaker |
| `TECH_START_ROWS` | dict (`technology_sheet_io`) | Fixed technology anchors (Biomass, CSP, Hydropower, …) |

## 2. Input Parameters

### B1. Investment-plan blocks — `infrastructure_extractor` / `pure_input_blocks` (Year × Technology)

| Python key | Excel field | Description |
|------------|-------------|-------------|
| `capital_cost` | `Capital Cost` | Capital investment |
| `elec_production` | `ActualGeneration` | Actual electricity generation |
| `potential_generation` | `PotentialGeneration` | Potential generation |
| `opex` | `OPEX` | Operating expenditure |
| `co2_emission` | `Emissions` | CO2 emissions |
| `carbon_price` | `Carbon Price` | Carbon price |
| `carbon_credit_price` | *(legacy)* | Carbon credit price |
| `emission_savings` | `Emissions Savings` | Emission savings |
| `variable_cost` / `fixed_cost` / `ffe` | OPEX sum / (legacy) | Variable / fixed / fossil-fuel expenditure |

### B2. Exchange rate / macro — `data_processor` / `fx` / `financing_baseline`

| Python name | Description |
|-------------|-------------|
| `get_melted_currency_df()` | Long FX table (`Year, Currency, Exchange Rate`) |
| `exchange_rates_by_year` / `base_rates` | Default FX when sheet absent (`fx.py`) |
| `discount_rate` (=`5.33/100`), `starting_year` (=`2024`), `foreign_currency` (=`"USD"`), `number_of_payments_per_annum` | Code constants |

### B3. Historic financing — EXISTING INFRASTRUCTURE (per project row; column names = field names)

`Volume of Finance`, `Currency`, `Rate`, `Term`, `Grace period`, `Schedule`,
`Financing Source`, `Type of Finance`, `Financing Sector`, `Financial Institution`,
`Origin of Finance`

### B4. Funding availability — Funding Baseline (Year × Currency × Type)

`Volume (Million)`, `Govt Share`, `Type`, `Exchange Rate`

### B5. Forward financing structure — NEW INFRASTRUCTURE (internal aliases in `funding_allocation`)

| Python alias | Excel `Parameter` | Category |
|--------------|-------------------|----------|
| `interest_rate` | `Interest Rate` | Debt |
| `grace_period` | `Grace Period` | Debt |
| `loan_term` | `Loan Term` | Debt |
| `rate_of_return` | `Rate of Return` | Equity |
| `project_life` | `Project Life` | Equity |
| `debt_share` | `Debt Share` | Financing Shares |
| `fin_share` | `Share of Finance` | Financing Shares |
| `fc_debt_ratio` | `Debt` | Foreign Currency Shares |
| `fc_equity_ratio` | `Equity` | Foreign Currency Shares |

### B6. Revenue parameters — PPA / OTHER REVENUE (`technology_sheet_io`, Technology × Scenario × Year)

| Python key | Excel field |
|------------|-------------|
| `ppa_contracted_generation` | `PPA Contracted Generation` |
| `ppa_standard_offtaker_share` | `Standard Off-taker Share` |
| `ppa_direct_offtaker_tariff` | `Direct Off-taker Tariff` |
| `ppa_standard_tariff` | `Standard Off-taker Tariff` |
| `ppa_contracted_capacity` | `PPA Contracted Capacity` |
| `ppa_capacity_fee` | `PPA Capacity Fee` |
| `ppa_penalty_tariff` | `PPA Penalty Tariff` |
| `redispatch_compensation_price` | `Redispatch Compensation Price` |
| `total_grant_amount` | `Grants` |
| `corporate_tax_rate` | `Corporate Tax Rate` |
| `receivables` / `liabilities` | `Receivables` / `Liabilities` |

WHOLESALE REVENUE dynamic fields: `Share of Off-take`, `Wholesale Price`
(generated keys `{slug}_share_{Currency}`, `{slug}_sale_price_{Currency}`).

## 3. Computed Variables

Given as actual **function names / column names / dict keys**.

### V1. Funding availability — `data_processor` / `high_level_dashboard`

`volume_in_usd`, `get_funding_envelope()`, `cal_annual_cagr()`, `cal_period_cagr()`,
`log_reg_growth_rate()`, `get_funding_availability_full()`; `get_summary()` outputs
`Investment needs` / `Funding availability` / `Financing requirement` / `Funding shortfall`

### V2. Investment needs — `investment_needs_extra.cal_invest_needs`

`df_cap_by_class_lc` / `df_cap_by_class_nz`, `df_cap_by_tech_lc` / `df_cap_by_tech_nz`,
`emission_savings`, `expenditure`, `fossil_fuel_savings`, `df_financing_needs_ffr`

### V3. Historic financing stats — `financing_baseline` / `financing_stats`

`cal_repayment_schedule()`, `cal_grant_element()` → `Grant Element`,
`cal_market_element()` → `Market Element`, `Maturity`, `get_technology_summary_table()`
(incl. `WACC (%)`, `Debt Share (%)`, `Loan Term (years)`, …)

### V4. Per-technology allocation & repayment — `funding_allocation` / `repayment_extras`

`inv_fc_debt`, `inv_fc_equity`, `inv_lc_debt`, `inv_lc_equity`, `get_allocation_matrix()`,
`calculate_detailed_repayments()` (outputs `Loans ({source})` / `Equity ({source})`),
`cal_interest_cost()` → `interest_cost`

### V5. Generation, tariffs, market revenue — `offtaker_tariffs` / `market_revenue`

`total_generation`, `ppa_met_generation`, `whole_sale_generation`,
`ppa_direct_offtaker_share`, `redispatch_compensation`, `calc_sale_price()` → `sale_price`,
`total_ppa_revenue`, `total_wholesale_revnue` (misspelled in code), `power_purchased`,
`tariff`, `capacity_purchased`, `capacity_tariff`, `power_purchase_cost`

### V6. Costs, tax, cashflow — `infrastructure_extractor` / notebook

`corporate_tax_expenses`, `cashflow`, `cost_of_elec_in_pj`, `cost_of_elec`, `cost_of_co2`,
`total_cost`, `delta_capital_cost`

---

> Note: many per-technology time series in V4–V6 (e.g. `total_ppa_revenue`, `cashflow`)
> are currently assembled in `minfin_notebook.ipynb`, while the logic functions live in
> the modules listed.
