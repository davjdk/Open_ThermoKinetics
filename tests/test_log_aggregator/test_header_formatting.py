"""
Tests for header formatting functionality in operation logs.

This module tests both standard and minimalist header formats,
including fallback behavior and source info extraction.
"""

from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.table_formatter import OperationTableFormatter


class TestHeaderFormatting:
    """Test cases for operation header formatting."""

    def test_standard_header_format(self):
        """Test standard format header generation."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0  # 2022-01-01 00:00:00 UTC

        formatter = OperationTableFormatter(formatting_config={"header_format": "standard"})

        header = formatter._format_operation_header(operation_log, 1)

        assert 'Operation "TEST_OPERATION" – STARTED' in header
        assert "id=1" in header
        assert "2022-01-01" in header

    def test_minimalist_header_format(self):
        """Test minimalist format header generation."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        operation_log.source_module = "test_module.py"
        operation_log.source_line = 42

        formatter = OperationTableFormatter(formatting_config={"header_format": "source_based"})

        header = formatter._format_operation_header(operation_log, 2)

        assert header.startswith('test_module.py:42 "TEST_OPERATION"')
        assert "id=2" in header
        assert "2022-01-01" in header

    def test_fallback_to_standard_when_no_source_info(self):
        """Test fallback to standard format when source info is missing."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        # source_module and source_line are None

        formatter = OperationTableFormatter(formatting_config={"header_format": "source_based"})

        header = formatter._format_operation_header(operation_log, 3)

        # Should use standard format
        assert 'Operation "TEST_OPERATION" – STARTED' in header

    def test_long_module_name_truncation(self):
        """Test truncation of long module names."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        operation_log.source_module = "very_long_module_name_that_should_be_truncated.py"
        operation_log.source_line = 100

        formatter = OperationTableFormatter(formatting_config={"header_format": "source_based"})

        header = formatter._format_operation_header(operation_log, 4)  # Check that module name is truncated
        assert "..." in header
        # Check that it starts with truncated module info
        assert header.startswith("...should_be_truncated.py:100")

    def test_format_source_info_normal_module(self):
        """Test source info formatting for normal module names."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.source_module = "calculations_data.py"
        operation_log.source_line = 127

        formatter = OperationTableFormatter()
        source_info = formatter._format_source_info(operation_log)

        assert source_info == "calculations_data.py:127"

    def test_format_source_info_missing_data(self):
        """Test source info formatting when data is missing."""
        operation_log = OperationLog("TEST_OPERATION")
        # Missing source_module and source_line

        formatter = OperationTableFormatter()
        source_info = formatter._format_source_info(operation_log)

        assert source_info == "unknown:0"

    def test_should_use_minimalist_header_mode_minimalist(self):
        """Test minimalist header detection for mode=minimalist."""
        formatter = OperationTableFormatter(formatting_config={"mode": "minimalist"})
        assert formatter._should_use_minimalist_header()

    def test_should_use_minimalist_header_format_source_based(self):
        """Test minimalist header detection for header_format=source_based."""
        formatter = OperationTableFormatter(formatting_config={"header_format": "source_based"})
        assert formatter._should_use_minimalist_header()

    def test_should_use_minimalist_header_standard_mode(self):
        """Test minimalist header detection for standard configuration."""
        formatter = OperationTableFormatter(formatting_config={"mode": "standard", "header_format": "standard"})
        assert not formatter._should_use_minimalist_header()

    def test_minimalist_mode_constructor_parameter(self):
        """Test that minimalist_mode parameter enables source-based headers."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        operation_log.source_module = "test_module.py"
        operation_log.source_line = 50

        formatter = OperationTableFormatter(minimalist_mode=True)

        header = formatter._format_operation_header(operation_log, 5)

        # Should use minimalist format when minimalist_mode=True
        assert header.startswith('test_module.py:50 "TEST_OPERATION"')

    def test_standard_mode_preserves_existing_behavior(self):
        """Test that standard mode preserves existing header behavior."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0

        formatter = OperationTableFormatter()  # Default constructor

        header = formatter._format_operation_header(operation_log, 6)

        # Should use standard format by default
        assert 'Operation "TEST_OPERATION" – STARTED' in header
        assert "id=6" in header
