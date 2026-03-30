"""
Tests for the data processing module.
"""
import pytest
from MinFin.data_processor import DataProcessor

def test_data_processor_initialization():
    """Test that DataProcessor can be initialized."""
    processor = DataProcessor()
    assert processor is not None 