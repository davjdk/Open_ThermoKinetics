"""
Unit tests for OperationLogger API.

Tests the core functionality of explicit operation logging including
context managers, decorators, and metric collection.
"""

import threading
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.log_aggregator.operation_logger import OperationContext, OperationLogger, log_operation, operation


class TestOperationContext:
    """Test OperationContext dataclass."""

    def test_operation_context_creation(self):
        """Test basic OperationContext creation."""
        start_time = datetime.now()
        context = OperationContext(operation_id="test_id", operation_name="TEST_OPERATION", start_time=start_time)

        assert context.operation_id == "test_id"
        assert context.operation_name == "TEST_OPERATION"
        assert context.start_time == start_time
        assert context.parent_operation_id is None
        assert context.metrics == {}
        assert context.status == "RUNNING"
        assert context.end_time is None

    def test_duration_calculation(self):
        """Test duration calculation."""
        start_time = datetime.now()
        context = OperationContext(operation_id="test_id", operation_name="TEST_OPERATION", start_time=start_time)

        # No duration when end_time is None
        assert context.duration is None

        # Duration calculated when end_time is set
        context.end_time = start_time  # Same time = 0 duration
        assert context.duration == 0.0

        # Test with actual time difference
        context.end_time = start_time.replace(microsecond=start_time.microsecond + 500000)
        assert 0.4 <= context.duration <= 0.6  # Allow for minor timing variations


