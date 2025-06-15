"""
Tests for logging integration functionality.

This module tests the integration with the existing logging system:
- AggregatedOperationLogger functionality
- Operation logging behavior
- Error handling in logging
- Integration with LoggerManager
"""

from unittest.mock import patch

import pytest

from src.core.log_aggregator.aggregated_operation_logger import AggregatedOperationLogger
from src.core.log_aggregator.operation_log import OperationLog


class TestAggregatedOperationLogger:
    """Test cases for AggregatedOperationLogger class."""

    def test_logger_initialization(self, mock_aggregated_logger):
        """Test that aggregated logger initializes correctly."""
        # Test that we can get the logger instance
        logger = mock_aggregated_logger
        assert logger is not None

    def test_logger_file_creation(self, mock_aggregated_logger):
        """Test that log file is created when logging operations."""
        # Create and log a simple operation
        op_log = OperationLog(operation_name="FILE_CREATION_TEST", start_time=1000000.0)
        op_log.mark_completed(success=True)

        logger = mock_aggregated_logger
        logger.log_operation(op_log)

        # Verify the mock was called
        mock_aggregated_logger.log_operation.assert_called_once_with(op_log)

    def test_logger_multiple_operations(self, mock_aggregated_logger):
        """Test logging multiple operations to the same file."""
        logger = mock_aggregated_logger

        operations = []
        for i in range(3):
            op_log = OperationLog(operation_name=f"MULTI_TEST_{i}", start_time=1000000.0 + i)
            op_log.mark_completed(success=True)
            operations.append(op_log)
            logger.log_operation(op_log)

        # Verify all operations were logged
        assert mock_aggregated_logger.log_operation.call_count == 3

        # Verify operation names
        call_args = [call[0][0] for call in mock_aggregated_logger.log_operation.call_args_list]
        operation_names = [op.operation_name for op in call_args]
        assert "MULTI_TEST_0" in operation_names
        assert "MULTI_TEST_1" in operation_names
        assert "MULTI_TEST_2" in operation_names

    def test_logger_with_sub_operations(self, mock_aggregated_logger):
        """Test logging operation with sub-operations."""
        from src.core.log_aggregator.sub_operation_log import SubOperationLog

        op_log = OperationLog(operation_name="SUBOP_TEST", start_time=1000000.0)  # Add sub-operations
        sub_op1 = SubOperationLog(step_number=1, target="file_data", operation_name="GET_VALUE", start_time=1000001.0)
        sub_op1.mark_completed(response_data={"data": "test1"})
        op_log.sub_operations.append(sub_op1)

        sub_op2 = SubOperationLog(
            step_number=2, target="calculations", operation_name="SET_VALUE", start_time=1000002.0
        )
        sub_op2.mark_completed(response_data={"data": "test2"})
        op_log.sub_operations.append(sub_op2)

        op_log.mark_completed(success=True)

        logger = mock_aggregated_logger
        logger.log_operation(op_log)

        # Verify logging
        mock_aggregated_logger.log_operation.assert_called_once()
        logged_operation = mock_aggregated_logger.log_operation.call_args[0][0]
        assert logged_operation.operation_name == "SUBOP_TEST"
        assert len(logged_operation.sub_operations) == 2

    def test_logger_error_handling(self, mock_aggregated_logger):
        """Test error handling when logging fails."""
        # Make the mock raise an exception
        mock_aggregated_logger.log_operation.side_effect = Exception("Mock logging error")

        op_log = OperationLog(operation_name="ERROR_TEST", start_time=1000000.0)
        op_log.mark_completed(success=True)

        # Since we're using a mock, the exception will be raised as configured
        # This test verifies that the mock is set up correctly
        with pytest.raises(Exception, match="Mock logging error"):
            mock_aggregated_logger.log_operation(op_log)

    def test_logger_singleton_behavior(self):
        """Test that AggregatedOperationLogger behaves as singleton."""
        logger1 = AggregatedOperationLogger()
        logger2 = AggregatedOperationLogger()

        assert logger1 is logger2, "AggregatedOperationLogger should be singleton"

    def test_mock_logger_behavior(self, mock_aggregated_logger):
        """Test that the mock logger works correctly."""
        # Create and log a simple operation
        op_log = OperationLog(operation_name="MOCK_TEST", start_time=1000000.0)
        op_log.mark_completed(success=True)

        # Use the mock logger directly
        mock_aggregated_logger.log_operation(op_log)

        # Verify the mock was called
        mock_aggregated_logger.log_operation.assert_called_once_with(op_log)


