# MinFin API Documentation

Workflow logic lives in the `MinFin` package. The main entry point is `minfin_notebook.ipynb`. Prefer explicit imports:

```python
from MinFin.data_processor import load_excel_data, input_extractor, detect_workbook_format
from MinFin.financing_baseline import financing_baseline_extractor, financing_baseline_stats
from MinFin.high_level_dashboard import hd  # alias for high_level_dashboard
```

See [input_workbook_mapping.md](input_workbook_mapping.md) for legacy vs pure-input workbook layouts.

## Data loading (`data_processor`)

### `load_excel_data(file_path, workbook_format="auto")`

Load definition-style tables (`df_technologies`, `df_currencies`, etc.) from legacy `.xlsm` or pure-input `.xlsx` workbooks.

### `detect_workbook_format(file_path)`

Returns `"pure_input"` or `"legacy"` based on sheet names.

### `input_extractor(scenario, workbook_format="legacy", file_path=None)`

Extract infrastructure blocks (capital cost, OPEX, etc.) from **New Infrastructure (Input)** or **INVESTMENT PLAN**.

### `read_infrastructure_input` / `read_financing_baseline`

Read wide legacy sheets; return `None` for pure-input workbooks.

## Financing baseline (`financing_baseline`, `financing_stats`)

### `financing_baseline_extractor`

Historic instrument ingestion, repayment schedules, grant/market elements. Use `financing_baseline_extractor.from_workbook(file_path)` for both layouts.

### `financing_baseline_stats`

Aggregations over historic financing and repayment schedules, including `get_technology_financing_requirement()`.

## Dashboard (`high_level_dashboard`)

### `high_level_dashboard` (alias `hd`)

Scenario dashboard: financing summary, funding availability, net-zero financing needs.

## FX (`fx`)

### `get_exchange_rates(target_currency, currency_series, year_series, rates_by_year=None)`

Convert volumes using year/currency lookup tables.
