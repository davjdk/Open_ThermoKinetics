"""
Test fixtures and configuration for log aggregator tests.
"""

import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from src.core.app_settings import OperationType
from src.core.base_signals import BaseSlots
from src.core.log_aggregator import OperationLogger, operation
from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.sub_operation_log import SubOperationLog


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def operation_logger():
    """Create a fresh OperationLogger instance for testing."""
    return OperationLogger()


@pytest.fixture
def sample_operation_log():
    """Create a sample OperationLog with test data."""
    op_log = OperationLog(operation_name="TEST_OPERATION", start_time=time.time())

    # Add some sample sub-operations
    sub_op1 = SubOperationLog(
        step_number=1,
        operation_name="GET_VALUE",
        target="file_data",
        start_time=time.time(),
        request_kwargs={"path_keys": ["file1.csv", "temperature"]},
    )
    sub_op1.mark_completed(response_data={"data": [1, 2, 3]})

    sub_op2 = SubOperationLog(
        step_number=2,
        operation_name="SET_VALUE",
        target="calculations",
        start_time=time.time(),
        request_kwargs={"path_keys": ["file1.csv", "reaction_0"], "value": {"function": "ads"}},
    )
    sub_op2.mark_completed(response_data={"data": {"success": True}})

    # Add a failed sub-operation
    sub_op3 = SubOperationLog(
        step_number=3, operation_name="INVALID_OP", target="nowhere", start_time=time.time(), request_kwargs={}
    )
    sub_op3.mark_completed(response_data=None, exception_info="ValueError: Invalid operation")

    op_log.sub_operations.extend([sub_op1, sub_op2, sub_op3])
    op_log.mark_completed(success=True)

    return op_log


@pytest.fixture
def mock_base_slots_instance():
    """Create a mock BaseSlots instance for testing."""
    mock_instance = Mock(spec=BaseSlots)

    # Mock handle_request_cycle to return different types of responses
    def mock_handle_request_cycle(target: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Mock implementation of handle_request_cycle."""
        if operation == "GET_VALUE":
            return {"data": [1, 2, 3]}
        elif operation == "SET_VALUE":
            return {"data": {"success": True}}
        elif operation == "LOAD_FILE":
            return {"data": True}
        elif operation == "ERROR_OPERATION":
            return {"data": {"success": False, "error": "Test error"}}
        elif operation == "EXCEPTION_OPERATION":
            raise ValueError("Test exception")
        else:
            return {"data": "default_response"}

    mock_instance.handle_request_cycle = Mock(side_effect=mock_handle_request_cycle)
    return mock_instance


@pytest.fixture
def sample_test_class():  # noqa: C901
    """Create a test class that inherits from BaseSlots for testing."""

    class TestOperationClass(BaseSlots):
        """Test class for operation decoration."""

        def __init__(self):
            # Don't call super().__init__() to avoid BaseSignals dependency
            pass

        def handle_request_cycle(self, target: str, operation: str, **kwargs) -> Dict[str, Any]:
            """Mock handle_request_cycle method."""
            if operation == "GET_VALUE":
                return {"data": [1, 2, 3]}
            elif operation == "SET_VALUE":
                return {"data": {"success": True}}
            elif operation == "ERROR_OPERATION":
                return {"data": {"success": False, "error": "Test error"}}
            elif operation == "EXCEPTION_OPERATION":
                raise ValueError("Test exception")
            else:
                return {"data": "default_response"}

        @operation("SIMPLE_OPERATION")
        def simple_operation(self) -> str:
            """Simple operation without sub-operations."""
            return "success"

        @operation("OPERATION_WITH_SUBOPS")
        def operation_with_subops(self) -> bool:
            """Operation that makes sub-operation calls."""
            self.handle_request_cycle("file_data", "GET_VALUE", path_keys=["test"])
            self.handle_request_cycle("calculations", "SET_VALUE", value=42)
            return True

        @operation("OPERATION_WITH_ERROR")
        def operation_with_error(self) -> None:
            """Operation that raises an exception."""
            self.handle_request_cycle("file_data", "GET_VALUE", path_keys=["test"])
            raise RuntimeError("Test operation error")

        @operation("NESTED_OPERATIONS")
        def nested_operations(self) -> bool:
            """Operation with nested handle_request_cycle calls."""
            self.handle_request_cycle("file_data", "GET_VALUE", path_keys=["test1"])

            # Simulate nested calls
            for i in range(3):
                self.handle_request_cycle("calculations", "SET_VALUE", index=i, value=i * 10)

            self.handle_request_cycle("file_data", "GET_VALUE", path_keys=["test2"])
            return True

    return TestOperationClass


@pytest.fixture
def all_operation_types():
    """Return all OperationType enum values for comprehensive testing."""
    return list(OperationType)


@pytest.fixture
def deterministic_time(monkeypatch):
    """Mock time.time to return deterministic values for testing."""
    start_time = 1000000.0
    current_time = start_time

    def mock_time():
        nonlocal current_time
        current_time += 0.1  # Each call advances by 100ms
        return current_time

    monkeypatch.setattr("time.time", mock_time)
    return start_time


@pytest.fixture(autouse=True)
def reset_thread_local():
    """Reset thread-local storage before each test."""
    from src.core.log_aggregator.operation_logger import set_current_operation_logger

    set_current_operation_logger(None)


@pytest.fixture
def error_response_data():
    """Sample error response data for testing."""
    return {
        "success_response": {"data": {"success": True, "result": "OK"}},
        "error_response": {"data": {"success": False, "error": "Test error message"}},
        "simple_data": {"data": [1, 2, 3]},
        "bool_data": {"data": True},
        "str_data": {"data": "test_string"},
        "dict_data": {"data": {"key": "value"}},
        "none_data": {"data": None},
        "float_data": {"data": 3.14159},
        "int_data": {"data": 42},
    }


@pytest.fixture
def mock_aggregated_logger(monkeypatch):
    """Mock the aggregated logger to prevent file I/O during tests."""
    mock_logger = Mock()
    mock_logger.log_operation = Mock()

    def mock_get_aggregated_logger():
        return mock_logger

    monkeypatch.setattr("src.core.log_aggregator.operation_logger.get_aggregated_logger", mock_get_aggregated_logger)
    return mock_logger
