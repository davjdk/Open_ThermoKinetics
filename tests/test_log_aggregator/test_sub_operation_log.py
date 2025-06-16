"""
Unit tests for SubOperationLog with enhanced error handling capabilities.

Tests the extended functionality including error details, exception tracking,
and automatic error analysis integration.
"""

from unittest.mock import Mock, patch

from src.core.log_aggregator.error_handler import ErrorAnalysis, ErrorCategory, ErrorSeverity
from src.core.log_aggregator.sub_operation_log import SubOperationLog


class TestSubOperationLogEnhanced:
    """Test cases for enhanced SubOperationLog functionality."""

    def test_basic_creation_with_new_fields(self):
        """Test SubOperationLog creation with new error handling fields."""
        sub_operation = SubOperationLog(
            step_number=1,
            operation_name="TEST_OP",
            target="test_target",
            start_time=1640995200.0,
            error_details=None,
            exception_traceback=None,
            response_data_raw=None,
        )

        assert sub_operation.step_number == 1
        assert sub_operation.operation_name == "TEST_OP"
        assert sub_operation.target == "test_target"
        assert sub_operation.error_details is None
        assert sub_operation.exception_traceback is None
        assert sub_operation.response_data_raw is None

    def test_has_detailed_error_false(self):
        """Test has_detailed_error returns False when no error details."""
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )

        assert not sub_operation.has_detailed_error()

    def test_has_detailed_error_true(self):
        """Test has_detailed_error returns True when error details exist."""
        error_details = ErrorAnalysis(
            error_type=ErrorCategory.DATA_VALIDATION_ERROR,
            error_message="Test error",
            error_context={},
            severity=ErrorSeverity.HIGH,
            suggested_action="Fix the data",
        )

        sub_operation = SubOperationLog(
            step_number=1,
            operation_name="TEST_OP",
            target="test_target",
            start_time=1640995200.0,
            error_details=error_details,
        )

        assert sub_operation.has_detailed_error()

    def test_get_error_summary_with_error_details(self):
        """Test get_error_summary with error details present."""
        error_details = ErrorAnalysis(
            error_type=ErrorCategory.COMMUNICATION_ERROR,
            error_message="Connection failed",
            error_context={},
            severity=ErrorSeverity.CRITICAL,
            suggested_action="Check network",
        )

        sub_operation = SubOperationLog(
            step_number=1,
            operation_name="TEST_OP",
            target="test_target",
            start_time=1640995200.0,
            error_details=error_details,
        )

        summary = sub_operation.get_error_summary()
        assert summary == "communication_error: Connection failed"

    def test_get_error_summary_with_exception_only(self):
        """Test get_error_summary with only exception traceback."""
        exception_tb = "ValueError: Invalid input"

        sub_operation = SubOperationLog(
            step_number=1,
            operation_name="TEST_OP",
            target="test_target",
            start_time=1640995200.0,
            exception_traceback=exception_tb,
        )

        summary = sub_operation.get_error_summary()
        assert summary == "ValueError: Invalid input"

    def test_get_error_summary_truncation(self):
        """Test get_error_summary truncates long error messages."""
        long_error = "A" * 100  # 100 character error message

        sub_operation = SubOperationLog(
            step_number=1,
            operation_name="TEST_OP",
            target="test_target",
            start_time=1640995200.0,
            error_details=ErrorAnalysis(
                error_type=ErrorCategory.UNKNOWN_ERROR,
                error_message=long_error,
                error_context={},
                severity=ErrorSeverity.LOW,
                suggested_action=None,
            ),
        )

        summary = sub_operation.get_error_summary()
        assert len(summary) <= 53  # 50 characters + "..."
        assert summary.endswith("...")

    def test_get_error_summary_with_no_error(self):
        """Test get_error_summary with no error information."""
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )

        summary = sub_operation.get_error_summary()
        assert summary == "Unknown error"

    @patch("src.core.log_aggregator.error_handler.SubOperationErrorHandler")
    def test_analyze_error_if_needed_called(self, mock_handler_class):
        """Test _analyze_error_if_needed is called when conditions are met."""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        mock_analysis = ErrorAnalysis(
            error_type=ErrorCategory.FILE_OPERATION_ERROR,
            error_message="Access denied",
            error_context={},
            severity=ErrorSeverity.HIGH,
            suggested_action="Check permissions",
        )
        mock_handler.analyze_error.return_value = mock_analysis

        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )  # Simulate error condition requiring analysis
        sub_operation.mark_completed(None, exception_info="ValueError: Test error")

        # Verify handler was called
        mock_handler_class.assert_called_once()
        mock_handler.analyze_error.assert_called_once()
        assert sub_operation.error_details == mock_analysis

    @patch("src.core.log_aggregator.error_handler.SubOperationErrorHandler")
    def test_analyze_error_if_needed_not_called_for_success(self, mock_handler_class):
        """Test _analyze_error_if_needed is not called for successful operations."""
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )

        sub_operation.mark_completed({"data": {"result": "success"}})

        # Verify handler was not called for successful operation
        mock_handler_class.assert_not_called()

    def test_mark_completed_with_exception_saves_traceback(self):
        """Test mark_completed saves exception traceback."""
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )

        test_exception = ValueError("Test error message")

        with patch("src.core.log_aggregator.error_handler.SubOperationErrorHandler"):
            sub_operation.mark_completed(None, exception_info=str(test_exception))

        # Verify exception information is captured
        assert sub_operation.exception_traceback is not None
        assert "Test error message" in sub_operation.exception_traceback

    def test_mark_completed_saves_raw_response_data(self):
        """Test mark_completed saves raw response data."""
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )

        response_data = {"test": "data", "complex": [1, 2, 3]}
        sub_operation.mark_completed(response_data)

        assert sub_operation.response_data_raw == response_data

    def test_mark_completed_with_different_data_types(self):
        """Test mark_completed handles different response data types correctly."""
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )

        # Test with DataFrame (simulated as dict)
        df_like_data = {"columns": ["A", "B"], "data": [[1, 2], [3, 4]]}
        sub_operation.mark_completed(df_like_data)

        assert sub_operation.response_data_raw == df_like_data
        assert sub_operation.data_type == "list"  # The "data" field is a list

    @patch("src.core.log_aggregator.error_handler.SubOperationErrorHandler")
    def test_error_analysis_integration(self, mock_handler_class):
        """Test complete error analysis integration workflow."""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        # Create detailed error analysis
        mock_analysis = ErrorAnalysis(
            error_type=ErrorCategory.CALCULATION_ERROR,
            error_message="Division by zero",
            error_context={"operation": "divide", "operands": [10, 0]},
            severity=ErrorSeverity.HIGH,
            suggested_action="Check for zero values before division; Add input validation",
        )
        mock_handler.analyze_error.return_value = mock_analysis

        sub_operation = SubOperationLog(
            step_number=1, operation_name="CALCULATE", target="math_module", start_time=1640995200.0
        )

        # Simulate error during operation
        error_exception = ZeroDivisionError("division by zero")
        sub_operation.mark_completed(None, exception_info=str(error_exception))

        # Verify comprehensive error handling
        assert sub_operation.status == "Error"
        assert sub_operation.error_details == mock_analysis
        assert sub_operation.has_detailed_error()
        assert sub_operation.get_error_summary() == "calculation_error: Division by zero"
        assert sub_operation.exception_traceback is not None
        assert "division by zero" in sub_operation.exception_traceback

        # Verify error handler was called with correct parameters
        mock_handler.analyze_error.assert_called_once()
        call_args = mock_handler.analyze_error.call_args
        # Verify that the sub_operation instance was passed
        assert call_args[0][0] == sub_operation  # First positional argument is the sub_operation

    def test_backward_compatibility(self):
        """Test that new features don't break existing functionality."""
        # Create SubOperationLog the old way (without new fields)
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )  # Test original functionality still works
        sub_operation.mark_completed({"data": {"key": "value"}})

        assert sub_operation.status == "OK"
        assert sub_operation.data_type == "dict"
        assert sub_operation.response_data_raw == {"data": {"key": "value"}}

        # Test new functionality with defaults
        assert not sub_operation.has_detailed_error()
        assert sub_operation.get_error_summary() == "Unknown error"  # Default when no error
