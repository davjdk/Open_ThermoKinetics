"""
Performance tests for log aggregator error analysis.

This module tests performance characteristics of the error analysis
and formatting system to ensure minimal impact on application performance.
"""

import time

import pytest

from src.core.log_aggregator.error_handler import ErrorAnalysis, ErrorCategory, ErrorSeverity
from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.sub_operation_log import SubOperationLog
from src.core.log_aggregator.table_formatter import OperationTableFormatter


class TestErrorAnalysisPerformance:
    """Test performance impact of error analysis."""

    def test_error_analysis_performance(self):
        """Test that error analysis doesn't significantly impact performance."""
        # Create a sub-operation with error
        sub_op = SubOperationLog(
            step_number=1, operation_name="TEST_OPERATION", target="test_target", start_time=time.time()
        )
        sub_op.mark_completed(response_data=None)
        sub_op.status = "Error"

        # Simulate error details
        error_analysis = ErrorAnalysis(
            error_type=ErrorCategory.DATA_VALIDATION_ERROR,
            severity=ErrorSeverity.HIGH,
            error_message="Test error message",
            error_context={"test_key": "test_value"},
            technical_details="Test technical details",
            suggested_action="Test suggested action",
        )
        sub_op.error_details = error_analysis

        # Measure formatting performance
        formatter = OperationTableFormatter(include_error_details=True)

        start_time = time.time()
        result = formatter._format_single_error_details(sub_op)
        end_time = time.time()

        execution_time = end_time - start_time

        # Assert that formatting takes less than 10ms
        assert execution_time < 0.01, f"Error details formatting took {execution_time:.4f}s, expected < 0.01s"

        # Assert that result contains expected content
        assert "TEST_OPERATION" in result
        assert "HIGH" in result
        assert "Test error message" in result

    def test_large_operation_log_formatting(self):
        """Test formatting performance with large operation logs."""
        # Create operation with many sub-operations
        op_log = OperationLog(operation_name="LARGE_OPERATION", start_time=time.time())

        # Create 100 sub-operations with mixed statuses
        for i in range(100):
            sub_op = SubOperationLog(
                step_number=i + 1,
                operation_name=f"SUB_OPERATION_{i}",
                target=f"target_{i % 5}",  # Vary targets
                start_time=time.time(),
            )

            # Make every 10th operation have an error
            if i % 10 == 0:
                sub_op.mark_completed(response_data=None)
                sub_op.status = "Error"
            else:
                sub_op.mark_completed(response_data={"success": True, "data": f"result_{i}"})

            op_log.sub_operations.append(sub_op)

        op_log.mark_completed(success=True)

        # Measure formatting performance
        formatter = OperationTableFormatter(include_error_details=True)

        start_time = time.time()
        result = formatter.format_operation_log(op_log)
        end_time = time.time()

        execution_time = end_time - start_time

        # Assert that formatting takes less than 100ms for 100 sub-operations
        assert execution_time < 0.1, f"Large operation formatting took {execution_time:.4f}s, expected < 0.1s"

        # Assert that result contains expected content
        assert "LARGE_OPERATION" in result
        assert "steps 100" in result
        assert "SUB_OPERATION_0" in result
        assert "SUB_OPERATION_99" in result

    def test_error_details_overhead(self):
        """Test overhead of error details vs normal formatting."""
        # Create operation with sub-operations having errors
        op_log = OperationLog(operation_name="OVERHEAD_TEST", start_time=time.time())

        # Create 50 sub-operations with errors
        for i in range(50):
            sub_op = SubOperationLog(
                step_number=i + 1, operation_name=f"ERROR_OP_{i}", target=f"target_{i}", start_time=time.time()
            )
            sub_op.mark_completed(response_data=None)
            sub_op.status = "Error"
            op_log.sub_operations.append(sub_op)

        op_log.mark_completed(success=False)

        # Test formatting without error details
        formatter_no_errors = OperationTableFormatter(include_error_details=False)
        start_time = time.time()
        result_no_errors = formatter_no_errors.format_operation_log(op_log)
        time_no_errors = time.time() - start_time

        # Test formatting with error details
        formatter_with_errors = OperationTableFormatter(include_error_details=True)
        start_time = time.time()
        result_with_errors = formatter_with_errors.format_operation_log(op_log)
        time_with_errors = time.time() - start_time

        # Both should complete quickly
        assert time_no_errors < 0.05, f"No error details formatting took {time_no_errors:.4f}s"
        assert time_with_errors < 0.1, f"With error details formatting took {time_with_errors:.4f}s"

        # Results should be different
        assert len(result_with_errors) >= len(result_no_errors)
        assert "OVERHEAD_TEST" in result_no_errors
        assert "OVERHEAD_TEST" in result_with_errors

    def test_formatter_configuration_performance(self):
        """Test that changing formatter configuration doesn't impact performance."""
        formatter = OperationTableFormatter()

        # Create simple operation log
        op_log = OperationLog(operation_name="CONFIG_TEST", start_time=time.time())
        sub_op = SubOperationLog(
            step_number=1, operation_name="SIMPLE_OP", target="simple_target", start_time=time.time()
        )
        sub_op.mark_completed(response_data={"success": True})
        op_log.sub_operations.append(sub_op)
        op_log.mark_completed(success=True)

        # Test multiple configuration changes
        configurations = [
            {"include_error_details": True, "max_error_context_items": 5},
            {"include_error_details": False, "max_error_context_items": 3},
            {"include_error_details": True, "max_error_context_items": 10},
            {"include_error_details": False, "max_error_context_items": 1},
        ]

        total_time = 0
        for config in configurations:
            formatter.include_error_details = config["include_error_details"]
            formatter.max_error_context_items = config["max_error_context_items"]

            start_time = time.time()
            result = formatter.format_operation_log(op_log)
            execution_time = time.time() - start_time
            total_time += execution_time

            assert "CONFIG_TEST" in result

        # All configurations should complete quickly
        average_time = total_time / len(configurations)
        assert average_time < 0.01, f"Average configuration time {average_time:.4f}s, expected < 0.01s"

    @pytest.mark.parametrize("num_operations", [10, 50, 100, 200])
    def test_scalability_with_operation_count(self, num_operations):
        """Test scalability with different numbers of operations."""
        op_log = OperationLog(operation_name=f"SCALE_TEST_{num_operations}", start_time=time.time())

        # Create specified number of sub-operations
        for i in range(num_operations):
            sub_op = SubOperationLog(
                step_number=i + 1, operation_name=f"OP_{i}", target=f"target_{i % 3}", start_time=time.time()
            )
            sub_op.mark_completed(response_data={"success": True, "data": i})
            op_log.sub_operations.append(sub_op)

        op_log.mark_completed(success=True)

        formatter = OperationTableFormatter(include_error_details=True)

        start_time = time.time()
        result = formatter.format_operation_log(op_log)
        execution_time = time.time() - start_time

        # Performance should scale reasonably (linear or better)
        max_expected_time = num_operations * 0.001  # 1ms per operation max
        assert execution_time < max_expected_time, (
            f"Formatting {num_operations} operations took {execution_time:.4f}s, "
            f"expected < {max_expected_time:.4f}s"
        )

        # Result should contain expected content
        assert f"SCALE_TEST_{num_operations}" in result
        assert f"steps {num_operations}" in result
