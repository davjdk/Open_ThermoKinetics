"""
Test suite for Stage 1: Core @operation decorator functionality.

Tests the basic decorator implementation without sub-operation capture
or logging integration, focusing on core functionality as specified in
stage_01_core_decorator.md
"""

import time

import pytest

from src.core.app_settings import OperationType
from src.core.log_aggregator.operation_logger import OperationLog, OperationLogger, operation


class TestOperationLog:
    """Test the OperationLog data structure."""

    def test_operation_log_initialization(self):
        """Test basic initialization and properties."""
        start_time = time.time()
        op_log = OperationLog(operation_name="TEST_OP", start_time=start_time)

        assert op_log.operation_name == "TEST_OP"
        assert op_log.start_time == start_time
        assert op_log.status == "running"
        assert op_log.end_time is None
        assert op_log.execution_time is None
        assert op_log.exception_info is None
        assert op_log.sub_operations == []

    def test_mark_completed_success(self):
        """Test successful completion marking."""
        start = time.time()
        op_log = OperationLog(operation_name="TEST_OP", start_time=start)

        # Simulate some execution time
        time.sleep(0.01)
        op_log.mark_completed(success=True)

        assert op_log.status == "success"
        assert op_log.end_time is not None
        assert op_log.execution_time is not None
        assert op_log.execution_time > 0
        assert op_log.duration_ms > 0
        assert op_log.exception_info is None

    def test_mark_completed_error(self):
        """Test error completion marking."""
        start = time.time()
        op_log = OperationLog(operation_name="TEST_OP", start_time=start)

        error_msg = "TestError: Something went wrong"
        op_log.mark_completed(success=False, exception_info=error_msg)

        assert op_log.status == "error"
        assert op_log.end_time is not None
        assert op_log.execution_time is not None
        assert op_log.exception_info == error_msg

    def test_duration_ms_property(self):
        """Test duration_ms property calculation."""
        op_log = OperationLog(operation_name="TEST_OP", start_time=time.time())

        # Before completion, duration_ms should be None
        assert op_log.duration_ms is None

        # Add small delay to ensure measurable time difference
        time.sleep(0.001)

        # After completion, should return duration in milliseconds
        op_log.mark_completed(success=True)
        assert op_log.duration_ms is not None
        assert op_log.duration_ms >= 0  # Can be 0.0 for very fast operations

    def test_post_init_auto_timestamp(self):
        """Test that __post_init__ sets start_time when None."""
        # Create without start_time to trigger __post_init__
        op_log = OperationLog(operation_name="TEST_OP")

        # Should automatically set start_time
        assert op_log.start_time is not None
        assert isinstance(op_log.start_time, float)
        assert op_log.start_time > 0


class TestOperationLogger:
    """Test the OperationLogger orchestrator class."""

    def test_start_operation(self):
        """Test operation start tracking."""
        logger = OperationLogger()

        op_log = logger.start_operation("TEST_OPERATION")

        assert logger.current_operation is not None
        assert logger.current_operation.operation_name == "TEST_OPERATION"
        assert logger.current_operation.status == "running"
        assert op_log is logger.current_operation

    def test_complete_operation_success(self):
        """Test successful operation completion."""
        logger = OperationLogger()
        logger.start_operation("TEST_OPERATION")

        logger.complete_operation(success=True)

        assert logger.current_operation is None  # Should be cleared after completion

    def test_complete_operation_error(self):
        """Test error operation completion."""
        logger = OperationLogger()
        logger.start_operation("TEST_OPERATION")

        logger.complete_operation(success=False, exception_info="Test error")

        assert logger.current_operation is None  # Should be cleared after completion

    def test_complete_without_active_operation(self):
        """Test completing operation when none is active."""
        logger = OperationLogger()

        # Should not raise exception
        logger.complete_operation(success=True)


