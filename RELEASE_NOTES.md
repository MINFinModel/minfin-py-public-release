# Release Notes

## v0.2.0-beta — 2026-03-30

### Overview

First packaged release of **MinFin** (`MinFin-Py`), an open-source Python toolkit for energy finance analysis. This release consolidates all notebook-based workflow logic into an installable `MinFin` package, adds new technology-specific analysis modules, and ships a bundled example workbook so users can get started immediately.

---

### New Features

#### Core Package (`MinFin`)

- **`definitions_io.py`** — Definition row models and DataFrame loaders for core MINFin entities:
  - `ParameterConstraint`, `FinancingBaseline`, `FundingBaseline`, `Scenario`, `Currency`, `Technology`
  - Helper utilities to load each entity type from raw DataFrames.

- **`disag_tables.py`** — Disaggregation lookup tables and segment roll-up helpers:
  - Maps technology classifications to model segments.
  - Aggregates parameters by segment for downstream analysis.

- **`technology_sheet_io.py`** — Technology Disaggregation sheet extraction from the MINFin Excel workbook.

- **`funding_allocation.py`** — Funding allocation calculations across instrument types and technologies.

- **`investment_needs_extra.py`** — Extended investment-needs blocks with summary DataFrames.

- **`market_revenue.py`** — PPA / wholesale revenue split and net-zero (NZ) funding chart helpers.

- **`offtaker_tariffs.py`** — Offtaker tariff processing utilities.

- **`repayment_extras.py`** — Additional repayment schedule helpers, including:
  - `epp_with_grace_p_and_i_payment` — Static method for *EPP with Grace on Principal and Interest* repayment type.

- **`plotting_notebook.py`** — Plotly/seaborn chart builders designed for use inside Jupyter notebooks.

- **`notebook_dashboard.py`** — Backwards-compatibility shim; re-exports `NotebookHighLevelDashboard` from `high_level_dashboard` so older notebook imports continue to work.

#### Financing Baseline (`financing_baseline.py`)

- New method to extract **exchange rates by year** from the baseline DataFrame.
- Fixed column/row indexing for more robust sheet parsing.
- Corrected *Volume of Finance* value reference in repayment calculations.
- Improved grace-period handling in repayment schedules.
- Strengthened **division-by-zero guards** in weighted-average and sector-share calculations.


### Documentation

- `README.md` — Comprehensive repository overview: structure, module descriptions, installation, quick-start examples, data requirements.
- `MinFin/README.md` — Detailed per-module API summary.
- `docs/API.md` — `DataProcessor` and `HighLevelDashboard` API reference.
- `docs/CONTRIBUTING.md` — Contribution guidelines.

---

### Installation

```bash
git clone https://github.com/MINFinModel/MINFin-Py.git
cd MINFin-Py
pip install -r requirements.txt
# optional editable install
pip install -e .
```

**Requirements**: Python ≥ 3.8, pandas ≥ 1.5, numpy ≥ 1.21, matplotlib ≥ 3.5, seaborn ≥ 0.11, plotly ≥ 5.0, openpyxl ≥ 3.0, xlrd ≥ 2.0.

---

### Quick Start

```python
from MinFin.financing_baseline import financing_baseline_extractor, financing_baseline_stats
from MinFin.high_level_dashboard import hd            # class alias
from MinFin.definitions_io import load_technologies   # new in v0.1.0
```

Open `minfin_notebook.ipynb` and set `file_path` to your `.xlsm` workbook (or use the bundled example under `data/`).

---

### Known Limitations

- Input workbooks must conform to the MINFin Excel schema (Definitions, Financing/Funding Baselines, Technology Disag sheets).
- The package is still evolving; minor breaking changes may occur in patch releases before v1.0.

---


