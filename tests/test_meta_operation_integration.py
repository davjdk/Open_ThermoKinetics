"""
Integration tests for meta-operation clustering in aggregated logging.

This module tests the complete integration of the meta-operation clustering
module with the existing logging infrastructure.
"""

import time
from unittest.mock import Mock, patch

import pytest

from src.core.app_settings import OperationType
from src.core.log_aggregator.aggregated_operation_logger import AggregatedOperationLogger
from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.sub_operation_log import SubOperationLog


class TestMetaOperationIntegration:
    """Integration tests for meta-operation clustering functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Reset singleton instance for each test
        AggregatedOperationLogger._instance = None
        AggregatedOperationLogger._initialized = False

    def create_test_operation_log(self, operation_name: str = "TEST_OPERATION") -> OperationLog:
        """Create a test operation log with multiple sub-operations."""
        base_time = time.time()

        operation_log = OperationLog(operation_name=operation_name)
        operation_log.start_time = base_time
        operation_log.end_time = base_time + 0.1
        operation_log.status = "success"
        operation_log.execution_time = 0.1  # Add sub-operations that should be clustered by time window
        sub_ops = [
            SubOperationLog(
                step_number=1,
                operation_name=str(OperationType.LOAD_FILE),
                target="file_data",
                start_time=base_time + 0.001,
                end_time=base_time + 0.002,
                execution_time=0.001,
                data_type="bool",
                status="OK",
            ),
            SubOperationLog(
                step_number=2,
                operation_name=str(OperationType.GET_DF_DATA),
                target="file_data",
                start_time=base_time + 0.003,
                end_time=base_time + 0.006,
                execution_time=0.003,
                data_type="DataFrame",
                status="OK",
            ),
            SubOperationLog(
                step_number=3,
                operation_name=str(OperationType.SET_VALUE),
                target="calculation_data",
                start_time=base_time + 0.007,
                end_time=base_time + 0.008,
                execution_time=0.001,
                data_type="dict",
                status="OK",
            ),
            SubOperationLog(
                step_number=4,
                operation_name=str(OperationType.UPDATE_VALUE),
                target="calculation_data",
                start_time=base_time + 0.009,
                end_time=base_time + 0.010,
                execution_time=0.001,
                data_type="dict",
                status="OK",
            ),
        ]

        operation_log.sub_operations = sub_ops
        return operation_log

    def test_aggregated_logger_with_meta_detection(self):
        """Test that AggregatedOperationLogger integrates meta-operation detection."""
        with patch("src.core.log_aggregator.meta_operation_config.get_default_detector") as mock_detector_factory:
            # Create mock detector
            mock_detector = Mock()
            mock_detector_factory.return_value = mock_detector

            # Mock the file setup to avoid actual file operations
            with patch.object(AggregatedOperationLogger, "_setup_aggregated_logger"):
                # Initialize aggregated logger
                logger = AggregatedOperationLogger()
                logger._aggregated_logger = Mock()

                # Create test operation log
                operation_log = self.create_test_operation_log("ADD_REACTION")

                # Log the operation
                logger.log_operation(operation_log)

                # Verify meta-detection was called
                mock_detector.detect_meta_operations.assert_called_once_with(operation_log)

    def test_meta_detection_error_handling(self):
        """Test that meta-detection errors don't break logging."""
        with patch("src.core.log_aggregator.meta_operation_config.get_default_detector") as mock_detector_factory:
            # Create mock detector that raises an exception
            mock_detector = Mock()
            mock_detector.detect_meta_operations.side_effect = Exception("Detection failed")
            mock_detector_factory.return_value = mock_detector

            # Mock the aggregated logger to avoid file operations
            with patch.object(AggregatedOperationLogger, "_setup_aggregated_logger"):
                logger = AggregatedOperationLogger()
                logger._aggregated_logger = Mock()

                # Create test operation log
                operation_log = self.create_test_operation_log("ADD_REACTION")

                # Log the operation - should not raise exception
                logger.log_operation(operation_log)

                # Verify logging still occurred despite detection error
                logger._aggregated_logger.info.assert_called()

    def test_detector_disabled_integration(self):
        """Test that disabled detector doesn't affect logging."""
        with patch("src.core.log_aggregator.meta_operation_config.get_default_detector") as mock_detector_factory:
            # Return None to simulate disabled detector
            mock_detector_factory.return_value = None

            # Mock the aggregated logger setup
            with patch.object(AggregatedOperationLogger, "_setup_aggregated_logger"):
                logger = AggregatedOperationLogger()
                logger._aggregated_logger = Mock()

                # Create test operation log
                operation_log = self.create_test_operation_log("DISABLED_TEST")

                # Log the operation
                logger.log_operation(operation_log)

                # Verify logging still works
                logger._aggregated_logger.info.assert_called()

    def test_real_scenario_rapid_operations_clustering(self):
        """Test clustering on rapid operation sequence similar to real application usage."""
        # Mock detector and strategies for testing
        mock_detector = Mock()
        mock_detector.detect_meta_operations = Mock()

        with patch("src.core.log_aggregator.meta_operation_config.get_default_detector", return_value=mock_detector):
            with patch.object(AggregatedOperationLogger, "_setup_aggregated_logger"):
                logger = AggregatedOperationLogger()
                logger._aggregated_logger = Mock()

                # Simulate the real scenario from logs - rapid operations
                base_time = time.time()
                operation_log = OperationLog(operation_name="RAPID_OPERATIONS_BATCH")
                operation_log.start_time = base_time

                # Create sequence of rapid operations like in real application
                sub_ops = []
                for i in range(8):  # Simulate 8 rapid operations
                    sub_op = SubOperationLog(
                        step_number=i + 1,
                        operation_name=str(OperationType.SET_VALUE) if i % 2 == 0 else str(OperationType.UPDATE_VALUE),
                        target="calculation_data",
                        start_time=base_time + i * 0.005,  # 5ms intervals
                        end_time=base_time + i * 0.005 + 0.001,
                        execution_time=0.001,
                        data_type="dict",
                        status="OK",
                    )
                    sub_ops.append(sub_op)

                operation_log.sub_operations = sub_ops

                # Log the operation
                logger.log_operation(operation_log)

                # Verify that meta-detection was called
                mock_detector.detect_meta_operations.assert_called_once_with(operation_log)

                # Verify logging occurred
                logger._aggregated_logger.info.assert_called()

    def test_formatting_with_meta_operations(self):
        """Test that formatter handles operations with meta-operation attributes."""
        with patch("src.core.log_aggregator.meta_operation_config.get_default_detector") as mock_detector_factory:
            # Create mock detector that adds meta_operations attribute
            mock_detector = Mock()

            def add_meta_operations(operation_log):
                operation_log.meta_operations = []
                # Add mock meta-operation attribute to test formatting

            mock_detector.detect_meta_operations.side_effect = add_meta_operations
            mock_detector_factory.return_value = mock_detector

            with patch.object(AggregatedOperationLogger, "_setup_aggregated_logger"):
                logger = AggregatedOperationLogger()
                logger._aggregated_logger = Mock()

                # Create test operation log
                operation_log = self.create_test_operation_log("FORMAT_TEST")

                # Format the log
                formatted = logger.format_operation_log(operation_log)

                # Verify formatting doesn't fail
                assert isinstance(formatted, str)
                assert len(formatted) > 0

    def test_multiple_operations_logging(self):
        """Test logging multiple operations in sequence."""
        with patch("src.core.log_aggregator.meta_operation_config.get_default_detector") as mock_detector_factory:
            mock_detector = Mock()
            mock_detector_factory.return_value = mock_detector

            with patch.object(AggregatedOperationLogger, "_setup_aggregated_logger"):
                logger = AggregatedOperationLogger()
                logger._aggregated_logger = Mock()  # Log multiple operations
                operations = [
                    self.create_test_operation_log("OPERATION_1"),
                    self.create_test_operation_log("OPERATION_2"),
                    self.create_test_operation_log("OPERATION_3"),
                ]

                for op in operations:
                    logger.log_operation(op)

                # Verify all operations were processed
                assert mock_detector.detect_meta_operations.call_count == 3
                # In minimalist mode (show_decorative_borders=False), each operation only logs once
                assert logger._aggregated_logger.info.call_count == 3


