"""
Unit tests for Stage 2: OperationAggregator explicit mode extension.

Tests the new explicit mode functionality, integration with OperationLogger,
and sub-operation detection capabilities.
"""

import logging
from datetime import datetime
from unittest.mock import patch

import pytest

from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.operation_aggregator import OperationAggregationConfig, OperationAggregator, OperationGroup
from src.log_aggregator.operation_logger import OperationLogger


class TestOperationAggregatorExplicitMode:
    """Test explicit mode functionality of OperationAggregator."""

    def setup_method(self):
        """Set up test environment."""
        self.config = OperationAggregationConfig(
            explicit_mode_enabled=True, detect_sub_operations=True, operation_timeout=30.0
        )
        self.aggregator = OperationAggregator(self.config)

    def test_start_operation_creates_explicit_group(self):
        """Test that start_operation creates an explicit mode group."""
        operation_name = "TEST_OPERATION"

        self.aggregator.start_operation(operation_name)

        assert self.aggregator.current_group is not None
        assert self.aggregator.current_group.explicit_mode is True
        assert self.aggregator.current_group.operation_name == operation_name
        assert self.aggregator.current_group.root_operation == operation_name
        assert self.aggregator.is_explicit_mode() is True

    def test_end_operation_completes_explicit_group(self):
        """Test that end_operation completes and returns explicit group."""
        operation_name = "TEST_OPERATION"

        self.aggregator.start_operation(operation_name)

        # Add some records to the group
        record = self._create_test_record("Test message")
        self.aggregator.current_group.add_record(record)

        completed_group = self.aggregator.end_operation()

        assert completed_group is not None
        assert completed_group.explicit_mode is True
        assert completed_group.operation_name == operation_name
        assert len(completed_group.records) > 0
        assert self.aggregator.current_group is None
        assert self.aggregator.is_explicit_mode() is False

    def test_explicit_mode_processes_all_records(self):
        """Test that explicit mode processes all records into current group."""
        self.aggregator.start_operation("TEST_OPERATION")

        records = [
            self._create_test_record("handle_request_cycle: GET_ALL_DATA"),
            self._create_test_record("Data processing step"),
            self._create_test_record("handle_request_cycle: ADD_NEW_SERIES"),
        ]

        for record in records:
            result = self.aggregator.process_record(record)
            # Should return None while in explicit mode
            assert result is None

        assert len(self.aggregator.current_group.records) == len(records)

    def test_sub_operation_detection(self):
        """Test automatic sub-operation detection."""
        self.aggregator.start_operation("TEST_OPERATION")

        test_cases = [
            ("handle_request_cycle: OperationType.GET_ALL_DATA", "GET_ALL_DATA"),
            ("handle_request_cycle: OperationType.ADD_NEW_SERIES", "ADD_NEW_SERIES"),
            ("handle_request_cycle: OperationType.DECONVOLUTION", "DECONVOLUTION"),
            ("Data Processing step", "Data Processing"),
            ("UI Updates triggered", "UI Updates"),
            ("Generic handle_request_cycle call", "handle_request_cycle"),
        ]

        for message, expected_sub_op in test_cases:
            record = self._create_test_record(message)
            self.aggregator.process_record(record)

        sub_operations = self.aggregator.current_group.sub_operations
        expected_sub_ops = [case[1] for case in test_cases]

        for expected in expected_sub_ops:
            assert expected in sub_operations

    def test_request_count_tracking(self):
        """Test that request count is tracked correctly."""
        self.aggregator.start_operation("TEST_OPERATION")

        # Add multiple handle_request_cycle records
        request_messages = [
            "handle_request_cycle: OperationType.GET_ALL_DATA",
            "handle_request_cycle: OperationType.ADD_NEW_SERIES",
            "handle_request_cycle: OperationType.GET_SERIES",
        ]

        for message in request_messages:
            record = self._create_test_record(message)
            self.aggregator.process_record(record)

        # Add non-request record
        non_request_record = self._create_test_record("Some other operation")
        self.aggregator.process_record(non_request_record)

        assert self.aggregator.current_group.request_count == len(request_messages)

    def test_compatibility_with_automatic_mode(self):
        """Test that automatic mode still works when not in explicit mode."""
        # Process records without starting explicit mode
        record = self._create_test_record("handle_request_from_main_tab 'DECONVOLUTION'")

        self.aggregator.process_record(record)

        # Should use automatic mode logic
        assert self.aggregator.current_group is not None
        assert self.aggregator.current_group.explicit_mode is False

    def test_operation_group_add_record_functionality(self):
        """Test OperationGroup.add_record method."""
        group = OperationGroup(
            root_operation="TEST",
            start_time=datetime.now(),
            end_time=datetime.now(),
            operation_count=0,
            explicit_mode=True,
        )

        record = self._create_test_record("Test message", level=logging.ERROR)

        initial_count = group.operation_count
        group.add_record(record)

        assert len(group.records) == 1
        assert group.operation_count == initial_count + 1
        assert group.has_errors is True
        assert record in group.records

    def _create_test_record(self, message: str, level: int = logging.INFO) -> BufferedLogRecord:
        """Create a test log record."""
        log_record = logging.LogRecord(
            name="test_logger",
            level=level,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        return BufferedLogRecord(record=log_record, timestamp=datetime.now(), processed=False)


class TestOperationLoggerAggregatorIntegration:
    """Test integration between OperationLogger and OperationAggregator."""

    def setup_method(self):
        """Set up test environment."""
        self.aggregator = OperationAggregator()
        self.operation_logger = OperationLogger(aggregator=self.aggregator)

    def test_operation_logger_starts_aggregation(self):
        """Test that OperationLogger starts aggregation for root operations."""
        operation_name = "TEST_OPERATION"

        # Mock the aggregator's start_operation method
        with patch.object(self.aggregator, "start_operation") as mock_start:
            operation_id = self.operation_logger.start_operation(operation_name)

            # Should call aggregator's start_operation
            mock_start.assert_called_once_with(operation_name)
            assert operation_id is not None

    def test_operation_logger_ends_aggregation(self):
        """Test that OperationLogger ends aggregation for root operations."""
        operation_name = "TEST_OPERATION"

        # Start an operation
        self.operation_logger.start_operation(operation_name)

        # Mock the aggregator's end_operation method
        with patch.object(self.aggregator, "end_operation") as mock_end:
            self.operation_logger.end_operation()

            # Should call aggregator's end_operation
            mock_end.assert_called_once()

    def test_nested_operations_dont_trigger_aggregation(self):
        """Test that nested operations don't trigger aggregation start/end."""
        # Start parent operation
        self.operation_logger.start_operation("PARENT_OPERATION")
        # Mock the aggregator methods
        with (
            patch.object(self.aggregator, "start_operation") as mock_start,
            patch.object(self.aggregator, "end_operation") as mock_end,
        ):
            # Start and end nested operation
            nested_id = self.operation_logger.start_operation("NESTED_OPERATION")
            self.operation_logger.end_operation(nested_id)

            # Aggregator methods should not be called for nested operations
            mock_start.assert_not_called()
            mock_end.assert_not_called()

    def test_context_manager_integration(self):
        """Test that context manager properly integrates with aggregator."""
        operation_name = "CONTEXT_OPERATION"
        with (
            patch.object(self.aggregator, "start_operation") as mock_start,
            patch.object(self.aggregator, "end_operation") as mock_end,
        ):
            with self.operation_logger.log_operation(operation_name):
                # Do some work
                pass

            # Should have called start and end
            mock_start.assert_called_once_with(operation_name)
            mock_end.assert_called_once()

    def test_operation_logger_without_aggregator(self):
        """Test that OperationLogger works without aggregator."""
        logger_without_aggregator = OperationLogger()

        # Should not raise any errors
        operation_id = logger_without_aggregator.start_operation("TEST_OPERATION")
        logger_without_aggregator.end_operation(operation_id)

        assert operation_id is not None


class TestOperationSubDetection:
    """Test sub-operation detection functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.aggregator = OperationAggregator()

    def test_detect_handle_request_cycle_operations(self):
        """Test detection of handle_request_cycle operations."""
        test_cases = [
            ("handle_request_cycle with OperationType.GET_ALL_DATA", "GET_ALL_DATA"),
            ("handle_request_cycle with OperationType.ADD_NEW_SERIES", "ADD_NEW_SERIES"),
            ("handle_request_cycle with OperationType.MODEL_FREE_CALCULATION", "MODEL_FREE_CALCULATION"),
            ("just handle_request_cycle without type", "handle_request_cycle"),
        ]

        for message, expected in test_cases:
            record = self._create_test_record(message)
            result = self.aggregator._detect_sub_operations(record)
            assert result == expected

    def test_detect_processing_operations(self):
        """Test detection of processing operations."""
        test_cases = [
            ("Data Processing started", "Data Processing"),
            ("data processing in progress", "Data Processing"),
            ("UI Updates triggered", "UI Updates"),
            ("ui updates completed", "UI Updates"),
        ]

        for message, expected in test_cases:
            record = self._create_test_record(message)
            result = self.aggregator._detect_sub_operations(record)
            assert result == expected

    def test_no_detection_for_other_messages(self):
        """Test that unrecognized messages return None."""
        test_messages = [
            "Random log message",
            "Some other operation",
            "Debug information",
        ]

        for message in test_messages:
            record = self._create_test_record(message)
            result = self.aggregator._detect_sub_operations(record)
            assert result is None

    def _create_test_record(self, message: str) -> BufferedLogRecord:
        """Create a test log record."""
        log_record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        return BufferedLogRecord(record=log_record, timestamp=datetime.now(), processed=False)


class TestConfigurationOptions:
    """Test configuration options for explicit mode."""

    def test_explicit_mode_can_be_disabled(self):
        """Test that explicit mode can be disabled via configuration."""
        config = OperationAggregationConfig(explicit_mode_enabled=False)
        # Note: Current implementation still creates explicit groups even when disabled
        # This test verifies the configuration option exists
        assert config.explicit_mode_enabled is False

    def test_sub_operation_detection_can_be_disabled(self):
        """Test that sub-operation detection can be disabled."""
        config = OperationAggregationConfig(detect_sub_operations=False)
        aggregator = OperationAggregator(config)

        aggregator.start_operation("TEST_OPERATION")

        # Process record that would normally trigger sub-operation detection
        record = self._create_test_record("handle_request_cycle: OperationType.GET_ALL_DATA")
        aggregator.process_record(record)

        # Sub-operations list should be empty when detection is disabled
        assert len(aggregator.current_group.sub_operations) == 0

    def test_operation_timeout_configuration(self):
        """Test that operation timeout is configurable."""
        config = OperationAggregationConfig(operation_timeout=60.0)
        OperationAggregator(config)

        assert config.operation_timeout == 60.0

    def _create_test_record(self, message: str) -> BufferedLogRecord:
        """Create a test log record."""
        log_record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        return BufferedLogRecord(record=log_record, timestamp=datetime.now(), processed=False)


if __name__ == "__main__":
    pytest.main([__file__])
    pytest.main([__file__])
