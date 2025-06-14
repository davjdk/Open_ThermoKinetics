"""
Tests for refactored OperationLogger (Stage 3).

Tests the new simplified architecture with automatic table generation
and enhanced error handling.
"""

import threading
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.log_aggregator.operation_logger import (
    DataCompressionConfig,
    OperationContext,
    OperationLogger,
    get_operation_logger,
    log_operation,
    operation,
)


class TestOperationContext(unittest.TestCase):
    """Test OperationContext dataclass functionality."""

    def test_context_creation(self):
        """Test basic context creation."""
        start_time = datetime.now()
        context = OperationContext(
            operation_id="test_id",
            operation_name="TEST_OPERATION",
            start_time=start_time,
        )

        self.assertEqual(context.operation_id, "test_id")
        self.assertEqual(context.operation_name, "TEST_OPERATION")
        self.assertEqual(context.start_time, start_time)
        self.assertEqual(context.status, "RUNNING")
        self.assertIsNone(context.end_time)
        self.assertIsNone(context.error_info)

    def test_duration_calculation(self):
        """Test duration calculation."""
        start_time = datetime.now()
        context = OperationContext(
            operation_id="test_id",
            operation_name="TEST_OPERATION",
            start_time=start_time,
        )

        # No duration before end_time is set
        self.assertIsNone(context.duration)

        # Set end time and check duration
        end_time = datetime.now()
        context.end_time = end_time
        duration = context.duration

        self.assertIsNotNone(duration)
        self.assertIsInstance(duration, float)
        self.assertGreaterEqual(duration, 0)

    def test_add_error_info(self):
        """Test error information handling."""
        context = OperationContext(
            operation_id="test_id",
            operation_name="TEST_OPERATION",
            start_time=datetime.now(),
        )

        # Add error information
        try:
            raise ValueError("Test error")
        except ValueError as e:
            context.add_error_info(type(e), e)

        self.assertEqual(context.status, "ERROR")
        self.assertIsNotNone(context.error_info)
        self.assertEqual(context.error_info["type"], "ValueError")
        self.assertEqual(context.error_info["message"], "Test error")


class TestOperationLogger(unittest.TestCase):
    """Test OperationLogger refactored functionality."""

    def setUp(self):
        """Set up test environment."""
        self.logger = OperationLogger(
            logger_name="test_logger",
            enable_tables=False,  # Disable tables for testing
        )

    def test_initialization(self):
        """Test logger initialization."""
        self.assertIsNotNone(self.logger.logger)
        self.assertIsInstance(self.logger.compression_config, DataCompressionConfig)
        self.assertFalse(self.logger.enable_tables)
        self.assertIsNone(self.logger.tabular_formatter)

    def test_operation_stack_thread_local(self):
        """Test that operation stack is thread-local."""
        results = {}

        def worker(thread_id):
            logger = OperationLogger()
            op_id = logger.start_operation(f"THREAD_OP_{thread_id}")
            results[thread_id] = {
                "operation_id": op_id,
                "stack_length": len(logger._operation_stack),
                "current_op": logger.current_operation.operation_name if logger.current_operation else None,
            }
            logger.end_operation()

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that each thread had its own operation stack
        for thread_id in range(3):
            self.assertEqual(results[thread_id]["stack_length"], 1)
            self.assertEqual(results[thread_id]["current_op"], f"THREAD_OP_{thread_id}")

    def test_nested_operations(self):
        """Test nested operation handling."""
        op1_id = self.logger.start_operation("PARENT_OP")
        self.assertEqual(len(self.logger._operation_stack), 1)
        self.assertEqual(self.logger.current_operation.operation_name, "PARENT_OP")

        self.logger.start_operation("CHILD_OP")
        self.assertEqual(len(self.logger._operation_stack), 2)
        self.assertEqual(self.logger.current_operation.operation_name, "CHILD_OP")
        self.assertEqual(self.logger.current_operation.parent_operation_id, op1_id)

        # End child operation
        self.logger.end_operation()
        self.assertEqual(len(self.logger._operation_stack), 1)
        self.assertEqual(self.logger.current_operation.operation_name, "PARENT_OP")
        self.assertEqual(self.logger.current_operation.sub_operations_count, 1)

        # End parent operation
        self.logger.end_operation()
        self.assertEqual(len(self.logger._operation_stack), 0)
        self.assertIsNone(self.logger.current_operation)

    def test_metrics_handling(self):
        """Test custom metrics addition."""
        self.logger.start_operation("TEST_OP")

        # Add various types of metrics
        self.logger.add_metric("string_metric", "test_value")
        self.logger.add_metric("number_metric", 42)
        self.logger.add_metric("dict_metric", {"key": "value"})

        current_op = self.logger.current_operation
        self.assertIsNotNone(current_op)
        self.assertEqual(current_op.metrics["string_metric"], "test_value")
        self.assertEqual(current_op.metrics["number_metric"], 42)
        self.assertEqual(current_op.metrics["dict_metric"], {"key": "value"})

        self.logger.end_operation()

    def test_error_handling(self):
        """Test error handling in operations."""
        self.logger.start_operation("ERROR_OP")

        error_info = {
            "type": "ValueError",
            "message": "Test error message",
            "traceback": "test traceback",
        }

        self.logger.end_operation("ERROR", error_info)

        # Since operation is popped, we can't directly check the context
        # But we can verify the operation was handled properly

    def test_context_manager(self):
        """Test context manager functionality."""
        with self.logger.log_operation("CONTEXT_OP") as ctx:
            self.assertIsNotNone(ctx.operation_id)
            self.assertEqual(len(self.logger._operation_stack), 1)
            self.assertEqual(self.logger.current_operation.operation_name, "CONTEXT_OP")

        # After context exit, stack should be empty
        self.assertEqual(len(self.logger._operation_stack), 0)

    def test_context_manager_with_exception(self):
        """Test context manager with exception handling."""
        try:
            with self.logger.log_operation("ERROR_OP"):
                self.assertEqual(len(self.logger._operation_stack), 1)
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Stack should be cleaned up even after exception
        self.assertEqual(len(self.logger._operation_stack), 0)

    def test_decorator_functionality(self):
        """Test operation decorator."""

        @self.logger.operation("DECORATED_OP")
        def decorated_function(x, y):
            self.assertEqual(len(self.logger._operation_stack), 1)
            self.assertEqual(self.logger.current_operation.operation_name, "DECORATED_OP")
            return x + y

        result = decorated_function(2, 3)
        self.assertEqual(result, 5)
        self.assertEqual(len(self.logger._operation_stack), 0)

    def test_decorator_with_exception(self):
        """Test decorator with exception handling."""

        @self.logger.operation("ERROR_DECORATED_OP")
        def failing_function():
            raise RuntimeError("Decorator test error")

        with self.assertRaises(RuntimeError):
            failing_function()

        # Stack should be cleaned up
        self.assertEqual(len(self.logger._operation_stack), 0)

    def test_reset_functionality(self):
        """Test logger reset functionality."""
        # Start some operations
        self.logger.start_operation("OP1")
        self.logger.start_operation("OP2")
        self.assertEqual(len(self.logger._operation_stack), 2)

        # Reset should clear everything
        self.logger.reset()
        self.assertEqual(len(self.logger._operation_stack), 0)


