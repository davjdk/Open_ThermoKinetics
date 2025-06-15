"""
Tests for sub-operation capture functionality.

This module tests the interception and tracking of handle_request_cycle calls:
- Proxy wrapper functionality
- Sub-operation data collection
- Nested operation handling
- Status determination logic
"""

from unittest.mock import Mock

import pytest

from src.core.log_aggregator.operation_logger import HandleRequestCycleProxy, get_current_operation_logger


class TestHandleRequestCycleProxy:
    """Test cases for HandleRequestCycleProxy functionality."""

    def test_proxy_preserves_original_behavior(self, mock_base_slots_instance):
        """Test that proxy calls original method and preserves behavior."""
        original_method = mock_base_slots_instance.handle_request_cycle
        proxy = HandleRequestCycleProxy(original_method, mock_base_slots_instance)

        # Call proxy with test parameters
        result = proxy("file_data", "GET_VALUE", path_keys=["test"])

        # Verify original method was called with correct parameters
        original_method.assert_called_once_with("file_data", "GET_VALUE", path_keys=["test"])
        assert result == {"data": [1, 2, 3]}

    def test_proxy_without_active_operation(self, mock_base_slots_instance):
        """Test proxy behavior when no operation is active."""
        original_method = mock_base_slots_instance.handle_request_cycle
        proxy = HandleRequestCycleProxy(original_method, mock_base_slots_instance)

        # Ensure no operation logger is active
        assert get_current_operation_logger() is None

        result = proxy("file_data", "GET_VALUE", path_keys=["test"])

        # Should just call original method without logging
        original_method.assert_called_once_with("file_data", "GET_VALUE", path_keys=["test"])
        assert result == {"data": [1, 2, 3]}

    def test_proxy_with_active_operation(self, mock_base_slots_instance, operation_logger):
        """Test proxy behavior with active operation logging."""
        from src.core.log_aggregator.operation_logger import set_current_operation_logger

        # Set up active operation
        operation_logger.start_operation("TEST_OPERATION")
        set_current_operation_logger(operation_logger)

        try:
            original_method = mock_base_slots_instance.handle_request_cycle
            proxy = HandleRequestCycleProxy(original_method, mock_base_slots_instance)

            result = proxy("file_data", "GET_VALUE", path_keys=["test"])

            # Verify original method was called
            original_method.assert_called_once_with("file_data", "GET_VALUE", path_keys=["test"])
            assert result == {"data": [1, 2, 3]}

            # Verify sub-operation was logged
            assert len(operation_logger.current_operation.sub_operations) == 1
            sub_op = operation_logger.current_operation.sub_operations[0]
            assert sub_op.operation_name == "GET_VALUE"
            assert sub_op.target == "file_data"
            assert sub_op.request_kwargs == {"path_keys": ["test"]}
            assert sub_op.status == "OK"

        finally:
            set_current_operation_logger(None)

    def test_proxy_handles_exceptions(self, mock_base_slots_instance, operation_logger):
        """Test proxy handling of exceptions from original method."""
        from src.core.log_aggregator.operation_logger import set_current_operation_logger

        operation_logger.start_operation("TEST_OPERATION")
        set_current_operation_logger(operation_logger)

        try:
            original_method = mock_base_slots_instance.handle_request_cycle
            proxy = HandleRequestCycleProxy(original_method, mock_base_slots_instance)

            # Test with operation that raises exception
            with pytest.raises(ValueError, match="Test exception"):
                proxy("file_data", "EXCEPTION_OPERATION")  # Verify sub-operation was logged with error status
            assert len(operation_logger.current_operation.sub_operations) == 1
            sub_op = operation_logger.current_operation.sub_operations[0]
            assert sub_op.operation_name == "EXCEPTION_OPERATION"
            assert sub_op.status == "Error"
            assert "ValueError: Test exception" in sub_op.error_message

        finally:
            set_current_operation_logger(None)


