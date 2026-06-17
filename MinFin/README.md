# MinFin Module

A Python module for analyzing and processing financial data related to technology financing, with a focus on renewable energy and infrastructure projects.

## Overview

The MinFin module provides tools for analyzing financing structures, calculating key financial metrics, and generating comprehensive reports for different technologies and financing sources. It handles various aspects of project finance including:

- Debt and equity financing analysis
- Interest rate calculations
- Grant element calculations
- Repayment schedule generation
- Technology-specific financing requirements
- Multi-source financing analysis

## Installation

```bash
# Clone the repository
git clone [repository-url]

# Navigate to the project directory
cd MinFin
```

## Dependencies

- Python 3.x
- pandas
- numpy

## Module Structure

### Support modules

- `workbook_format` — legacy vs pure-input detection
- `excel_io` — year-column detection and long-sheet reads
- `pure_input_blocks` / `infrastructure_extractor` — INVESTMENT PLAN and wide-sheet extraction (`data_processor` re-exports the public API)
- `fx` — shared exchange-rate helpers
- `financing_stats` — `financing_baseline_stats` (re-exported from `financing_baseline`)

### Main Classes

1. `financing_baseline_extractor`
   - Handles data extraction and preprocessing
   - Manages currency conversions
   - Calculates repayment schedules
   - Processes grant elements

2. `financing_baseline_stats`
   - Generates statistical analysis
   - Creates summary tables
   - Calculates financing metrics
   - Produces technology-specific reports

### Key Features

- Multi-currency support
- Flexible financing source analysis
- Technology-specific metrics
- Comprehensive reporting capabilities
- Grant element calculations
- WACC (Weighted Average Cost of Capital) calculations

## Usage Examples

### Basic Setup

```python
from MinFin.financing_baseline import financing_baseline_extractor, financing_baseline_stats

# Initialize the extractor
extractor = financing_baseline_extractor(
    df_financing_baseline_full,
    currency='KES',
    starting_year=2024,
    number_of_payments_per_annum=1
)

# Calculate repayment schedule
repayment_schedule = extractor.cal_repayment_schedule(df)

# Initialize stats analyzer
fbs = financing_baseline_stats(extractor, repayment_schedule)
```

### Generate Technology Summary

```python
# Get comprehensive technology summary
tech_summary = fbs.get_technology_summary_table()

# Get financing breakdown for specific technology
solar_financing = fbs.get_technology_financing_by_source(technology="Solar PV")

# Get specific metric across all technologies
debt_equity_data = fbs.get_technology_financing_by_source(metric="Debt Equity Share")
```

### Analyze Financing Sources

```python
# Get institution shares
institution_shares = fbs.get_institution_shares()

# Get financing sector shares
sector_shares = fbs.get_financing_sector_shares()

# Get repayment statistics
repayment_stats = fbs.get_repayment_statistics()
```

## Key Metrics

The module calculates various financial metrics including:

- Debt/Equity ratios
- Interest rates
- Grace periods
- Loan terms
- Grant elements
- WACC
- Financing volumes
- Market elements

## Data Structure

The module expects input data in a specific format with the following key columns:

- Technology
- Financing Source
- Type of Finance
- Volume of Finance
- Currency
- Year
- Rate
- Term
- Grace period
- Schedule

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Specify your license here]

## Contact

[Your contact information] 