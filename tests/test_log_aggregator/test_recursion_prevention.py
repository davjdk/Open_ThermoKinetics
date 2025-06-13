"""Test prevention of recursive log processing."""

import logging
import time
from unittest.mock import MagicMock, patch

from src.log_aggregator.config import AggregationConfig
from src.log_aggregator.realtime_handler import AggregatingHandler


class TestRecursionPrevention:
    """Test prevention of recursive log processing."""

    def test_internal_logger_filtering(self):
        """Test that internal log_aggregator messages are filtered out."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)

        # Internal aggregator message - should be forwarded directly
        internal_record = logging.LogRecord(
            name="log_aggregator.realtime_handler",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Internal error",
            args=(),
            exc_info=None,
        )

        handler.emit(internal_record)  # Should be forwarded directly without aggregation
        target_handler.emit.assert_called_once_with(internal_record)

        # External message - should also be forwarded (but with aggregation processing)
        target_handler.reset_mock()
        external_record = logging.LogRecord(
            name="app.module", level=logging.INFO, pathname="", lineno=0, msg="App message", args=(), exc_info=None
        )

        handler.emit(external_record)

        # Should be forwarded (aggregating handler forwards all messages)
        target_handler.emit.assert_called_once_with(external_record)

    def test_cascade_error_prevention(self):
        """Test prevention of cascading internal errors."""
        target_handler = MagicMock()
        config = AggregationConfig()  # Mock internal error in value aggregator
        with patch(
            "src.log_aggregator.realtime_handler.AggregatingHandler._handle_internal_error"
        ) as mock_error_handler:
            handler = AggregatingHandler(target_handler, config)

            # Force internal error by mocking value_aggregator
            handler.value_aggregator.process_message = MagicMock(side_effect=Exception("Formatting error"))

            # This should trigger internal error handling
            test_record = logging.LogRecord(
                name="app.test", level=logging.INFO, pathname="", lineno=0, msg="Test message", args=(), exc_info=None
            )

            handler.emit(test_record)

            # Internal error should be caught and handled
            mock_error_handler.assert_called()

    def test_error_threshold_degradation(self):
        """Test automatic degradation when error threshold is exceeded."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)

        # Set low threshold for testing
        handler._max_internal_errors = 3  # Simulate multiple internal errors
        for i in range(5):
            handler._handle_internal_error(Exception(f"Error {i}"))

        # After threshold, features should be disabled
        assert not handler.enable_error_expansion
        assert not handler.enable_value_aggregation

    def test_internal_logger_patterns(self):
        """Test detection of various internal logger patterns."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)

        internal_patterns = [
            "log_aggregator.realtime_handler",
            "log_aggregator.buffer_manager",
            "log_aggregator.pattern_detector",
            "log_aggregator.value_aggregator",
            "log_aggregator.error_expansion",
        ]

        for pattern in internal_patterns:
            target_handler.reset_mock()
            internal_record = logging.LogRecord(
                name=pattern,
                level=logging.WARNING,
                pathname="",
                lineno=0,
                msg="Internal message",
                args=(),
                exc_info=None,
            )

            handler.emit(internal_record)

            # Should be forwarded directly
            target_handler.emit.assert_called_once_with(internal_record)

    def test_error_recovery_mechanism(self):
        """Test that handler can recover from internal errors."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)

        # Mock an internal method to fail initially, then succeed
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary error")
            return "processed"

        handler.value_aggregator.process_message = MagicMock(side_effect=side_effect)

        # First two calls should trigger error handling
        for i in range(2):
            test_record = logging.LogRecord(
                name="app.test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"Test message {i}",
                args=(),
                exc_info=None,
            )
            handler.emit(test_record)

        # Third call should succeed
        test_record = logging.LogRecord(
            name="app.test", level=logging.INFO, pathname="", lineno=0, msg="Test message 3", args=(), exc_info=None
        )
        handler.emit(test_record)

        # Handler should still be functional
        assert handler._enabled

    def test_cyclic_logging_prevention(self):
        """Test prevention of cyclic logging in error handling."""
        target_handler = MagicMock()
        config = AggregationConfig()

        # Create a handler that logs to itself (simulating a cycle)
        handler = AggregatingHandler(target_handler, config)  # Mock the internal error handler to try to log
        original_handle_error = handler._handle_internal_error

        def mock_handle_error(error):
            # This simulates trying to log during error handling
            # which could create a cycle
            try:
                error_record = logging.LogRecord(
                    name="log_aggregator.error_handler",
                    level=logging.ERROR,
                    pathname="",
                    lineno=0,
                    msg="Error in error handler",
                    args=(),
                    exc_info=None,
                )
                handler.emit(error_record)
            except Exception:
                pass  # Prevent actual cycles in test
            return original_handle_error(error)

        handler._handle_internal_error = mock_handle_error

        # Force an error in processing
        handler.value_aggregator.process_message = MagicMock(side_effect=Exception("Test error"))

        # This should not create an infinite loop
        test_record = logging.LogRecord(
            name="app.test", level=logging.INFO, pathname="", lineno=0, msg="Test message", args=(), exc_info=None
        )

        # Should complete without hanging
        start_time = time.time()
        handler.emit(test_record)
        end_time = time.time()  # Should complete quickly (not hang in infinite loop)
        assert end_time - start_time < 1.0  # Should take less than 1 second

    def test_health_status_during_errors(self):
        """Test that health status reflects error conditions."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)

        # Initial state should be healthy
        assert handler._enabled

        # Set low threshold for testing
        handler._max_internal_errors = 3

        # Force multiple errors to trigger degradation
        for i in range(5):  # Exceed the threshold we just set
            handler._handle_internal_error(Exception(f"Error {i}"))

        # Handler should be in degraded state
        assert not handler.enable_error_expansion
        assert not handler.enable_value_aggregation

    def test_safe_shutdown_on_errors(self):
        """Test that handler shuts down safely on critical errors."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)

        # Mock critical error in buffer manager
        handler.buffer_manager.add_record = MagicMock(side_effect=MemoryError("Out of memory"))

        test_record = logging.LogRecord(
            name="app.test", level=logging.INFO, pathname="", lineno=0, msg="Test message", args=(), exc_info=None
        )

        # Should handle critical error gracefully
        handler.emit(test_record)

        # Handler should still forward the record despite internal errors
        target_handler.emit.assert_called()