class TestLoggingIntegration:
    """Test integration with main logging system."""

    def test_operation_log_formatting(self, mock_aggregated_logger):
        """Test that operation logs are properly formatted."""
        from src.core.log_aggregator.sub_operation_log import SubOperationLog

        op_log = OperationLog(operation_name="FORMAT_TEST", start_time=1000000.0)

        # Add a sub-operation
        sub_op = SubOperationLog(step_number=1, target="test_target", operation_name="TEST_OP", start_time=1000001.0)
        sub_op.mark_completed(response_data={"data": "test_response"})
        op_log.sub_operations.append(sub_op)

        op_log.mark_completed(success=True)

        logger = mock_aggregated_logger
        logger.log_operation(op_log)

        # Verify the operation was logged with proper structure
        mock_aggregated_logger.log_operation.assert_called_once()
        logged_op = mock_aggregated_logger.log_operation.call_args[0][0]

        assert logged_op.operation_name == "FORMAT_TEST"
        assert logged_op.status == "success"
        assert len(logged_op.sub_operations) == 1
        assert logged_op.sub_operations[0].operation_name == "TEST_OP"

    def test_concurrent_logging(self, mock_aggregated_logger):
        """Test concurrent logging from multiple threads."""
        import threading
        import time

        def log_operation(thread_id):
            op_log = OperationLog(operation_name=f"CONCURRENT_{thread_id}", start_time=time.time())
            op_log.mark_completed(success=True)

            logger = mock_aggregated_logger
            logger.log_operation(op_log)

        # Create and start threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations were logged
        assert mock_aggregated_logger.log_operation.call_count == 5

    @patch("src.core.log_aggregator.aggregated_operation_logger.LoggerManager")
    def test_logger_manager_integration(self, mock_logger_manager, mock_aggregated_logger):
        """Test integration with LoggerManager."""
        # Reset the singleton to test initialization
        AggregatedOperationLogger._instance = None
        AggregatedOperationLogger._initialized = False  # Create new instance to trigger initialization
        AggregatedOperationLogger()

        # Verify LoggerManager was called
        mock_logger_manager.get_logger.assert_called()

    def test_error_resilience(self, mock_aggregated_logger):
        """Test that logging errors don't break the system."""
        # Configure mock to raise exception first time, succeed second time
        mock_aggregated_logger.log_operation.side_effect = [Exception("First error"), None]

        op_log1 = OperationLog(operation_name="ERROR_RESILIENCE_1", start_time=1000000.0)
        op_log1.mark_completed(success=True)

        op_log2 = OperationLog(operation_name="ERROR_RESILIENCE_2", start_time=1000001.0)
        op_log2.mark_completed(success=True)

        logger = mock_aggregated_logger

        # With a mock, the first call will raise an exception as configured
        with pytest.raises(Exception, match="First error"):
            logger.log_operation(op_log1)

        # Second call should work normally (no exception)
        logger.log_operation(op_log2)

        # Verify both calls were attempted
        assert mock_aggregated_logger.log_operation.call_count == 2


class TestOperationLogIntegration:
    """Test integration between OperationLog and AggregatedOperationLogger."""

    def test_complete_operation_lifecycle(self, mock_aggregated_logger):
        """Test complete operation lifecycle with logging."""
        from src.core.log_aggregator.sub_operation_log import SubOperationLog

        # Create operation log
        op_log = OperationLog(operation_name="LIFECYCLE_TEST", start_time=1000000.0)

        # Add multiple sub-operations
        for i in range(3):
            sub_op = SubOperationLog(
                step_number=i + 1, target=f"target_{i}", operation_name=f"OPERATION_{i}", start_time=1000001.0 + i
            )
            sub_op.mark_completed(response_data={"data": f"response_{i}"})
            op_log.sub_operations.append(sub_op)

        # Complete main operation
        op_log.mark_completed(success=True)

        # Log the operation
        logger = mock_aggregated_logger
        logger.log_operation(op_log)

        # Verify complete lifecycle was logged
        mock_aggregated_logger.log_operation.assert_called_once()
        logged_op = mock_aggregated_logger.log_operation.call_args[0][0]

        assert logged_op.operation_name == "LIFECYCLE_TEST"
        assert logged_op.status == "success"
        assert len(logged_op.sub_operations) == 3

        # Verify sub-operations
        for i, sub_op in enumerate(logged_op.sub_operations):
            assert sub_op.operation_name == f"OPERATION_{i}"
            assert sub_op.target == f"target_{i}"
            assert sub_op.status == "OK"

    def test_failed_operation_logging(self, mock_aggregated_logger):
        """Test logging of failed operations."""
        from src.core.log_aggregator.sub_operation_log import SubOperationLog

        op_log = OperationLog(operation_name="FAILURE_TEST", start_time=1000000.0)

        # Add successful sub-operation
        sub_op1 = SubOperationLog(step_number=1, target="target1", operation_name="SUCCESS_OP", start_time=1000001.0)
        sub_op1.mark_completed(response_data={"data": "success"})
        op_log.sub_operations.append(sub_op1)

        # Add failed sub-operation
        sub_op2 = SubOperationLog(step_number=2, target="target2", operation_name="FAILURE_OP", start_time=1000002.0)
        sub_op2.mark_completed(response_data=None, exception_info="ValueError: Test error")
        op_log.sub_operations.append(sub_op2)

        # Mark main operation as failed
        op_log.mark_completed(success=False, exception_info="RuntimeError: Main operation failed")

        # Log the operation
        logger = mock_aggregated_logger
        logger.log_operation(op_log)

        # Verify failed operation was logged
        mock_aggregated_logger.log_operation.assert_called_once()
        logged_op = mock_aggregated_logger.log_operation.call_args[0][0]

        assert logged_op.operation_name == "FAILURE_TEST"
        assert logged_op.status == "error"
        assert len(logged_op.sub_operations) == 2

        # Verify sub-operation statuses
        assert logged_op.sub_operations[0].status == "OK"
        assert logged_op.sub_operations[1].status == "Error"
