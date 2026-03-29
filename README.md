# MinFin Energy Finance Analysis Toolkit

A comprehensive toolkit for analyzing energy finance data, focusing on renewable energy projects and infrastructure financing. This repository contains multiple modules for different aspects of energy finance analysis.

## Repository Structure

```
.
├── data/                   # Source data files (place sample .xlsm here)
├── docs/                   # Documentation
│   ├── API.md
│   └── CONTRIBUTING.md
├── MinFin/                 # Core Python package
│   ├── data_processor.py
│   ├── financing_baseline.py
│   ├── high_level_dashboard.py
│   ├── save_figure.py
│   ├── utils.py
│   ├── definitions_io.py       # Definition rows + loaders
│   ├── investment_needs_extra.py
│   ├── technology_sheet_io.py  # Technology Disag extraction
│   ├── funding_allocation.py
│   ├── offtaker_tariffs.py
│   ├── repayment_extras.py
│   ├── disag_tables.py
│   ├── notebook_dashboard.py   # compat: NotebookHighLevelDashboard → high_level_dashboard
│   ├── plotting_notebook.py
│   └── market_revenue.py       # PPA / wholesale revenue split + NZ funding chart
├── MinFin_Notebook/       # Extra Jupyter notebooks
│   └── financial_instruments.ipynb
├── minfin_output/         # Generated figures (HTML/PNG)
│   └── figures/
├── tests/
├── requirements.txt
├── minfin_notebook.ipynb    # Legacy demo (may be replaced)
├── addtional_input.ipynb    # Current main workflow notebook
└── README.md
```

The workflow logic that previously lived only in `addtional_input.ipynb` is being moved into the `MinFin` modules above so notebooks can `import` reusable functions. See each module docstring for scope.

## Modules Overview

### Core (`MinFin`)

- Debt and equity financing analysis, repayment schedules, grant elements (`financing_baseline.py`, `utils.py`).
- Excel ingestion (`data_processor.py`), high-level dashboard (`high_level_dashboard.py`).
- Plot export helpers (`save_figure.py`, `plotting_notebook.py` for Plotly/seaborn charts used in notebooks).

[Detailed MinFin Module Documentation](MinFin/README.md)

### Notebooks

- **`addtional_input.ipynb`**: Primary analysis workflow; prefer importing from `MinFin` rather than duplicating large `def` blocks.
- **`minfin_notebook.ipynb`**: Older demo; may be superseded.

### Output

- **`minfin_output/figures/`**: Generated HTML/PNG figures.

## Installation

```bash
git clone <repository-url>
cd MinFin
pip install -r requirements.txt
# optional editable install
pip install -e .
```

## Dependencies

- Python 3.8+
- pandas, numpy, matplotlib, seaborn, plotly, openpyxl, jupyter (see `requirements.txt`)

## Quick Start

```python
from MinFin.financing_baseline import financing_baseline_extractor, financing_baseline_stats
from MinFin.high_level_dashboard import hd  # class alias; same as `high_level_dashboard`
```

`notebook_dashboard` still re-exports `NotebookHighLevelDashboard` for older imports.

## Data Requirements

Input workbooks should match the MINFin Excel structure (Definitions, Financing/Funding baselines, Technology Disag sheets, etc.). Use a sample `.xlsm` under `data/` and set `file_path` in the notebook accordingly.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License

See [LICENSE](LICENSE).

## Acknowledgments

## Version History

- v0.0.1beta: Initial release
- Ongoing: Notebook logic migrated into `MinFin` submodules for reuse and testing.
