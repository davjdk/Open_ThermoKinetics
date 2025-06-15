"""
Tests for table formatting functionality.

This module tests the formatting of operation logs into readable tables:
- Table structure and formatting
- Operation header formatting
- Summary formatting
- Edge cases in formatting
"""

import time

from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.sub_operation_log import SubOperationLog
from src.core.log_aggregator.table_formatter import OperationTableFormatter, format_operation_log


class TestOperationTableFormatter:
    """Test cases for OperationTableFormatter class."""

    def test_formatter_initialization(self):
        """Test that formatter initializes correctly."""
        formatter = OperationTableFormatter()
        assert formatter is not None

    def test_format_empty_operation(self):
        """Test formatting operation with no sub-operations."""
        op_log = OperationLog(operation_name="EMPTY_OPERATION", start_time=time.time())
        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)

        assert "EMPTY_OPERATION" in result
        assert "COMPLETED" in result  # "completed" in English
        assert "steps 0" in result
        assert "time" in result or "Duration:" in result

    def test_format_operation_with_suboperations(self, sample_operation_log):
        """Test formatting operation with multiple sub-operations."""
        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(sample_operation_log)  # Check header (English output)
        assert "TEST_OPERATION" in result
        assert "id=" in result  # Operation ID

        # Check table headers (English)
        assert "Step" in result  # "Step" in English
        assert "Sub-operation" in result  # "Operation" in English
        assert "Target" in result  # "Target" in English
        assert "Result data type" in result  # "Data Type" in English
        assert "Status" in result  # "Status" in English
        assert "Time" in result  # "Duration" in English

        # Check that all sub-operations are included
        assert "GET_VALUE" in result
        assert "SET_VALUE" in result
        assert "INVALID_OP" in result  # Check status representations
        assert "OK" in result  # Success indicator in English
        assert "Error" in result  # Failure indicator in English

        # Check summary
        assert "steps 3" in result  # "3 sub-operations" in English
        assert "successful 2" in result  # "2 successful" in English
        assert "with errors 1" in result  # "1 failed" in English

    def test_format_operation_headers(self, sample_operation_log):
        """Test that operation headers are formatted correctly."""
        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(sample_operation_log)

        lines = result.split("\n")
        header_line = next(line for line in lines if "TEST_OPERATION" in line and "STARTED" in line)

        assert "TEST_OPERATION" in header_line
        assert "STARTED" in header_line  # "STARTED" in English
        assert "id=" in header_line  # Operation ID    def test_format_operation_summary(self, sample_operation_log):
        """Test that operation summary is formatted correctly."""
        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(sample_operation_log)

        lines = result.split("\n")
        summary_line = next(line for line in lines if "steps" in line and "successful" in line)

        assert "steps 3" in summary_line
        assert "successful 2" in summary_line
        assert "with errors 1" in summary_line

    def test_format_different_data_types(self):
        """Test formatting with different response data types."""
        op_log = OperationLog(operation_name="DATA_TYPES_TEST", start_time=time.time())

        # Create sub-operations with different data types
        data_types = [
            ({"data": True}, "bool"),
            ({"data": 42}, "int"),
            ({"data": "test"}, "str"),
            ({"data": [1, 2, 3]}, "list"),
            ({"data": {"key": "value"}}, "dict"),
            ({"data": None}, "None"),  # Output shows "None" not "NoneType"
            ({"data": 3.14}, "float"),
        ]

        for i, (response_data, expected_type) in enumerate(data_types):
            sub_op = SubOperationLog(
                step_number=i + 1,
                operation_name=f"OP_{expected_type.upper()}",
                target="test_target",
                start_time=time.time(),
                request_kwargs={},
            )
            sub_op.mark_completed(response_data=response_data)
            op_log.sub_operations.append(sub_op)

        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)

        # Check that all data types are represented
        for _, expected_type in data_types:
            assert expected_type in result

    def test_format_status_indicators(self):
        """Test that status indicators are formatted correctly."""
        op_log = OperationLog(operation_name="STATUS_TEST", start_time=time.time())

        # Create successful sub-operation
        sub_op1 = SubOperationLog(
            step_number=1, operation_name="SUCCESS_OP", target="test_target", start_time=time.time(), request_kwargs={}
        )
        sub_op1.mark_completed(response_data={"data": "success"})

        # Create failed sub-operation
        sub_op2 = SubOperationLog(
            step_number=2, operation_name="FAILED_OP", target="test_target", start_time=time.time(), request_kwargs={}
        )
        sub_op2.mark_completed(response_data=None, exception_info="Test error")

        op_log.sub_operations.extend([sub_op1, sub_op2])
        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)  # Check status indicators
        assert "OK" in result  # Success indicator
        assert "Error" in result  # Failure indicator

    def test_format_timing_information(self, deterministic_time):
        """Test that timing information is formatted correctly."""
        op_log = OperationLog(operation_name="TIMING_TEST", start_time=deterministic_time)
        sub_op = SubOperationLog(
            step_number=1,
            operation_name="TIMED_OP",
            target="test_target",
            start_time=deterministic_time + 0.1,
            request_kwargs={},
        )  # Mock time advancement and mark as completed
        sub_op.end_time = deterministic_time + 0.2
        sub_op.mark_completed(response_data={"data": "success"})
        sub_op.execution_time = 0.1  # 100ms - override after mark_completed

        op_log.sub_operations.append(sub_op)
        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)  # Check that duration is included
        assert "0.100" in result  # 100ms duration formatted as 0.100 seconds
        assert "Duration:" in result or "Time, s" in result

    def test_format_long_operation_names(self):
        """Test formatting with very long operation names."""
        op_log = OperationLog(
            operation_name="VERY_LONG_OPERATION_NAME_THAT_MIGHT_BREAK_FORMATTING", start_time=time.time()
        )

        sub_op = SubOperationLog(
            step_number=1,
            operation_name="ANOTHER_VERY_LONG_OPERATION_NAME_FOR_SUB_OPERATION",
            target="very_long_target_name_that_should_not_break_table",
            start_time=time.time(),
            request_kwargs={"very_long_parameter_name": "very_long_parameter_value"},
        )
        sub_op.mark_completed(response_data={"data": "success"})
        op_log.sub_operations.append(sub_op)
        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)

        # Should not raise exception and should contain the operation names (or their truncated versions)
        assert "VERY_LONG_OPERATION_NAME" in result
        # The sub-operation name might be truncated in the table, so check for truncated version
        assert "ANOTHER_VERY_LONG..." in result or "ANOTHER_VERY_LONG_OPERATION_NAME" in result

    def test_format_special_characters(self):
        """Test formatting with special characters in data."""
        op_log = OperationLog(operation_name="SPECIAL_CHARS_TEST", start_time=time.time())

        sub_op = SubOperationLog(
            step_number=1,
            operation_name="SPECIAL_OP",
            target="test_target",
            start_time=time.time(),
            request_kwargs={"path": "C:\\Windows\\System32\\file.txt", "regex": r"\d+\.\d+"},
        )
        sub_op.mark_completed(response_data={"data": "success with üñíçødé"})
        op_log.sub_operations.append(sub_op)
        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)  # Should handle special characters without issues
        assert "SPECIAL_OP" in result
        # The actual response data doesn't appear in the table, just the data type
        assert "str" in result  # Data type shows as 'str'


