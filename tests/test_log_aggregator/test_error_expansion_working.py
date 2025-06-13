"""Simple working test for ErrorExpansionEngine component."""

import logging
from datetime import datetime

from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.error_expansion import ErrorExpansionEngine


class TestErrorExpansionWorking:
    """Simple working tests for ErrorExpansionEngine."""

    def test_basic_error_expansion(self):
        """Test basic error expansion functionality."""
        engine = ErrorExpansionEngine()

        # Simple error record
        error_record = logging.LogRecord(
            name="test_error",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Test error message",
            args=(),
            exc_info=None,
        )
        buffered_error = BufferedLogRecord(record=error_record, timestamp=datetime.now())

        # Should expand without issues
        result = engine.expand_error(buffered_error, [])
        assert result is not None

    def test_error_expansion_with_unicode(self):
        """Test error expansion with Unicode messages."""
        engine = ErrorExpansionEngine()

        # Unicode error record
        error_record = logging.LogRecord(
            name="unicode_test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Unicode error: Ошибка обработки",
            args=(),
            exc_info=None,
        )
        buffered_error = BufferedLogRecord(record=error_record, timestamp=datetime.now())

        # Should handle Unicode gracefully
        result = engine.expand_error(buffered_error, [])
        assert result is not None

    def test_error_expansion_with_context(self):
        """Test error expansion with context records."""
        engine = ErrorExpansionEngine()

        # Create context records
        context_records = []
        for i in range(3):
            context_record = logging.LogRecord(
                name="context_test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"Context record {i}",
                args=(),
                exc_info=None,
            )
            context_records.append(BufferedLogRecord(record=context_record, timestamp=datetime.now()))

        # Error record
        error_record = logging.LogRecord(
            name="error_test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error with context",
            args=(),
            exc_info=None,
        )
        buffered_error = BufferedLogRecord(record=error_record, timestamp=datetime.now())

        # Should expand with context
        result = engine.expand_error(buffered_error, context_records)
        assert result is not None