class TestSubOperationCapture:
    """Test cases for sub-operation capture during decorated operations."""

    def test_capture_single_suboperation(self, sample_test_class, mock_aggregated_logger):
        """Test capturing a single sub-operation."""
        test_instance = sample_test_class()
        test_instance.operation_with_subops()

        # Verify operation was logged
        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        # Should have captured 2 sub-operations
        assert len(operation_log.sub_operations) == 2

        # Check first sub-operation
        sub_op1 = operation_log.sub_operations[0]
        assert sub_op1.step_number == 1
        assert sub_op1.operation_name == "GET_VALUE"
        assert sub_op1.target == "file_data"
        assert sub_op1.status == "OK"

        # Check second sub-operation
        sub_op2 = operation_log.sub_operations[1]
        assert sub_op2.step_number == 2
        assert sub_op2.operation_name == "SET_VALUE"
        assert sub_op2.target == "calculations"
        assert sub_op2.status == "OK"

    def test_capture_nested_suboperations(self, sample_test_class, mock_aggregated_logger):
        """Test capturing nested sub-operations."""
        test_instance = sample_test_class()
        test_instance.nested_operations()

        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        # Should have captured 5 sub-operations (1 + 3 + 1)
        assert len(operation_log.sub_operations) == 5

        # Check that step numbers are sequential
        for i, sub_op in enumerate(operation_log.sub_operations):
            assert sub_op.step_number == i + 1

        # Check operation names
        expected_operations = ["GET_VALUE", "SET_VALUE", "SET_VALUE", "SET_VALUE", "GET_VALUE"]
        actual_operations = [sub_op.operation_name for sub_op in operation_log.sub_operations]
        assert actual_operations == expected_operations

    def test_suboperation_timing(self, sample_test_class, mock_aggregated_logger, deterministic_time):
        """Test that sub-operations have proper timing information."""
        test_instance = sample_test_class()
        test_instance.operation_with_subops()

        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        for sub_op in operation_log.sub_operations:
            assert sub_op.start_time is not None
            assert sub_op.end_time is not None
            assert sub_op.duration_ms is not None
            assert sub_op.duration_ms >= 0

    def test_suboperation_with_error(self, sample_test_class, mock_aggregated_logger):
        """Test sub-operation capture when main operation fails."""
        test_instance = sample_test_class()
        with pytest.raises(RuntimeError, match="Test operation error"):
            test_instance.operation_with_error()

        mock_aggregated_logger.log_operation.assert_called_once()
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]

        # Should have captured the sub-operation before the error
        assert len(operation_log.sub_operations) == 1
        sub_op = operation_log.sub_operations[0]
        assert sub_op.operation_name == "GET_VALUE"
        assert sub_op.status == "OK"  # Main operation should be marked as failed
        assert operation_log.status == "error"
        assert "RuntimeError: Test operation error" in operation_log.exception_info