class TestFormatOperationLogFunction:
    """Test cases for the format_operation_log convenience function."""

    def test_format_operation_log_function(self, sample_operation_log):
        """Test the format_operation_log convenience function."""
        result = format_operation_log(sample_operation_log)

        assert isinstance(result, str)
        assert "TEST_OPERATION" in result
        assert "steps 3" in result

    def test_format_operation_log_with_none(self):
        """Test format_operation_log with None input."""
        result = format_operation_log(None)
        assert result == "No operation data available."

    def test_format_operation_log_consistency(self, sample_operation_log):
        """Test that convenience function produces same result as formatter."""
        formatter = OperationTableFormatter()
        direct_result = formatter.format_operation_log(sample_operation_log)
        convenience_result = format_operation_log(sample_operation_log)

        # The results should be identical since we're using the same operation log
        # If they differ, it's likely due to ID incrementing - check core content
        if direct_result != convenience_result:  # Strip out the operation ID from both results for comparison
            import re

            direct_no_id = re.sub(r"\(id=\d+,", "(id=X,", direct_result)
            convenience_no_id = re.sub(r"\(id=\d+,", "(id=X,", convenience_result)
            assert direct_no_id == convenience_no_id
        else:
            assert direct_result == convenience_result


class TestTableFormattingEdgeCases:
    """Test edge cases in table formatting."""

    def test_format_operation_with_no_duration(self):
        """Test formatting operation where duration calculation might fail."""
        op_log = OperationLog(operation_name="NO_DURATION_TEST", start_time=time.time())

        # Don't call mark_completed to simulate incomplete operation
        op_log.end_time = None

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)

        # Should handle missing duration gracefully
        assert "NO_DURATION_TEST" in result

    def test_format_suboperation_with_no_duration(self):
        """Test formatting sub-operation with missing timing information."""
        op_log = OperationLog(operation_name="SUB_NO_DURATION_TEST", start_time=time.time())

        sub_op = SubOperationLog(
            step_number=1,
            operation_name="NO_TIMING_OP",
            target="test_target",
            start_time=time.time(),
            request_kwargs={},
        )
        # Don't set end_time to simulate timing issue
        sub_op.status = "completed"
        sub_op.response_data = {"data": "success"}
        sub_op.response_data_type = "dict"

        op_log.sub_operations.append(sub_op)
        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)

        # Should handle missing sub-operation duration gracefully
        assert "NO_TIMING_OP" in result

    def test_format_with_empty_response_data(self):
        """Test formatting with empty or missing response data."""
        op_log = OperationLog(operation_name="EMPTY_RESPONSE_TEST", start_time=time.time())

        sub_op = SubOperationLog(
            step_number=1,
            operation_name="EMPTY_RESPONSE_OP",
            target="test_target",
            start_time=time.time(),
            request_kwargs={},
        )
        sub_op.mark_completed(response_data=None)
        op_log.sub_operations.append(sub_op)
        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)

        assert "EMPTY_RESPONSE_OP" in result
        assert "NoneType" in result or "None" in result

    def test_format_with_complex_nested_data(self):
        """Test formatting with complex nested data structures."""
        op_log = OperationLog(operation_name="COMPLEX_DATA_TEST", start_time=time.time())

        complex_data = {
            "data": {
                "nested": {"deeply": {"nested": ["array", "with", {"mixed": "types"}]}},
                "numbers": [1, 2, 3, 4, 5] * 100,  # Large array
            }
        }

        sub_op = SubOperationLog(
            step_number=1,
            operation_name="COMPLEX_OP",
            target="test_target",
            start_time=time.time(),
            request_kwargs={"complex_param": complex_data},
        )
        sub_op.mark_completed(response_data=complex_data)
        op_log.sub_operations.append(sub_op)
        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(op_log)

        # Should handle complex data without breaking
        assert "COMPLEX_OP" in result
        assert "dict" in result

    def test_format_operation_status_variations(self):
        """Test formatting with different operation status variations."""
        status_cases = [
            ("completed", True, None),
            ("failed", False, "RuntimeError: Test error"),
            ("failed", False, "ValueError: Another error"),
        ]

        for i, (expected_status, success, exception_info) in enumerate(status_cases):
            op_log = OperationLog(operation_name=f"STATUS_TEST_{i}", start_time=time.time())
            op_log.mark_completed(success=success, exception_info=exception_info)

            formatter = OperationTableFormatter()
            result = formatter.format_operation_log(op_log)

            assert f"STATUS_TEST_{i}" in result
            if expected_status == "completed":
                assert "COMPLETED" in result.upper()
            else:
                # Failed operations show as "COMPLETED (status: with error)"
                assert "WITH ERROR" in result.upper() or "FAILED" in result.upper()
                if exception_info:
                    assert exception_info in result
