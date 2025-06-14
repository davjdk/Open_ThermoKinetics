"""
Tests for operation decorator functionality.

This module tests the enhanced @operation decorator with automatic OperationType
integration and BaseSlots compatibility.
"""

from unittest.mock import Mock, patch

import pytest

from src.core.app_settings import OperationType
from src.log_aggregator.operation_decorator import (
    _auto_detect_operation_type,
    _determine_operation_name,
    _function_to_operation_name,
    auto_decorate_baseslots_class,
    get_current_operation_context,
    is_operation_active,
    operation,
)
from src.log_aggregator.operation_metaclass import AutoOperationMeta, operation_aware_class


class TestOperationDecorator:
    """Test cases for operation decorator functionality."""

    def test_basic_operation_decorator(self):
        """Test basic operation decorator functionality."""
        # Mock operation logger
        with patch("src.log_aggregator.operation_decorator.get_operation_logger") as mock_logger_getter:
            mock_logger = Mock()
            mock_logger.current_operation = None
            mock_logger.start_operation.return_value = "test_op_id"
            mock_logger_getter.return_value = mock_logger

            @operation("TEST_OPERATION")
            def test_function():
                return "test_result"

            result = test_function()

            # Verify operation logging calls
            mock_logger.start_operation.assert_called_once_with("TEST_OPERATION")
            mock_logger.end_operation.assert_called_once_with("test_op_id", "SUCCESS")
            mock_logger.add_metric.assert_called()
            assert result == "test_result"

    def test_operation_decorator_with_operationtype_enum(self):
        """Test operation decorator with OperationType enum."""
        with patch("src.log_aggregator.operation_decorator.get_operation_logger") as mock_logger_getter:
            mock_logger = Mock()
            mock_logger.current_operation = None
            mock_logger.start_operation.return_value = "test_op_id"
            mock_logger_getter.return_value = mock_logger

            @operation(OperationType.LOAD_FILE)
            def load_file_function():
                return "file_loaded"

            result = load_file_function()

            # Verify operation logging with enum value
            mock_logger.start_operation.assert_called_once_with(OperationType.LOAD_FILE.value)
            assert result == "file_loaded"

    def test_operation_decorator_exception_handling(self):
        """Test operation decorator exception handling."""
        with patch("src.log_aggregator.operation_decorator.get_operation_logger") as mock_logger_getter:
            mock_logger = Mock()
            mock_logger.current_operation = None
            mock_logger.start_operation.return_value = "test_op_id"
            mock_logger_getter.return_value = mock_logger

            @operation("TEST_OPERATION", handle_exceptions=True)
            def failing_function():
                raise ValueError("Test error")

            result = failing_function()

            # Verify error handling
            mock_logger.start_operation.assert_called_once_with("TEST_OPERATION")
            mock_logger.end_operation.assert_called_once_with("test_op_id", "ERROR")
            mock_logger.add_metric.assert_any_call("exception_type", "ValueError")
            mock_logger.add_metric.assert_any_call("exception_message", "Test error")
            assert result is None

    def test_operation_decorator_exception_propagation(self):
        """Test operation decorator exception propagation when handle_exceptions=False."""
        with patch("src.log_aggregator.operation_decorator.get_operation_logger") as mock_logger_getter:
            mock_logger = Mock()
            mock_logger.current_operation = None
            mock_logger.start_operation.return_value = "test_op_id"
            mock_logger_getter.return_value = mock_logger

            @operation("TEST_OPERATION", handle_exceptions=False)
            def failing_function():
                raise ValueError("Test error")

            with pytest.raises(ValueError, match="Test error"):
                failing_function()

            # Verify error logging but exception is re-raised
            mock_logger.start_operation.assert_called_once_with("TEST_OPERATION")
            mock_logger.end_operation.assert_called_once_with("test_op_id", "ERROR")

    def test_nested_operations(self):
        """Test nested operation handling."""
        with patch("src.log_aggregator.operation_decorator.get_operation_logger") as mock_logger_getter:
            mock_logger = Mock()
            # Simulate nested operation scenario
            mock_operation_context = Mock()
            mock_operation_context.operation_name = "PARENT_OPERATION"
            mock_logger.current_operation = None  # Start with no operation
            mock_logger.start_operation.return_value = "test_op_id"
            mock_logger_getter.return_value = mock_logger

            @operation("PARENT_OPERATION")
            def parent_function():
                # Simulate nested call
                mock_logger.current_operation = mock_operation_context
                return child_function()

            @operation("CHILD_OPERATION")
            def child_function():
                return "child_result"

            result = parent_function()

            # Verify both operations were logged
            assert mock_logger.start_operation.call_count == 2
            assert result == "child_result"

    def test_auto_detect_operation_type(self):
        """Test automatic operation type detection."""
        # Test exact matches
        assert _auto_detect_operation_type("add_reaction") == OperationType.ADD_REACTION.value
        assert _auto_detect_operation_type("deconvolution") == OperationType.DECONVOLUTION.value
        assert _auto_detect_operation_type("load_file") == OperationType.LOAD_FILE.value

        # Test with prefixes
        assert _auto_detect_operation_type("_handle_add_reaction") == OperationType.ADD_REACTION.value
        assert _auto_detect_operation_type("handle_deconvolution") == OperationType.DECONVOLUTION.value
        assert _auto_detect_operation_type("process_load_file") == OperationType.LOAD_FILE.value

        # Test no match
        assert _auto_detect_operation_type("unknown_operation") is None

    def test_function_to_operation_name(self):
        """Test function name to operation name conversion."""
        assert _function_to_operation_name("test_function") == "TEST_FUNCTION"
        assert _function_to_operation_name("_handle_operation") == "OPERATION"
        assert _function_to_operation_name("handle_file_load") == "FILE_LOAD"
        assert _function_to_operation_name("process_data") == "DATA"

    def test_determine_operation_name(self):
        """Test operation name determination logic."""

        def mock_function():
            pass

        # Test explicit OperationType
        result = _determine_operation_name(mock_function, OperationType.LOAD_FILE, True)
        assert result == OperationType.LOAD_FILE.value

        # Test explicit string
        result = _determine_operation_name(mock_function, "CUSTOM_OP", True)
        assert result == "CUSTOM_OP"

        # Test auto-detection disabled
        mock_function.__name__ = "some_function"
        result = _determine_operation_name(mock_function, None, False)
        assert result == "SOME_FUNCTION"

    def test_operation_metadata_preservation(self):
        """Test that operation decorator preserves function metadata."""

        @operation("TEST_OPERATION")
        def test_function_with_docstring():
            """This is a test function."""
            return "result"

        # Check metadata preservation
        assert test_function_with_docstring.__name__ == "test_function_with_docstring"
        assert test_function_with_docstring.__doc__ == "This is a test function."
        assert hasattr(test_function_with_docstring, "_operation_name")
        assert test_function_with_docstring._operation_name == "TEST_OPERATION"
        assert test_function_with_docstring._is_operation_decorated is True


