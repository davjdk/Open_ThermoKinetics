"""
Test module for table_formatter functionality.

This module contains unit tests for the OperationTableFormatter class
to verify proper formatting of operation logs.
"""

import time

from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.sub_operation_log import SubOperationLog
from src.core.log_aggregator.table_formatter import OperationTableFormatter, format_operation_log


class TestOperationTableFormatter:
    """Test cases for OperationTableFormatter class."""

    def test_format_empty_operation(self):
        """Test formatting of operation with no sub-operations."""
        formatter = OperationTableFormatter()
        operation_log = OperationLog(operation_name="TEST_OPERATION")
        operation_log.mark_completed(success=True)

        result = formatter.format_operation_log(operation_log)

        assert "TEST_OPERATION" in result
        assert "НАЧАЛО" in result
        assert "ЗАВЕРШЕНО" in result
        assert "No sub-operations recorded." in result
        assert "успешно" in result

    def test_format_operation_with_sub_operations(self):
        """Test formatting of operation with multiple sub-operations."""
        formatter = OperationTableFormatter()
        operation_log = OperationLog(operation_name="DATA_PROCESSING")

        # Add some sub-operations
        sub_op1 = SubOperationLog(
            step_number=1,
            operation_name="LOAD_FILE",
            target="file_data",
            start_time=time.time(),
        )
        sub_op1.mark_completed(response_data={"data": {"success": True}})

        sub_op2 = SubOperationLog(
            step_number=2,
            operation_name="VALIDATE_DATA",
            target="validation_engine",
            start_time=time.time(),
        )
        sub_op2.mark_completed(response_data={"data": True})

        operation_log.sub_operations = [sub_op1, sub_op2]
        operation_log.mark_completed(success=True)

        result = formatter.format_operation_log(operation_log)

        assert "DATA_PROCESSING" in result
        assert "LOAD_FILE" in result
        assert "VALIDATE_DATA" in result
        assert "file_data" in result
        assert "validation_e" in result  # Text is truncated
        assert "Шаг" in result  # Table header
        assert "Подоперация" in result  # Table header

    def test_format_operation_with_errors(self):
        """Test formatting of operation with failed sub-operations."""
        formatter = OperationTableFormatter()
        operation_log = OperationLog(operation_name="FAILED_OPERATION")

        # Add a failed sub-operation
        sub_op = SubOperationLog(
            step_number=1,
            operation_name="PROCESS_DATA",
            target="processor",
            start_time=time.time(),
        )
        sub_op.mark_completed(response_data=None, exception_info="ValueError: Invalid data format")

        operation_log.sub_operations = [sub_op]
        operation_log.mark_completed(success=False, exception_info="ValueError: Invalid data format")

        result = formatter.format_operation_log(operation_log)

        assert "FAILED_OPERATION" in result
        assert "Error" in result
        assert "с ошибкой" in result
        assert "ОШИБКА:" in result
        assert "ValueError" in result

    def test_format_operation_with_mixed_results(self):
        """Test formatting of operation with both successful and failed sub-operations."""
        formatter = OperationTableFormatter()
        operation_log = OperationLog(operation_name="MIXED_RESULTS")

        # Successful sub-operation
        sub_op1 = SubOperationLog(
            step_number=1,
            operation_name="FIRST_STEP",
            target="component1",
            start_time=time.time(),
        )
        sub_op1.mark_completed(response_data={"data": True})

        # Failed sub-operation
        sub_op2 = SubOperationLog(
            step_number=2,
            operation_name="SECOND_STEP",
            target="component2",
            start_time=time.time(),
        )
        sub_op2.mark_completed(response_data=None, exception_info="Error occurred")

        operation_log.sub_operations = [sub_op1, sub_op2]
        operation_log.mark_completed(success=False)

        result = formatter.format_operation_log(operation_log)

        assert "MIXED_RESULTS" in result
        assert "OK" in result  # First sub-operation
        assert "Error" in result  # Second sub-operation
        assert "шагов 2" in result
        assert "успешно 1" in result
        assert "с ошибками 1" in result

    def test_convenience_function(self):
        """Test the convenience format_operation_log function."""
        operation_log = OperationLog(operation_name="CONVENIENCE_TEST")
        operation_log.mark_completed(success=True)

        result = format_operation_log(operation_log)

        assert "CONVENIENCE_TEST" in result
        assert "НАЧАЛО" in result
        assert "ЗАВЕРШЕНО" in result

    def test_table_format_configuration(self):
        """Test different table format configurations."""
        formatter = OperationTableFormatter(table_format="simple")
        operation_log = OperationLog(operation_name="FORMAT_TEST")

        sub_op = SubOperationLog(
            step_number=1,
            operation_name="TEST_OP",
            target="target",
            start_time=time.time(),
        )
        sub_op.mark_completed(response_data={"data": True})
        operation_log.sub_operations = [sub_op]
        operation_log.mark_completed(success=True)

        result = formatter.format_operation_log(operation_log)

        assert "FORMAT_TEST" in result
        # Simple format should not have grid borders
        assert "+" not in result or result.count("+") < 5

    def test_text_truncation(self):
        """Test text truncation for long values."""
        formatter = OperationTableFormatter()
        operation_log = OperationLog(operation_name="TRUNCATION_TEST")

        # Create sub-operation with very long name
        long_operation_name = "VERY_LONG_OPERATION_NAME_THAT_SHOULD_BE_TRUNCATED"
        sub_op = SubOperationLog(
            step_number=1,
            operation_name=long_operation_name,
            target="very_long_target_name_that_exceeds_normal_length",
            start_time=time.time(),
        )
        sub_op.mark_completed(response_data={"data": True})
        operation_log.sub_operations = [sub_op]
        operation_log.mark_completed(success=True)

        result = formatter.format_operation_log(operation_log)

        # Check that text is truncated (should contain "...")
        assert "..." in result

    def test_none_operation_log(self):
        """Test handling of None operation log."""
        formatter = OperationTableFormatter()

        result = formatter.format_operation_log(None)

        assert "No operation data available." in result

    def test_available_formats(self):
        """Test getting available table formats."""
        formatter = OperationTableFormatter()
        formats = formatter.get_available_formats()

        assert isinstance(formats, list)
        assert "grid" in formats
        assert "simple" in formats
        assert "plain" in formats

    def test_set_table_format(self):
        """Test changing table format."""
        formatter = OperationTableFormatter()
        original_format = formatter.table_format

        formatter.set_table_format("plain")
        assert formatter.table_format == "plain"

        # Reset to original
        formatter.set_table_format(original_format)
