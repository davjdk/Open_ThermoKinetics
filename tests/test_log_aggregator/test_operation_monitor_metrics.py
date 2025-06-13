"""
Unit tests for Stage 3 enhanced OperationMonitor metrics functionality.

This module tests the enhanced metrics collection, custom metrics tracking,
and log message parsing capabilities added in Stage 3.
"""

import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.log_aggregator.operation_monitor import (
    LogMetricsExtractor,
    OperationMonitor,
    OperationMonitoringConfig,
    OperationStatus,
)


class TestLogMetricsExtractor:
    """Test log metrics extraction functionality."""

    def test_extract_sub_operation(self):
        """Test extraction of sub-operation from log message."""
        extractor = LogMetricsExtractor()
        message = "handle_request_cycle processing OperationType.DECONVOLUTION request"

        metrics = extractor.extract_metrics(message)

        assert "sub_operation" in metrics
        assert metrics["sub_operation"] == "DECONVOLUTION"

    def test_extract_duration_metrics(self):
        """Test extraction of duration metrics."""
        extractor = LogMetricsExtractor()

        # Test seconds
        message = "operation completed in 2.5 seconds"
        metrics = extractor.extract_metrics(message)
        assert "duration" in metrics
        assert metrics["duration"] == 2.5

        # Test milliseconds
        message = "operation completed in 1500ms"
        metrics = extractor.extract_metrics(message)
        assert "duration" in metrics
        assert metrics["duration"] == 1500

    def test_extract_file_count(self):
        """Test extraction of file count."""
        extractor = LogMetricsExtractor()
        message = "processing 5 files for analysis"

        metrics = extractor.extract_metrics(message)

        assert "file_count" in metrics
        assert metrics["file_count"] == 5

    def test_extract_reaction_count(self):
        """Test extraction of reaction count."""
        extractor = LogMetricsExtractor()
        message = "3 reactions found in deconvolution"

        metrics = extractor.extract_metrics(message)

        assert "reaction_count" in metrics
        assert metrics["reaction_count"] == 3

    def test_extract_quality_metrics(self):
        """Test extraction of quality metrics (MSE, R²)."""
        extractor = LogMetricsExtractor()

        # Test MSE
        message = "Optimization finished with MSE: 0.00123"
        metrics = extractor.extract_metrics(message)
        assert "mse_value" in metrics
        assert metrics["mse_value"] == 0.00123

        # Test R²
        message = "Model fit R²: 0.9876"
        metrics = extractor.extract_metrics(message)
        assert "r_squared" in metrics
        assert metrics["r_squared"] == 0.9876

    def test_extract_performance_metrics(self):
        """Test extraction of performance metrics."""
        extractor = LogMetricsExtractor()

        # Test CPU usage
        message = "Current CPU usage: 45.6%"
        metrics = extractor.extract_metrics(message)
        assert "cpu_usage" in metrics
        assert metrics["cpu_usage"] == 45.6

        # Test memory usage
        message = "Memory usage: 512.3 MB"
        metrics = extractor.extract_metrics(message)
        assert "memory_usage_mb" in metrics
        assert metrics["memory_usage_mb"] == 512.3

    def test_extract_multiple_metrics(self):
        """Test extraction of multiple metrics from single message."""
        extractor = LogMetricsExtractor()
        message = "processing 3 files, found 5 reactions, MSE: 0.001"

        metrics = extractor.extract_metrics(message)

        assert len(metrics) == 3
        assert metrics["file_count"] == 3
        assert metrics["reaction_count"] == 5
        assert metrics["mse_value"] == 0.001

    def test_extract_no_metrics(self):
        """Test handling of messages with no extractable metrics."""
        extractor = LogMetricsExtractor()
        message = "This is a simple log message with no metrics"

        metrics = extractor.extract_metrics(message)

        assert len(metrics) == 0


