"""
Test Stage 2: Prevent recursive processing of internal aggregator logs.

This test verifies that:
1. Internal aggregator logs don't trigger recursive processing
2. Error degradation works when internal error threshold is exceeded
3. Separate debug logging is configured correctly
4. Fallback behavior works for problematic records
"""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from src.core.logger_config import LoggerManager
from src.log_aggregator.config import AggregationConfig
from src.log_aggregator.realtime_handler import AggregatingHandler


class TestStage2PreventRecursion:
    """Test cases for Stage 2: Prevent recursive processing of internal logs."""

    def setup_method(self):
        """Setup test environment."""
        # Reset logger configuration
        LoggerManager._configured = False
        LoggerManager._aggregating_handlers = []

        # Clear any existing handlers from loggers
        for logger_name in ["log_aggregator.realtime_handler", "solid_state_kinetics"]:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.propagate = True

    def test_internal_log_filtering(self):
        """Test that internal log_aggregator messages are filtered out."""
        # Setup mock target handler
        mock_target = MagicMock()

        # Create aggregating handler
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler=mock_target, config=config)

        # Create internal log record
        internal_record = logging.LogRecord(
            name="log_aggregator.realtime_handler",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Internal aggregator error",
            args=(),
            exc_info=None,
        )

        # Emit internal record - should be forwarded directly
        handler.emit(internal_record)

        # Verify it was forwarded but not processed for aggregation
        mock_target.emit.assert_called_once_with(internal_record)

        # Verify statistics - should show record received but no processing
        stats = handler.get_statistics()
        assert stats["handler"]["total_records_received"] == 1
        assert stats["handler"]["total_records_forwarded"] == 1

    def test_external_log_processing(self):
        """Test that external logs are processed normally."""
        # Setup mock target handler
        mock_target = MagicMock()

        # Create aggregating handler
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler=mock_target, config=config)

        # Create external log record
        external_record = logging.LogRecord(
            name="gui.main_window",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="External log message",
            args=(),
            exc_info=None,
        )

        # Emit external record - should be processed for aggregation
        handler.emit(external_record)

        # Verify it was forwarded and potentially processed
        assert mock_target.emit.called

        # Verify statistics show processing
        stats = handler.get_statistics()
        assert stats["handler"]["total_records_received"] == 1

    def test_internal_error_monitoring(self):
        """Test internal error monitoring and degradation."""
        # Setup mock target handler
        mock_target = MagicMock()

        # Create config with low error threshold for testing
        config = AggregationConfig()
        config.max_internal_errors = 2
        config.error_reset_interval = 300

        handler = AggregatingHandler(target_handler=mock_target, config=config)

        # Simulate internal errors by calling _handle_internal_error directly
        error1 = Exception("First internal error")
        error2 = Exception("Second internal error")
        error3 = Exception("Third internal error - should trigger degradation")
        # First two errors should be logged but not trigger degradation
        handler._handle_internal_error(error1)
        assert handler._internal_error_count == 1
        assert handler.enable_error_expansion
        assert handler.enable_value_aggregation

        handler._handle_internal_error(error2)
        assert handler._internal_error_count == 2
        assert handler.enable_error_expansion
        assert handler.enable_value_aggregation

        # Third error should trigger degradation
        handler._handle_internal_error(error3)
        assert handler._internal_error_count == 3
        assert not handler.enable_error_expansion
        assert not handler.enable_value_aggregation

    def test_error_count_reset(self):
        """Test that error count resets after time interval."""
        # Setup mock target handler
        mock_target = MagicMock()

        # Create config with short reset interval for testing
        config = AggregationConfig()
        config.max_internal_errors = 5
        config.error_reset_interval = 1  # 1 second for testing

        handler = AggregatingHandler(target_handler=mock_target, config=config)

        # Simulate some errors
        for i in range(3):
            handler._handle_internal_error(Exception(f"Error {i}"))

        assert handler._internal_error_count == 3

        # Wait for reset interval and simulate another error
        time.sleep(1.1)  # Wait slightly longer than reset interval
        handler._handle_internal_error(Exception("Error after reset"))

        # Error count should have been reset
        assert handler._internal_error_count == 1

    def test_safe_fallback_processing(self):
        """Test safe fallback processing for problematic records."""
        # Setup mock target handler
        mock_target = MagicMock()

        # Create handler that will encounter processing errors
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler=mock_target, config=config)

        # Create problematic record with formatting issues
        problematic_record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message with %s formatting %d",  # Missing args
            args=(),  # Empty args will cause formatting error
            exc_info=None,
        )

        # Mock buffer_manager to raise an exception during processing
        with patch.object(handler.buffer_manager, "add_record", side_effect=Exception("Buffer error")):
            # Emit record - should trigger fallback
            handler.emit(problematic_record)

        # Verify fallback was called and record was forwarded
        assert mock_target.emit.called
        forwarded_record = mock_target.emit.call_args[0][0]

        # Verify the record message was safely formatted
        assert "[UNFORMATTED]" in forwarded_record.msg or "[FORMATTING_ERROR]" in forwarded_record.msg

    def test_separate_debug_logging_configuration(self):
        """Test that separate debug logging is configured for internal loggers."""
        # Configure logging with aggregation enabled
        LoggerManager.configure_logging(enable_aggregation=True, aggregation_preset="minimal")

        # Check that internal loggers have separate handlers and no propagation
        internal_logger_names = [
            "log_aggregator.realtime_handler",
            "log_aggregator.pattern_detector",
            "log_aggregator.error_expansion",
        ]

        for logger_name in internal_logger_names:
            logger = logging.getLogger(logger_name)

            # Should have handlers (from debug setup)
            assert len(logger.handlers) > 0
            # Should not propagate to prevent recursion
            assert not logger.propagate  # Should be set to DEBUG level
            assert logger.level == logging.DEBUG

    def test_no_recursive_chain_in_logs(self):
        """Integration test to verify no recursive chains occur."""
        # Configure full logging system
        LoggerManager.configure_logging(
            enable_aggregation=True, enable_error_expansion=True, aggregation_preset="minimal"
        )

        # Get both application and internal loggers
        app_logger = LoggerManager.get_logger("test.module")
        internal_logger = LoggerManager.get_logger("log_aggregator.realtime_handler")

        # Count initial log records
        initial_count = 0
        for handler in LoggerManager._aggregating_handlers:
            initial_count += handler._total_records_received

        # Log from application - should be processed
        app_logger.error("Application error message")

        # Log from internal aggregator - should be filtered
        internal_logger.error("Internal aggregator error")

        # Log another application message
        app_logger.info("Another application message")

        # Verify no explosive growth in record count
        final_count = 0
        for handler in LoggerManager._aggregating_handlers:
            final_count += handler._total_records_received

        # Should have processed only the external messages
        records_processed = final_count - initial_count
        # Allow for some configuration-related logs but verify main filtering works
        assert records_processed < 20  # Much less than what we'd see with recursion

    def test_configuration_parameters(self):
        """Test that new configuration parameters are properly handled."""
        config = AggregationConfig()
        # Verify new Stage 2 parameters exist with default values
        assert hasattr(config, "prevent_internal_recursion")
        assert config.prevent_internal_recursion

        assert hasattr(config, "max_internal_errors")
        assert config.max_internal_errors == 10

        assert hasattr(config, "error_reset_interval")
        assert config.error_reset_interval == 300

        assert hasattr(config, "separate_debug_logging")
        assert config.separate_debug_logging

        # Test that these parameters are used in handler initialization
        mock_target = MagicMock()
        config.max_internal_errors = 5
        config.error_reset_interval = 600

        handler = AggregatingHandler(target_handler=mock_target, config=config)
        assert handler._max_internal_errors == 5
        assert handler._error_reset_interval == 600


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