class TestSubOperationDataCollection:
    """Test cases for sub-operation data collection and analysis."""

    def test_suboperation_data_types(self, operation_logger, error_response_data):
        """Test detection of different data types in sub-operation responses."""
        from src.core.log_aggregator.operation_logger import set_current_operation_logger

        operation_logger.start_operation("DATA_TYPE_TEST")
        set_current_operation_logger(operation_logger)

        try:
            # Mock instance with handle_request_cycle
            mock_instance = Mock()

            def mock_handle_request_cycle(target, operation, **kwargs):
                response_mapping = {
                    "BOOL_OP": error_response_data["bool_data"],
                    "STR_OP": error_response_data["str_data"],
                    "LIST_OP": error_response_data["simple_data"],
                    "DICT_OP": error_response_data["dict_data"],
                    "NONE_OP": error_response_data["none_data"],
                    "FLOAT_OP": error_response_data["float_data"],
                    "INT_OP": error_response_data["int_data"],
                }
                return response_mapping.get(operation, {"data": "unknown"})

            mock_instance.handle_request_cycle = mock_handle_request_cycle

            # Set up proxy
            from src.core.log_aggregator.operation_logger import HandleRequestCycleProxy

            proxy = HandleRequestCycleProxy(mock_instance.handle_request_cycle, mock_instance)

            # Test different data types
            proxy("test", "BOOL_OP")
            proxy("test", "STR_OP")
            proxy("test", "LIST_OP")
            proxy("test", "DICT_OP")
            proxy("test", "NONE_OP")
            proxy("test", "FLOAT_OP")
            proxy("test", "INT_OP")

            # Verify data types were captured correctly
            sub_operations = operation_logger.current_operation.sub_operations
            assert len(sub_operations) == 7

            expected_types = ["bool", "str", "list", "dict", "None", "float", "int"]
            actual_types = [sub_op.data_type for sub_op in sub_operations]
            assert actual_types == expected_types

        finally:
            set_current_operation_logger(None)

    def test_suboperation_status_determination(self, operation_logger, error_response_data):
        """Test correct status determination for sub-operations."""
        from src.core.log_aggregator.operation_logger import set_current_operation_logger

        operation_logger.start_operation("STATUS_TEST")
        set_current_operation_logger(operation_logger)

        try:
            mock_instance = Mock()

            def mock_handle_request_cycle(target, operation, **kwargs):
                response_mapping = {
                    "SUCCESS_OP": error_response_data["success_response"],
                    "ERROR_OP": error_response_data["error_response"],
                    "SIMPLE_OP": error_response_data["simple_data"],
                }
                if operation == "EXCEPTION_OP":
                    raise ValueError("Test exception")
                return response_mapping.get(operation, {"data": "unknown"})

            mock_instance.handle_request_cycle = mock_handle_request_cycle

            from src.core.log_aggregator.operation_logger import HandleRequestCycleProxy

            proxy = HandleRequestCycleProxy(mock_instance.handle_request_cycle, mock_instance)

            # Test successful operations
            proxy("test", "SUCCESS_OP")
            proxy("test", "SIMPLE_OP")

            # Test error response
            proxy("test", "ERROR_OP")

            # Test exception
            with pytest.raises(ValueError):
                proxy("test", "EXCEPTION_OP")

            sub_operations = operation_logger.current_operation.sub_operations
            assert len(sub_operations) == 4  # Check statuses
            assert sub_operations[0].status == "OK"  # SUCCESS_OP
            assert sub_operations[1].status == "OK"  # SIMPLE_OP
            assert sub_operations[2].status == "Error"  # ERROR_OP (data has success=False)
            assert sub_operations[3].status == "Error"  # EXCEPTION_OP

        finally:
            set_current_operation_logger(None)

    def test_suboperation_kwargs_capture(self, operation_logger):
        """Test that sub-operation kwargs are properly captured."""
        from src.core.log_aggregator.operation_logger import set_current_operation_logger

        operation_logger.start_operation("KWARGS_TEST")
        set_current_operation_logger(operation_logger)

        try:
            mock_instance = Mock()
            mock_instance.handle_request_cycle = Mock(return_value={"data": "success"})

            from src.core.log_aggregator.operation_logger import HandleRequestCycleProxy

            proxy = HandleRequestCycleProxy(mock_instance.handle_request_cycle, mock_instance)

            # Test with various kwargs
            test_kwargs = {
                "path_keys": ["file1.csv", "reaction_0"],
                "value": {"function": "ads", "coeffs": {"h": 1.0}},
                "index": 42,
                "flag": True,
            }

            proxy("calculations", "SET_VALUE", **test_kwargs)

            sub_op = operation_logger.current_operation.sub_operations[0]
            assert sub_op.request_kwargs == test_kwargs
            assert sub_op.target == "calculations"
            assert sub_op.operation_name == "SET_VALUE"

        finally:
            set_current_operation_logger(None)


class TestProxyRestoration:
    """Test cases for proper restoration of original methods."""

    def test_proxy_setup_and_restoration(self, mock_base_slots_instance, operation_logger):
        """Test that original methods are properly restored after operation."""
        original_method = mock_base_slots_instance.handle_request_cycle

        # Set up interception
        operation_logger.setup_handle_request_cycle_interception(mock_base_slots_instance)

        # Verify method was replaced with proxy
        assert mock_base_slots_instance.handle_request_cycle != original_method
        assert isinstance(mock_base_slots_instance.handle_request_cycle, HandleRequestCycleProxy)

        # Restore original method
        operation_logger.restore_handle_request_cycle(mock_base_slots_instance)

        # Verify original method was restored
        assert mock_base_slots_instance.handle_request_cycle == original_method

    def test_restoration_without_setup(self, mock_base_slots_instance, operation_logger):
        """Test restoration when no interception was set up."""
        # Try to restore without setting up interception first
        # This should not raise an exception
        operation_logger.restore_handle_request_cycle(mock_base_slots_instance)

    def test_multiple_instances_restoration(self, operation_logger):
        """Test restoration with multiple instances."""
        # Create multiple mock instances
        instance1 = Mock()
        instance1.handle_request_cycle = Mock(return_value={"data": "result1"})

        instance2 = Mock()
        instance2.handle_request_cycle = Mock(return_value={"data": "result2"})

        original_method1 = instance1.handle_request_cycle
        original_method2 = instance2.handle_request_cycle

        # Set up interception for both
        operation_logger.setup_handle_request_cycle_interception(instance1)
        operation_logger.setup_handle_request_cycle_interception(instance2)

        # Verify both were replaced
        assert instance1.handle_request_cycle != original_method1
        assert instance2.handle_request_cycle != original_method2

        # Restore both
        operation_logger.restore_handle_request_cycle(instance1)
        operation_logger.restore_handle_request_cycle(instance2)

        # Verify both were restored
        assert instance1.handle_request_cycle == original_method1
        assert instance2.handle_request_cycle == original_method2
