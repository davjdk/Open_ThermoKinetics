"""
Tests for the @operation decorator functionality.

This module tests the core decorator behavior including:
- Basic functionality and signature preservation
- Exception handling and status tracking
- Operation timing measurement
- Integration with OperationLogger
"""

import pytest

from src.core.log_aggregator import operation
from src.core.log_aggregator.operation_logger import get_current_operation_logger, set_current_operation_logger


class TestOperationDecorator:
    """Test cases for @operation decorator basic functionality."""

    def test_decorator_basic_functionality(self, mock_aggregated_logger):
        """Test that decorated method executes and returns correct result."""

        @operation("TEST_OPERATION")
        def test_method() -> str:
            """Test method that returns a simple string."""
            return "test_result"

        result = test_method()

        assert result == "test_result"
        mock_aggregated_logger.log_operation.assert_called_once()

    def test_decorator_preserves_function_signature(self, mock_aggregated_logger):
        """Test that decorator preserves original function signature and metadata."""

        @operation("SIGNATURE_TEST")
        def test_method_with_args(arg1: int, arg2: str = "default") -> str:
            """Test method with arguments and docstring."""
            return f"{arg1}_{arg2}"

        # Test that function still works with arguments
        result = test_method_with_args(42, "custom")
        assert result == "42_custom"

        result_default = test_method_with_args(100)
        assert result_default == "100_default"

        # Test that metadata is preserved
        assert test_method_with_args.__name__ == "test_method_with_args"
        assert "Test method with arguments" in test_method_with_args.__doc__

    def test_decorator_measures_execution_time(self, mock_aggregated_logger, deterministic_time):
        """Test that decorator properly measures execution time."""

        @operation("TIMING_TEST")
        def slow_method():
            """Method that takes some time to execute."""
            # Mock time.time is set up to advance by 0.1s per call
            pass

        slow_method()

        # Verify that log_operation was called with proper timing
        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        assert operation_log.operation_name == "TIMING_TEST"
        assert operation_log.duration_ms is not None
        assert operation_log.duration_ms > 0

    def test_decorator_with_exception(self, mock_aggregated_logger):
        """Test that decorator correctly handles exceptions."""

        @operation("ERROR_OPERATION")
        def failing_method():
            """Method that raises an exception."""
            raise ValueError("Test error message")

        with pytest.raises(ValueError, match="Test error message"):
            failing_method()

        # Verify that operation was still logged despite the exception
        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        assert operation_log.operation_name == "ERROR_OPERATION"
        assert operation_log.status == "error"
        assert operation_log.exception_info == "ValueError: Test error message"

    def test_decorator_without_suboperations(self, mock_aggregated_logger):
        """Test operation without handle_request_cycle calls."""

        @operation("SIMPLE_OPERATION")
        def simple_method() -> int:
            """Simple method without sub-operations."""
            return 42

        result = simple_method()

        assert result == 42
        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        assert operation_log.operation_name == "SIMPLE_OPERATION"
        assert operation_log.status == "success"
        assert len(operation_log.sub_operations) == 0

    def test_decorator_with_class_method(self, sample_test_class, mock_aggregated_logger):
        """Test decorator works with class methods."""
        test_instance = sample_test_class()
        result = test_instance.simple_operation()

        assert result == "success"
        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        assert operation_log.operation_name == "SIMPLE_OPERATION"
        assert operation_log.status == "success"

    def test_decorator_thread_local_storage(self, mock_aggregated_logger):
        """Test that decorator properly manages thread-local storage."""

        @operation("THREAD_LOCAL_TEST")
        def test_method():
            """Test method to check thread-local storage."""
            # During execution, current_operation_logger should be set
            current_logger = get_current_operation_logger()
            assert current_logger is not None
            assert current_logger.current_operation is not None
            return "success"

        # Before execution, no operation logger should be set
        assert get_current_operation_logger() is None

        result = test_method()

        # After execution, thread-local storage should be cleaned up
        assert result == "success"
        assert get_current_operation_logger() is None

    def test_decorator_nested_operations_not_supported(self, mock_aggregated_logger):
        """Test that nested decorated operations work independently."""

        @operation("OUTER_OPERATION")
        def outer_method():
            """Outer operation method."""
            return inner_method()

        @operation("INNER_OPERATION")
        def inner_method():
            """Inner operation method."""
            return "inner_result"

        result = outer_method()

        assert result == "inner_result"
        # Both operations should be logged separately
        assert mock_aggregated_logger.log_operation.call_count == 2

    def test_decorator_with_return_values(self, mock_aggregated_logger):
        """Test decorator with various return value types."""

        @operation("RETURN_TEST")
        def method_with_return(return_type: str):
            """Method that returns different types based on parameter."""
            if return_type == "str":
                return "string_result"
            elif return_type == "int":
                return 42
            elif return_type == "list":
                return [1, 2, 3]
            elif return_type == "dict":
                return {"key": "value"}
            elif return_type == "none":
                return None
            else:
                return True

        # Test different return types
        assert method_with_return("str") == "string_result"
        assert method_with_return("int") == 42
        assert method_with_return("list") == [1, 2, 3]
        assert method_with_return("dict") == {"key": "value"}
        assert method_with_return("none") is None
        assert method_with_return("bool") is True

        # All executions should be logged
        assert mock_aggregated_logger.log_operation.call_count == 6


class TestOperationDecoratorExceptionHandling:
    """Test cases for exception handling in @operation decorator."""

    def test_exception_preserves_original_traceback(self, mock_aggregated_logger):
        """Test that exceptions preserve original traceback information."""

        @operation("TRACEBACK_TEST")
        def method_with_nested_calls():
            """Method with nested function calls for traceback testing."""

            def inner_function():
                raise RuntimeError("Inner function error")

            def middle_function():
                inner_function()

            middle_function()

        with pytest.raises(RuntimeError, match="Inner function error"):
            method_with_nested_calls()

        # Verify that operation was logged with exception info
        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        assert operation_log.status == "error"
        assert "RuntimeError: Inner function error" in operation_log.exception_info

    def test_multiple_exception_types(self, mock_aggregated_logger):
        """Test handling of different exception types."""
        exception_types = [
            (ValueError, "Value error"),
            (TypeError, "Type error"),
            (KeyError, "Key error"),
            (AttributeError, "Attribute error"),
            (RuntimeError, "Runtime error"),
        ]

        for exception_class, message in exception_types:

            @operation(f"EXCEPTION_TEST_{exception_class.__name__}")
            def failing_method():
                raise exception_class(message)

            with pytest.raises(exception_class, match=message):
                failing_method()

        # All exceptions should be logged
        assert mock_aggregated_logger.log_operation.call_count == len(exception_types)

    def test_decorator_exception_in_cleanup(self, mock_aggregated_logger, monkeypatch):
        """Test decorator behavior when cleanup operations fail."""

        # Mock set_current_operation_logger to raise an exception during cleanup
        original_set_logger = set_current_operation_logger

        def mock_set_logger_with_error(logger):
            if logger is None:  # This is the cleanup call
                raise RuntimeError("Cleanup error")
            original_set_logger(logger)

        monkeypatch.setattr(
            "src.core.log_aggregator.operation_logger.set_current_operation_logger", mock_set_logger_with_error
        )

        @operation("CLEANUP_ERROR_TEST")
        def test_method():
            return "success"  # The cleanup error should be raised

        with pytest.raises(RuntimeError, match="Cleanup error"):
            test_method()  # Operation should still be logged
        mock_aggregated_logger.log_operation.assert_called_once()
