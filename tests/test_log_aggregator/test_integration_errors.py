"""
Integration tests for error expansion with AggregatingHandler.

This module tests the integration of ErrorExpansionEngine with the main
AggregatingHandler to ensure proper error handling and expansion.
"""

import logging
import time
from unittest.mock import Mock, patch

import pytest

from src.log_aggregator.config import AggregationConfig
from src.log_aggregator.realtime_handler import AggregatingHandler


class TestErrorExpansionIntegration:
    """Integration tests for error expansion functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock target handler
        self.mock_target = Mock()

        # Create config with error expansion enabled
        self.config = AggregationConfig()
        self.config.error_expansion_enabled = True
        self.config.error_context_lines = 3
        self.config.error_threshold_level = "WARNING"
        self.config.buffer_size = 10
        self.config.flush_interval = 1.0

        # Create handler with error expansion
        self.handler = AggregatingHandler(target_handler=self.mock_target, config=self.config)

    def teardown_method(self):
        """Clean up after each test method."""
        self.handler.close()

    def test_error_expansion_enabled_initialization(self):
        """Test that error expansion is properly initialized when enabled."""
        assert self.handler.enable_error_expansion is True
        assert self.handler.error_expansion_engine is not None
        assert self.handler.error_expansion_engine.config.enabled is True

    def test_immediate_error_expansion(self):
        """Test that errors are immediately expanded when detected."""
        # Create an error log record
        error_record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="File not found: data.csv",
            args=(),
            exc_info=None,
        )
        error_record.filename = "test.py"

        # Emit the error record
        self.handler.emit(error_record)

        # Verify that target handler received an expanded record
        assert self.mock_target.emit.called

        # Get the emitted record
        emitted_record = self.mock_target.emit.call_args[0][0]

        # Verify it"s an expanded error
        expanded_message = emitted_record.getMessage()
        assert "DETAILED ERROR ANALYSIS" in expanded_message
        assert "ERROR" in expanded_message
        assert "File not found: data.csv" in expanded_message

    def test_error_expansion_with_context(self):
        """Test error expansion includes preceding context."""
        # Emit some context records first
        for i in range(3):
            context_record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="/path/to/context.py",
                lineno=10 + i,
                msg=f"Context message {i}",
                args=(),
                exc_info=None,
            )
            context_record.filename = "context.py"
            self.handler.emit(context_record)
            time.sleep(0.1)  # Small delay to ensure timestamp ordering

        # Reset mock to clear context emissions
        self.mock_target.reset_mock()

        # Emit error record
        error_record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="/path/to/error.py",
            lineno=100,
            msg="Warning: Operation failed",
            args=(),
            exc_info=None,
        )
        error_record.filename = "error.py"
        self.handler.emit(error_record)

        # Verify expanded error contains context
        assert self.mock_target.emit.called
        emitted_record = self.mock_target.emit.call_args[0][0]
        expanded_message = emitted_record.getMessage()

        assert "PRECEDING CONTEXT" in expanded_message
        assert "Context message" in expanded_message

    def test_non_error_records_not_expanded(self):
        """Test that non-error records are not expanded."""
        # Emit an INFO record
        info_record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Information message",
            args=(),
            exc_info=None,
        )
        info_record.filename = "test.py"

        self.handler.emit(info_record)

        # Verify normal forwarding (not expanded)
        assert self.mock_target.emit.called
        emitted_record = self.mock_target.emit.call_args[0][0]

        # Should be the original message, not expanded
        assert emitted_record.getMessage() == "Information message"
        assert "DETAILED ERROR ANALYSIS" not in emitted_record.getMessage()

    def test_error_expansion_toggle(self):
        """Test enabling and disabling error expansion."""
        # Initially enabled
        assert self.handler.enable_error_expansion is True

        # Disable error expansion
        self.handler.toggle_error_expansion(False)
        assert self.handler.enable_error_expansion is False

        # Emit error - should not be expanded
        error_record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        error_record.filename = "test.py"

        self.handler.emit(error_record)

        # Should receive original message, not expanded
        emitted_record = self.mock_target.emit.call_args[0][0]
        assert emitted_record.getMessage() == "Error message"
        assert "DETAILED ERROR ANALYSIS" not in emitted_record.getMessage()

        # Re-enable and test
        self.handler.toggle_error_expansion(True)
        assert self.handler.enable_error_expansion is True

    def test_error_expansion_statistics(self):
        """Test that error expansion statistics are tracked."""
        initial_stats = self.handler.get_statistics()
        initial_errors_expanded = initial_stats["handler"]["errors_expanded"]

        # Emit an error
        error_record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test error",
            args=(),
            exc_info=None,
        )
        error_record.filename = "test.py"

        self.handler.emit(error_record)

        # Check updated statistics
        final_stats = self.handler.get_statistics()
        assert final_stats["handler"]["errors_expanded"] == initial_errors_expanded + 1
        assert "error_expansion" in final_stats
        assert final_stats["handler"]["error_expansion_enabled"] is True

    def test_error_expansion_with_different_thresholds(self):
        """Test error expansion with different log level thresholds."""
        # Test with ERROR threshold - создаем новый конфиг с нужным порогом
        error_config = AggregationConfig(error_expansion_enabled=True, error_threshold_level="ERROR")
        handler_error = AggregatingHandler(target_handler=Mock(), config=error_config)

        # WARNING should not be expanded because threshold is ERROR
        warning_record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        warning_record.filename = "test.py"

        handler_error.emit(warning_record)
        emitted_record = handler_error.target_handler.emit.call_args[0][0]
        # Поскольку порог ERROR (40), а запись WARNING (30) - расширения не должно быть
        assert "DETAILED ERROR ANALYSIS" not in emitted_record.getMessage()

        # ERROR should be expanded
        error_record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        error_record.filename = "test.py"

        handler_error.emit(error_record)
        emitted_record = handler_error.target_handler.emit.call_args[0][0]
        assert "DETAILED ERROR ANALYSIS" in emitted_record.getMessage()

        handler_error.close()

    def test_error_expansion_with_disabled_aggregation(self):
        """Test error expansion when main aggregation is disabled."""
        # Disable main aggregation but keep error expansion
        self.handler.set_enabled(False)

        # Error should still be expanded if error expansion is enabled
        error_record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Error with disabled aggregation",
            args=(),
            exc_info=None,
        )
        error_record.filename = "test.py"

        self.handler.emit(error_record)

        # Should still forward to target (aggregation disabled)
        assert self.mock_target.emit.called
        emitted_record = self.mock_target.emit.call_args[0][0]

        # Should be original message since aggregation is disabled
        assert emitted_record.getMessage() == "Error with disabled aggregation"

    def test_error_expansion_exception_handling(self):
        """Test error expansion handles exceptions gracefully."""
        # Mock the error expansion engine to raise an exception
        with patch.object(self.handler.error_expansion_engine, "expand_error", side_effect=Exception("Test exception")):
            error_record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/path/to/test.py",
                lineno=42,
                msg="Error that will cause expansion failure",
                args=(),
                exc_info=None,
            )
            error_record.filename = "test.py"

            # Should not raise exception, should fallback to original record
            self.handler.emit(error_record)

            # Should still emit something (fallback)
            assert self.mock_target.emit.called

    def test_performance_with_many_errors(self):
        """Test performance impact of error expansion with many errors."""
        start_time = time.time()

        # Emit many error records
        for i in range(50):
            error_record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/path/to/test.py",
                lineno=42 + i,
                msg=f"Error message {i}",
                args=(),
                exc_info=None,
            )
            error_record.filename = "test.py"
            self.handler.emit(error_record)

        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (less than 2 seconds for 50 errors)
        assert elapsed_time < 2.0

        # Verify all errors were processed
        stats = self.handler.get_statistics()
        assert stats["handler"]["errors_expanded"] == 50

    def test_reset_error_expansion_statistics(self):
        """Test resetting error expansion statistics."""
        # Generate some errors
        for i in range(3):
            error_record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/path/to/test.py",
                lineno=42 + i,
                msg=f"Error {i}",
                args=(),
                exc_info=None,
            )
            error_record.filename = "test.py"
            self.handler.emit(error_record)

        # Verify statistics
        stats = self.handler.get_statistics()
        assert stats["handler"]["errors_expanded"] == 3
        assert stats["error_expansion"]["errors_analyzed"] == 3

        # Reset and verify
        self.handler.reset_statistics()
        reset_stats = self.handler.get_statistics()
        assert reset_stats["handler"]["errors_expanded"] == 0
        assert reset_stats["error_expansion"]["errors_analyzed"] == 0


class TestErrorExpansionConfiguration:
    """Test error expansion configuration integration."""

    def test_config_integration(self):
        """Test that configuration is properly integrated."""
        config = AggregationConfig()
        config.error_expansion_enabled = True
        config.error_context_lines = 7
        config.error_trace_depth = 15
        config.error_threshold_level = "CRITICAL"
        config.error_context_time_window = 20.0

        handler = AggregatingHandler(target_handler=Mock(), config=config)

        # Verify configuration was applied
        error_config = handler.error_expansion_engine.config
        assert error_config.enabled is True
        assert error_config.context_lines == 7
        assert error_config.trace_depth == 15
        assert error_config.error_threshold_level == "CRITICAL"
        assert error_config.context_time_window == 20.0

        handler.close()

    def test_disabled_error_expansion_config(self):
        """Test configuration with error expansion disabled."""
        config = AggregationConfig()
        config.error_expansion_enabled = False

        handler = AggregatingHandler(target_handler=Mock(), config=config)

        assert handler.enable_error_expansion is False

        handler.close()


@pytest.fixture
def sample_aggregating_handler():
    """Fixture providing a configured AggregatingHandler for tests."""
    config = AggregationConfig()
    config.error_expansion_enabled = True
    config.buffer_size = 5
    config.flush_interval = 0.5

    mock_target = Mock()
    handler = AggregatingHandler(target_handler=mock_target, config=config)

    yield handler, mock_target

    handler.close()