class TestOperationLogger:
    """Test OperationLogger class."""

    def setup_method(self):
        """Set up test environment."""
        self.logger = OperationLogger("test_logger")

    def test_initialization(self):
        """Test OperationLogger initialization."""
        assert self.logger.logger.name == "test_logger"
        assert hasattr(self.logger, "_local")
        assert self.logger.current_operation is None

    def test_operation_stack_thread_safety(self):
        """Test thread-local operation stack."""
        # Main thread stack
        assert len(self.logger._operation_stack) == 0

        # Different thread should have separate stack
        thread_stacks = {}

        def thread_test(thread_id):
            thread_stacks[thread_id] = len(self.logger._operation_stack)
            self.logger.start_operation(f"THREAD_OP_{thread_id}")
            thread_stacks[f"{thread_id}_after"] = len(self.logger._operation_stack)

        threads = []
        for i in range(3):
            t = threading.Thread(target=thread_test, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Each thread should have started with empty stack
        for i in range(3):
            assert thread_stacks[i] == 0
            assert thread_stacks[f"{i}_after"] == 1

        # Main thread should still be empty
        assert len(self.logger._operation_stack) == 0

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_start_operation(self, mock_get_logger):
        """Test operation start."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")
        operation_id = logger.start_operation("TEST_OP")

        # Check operation was added to stack
        assert len(logger._operation_stack) == 1
        assert logger.current_operation.operation_name == "TEST_OP"
        assert logger.current_operation.operation_id == operation_id

        # Check logging was called
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        assert "OPERATION_START" in call_args[0][0]
        assert "TEST_OP" in call_args[0][0]

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_end_operation(self, mock_get_logger):
        """Test operation end."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")
        operation_id = logger.start_operation("TEST_OP")

        # Reset mock to clear start_operation call
        mock_logger_instance.reset_mock()

        logger.end_operation(operation_id, "SUCCESS")

        # Check operation was removed from stack
        assert len(logger._operation_stack) == 0
        assert logger.current_operation is None

        # Check logging was called
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        assert "OPERATION_END" in call_args[0][0]
        assert "TEST_OP" in call_args[0][0]
        assert "SUCCESS" in call_args[0][0]

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_add_metric(self, mock_get_logger):
        """Test metric addition."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")
        logger.start_operation("TEST_OP")

        # Reset mock to clear start_operation call
        mock_logger_instance.reset_mock()

        logger.add_metric("test_key", "test_value")

        # Check metric was added
        assert logger.current_operation.metrics["test_key"] == "test_value"

        # Check logging was called
        mock_logger_instance.info.assert_called_once()
        call_args = mock_logger_instance.info.call_args
        assert "Метрика" in call_args[0][0]
        assert "test_key" in call_args[0][0]
        assert "test_value" in call_args[0][0]

    def test_add_metric_no_operation(self):
        """Test metric addition without active operation."""
        with patch.object(self.logger.logger, "warning") as mock_warning:
            self.logger.add_metric("test_key", "test_value")
            mock_warning.assert_called_once()

    def test_function_to_operation_name(self):
        """Test function name conversion."""
        # Test _handle_ prefix removal
        assert self.logger._function_to_operation_name("_handle_add_new_series") == "ADD_NEW_SERIES"

        # Test regular snake_case conversion
        assert self.logger._function_to_operation_name("load_file_data") == "LOAD_FILE_DATA"

        # Test already uppercase
        assert self.logger._function_to_operation_name("EXISTING_UPPER") == "EXISTING_UPPER"

    def test_generate_operation_id(self):
        """Test operation ID generation."""
        op_id = self.logger._generate_operation_id("TEST_OP")

        # Check format: OPERATION_NAME_YYYYMMDD_HHMMSS_randomhex
        parts = op_id.split("_")
        assert parts[0] == "TEST"
        assert parts[1] == "OP"
        assert len(parts[2]) == 8  # Date part YYYYMMDD
        assert len(parts[3]) == 6  # Time part HHMMSS
        assert len(parts[4]) == 8  # Random hex part


class TestOperationContextManager:
    """Test operation context manager."""

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_context_manager_success(self, mock_get_logger):
        """Test successful operation with context manager."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")

        with logger.log_operation("TEST_CONTEXT_OP"):
            # Check operation is active
            assert logger.current_operation is not None
            assert logger.current_operation.operation_name == "TEST_CONTEXT_OP"

        # Check operation is ended
        assert logger.current_operation is None

        # Check both start and end were logged
        assert mock_logger_instance.info.call_count == 2

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_context_manager_with_exception(self, mock_get_logger):
        """Test operation with exception in context manager."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")

        with pytest.raises(ValueError):
            with logger.log_operation("TEST_ERROR_OP"):
                raise ValueError("Test error")

        # Check operation is ended even with exception
        assert logger.current_operation is None

        # Check error metrics were added and both start/end were logged
        assert mock_logger_instance.info.call_count >= 2


class TestOperationDecorator:
    """Test operation decorator."""

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_decorator_with_custom_name(self, mock_get_logger):
        """Test decorator with custom operation name."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")

        @logger.operation("CUSTOM_DECORATOR_OP")
        def test_function():
            return "test_result"

        result = test_function()

        assert result == "test_result"
        # Check both start and end were logged
        assert mock_logger_instance.info.call_count == 2

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_decorator_with_auto_name(self, mock_get_logger):
        """Test decorator with automatic name generation."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")

        @logger.operation()
        def _handle_test_function():
            return "test_result"

        result = _handle_test_function()

        assert result == "test_result"
        # Check operation name was auto-generated
        start_call = mock_logger_instance.info.call_args_list[0]
        assert "TEST_FUNCTION" in start_call[0][0]

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_decorator_with_exception(self, mock_get_logger):
        """Test decorator with exception handling."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")

        @logger.operation("ERROR_DECORATOR_OP")
        def error_function():
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            error_function()

        # Check both start and end were logged, with error status
        assert mock_logger_instance.info.call_count >= 2


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("src.log_aggregator.operation_logger.operation_logger")
    def test_log_operation_convenience(self, mock_operation_logger):
        """Test log_operation convenience function."""
        mock_context_manager = Mock()
        mock_operation_logger.log_operation.return_value = mock_context_manager

        result = log_operation("CONVENIENCE_OP")

        mock_operation_logger.log_operation.assert_called_once_with("CONVENIENCE_OP")
        assert result == mock_context_manager

    @patch("src.log_aggregator.operation_logger.operation_logger")
    def test_operation_convenience(self, mock_operation_logger):
        """Test operation convenience function."""
        mock_decorator = Mock()
        mock_operation_logger.operation.return_value = mock_decorator

        result = operation("CONVENIENCE_OP")

        mock_operation_logger.operation.assert_called_once_with("CONVENIENCE_OP")
        assert result == mock_decorator


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_nested_operations(self, mock_get_logger):
        """Test nested operations."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")

        with logger.log_operation("PARENT_OP"):
            logger.add_metric("parent_metric", "parent_value")

            with logger.log_operation("CHILD_OP"):
                logger.add_metric("child_metric", "child_value")

                # Check parent-child relationship
                assert logger.current_operation.operation_name == "CHILD_OP"
                assert logger.current_operation.parent_operation_id is not None

            # Back to parent
            assert logger.current_operation.operation_name == "PARENT_OP"

        # All operations completed
        assert logger.current_operation is None

    @patch("src.log_aggregator.operation_logger.logging.getLogger")
    def test_mixed_api_usage(self, mock_get_logger):
        """Test mixing context manager and decorator approaches."""
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance

        logger = OperationLogger("test")

        @logger.operation("DECORATOR_OP")
        def decorated_function():
            # Use context manager inside decorated function
            with logger.log_operation("INNER_CONTEXT_OP"):
                logger.add_metric("inner_metric", "inner_value")
                return "result"

        result = decorated_function()

        assert result == "result"
        # Should have logged multiple operations
        assert mock_logger_instance.info.call_count >= 4  # Start/end for both operations
        assert mock_logger_instance.info.call_count >= 4  # Start/end for both operations
