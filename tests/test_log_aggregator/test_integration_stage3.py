"""
Integration tests for Stage 3 formatting integration.

This module tests the complete integration of error handling
with formatting functionality, ensuring end-to-end operation.
"""

import time

from src.core.log_aggregator import (
    AggregatedOperationLogger,
    ErrorAnalysis,
    ErrorCategory,
    ErrorSeverity,
    OperationLog,
    OperationTableFormatter,
    SubOperationLog,
    get_aggregated_logger,
)


class TestFormattingIntegration:
    """Test complete integration of error handling with formatting."""

    def test_end_to_end_error_logging(self):
        """Test complete end-to-end error logging flow."""
        # Create operation with sub-operations having detailed errors
        op_log = OperationLog(operation_name="MODEL_FIT_CALCULATION", start_time=time.time())

        # Create sub-operation with detailed error
        sub_op1 = SubOperationLog(
            step_number=1, operation_name="GET_SERIES_VALUE", target="series_data", start_time=time.time()
        )
        sub_op1.mark_completed(response_data=None)
        sub_op1.status = "Error"

        # Add detailed error analysis
        error_analysis = ErrorAnalysis(
            error_type=ErrorCategory.DATA_VALIDATION_ERROR,
            severity=ErrorSeverity.HIGH,
            error_message="Series data not found or invalid format",
            error_context={
                "Target series": "test_series",
                "Expected path": ["test_series", "experimental_data"],
                "Actual data type": "None",
            },
            technical_details="KeyError in series_data.get_value() - missing experimental_data key",
            suggested_action="Verify series data exists and has correct structure",
        )
        sub_op1.error_details = error_analysis  # Create successful sub-operation
        sub_op2 = SubOperationLog(
            step_number=2, operation_name="UPDATE_SERIES", target="series_data", start_time=time.time()
        )
        sub_op2.mark_completed(response_data={"success": True, "data": {"result": "updated"}})
        sub_op2.status = "OK"  # Explicitly set status to OK

        op_log.sub_operations = [sub_op1, sub_op2]
        op_log.mark_completed(success=True)

        # Test formatting with error details enabled
        formatter = OperationTableFormatter(include_error_details=True)
        result = formatter.format_operation_log(op_log)

        # Verify operation header
        assert "MODEL_FIT_CALCULATION" in result
        assert "=" * 80 in result

        # Verify sub-operations table
        assert "GET_SERIES_VALUE" in result
        assert "UPDATE_SERIES" in result
        assert "Error" in result
        assert "OK" in result

        # Verify error details block
        assert "ERROR DETAILS:" in result
        assert "Step 1:" in result
        assert "DATA_VALIDATION_ERROR" in result
        assert "HIGH" in result
        assert "Series data not found or invalid format" in result
        assert "Target series: test_series" in result
        assert "KeyError in series_data.get_value()" in result
        assert "Verify series data exists" in result

        # Verify summary
        assert "steps 2" in result
        assert "successful 1" in result
        assert "with errors 1" in result

    def test_error_details_disabled(self):
        """Test operation when error details are disabled."""
        # Create operation with error sub-operations
        op_log = OperationLog(operation_name="TEST_OPERATION", start_time=time.time())

        # Create sub-operation with detailed error
        sub_op = SubOperationLog(
            step_number=1, operation_name="FAILING_OPERATION", target="test_target", start_time=time.time()
        )
        sub_op.mark_completed(response_data=None)
        sub_op.status = "Error"

        # Add detailed error analysis
        error_analysis = ErrorAnalysis(
            error_type=ErrorCategory.CALCULATION_ERROR,
            severity=ErrorSeverity.CRITICAL,
            error_message="Critical calculation failure",
            error_context={"param1": "value1", "param2": "value2"},
            technical_details="Division by zero in calculation module",
            suggested_action="Check input parameters for valid ranges",
        )
        sub_op.error_details = error_analysis

        op_log.sub_operations = [sub_op]
        op_log.mark_completed(success=False)

        # Test formatting with error details disabled
        formatter = OperationTableFormatter(include_error_details=False)
        result = formatter.format_operation_log(op_log)

        # Verify basic content is present
        assert "TEST_OPERATION" in result
        assert "FAILING_OPERATION" in result
        assert "Error" in result

        # Verify error details block is NOT present
        assert "ERROR DETAILS:" not in result
        assert "CALCULATION_ERROR" not in result
        assert "CRITICAL" not in result
        assert "Critical calculation failure" not in result
        assert "Division by zero" not in result

    def test_aggregated_logger_error_details_configuration(self):
        """Test aggregated logger with configurable error details."""
        # Test with error details enabled
        logger_with_errors = AggregatedOperationLogger(include_error_details=True)
        assert logger_with_errors.get_error_details_enabled() is True

        # Test with error details disabled
        logger_no_errors = AggregatedOperationLogger(include_error_details=False)
        assert logger_no_errors.get_error_details_enabled() is False

        # Test changing configuration
        logger_with_errors.set_error_details_enabled(False)
        assert logger_with_errors.get_error_details_enabled() is False

        logger_no_errors.set_error_details_enabled(True)
        assert logger_no_errors.get_error_details_enabled() is True

    def test_max_error_context_items_limit(self):
        """Test that error context items are limited by max_error_context_items."""
        # Create sub-operation with many context items
        sub_op = SubOperationLog(
            step_number=1, operation_name="CONTEXT_TEST", target="test_target", start_time=time.time()
        )
        sub_op.mark_completed(response_data=None)
        sub_op.status = "Error"

        # Add error with many context items
        large_context = {f"context_key_{i}": f"value_{i}" for i in range(10)}
        error_analysis = ErrorAnalysis(
            error_type=ErrorCategory.DATA_VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            error_message="Test error with many context items",
            error_context=large_context,
            technical_details="Test technical details",
            suggested_action="Test suggested action",
        )
        sub_op.error_details = error_analysis

        # Test with limit of 3 context items
        formatter = OperationTableFormatter(include_error_details=True, max_error_context_items=3)
        result = formatter._format_single_error_details(sub_op)

        # Count context items in result
        context_lines = [line for line in result.split("\n") if line.strip().startswith("- context_key_")]
        assert len(context_lines) == 3, f"Expected 3 context items, got {len(context_lines)}"

        # Verify first 3 items are present
        assert "context_key_0: value_0" in result
        assert "context_key_1: value_1" in result
        assert "context_key_2: value_2" in result

        # Verify later items are not present
        assert "context_key_5: value_5" not in result
        assert "context_key_9: value_9" not in result

    def test_mixed_error_types_formatting(self):
        """Test formatting of operations with mixed error types."""
        op_log = OperationLog(operation_name="MIXED_ERRORS_TEST", start_time=time.time())

        # Create sub-operations with different error types
        error_types = [
            (ErrorCategory.DATA_VALIDATION_ERROR, ErrorSeverity.HIGH),
            (ErrorCategory.CALCULATION_ERROR, ErrorSeverity.CRITICAL),
            (ErrorCategory.COMMUNICATION_ERROR, ErrorSeverity.MEDIUM),
            (ErrorCategory.SYSTEM_ERROR, ErrorSeverity.LOW),
            (ErrorCategory.USER_INPUT_ERROR, ErrorSeverity.HIGH),
        ]

        for i, (error_type, severity) in enumerate(error_types):
            sub_op = SubOperationLog(
                step_number=i + 1, operation_name=f"ERROR_OP_{i}", target=f"target_{i}", start_time=time.time()
            )
            sub_op.mark_completed(response_data=None)
            sub_op.status = "Error"

            error_analysis = ErrorAnalysis(
                error_type=error_type,
                severity=severity,
                error_message=f"Error message for {error_type.value}",
                error_context={"error_index": i, "error_type": error_type.value},
                technical_details=f"Technical details for {error_type.value}",
                suggested_action=f"Action for {error_type.value}",
            )
            sub_op.error_details = error_analysis
            op_log.sub_operations.append(sub_op)

        op_log.mark_completed(success=False)

        # Format with error details
        formatter = OperationTableFormatter(include_error_details=True)
        result = formatter.format_operation_log(op_log)

        # Verify all error types are present
        for error_type, severity in error_types:
            assert error_type.value.upper() in result
            assert severity.value.upper() in result

        # Verify error details block structure
        assert "ERROR DETAILS:" in result
        assert "Step 1:" in result
        assert "Step 5:" in result

        # Verify summary shows all errors
        assert "steps 5" in result
        assert "with errors 5" in result
        assert "successful 0" in result

    def test_formatter_performance_with_error_details(self):
        """Test that error details don't significantly impact performance."""
        # Create large operation with many error sub-operations
        op_log = OperationLog(operation_name="PERFORMANCE_TEST", start_time=time.time())

        for i in range(50):
            sub_op = SubOperationLog(
                step_number=i + 1, operation_name=f"PERF_OP_{i}", target=f"target_{i % 5}", start_time=time.time()
            )

            # Make every 5th operation an error with detailed analysis
            if i % 5 == 0:
                sub_op.mark_completed(response_data=None)
                sub_op.status = "Error"

                error_analysis = ErrorAnalysis(
                    error_type=ErrorCategory.CALCULATION_ERROR,
                    severity=ErrorSeverity.HIGH,
                    error_message=f"Performance test error {i}",
                    error_context={"operation_index": i, "batch_number": i // 10, "error_frequency": "every_5th"},
                    technical_details=f"Simulated error for performance testing at index {i}",
                    suggested_action="This is a performance test, no action needed",
                )
                sub_op.error_details = error_analysis
            else:
                sub_op.mark_completed(response_data={"success": True, "index": i})

            op_log.sub_operations.append(sub_op)

        op_log.mark_completed(success=True)

        # Measure formatting time with error details
        formatter = OperationTableFormatter(include_error_details=True)
        start_time = time.time()
        result = formatter.format_operation_log(op_log)
        formatting_time = time.time() - start_time

        # Performance assertion: should complete within reasonable time
        assert formatting_time < 0.5, f"Formatting took {formatting_time:.3f}s, expected < 0.5s"

        # Verify result contains expected content
        assert "PERFORMANCE_TEST" in result
        assert "steps 50" in result
        assert "with errors 10" in result  # Every 5th of 50 = 10 errors
        assert "successful 40" in result

        # Verify error details are present
        assert "ERROR DETAILS:" in result
        assert "Performance test error" in result


class TestAggregatedLoggerIntegration:
    """Test integration with AggregatedOperationLogger."""

    def test_logger_with_error_details_enabled(self):
        """Test logger functionality with error details enabled."""
        # Create logger with error details
        logger = AggregatedOperationLogger(include_error_details=True)

        # Create operation with error
        op_log = OperationLog(operation_name="LOGGER_TEST", start_time=time.time())
        sub_op = SubOperationLog(
            step_number=1, operation_name="TEST_ERROR", target="test_target", start_time=time.time()
        )
        sub_op.mark_completed(response_data=None)
        sub_op.status = "Error"

        error_analysis = ErrorAnalysis(
            error_type=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.MEDIUM,
            error_message="Logger integration test error",
            error_context={"test_key": "test_value"},
        )
        sub_op.error_details = error_analysis
        op_log.sub_operations = [sub_op]
        op_log.mark_completed(success=False)

        # Log operation (should not raise exceptions)
        try:
            logger.log_operation(op_log)
            success = True
        except Exception as e:
            success = False
            error_msg = str(e)

        assert success, f"Logging operation failed: {error_msg if not success else 'Unknown error'}"

    def test_logger_configuration_changes(self):
        """Test changing logger configuration at runtime."""
        logger = get_aggregated_logger()

        # Test enabling/disabling error details
        original_setting = logger.get_error_details_enabled()

        logger.set_error_details_enabled(True)
        assert logger.get_error_details_enabled() is True

        logger.set_error_details_enabled(False)
        assert logger.get_error_details_enabled() is False

        # Restore original setting
        logger.set_error_details_enabled(original_setting)
        assert logger.get_error_details_enabled() == original_setting
