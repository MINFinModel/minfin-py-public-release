# MinFin API Documentation

## DataProcessor

The `DataProcessor` class handles all data processing operations for the MinFin toolkit.

### Methods

#### `__init__()`
Initialize a new DataProcessor instance.

#### `process_data(file_path)`
Process the input Excel file and prepare it for analysis.

Parameters:
- `file_path` (str): Path to the Excel file to process

Returns:
- Processed data in the required format

## HighLevelDashboard

The `HighLevelDashboard` class generates high-level financial dashboards.

### Methods

#### `__init__()`
Initialize a new HighLevelDashboard instance.

#### `generate_dashboard(data)`
Generate a dashboard from the processed data.

Parameters:
- `data`: Processed financial data

Returns:
- Dashboard visualization 