class TestEnhancedOperationMonitor:
    """Test enhanced OperationMonitor functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return OperationMonitoringConfig(
            enabled=True,
            max_operation_history=100,
            operation_timeout_seconds=30.0,
        )

    @pytest.fixture
    def monitor(self, config):
        """Create test monitor."""
        return OperationMonitor(config)

    def test_start_operation_tracking(self, monitor):
        """Test starting operation tracking."""
        monitor.start_operation_tracking("TEST_OPERATION")

        assert monitor.current_operation is not None
        assert monitor.current_operation.operation_type == "TEST_OPERATION"
        assert monitor.current_operation.status == OperationStatus.RUNNING
        assert isinstance(monitor.current_operation.start_time, datetime)

    def test_end_operation_tracking(self, monitor):
        """Test ending operation tracking."""
        monitor.start_operation_tracking("TEST_OPERATION")

        # Add some activity
        monitor.add_custom_metric("test_metric", 42)
        monitor.track_log_level("WARNING", "test warning")

        completed = monitor.end_operation_tracking()

        assert completed is not None
        assert completed.operation_type == "TEST_OPERATION"
        assert completed.status == OperationStatus.COMPLETED  # No errors
        assert completed.duration_ms is not None
        assert completed.custom_metrics["test_metric"] == 42
        assert completed.warning_count == 1
        assert monitor.current_operation is None
        assert len(monitor.completed_operations) == 1

    def test_nested_operations(self, monitor):
        """Test nested operation tracking."""
        # Start parent operation
        monitor.start_operation_tracking("PARENT_OPERATION")
        monitor.add_custom_metric("parent_metric", "parent_value")

        # Start child operation
        monitor.start_operation_tracking("CHILD_OPERATION")
        monitor.add_custom_metric("child_metric", "child_value")

        # End child operation
        child_completed = monitor.end_operation_tracking()
        assert child_completed.operation_type == "CHILD_OPERATION"
        assert child_completed.custom_metrics["child_metric"] == "child_value"

        # Check parent is restored
        assert monitor.current_operation.operation_type == "PARENT_OPERATION"
        assert monitor.current_operation.custom_metrics["parent_metric"] == "parent_value"

        # End parent operation
        parent_completed = monitor.end_operation_tracking()
        assert parent_completed.operation_type == "PARENT_OPERATION"
        assert monitor.current_operation is None

    def test_add_custom_metric(self, monitor):
        """Test adding custom metrics."""
        monitor.start_operation_tracking("TEST_OPERATION")

        monitor.add_custom_metric("string_metric", "test_value")
        monitor.add_custom_metric("numeric_metric", 123.45)
        monitor.add_custom_metric("list_metric", [1, 2, 3])

        metrics = monitor.current_operation.custom_metrics
        assert metrics["string_metric"] == "test_value"
        assert metrics["numeric_metric"] == 123.45
        assert metrics["list_metric"] == [1, 2, 3]

    def test_track_request_response(self, monitor):
        """Test tracking requests and responses."""
        monitor.start_operation_tracking("TEST_OPERATION")

        monitor.track_request("ComponentA", "ComponentB", "GET_DATA")
        monitor.track_request("ComponentB", "ComponentC", "PROCESS_DATA")
        monitor.track_response("ComponentC", "ComponentB", "PROCESS_DATA")
        monitor.track_response("ComponentB", "ComponentA", "GET_DATA")

        operation = monitor.current_operation
        assert operation.request_count == 2
        assert operation.response_count == 2
        assert "ComponentA" in operation.components_involved
        assert "ComponentB" in operation.components_involved
        assert "ComponentC" in operation.components_involved

    def test_track_log_levels(self, monitor):
        """Test tracking log levels and error counts."""
        monitor.start_operation_tracking("TEST_OPERATION")

        monitor.track_log_level("INFO", "info message")
        monitor.track_log_level("WARNING", "warning message")
        monitor.track_log_level("WARNING", "another warning")
        monitor.track_log_level("ERROR", "error message")

        operation = monitor.current_operation
        assert operation.warning_count == 2
        assert operation.error_count == 1

    def test_track_log_level_with_metrics(self, monitor):
        """Test that log level tracking extracts metrics from messages."""
        monitor.start_operation_tracking("TEST_OPERATION")

        message = "Processing completed with MSE: 0.00234 and 4 reactions found"
        monitor.track_log_level("INFO", message)

        operation = monitor.current_operation
        assert "mse_value" in operation.custom_metrics
        assert operation.custom_metrics["mse_value"] == 0.00234
        assert "reaction_count" in operation.custom_metrics
        assert operation.custom_metrics["reaction_count"] == 4

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    def test_add_performance_metrics(self, mock_memory, mock_cpu, monitor):
        """Test adding performance metrics."""
        # Mock psutil data
        mock_cpu.return_value = 75.5
        mock_memory.return_value = Mock(
            used=1024 * 1024 * 512,  # 512 MB
            available=1024 * 1024 * 1024,  # 1 GB
        )

        monitor.start_operation_tracking("TEST_OPERATION")
        monitor.add_performance_metrics()

        metrics = monitor.current_operation.custom_metrics
        assert "cpu_usage_percent" in metrics
        assert metrics["cpu_usage_percent"] == 75.5
        assert "memory_usage_mb" in metrics
        assert metrics["memory_usage_mb"] == 512.0
        assert "memory_available_mb" in metrics
        assert metrics["memory_available_mb"] == 1024.0

    def test_track_optimization_metrics(self, monitor):
        """Test tracking optimization-specific metrics."""
        monitor.start_operation_tracking("OPTIMIZATION")

        optimization_data = {
            "iteration_count": 150,
            "convergence_value": 0.00001,
            "optimization_method": "differential_evolution",
            "mse": 0.00123,
        }

        monitor.track_optimization_metrics(optimization_data)

        metrics = monitor.current_operation.custom_metrics
        assert metrics["iterations"] == 150
        assert metrics["convergence"] == 0.00001
        assert metrics["method"] == "differential_evolution"
        assert metrics["final_mse"] == 0.00123

    def test_track_data_operation_metrics_series(self, monitor):
        """Test tracking data operation metrics for series."""
        monitor.start_operation_tracking("ADD_NEW_SERIES")

        data_info = {"file_count": 3, "heating_rates": [3, 5, 10]}

        monitor.track_data_operation_metrics("ADD_NEW_SERIES", data_info)

        metrics = monitor.current_operation.custom_metrics
        assert metrics["files_processed"] == 3
        assert metrics["heating_rates"] == [3, 5, 10]

    def test_track_data_operation_metrics_deconvolution(self, monitor):
        """Test tracking data operation metrics for deconvolution."""
        monitor.start_operation_tracking("DECONVOLUTION")

        data_info = {"reaction_count": 4, "mse": 0.00045, "r_squared": 0.9876}

        monitor.track_data_operation_metrics("DECONVOLUTION", data_info)

        metrics = monitor.current_operation.custom_metrics
        assert metrics["reactions_found"] == 4
        assert metrics["final_mse"] == 0.00045
        assert metrics["r_squared"] == 0.9876

    def test_track_data_operation_metrics_calculation(self, monitor):
        """Test tracking data operation metrics for calculations."""
        monitor.start_operation_tracking("MODEL_FIT_CALCULATION")

        data_info = {"method": "Coats-Redfern", "reaction_count": 2}

        monitor.track_data_operation_metrics("MODEL_FIT_CALCULATION", data_info)

        metrics = monitor.current_operation.custom_metrics
        assert metrics["calculation_method"] == "Coats-Redfern"
        assert metrics["reactions_analyzed"] == 2

    def test_get_operation_metrics_for_aggregation(self, monitor):
        """Test getting operation metrics for aggregation."""
        monitor.start_operation_tracking("TEST_OPERATION")

        # Simulate some activity
        monitor.track_request("A", "B", "op")
        monitor.track_response("B", "A", "op")
        monitor.track_log_level("WARNING", "test warning")
        monitor.add_custom_metric("test_metric", 123)

        aggregation_data = monitor.get_operation_metrics_for_aggregation()

        assert "operation_name" in aggregation_data
        assert aggregation_data["operation_name"] == "TEST_OPERATION"
        assert aggregation_data["request_count"] == 1
        assert aggregation_data["response_count"] == 1
        assert aggregation_data["warning_count"] == 1
        assert aggregation_data["error_count"] == 0
        assert aggregation_data["status"] == "WARNING"  # Has warnings
        assert "A" in aggregation_data["components"]
        assert "B" in aggregation_data["components"]
        assert aggregation_data["test_metric"] == 123

    def test_check_operation_timeout(self, monitor):
        """Test operation timeout checking."""
        monitor.start_operation_tracking("TEST_OPERATION")

        # Simulate old start time
        monitor.current_operation.start_time = datetime.fromtimestamp(time.time() - 60)

        monitor.check_operation_timeout(30.0)  # 30 second timeout

        # Operation should be completed with timeout
        assert monitor.current_operation is None
        assert len(monitor.completed_operations) == 1
        completed = monitor.completed_operations[0]
        assert completed.status == OperationStatus.TIMEOUT
        assert "timeout" in completed.custom_metrics
        assert completed.custom_metrics["timeout"] is True

    def test_extract_metrics_from_logs(self, monitor):
        """Test extracting metrics from log records."""
        monitor.start_operation_tracking("TEST_OPERATION")

        # Mock log records
        mock_record1 = Mock()
        mock_record1.getMessage.return_value = "Processing 3 files with MSE: 0.001"
        mock_record1.levelname = "INFO"

        mock_record2 = Mock()
        mock_record2.getMessage.return_value = "Warning: High memory usage"
        mock_record2.levelname = "WARNING"

        monitor.extract_metrics_from_logs([mock_record1, mock_record2])

        operation = monitor.current_operation
        assert operation.warning_count == 1
        assert "file_count" in operation.custom_metrics
        assert operation.custom_metrics["file_count"] == 3
        assert "mse_value" in operation.custom_metrics
        assert operation.custom_metrics["mse_value"] == 0.001

    def test_enhanced_status_property(self, monitor):
        """Test enhanced status property based on error/warning counts."""
        monitor.start_operation_tracking("TEST_OPERATION")

        # Initially should be SUCCESS
        assert monitor.current_operation.enhanced_status == "SUCCESS"

        # Add warning
        monitor.track_log_level("WARNING", "test warning")
        assert monitor.current_operation.enhanced_status == "WARNING"

        # Add error
        monitor.track_log_level("ERROR", "test error")
        assert monitor.current_operation.enhanced_status == "ERROR"

    def test_no_current_operation_handling(self, monitor):
        """Test methods handle gracefully when no current operation."""
        # All these should not raise errors
        monitor.add_custom_metric("test", "value")
        monitor.track_request("A", "B", "op")
        monitor.track_response("B", "A", "op")
        monitor.track_log_level("INFO", "message")
        monitor.add_performance_metrics()
        monitor.track_optimization_metrics({})
        monitor.track_data_operation_metrics("TEST", {})

        # Should return empty dict
        assert monitor.get_operation_metrics_for_aggregation() == {}

        # Should return None
        assert monitor.end_operation_tracking() is None