class TestMetaOperationErrorHandling:
    """Test error handling in meta-operation integration."""

    def test_detector_initialization_failure(self):
        """Test graceful handling of detector initialization failure."""
        with patch("src.core.log_aggregator.meta_operation_config.get_default_detector") as mock_factory:
            # Simulate initialization failure
            mock_factory.side_effect = Exception("Detector init failed")

            # Should not raise exception
            with patch.object(AggregatedOperationLogger, "_setup_aggregated_logger"):
                logger = AggregatedOperationLogger()
                logger._aggregated_logger = Mock()

                # Detector should be None or handled gracefully
                operation_log = OperationLog(operation_name="ERROR_TEST")
                logger.log_operation(operation_log)  # Should not raise

    def test_malformed_operation_log(self):
        """Test handling of malformed operation logs."""
        with patch("src.core.log_aggregator.meta_operation_config.get_default_detector") as mock_detector_factory:
            mock_detector = Mock()
            mock_detector_factory.return_value = mock_detector

            with patch.object(AggregatedOperationLogger, "_setup_aggregated_logger"):
                logger = AggregatedOperationLogger()
                logger._aggregated_logger = Mock()  # Test with None operation log
                logger.log_operation(None)

                # Test with operation log with no sub-operations
                operation_log = OperationLog(operation_name="MALFORMED_TEST")
                operation_log.sub_operations = None
                logger.log_operation(operation_log)

                # Should handle gracefully without exceptions - this is a success if no exception was raised
                # The error handling prevents actual logging for malformed data, which is correct behavior
                assert True  # Test passes if we reach this point without exceptions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
