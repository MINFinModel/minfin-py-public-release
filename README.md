# MinFin Energy Finance Analysis Toolkit

A comprehensive toolkit for analyzing energy finance data, focusing on renewable energy projects and infrastructure financing. This repository contains multiple modules for different aspects of energy finance analysis.

## Repository Structure

```
.
├── MinFin/                 # Financial baseline analysis module
├── MinFin_Notebook/        # Jupyter notebooks for analysis
├── MinFin_Output/          # Output data and results
└── README.md
```

## Modules Overview

### 1. MinFin Module
A Python module for analyzing and processing financial data related to technology financing. Key features include:
- Debt and equity financing analysis
- Interest rate calculations
- Grant element calculations
- Repayment schedule generation
- Technology-specific financing requirements
- Multi-source financing analysis

[Detailed MinFin Module Documentation](MinFin/README.md)

### 2. MinFin_Notebook
Collection of Jupyter notebooks for:
- Data visualization
- Analysis workflows
- Example usage
- Results presentation

### 3. MinFin_Output
-  Figures 

## Installation

```bash
# Clone the repository
git clone [repository-url]

# Navigate to the project directory
cd CCG-Energy-Finance

# Install dependencies
pip install -r requirements.txt
``

## Dependencies

- Python 3.x
- pandas
- numpy
- jupyter
- matplotlib
- seaborn

## Quick Start

1. **Setup Environment**
```python
# Import required modules
from MinFin.financing_baseline import financing_baseline_extractor, financing_baseline_stats
```

2. **Load and Process Data**
```python
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

3. **Generate Analysis**
```python
# Get comprehensive technology summary
tech_summary = fbs.get_technology_summary_table()

# Analyze financing sources
institution_shares = fbs.get_institution_shares()
sector_shares = fbs.get_financing_sector_shares()
```

## Data Requirements

### Input Data Format
The toolkit expects input data with the following key columns:
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

### Sample Data
Sample data files are provided in the `MinFin_Output` directory for reference.

## Analysis Features

### Financial Metrics
- Debt/Equity ratios
- Interest rates
- Grace periods
- Loan terms
- Grant elements
- WACC (Weighted Average Cost of Capital)
- Financing volumes
- Market elements

### Reporting Capabilities
- Technology-specific summaries
- Financing source analysis
- Institution share analysis
- Sector share analysis
- Repayment statistics

## Usage Examples

### Technology Analysis
```python
# Get financing breakdown for specific technology
solar_financing = fbs.get_technology_financing_by_source(technology="Solar")

# Get specific metric across all technologies
debt_equity_data = fbs.get_technology_financing_by_source(metric="Debt Equity Share")
```

### Source Analysis
```python
# Get institution shares
institution_shares = fbs.get_institution_shares()

# Get financing sector shares
sector_shares = fbs.get_financing_sector_shares()

# Get repayment statistics
repayment_stats = fbs.get_repayment_statistics()
```

## Contributing

We welcome contributions! Please follow these steps:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Contact


## Acknowledgments


## Version History

- v0.0.1beta: Initial release