class TestOperationMetaclass:
    """Test cases for operation metaclass functionality."""

    @patch("src.log_aggregator.operation_metaclass.logger")
    def test_auto_operation_meta_with_baseslots(self, mock_logger):
        """Test AutoOperationMeta with BaseSlots subclass."""

        # Mock BaseSlots
        with patch("src.log_aggregator.operation_metaclass.AutoOperationMeta._is_baseslots_subclass") as mock_check:
            mock_check.return_value = True

            with patch("src.log_aggregator.operation_decorator.get_operation_logger"):

                class TestDataOperations(metaclass=AutoOperationMeta):
                    def process_request(self, params):
                        return "processed"

                # Verify the method was decorated
                assert hasattr(TestDataOperations.process_request, "_is_operation_decorated")
                mock_logger.debug.assert_called()

    def test_operation_aware_class_decorator(self):
        """Test operation_aware_class decorator."""

        with patch(
            "src.log_aggregator.operation_metaclass.AutoOperationMeta._auto_decorate_process_request"
        ) as mock_decorate:

            @operation_aware_class
            class TestClass:
                def process_request(self, params):
                    return "result"

            mock_decorate.assert_called_once_with(TestClass)


class MockBaseSlots:
    """Mock BaseSlots class for testing."""

    def __init__(self, actor_name="test_actor", signals=None):
        self.actor_name = actor_name
        self.signals = signals


class TestIntegrationWithBaseSlots:
    """Integration tests with BaseSlots-like classes."""

    def test_auto_decorate_baseslots_class(self):
        """Test automatic decoration of BaseSlots classes."""

        class TestDataOperations(MockBaseSlots):
            def process_request(self, params):
                return f"processing {params}"

        # Mock the BaseSlots check to return True
        with patch("src.log_aggregator.operation_decorator._is_baseslots_subclass") as mock_check:
            mock_check.return_value = True

            with patch("src.log_aggregator.operation_decorator.get_operation_logger"):
                decorated_class = auto_decorate_baseslots_class(TestDataOperations)

                # Verify decoration occurred
                assert hasattr(decorated_class.process_request, "_is_operation_decorated")

    def test_context_functions(self):
        """Test operation context functions."""

        with patch("src.log_aggregator.operation_decorator.get_operation_logger") as mock_logger_getter:
            mock_logger = Mock()
            mock_operation = Mock()
            mock_operation.operation_name = "TEST_OPERATION"
            mock_logger.current_operation = mock_operation
            mock_logger_getter.return_value = mock_logger

            # Test with active operation
            assert get_current_operation_context() == "TEST_OPERATION"
            assert is_operation_active() is True

            # Test with no active operation
            mock_logger.current_operation = None
            assert get_current_operation_context() is None
            assert is_operation_active() is False


if __name__ == "__main__":
    pytest.main([__file__])