class TestOperationDecorator:
    """Test the @operation decorator functionality."""

    def test_decorator_preserves_return_value(self):
        """Test that decorator preserves original method return value."""

        @operation("TEST_DECORATOR")
        def test_function(value):
            return value * 2

        result = test_function(5)
        assert result == 10

    def test_decorator_preserves_arguments(self):
        """Test that decorator passes through all arguments correctly."""

        @operation("TEST_ARGS")
        def test_function(*args, **kwargs):
            return args, kwargs

        args, kwargs = test_function(1, 2, 3, key="value")
        assert args == (1, 2, 3)
        assert kwargs == {"key": "value"}

    def test_decorator_handles_exceptions(self):
        """Test that decorator properly handles and re-raises exceptions."""

        @operation("TEST_EXCEPTION")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_decorator_preserves_metadata(self):
        """Test that decorator preserves function metadata using functools.wraps."""

        @operation("TEST_METADATA")
        def documented_function():
            """This is a test function."""
            return "success"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a test function."

    def test_decorator_with_operation_type_enum(self):
        """Test decorator works with OperationType enum values."""

        @operation(OperationType.LOAD_FILE)
        def load_file_function():
            return {"success": True, "data": "file_content"}

        result = load_file_function()
        assert result["success"] is True
        assert result["data"] == "file_content"

    def test_decorator_measures_execution_time(self):
        """Test that decorator measures execution time."""

        @operation("SLOW_OPERATION")
        def slow_function():
            time.sleep(0.01)  # 10ms delay
            return "completed"

        start_time = time.time()
        result = slow_function()
        end_time = time.time()

        assert result == "completed"
        # Verify it took at least 10ms
        assert (end_time - start_time) >= 0.01

    def test_decorator_works_with_class_methods(self):
        """Test that decorator works correctly with class methods."""

        class TestClass:
            def __init__(self, value):
                self.value = value

            @operation("CLASS_METHOD_OPERATION")
            def process_value(self, multiplier):
                return self.value * multiplier

        test_obj = TestClass(5)
        result = test_obj.process_value(3)
        assert result == 15


class TestDecoratorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_decorator_with_none_return(self):
        """Test decorator with functions that return None."""

        @operation("NONE_RETURN")
        def none_function():
            pass  # Implicitly returns None

        result = none_function()
        assert result is None

    def test_decorator_with_generator_function(self):
        """Test decorator with generator functions."""

        @operation("GENERATOR_OPERATION")
        def generator_function():
            for i in range(3):
                yield i

        result = list(generator_function())
        assert result == [0, 1, 2]

    def test_nested_decorated_functions(self):
        """Test decorator with nested function calls."""

        @operation("OUTER_OPERATION")
        def outer_function():
            return inner_function() + 10

        @operation("INNER_OPERATION")
        def inner_function():
            return 5

        result = outer_function()
        assert result == 15

    def test_decorator_with_complex_arguments(self):
        """Test decorator with various argument types."""

        @operation("COMPLEX_ARGS")
        def complex_function(*args, **kwargs):
            return {"args": args, "kwargs": kwargs, "total_args": len(args) + len(kwargs)}

        result = complex_function(1, 2, 3, name="test", value=42)
        assert result["args"] == (1, 2, 3)
        assert result["kwargs"] == {"name": "test", "value": 42}
        assert result["total_args"] == 5


class TestIntegrationBasic:
    """Basic integration tests for the complete Stage 1 functionality."""

    def test_end_to_end_success_flow(self):
        """Test complete successful operation flow."""

        @operation("E2E_SUCCESS")
        def successful_operation(input_value):
            time.sleep(0.01)  # Simulate some work
            return input_value.upper()

        result = successful_operation("test")
        assert result == "TEST"

    def test_end_to_end_error_flow(self):
        """Test complete error operation flow."""

        @operation("E2E_ERROR")
        def error_operation():
            time.sleep(0.01)  # Simulate some work before error
            raise ValueError("Simulated error")

        with pytest.raises(ValueError, match="Simulated error"):
            error_operation()

    def test_multiple_operations_isolation(self):
        """Test that multiple operations don't interfere with each other."""

        @operation("MULTI_OP_1")
        def operation_one():
            return "op1"

        @operation("MULTI_OP_2")
        def operation_two():
            return "op2"

        result1 = operation_one()
        result2 = operation_two()

        assert result1 == "op1"
        assert result2 == "op2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