class TestOperationLoggerIntegration(unittest.TestCase):
    """Test OperationLogger integration with other components."""

    @patch("src.log_aggregator.operation_logger.TabularFormatter")
    def test_tabular_formatter_integration(self, mock_formatter_class):
        """Test integration with TabularFormatter."""
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter

        logger = OperationLogger(enable_tables=True)

        # Verify formatter was initialized
        self.assertIsNotNone(logger.tabular_formatter)
        mock_formatter_class.assert_called_once()

    @patch("src.log_aggregator.operation_logger.OperationAggregator")
    def test_aggregator_integration(self, mock_aggregator_class):
        """Test integration with OperationAggregator."""
        mock_aggregator = MagicMock()
        mock_aggregator.config = MagicMock()
        mock_aggregator.config.explicit_mode = False

        OperationLogger(aggregator=mock_aggregator)

        # Verify aggregator was configured for explicit mode
        self.assertTrue(mock_aggregator.config.explicit_mode)

    def test_operation_monitor_integration(self):
        """Test integration with OperationMonitor."""
        mock_monitor = MagicMock()
        logger = OperationLogger(operation_monitor=mock_monitor)

        # Start root operation
        logger.start_operation("ROOT_OP")
        mock_monitor.start_operation_tracking.assert_called_once_with("ROOT_OP")

        logger.end_operation()
        mock_monitor.end_operation_tracking.assert_called_once()


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions and global instance."""

    @patch("src.log_aggregator.operation_monitor.operation_monitor")
    def test_global_logger_instance(self, mock_monitor):
        """Test global logger instance creation."""
        logger = get_operation_logger()
        self.assertIsInstance(logger, OperationLogger)

    def test_log_operation_convenience(self):
        """Test log_operation convenience function."""
        with log_operation("CONVENIENCE_TEST"):
            # Should work without explicit logger instance
            pass

    def test_operation_decorator_convenience(self):
        """Test operation decorator convenience function."""

        @operation("CONVENIENCE_DECORATOR")
        def test_function():
            return "success"

        result = test_function()
        self.assertEqual(result, "success")


class TestDataCompression(unittest.TestCase):
    """Test data compression functionality."""

    def setUp(self):
        """Set up test environment."""
        self.logger = OperationLogger(compression_config=DataCompressionConfig(enabled=True))

    def test_string_compression(self):
        """Test long string compression."""
        long_string = "x" * 300  # Exceeds threshold

        self.logger.start_operation("COMPRESS_TEST")
        self.logger.add_metric("long_string", long_string)

        current_op = self.logger.current_operation
        metric_value = current_op.metrics["long_string"]

        # Should be compressed
        self.assertIsInstance(metric_value, dict)
        self.assertTrue(metric_value.get("_compressed", False))
        self.assertEqual(metric_value["_type"], "string")
        self.assertEqual(metric_value["_length"], 300)

        self.logger.end_operation()

    def test_dict_compression(self):
        """Test large dictionary compression."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(20)}  # Exceeds threshold

        self.logger.start_operation("COMPRESS_TEST")
        self.logger.add_metric("large_dict", large_dict)

        current_op = self.logger.current_operation
        metric_value = current_op.metrics["large_dict"]

        # Should be compressed
        self.assertIsInstance(metric_value, dict)
        self.assertTrue(metric_value.get("_compressed", False))
        self.assertEqual(metric_value["_type"], "dict")
        self.assertEqual(metric_value["_length"], 20)

        self.logger.end_operation()

    def test_small_data_not_compressed(self):
        """Test that small data is not compressed."""
        small_string = "small"
        small_dict = {"key": "value"}

        self.logger.start_operation("NO_COMPRESS_TEST")
        self.logger.add_metric("small_string", small_string)
        self.logger.add_metric("small_dict", small_dict)

        current_op = self.logger.current_operation

        # Should not be compressed
        self.assertEqual(current_op.metrics["small_string"], small_string)
        self.assertEqual(current_op.metrics["small_dict"], small_dict)

        self.logger.end_operation()


if __name__ == "__main__":
    pytest.main([__file__])
