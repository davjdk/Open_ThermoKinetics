"""Test safe message handling across aggregator components."""

import logging
from datetime import datetime

from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.error_expansion import ErrorExpansionEngine
from src.log_aggregator.pattern_detector import PatternDetector
from src.log_aggregator.safe_message_utils import safe_extract_args, safe_get_message
from src.log_aggregator.value_aggregator import ValueAggregator


class TestSafeMessageHandling:
    """Test safe message handling across aggregator components."""

    def test_safe_get_message_with_format_errors(self):
        """Test safe_get_message with various formatting errors."""
        test_cases = [
            # (msg, args, expected_substring)
            ("Test error %d %s", (42,), "Test error"),  # Missing arg
            ("Value: %d", ("text",), "Value:"),  # Wrong type
            ("Format %s", (1, 2), "Format"),  # Extra arg
            ("No format", (), "No format"),  # No format
            ("%s %d %f", (), "%s %d %f"),  # No args with format
        ]

        for msg, args, expected in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )

            result = safe_get_message(record)
            assert expected in result
            assert isinstance(result, str)

    def test_safe_extract_args_robustness(self):
        """Test safe_extract_args with various edge cases."""
        # Normal case
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="Test %s", args=("arg",), exc_info=None
        )
        args = safe_extract_args(record)
        assert args == ("arg",)

        # No args
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="Test", args=(), exc_info=None
        )
        args = safe_extract_args(record)
        assert args == ()  # None args (edge case)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="Test", args=None, exc_info=None
        )
        # Manually set args to None to test edge case
        record.args = None
        args = safe_extract_args(record)
        assert args == ()

    def test_value_aggregator_with_bad_formatting(self):
        """Test ValueAggregator handles formatting errors gracefully."""
        aggregator = ValueAggregator()

        # Create problematic log record
        bad_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Array data: %s with size %d",
            args=(None,),
            exc_info=None,
        )

        buffered = BufferedLogRecord(record=bad_record, timestamp=datetime.now())

        # Should not raise exception
        result = aggregator.process_message(buffered)
        assert isinstance(result, str)

    def test_pattern_detector_with_bad_formatting(self):
        """Test PatternDetector handles formatting errors gracefully."""
        detector = PatternDetector()
        # Create records with formatting issues
        records = []
        test_data = [
            ("Pattern %d %s", (0,)),  # Missing arg
            ("Another %s", (1, 2)),  # Extra arg
            ("Normal message", ()),  # Normal
        ]

        for i, (msg, args) in enumerate(test_data):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
            records.append(buffered)

        # Should not raise exception
        patterns = detector.detect_patterns(records)
        assert isinstance(patterns, list)

    def test_error_expansion_with_bad_formatting(self):
        """Test ErrorExpansionEngine handles formatting errors gracefully."""
        engine = ErrorExpansionEngine()

        # Create error record with formatting issue
        error_record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error occurred: %s in module %s",
            args=("something",),
            exc_info=None,
        )
        buffered_error = BufferedLogRecord(record=error_record, timestamp=datetime.now())

        # Should not raise exception
        result = engine.expand_error(buffered_error, [])
        assert result is not None

    def test_unicode_message_handling(self):
        """Test handling of unicode characters in messages."""
        test_cases = [
            ("Тестовое сообщение %s", ("тест",)),
            ("Message with emoji: %s 🚀", ("test",)),
            ("Unicode error: %d %s", (42,)),  # Missing unicode arg
        ]

        for msg, args in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )

            # Should handle unicode without issues
            result = safe_get_message(record)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_large_data_formatting(self):
        """Test handling of large data structures in log formatting."""
        large_data = list(range(1000))

        # This could cause memory issues or slow formatting
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Large data: %s",
            args=(large_data,),
            exc_info=None,
        )

        result = safe_get_message(record)
        assert isinstance(result, str)
        # Message should be handled without crashing
        assert "Large data:" in result

    def test_none_and_empty_values(self):
        """Test handling of None and empty values in formatting."""
        test_cases = [
            ("Value is: %s", (None,)),
            ("Empty string: %s", ("",)),
            ("Zero: %d", (0,)),
            ("False: %s", (False,)),
        ]

        for msg, args in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )

            result = safe_get_message(record)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_circular_reference_protection(self):
        """Test protection against circular references in log data."""
        # Create circular reference
        circular_dict = {"key": None}
        circular_dict["key"] = circular_dict

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Circular data: %s",
            args=(circular_dict,),
            exc_info=None,
        )

        # Should handle circular reference without infinite recursion
        result = safe_get_message(record)
        assert isinstance(result, str)
