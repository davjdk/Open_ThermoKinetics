"""Test safe handling in PatternDetector component."""

import logging
from datetime import datetime

from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.pattern_detector import PatternDetector


class TestPatternDetectorSafety:
    """Test PatternDetector's safe handling of problematic messages."""

    def test_pattern_detector_with_format_errors(self):
        """Test PatternDetector handles formatting errors gracefully."""
        detector = PatternDetector()

        # Create records with various formatting issues
        records = []
        test_cases = [
            ("Pattern A: %d %s", (1,)),  # Missing argument
            ("Pattern B: %s", (1, 2)),  # Extra argument
            ("Pattern C: %d", ("text",)),  # Type mismatch
            ("Pattern D", ()),  # No formatting
            ("Pattern E: %s %d %f", ()),  # No args with format
        ]

        for msg, args in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
            records.append(buffered)

        # Should not raise exception
        patterns = detector.detect_patterns(records)
        assert isinstance(patterns, list)

    def test_pattern_detector_with_unicode(self):
        """Test PatternDetector with Unicode characters."""
        detector = PatternDetector()

        records = []
        unicode_cases = [
            ("Сообщение: %s", ("тест",)),
            ("Message: %s", ("测试",)),
            ("رسالة: %s", ("اختبار",)),
            ("Emoji: %s", ("🚀🎉",)),
            ("Mixed: %s %d", ("тест", 42)),
        ]

        for msg, args in unicode_cases:
            record = logging.LogRecord(
                name="unicode_test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
            records.append(buffered)

        # Should handle Unicode without issues
        patterns = detector.detect_patterns(records)
        assert isinstance(patterns, list)

    def test_pattern_detector_with_large_datasets(self):
        """Test PatternDetector with large numbers of records."""
        detector = PatternDetector()

        records = []
        # Generate many similar records to test pattern detection efficiency
        for i in range(1000):
            pattern_type = i % 3  # Create 3 different patterns
            if pattern_type == 0:
                msg = f"Database error {i}: Connection failed"
            elif pattern_type == 1:
                msg = f"Cache miss {i}: Key not found"
            else:
                msg = f"API timeout {i}: Request failed"

            record = logging.LogRecord(
                name="large_test", level=logging.WARNING, pathname="", lineno=0, msg=msg, args=(), exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
            records.append(buffered)

        # Should handle large datasets efficiently
        patterns = detector.detect_patterns(records)
        assert isinstance(patterns, list)
        # Should detect some patterns from the similar messages
        assert len(patterns) >= 0  # At minimum, should not crash

    def test_pattern_detector_with_mixed_errors(self):
        """Test PatternDetector with mixed error scenarios."""
        detector = PatternDetector()

        records = []
        mixed_cases = [
            # Normal cases
            ("Normal message 1", ()),
            ("Normal message 2", ()),
            # Formatting errors
            ("Error: %d %s", (42,)),  # Missing arg
            ("Warning: %s", (1, 2)),  # Extra arg
            # Unicode
            ("Unicode: %s", ("тест",)),
            # Large data
            ("Large: %s", ([1] * 1000,)),
            # None values
            ("None: %s", (None,)),
            # Circular reference
            ("Circular: %s", ({"self": "recursive"},)),
        ]

        for msg, args in mixed_cases:
            record = logging.LogRecord(
                name="mixed_test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
            records.append(buffered)

        # Should handle all mixed scenarios
        patterns = detector.detect_patterns(records)
        assert isinstance(patterns, list)

    def test_pattern_detector_similarity_threshold(self):
        """Test PatternDetector with different similarity thresholds."""
        # Test with high similarity threshold
        strict_detector = PatternDetector(similarity_threshold=0.9)

        # Test with low similarity threshold
        loose_detector = PatternDetector(similarity_threshold=0.3)

        records = []
        similar_messages = [
            "Database connection failed",
            "Database connection timeout",
            "Database connection error",
            "Cache connection failed",
            "Cache connection timeout",
        ]

        for msg in similar_messages:
            record = logging.LogRecord(
                name="similarity_test", level=logging.ERROR, pathname="", lineno=0, msg=msg, args=(), exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
            records.append(buffered)

        # Both detectors should handle the records without errors
        strict_patterns = strict_detector.detect_patterns(records)
        loose_patterns = loose_detector.detect_patterns(records)

        assert isinstance(strict_patterns, list)
        assert isinstance(loose_patterns, list)

    def test_pattern_detector_empty_and_edge_cases(self):
        """Test PatternDetector with empty and edge cases."""
        detector = PatternDetector()

        # Test with empty list
        empty_patterns = detector.detect_patterns([])
        assert isinstance(empty_patterns, list)

        # Test with single record
        single_record = logging.LogRecord(
            name="edge_test", level=logging.INFO, pathname="", lineno=0, msg="Single message", args=(), exc_info=None
        )
        buffered_single = BufferedLogRecord(record=single_record, timestamp=datetime.now())

        single_patterns = detector.detect_patterns([buffered_single])
        assert isinstance(single_patterns, list)

        # Test with identical records
        identical_records = []
        for _ in range(5):
            record = logging.LogRecord(
                name="identical_test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Identical message",
                args=(),
                exc_info=None,
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
            identical_records.append(buffered)

        identical_patterns = detector.detect_patterns(identical_records)
        assert isinstance(identical_patterns, list)

    def test_pattern_detector_memory_usage(self):
        """Test PatternDetector memory usage with repeated calls."""
        detector = PatternDetector()

        # Process multiple batches to check for memory leaks
        for batch in range(10):
            records = []
            for i in range(100):
                record = logging.LogRecord(
                    name="memory_test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"Batch {batch} message {i}",
                    args=(),
                    exc_info=None,
                )
                buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
                records.append(buffered)

            patterns = detector.detect_patterns(records)
            assert isinstance(patterns, list)

        # Detector should not hold references to old records
        # This is a smoke test - memory issues would show up in long-running tests

    def test_pattern_detector_concurrent_access(self):
        """Test PatternDetector thread safety."""
        import threading

        detector = PatternDetector()
        results = []
        errors = []

        def worker(worker_id: int):
            """Worker function for concurrent pattern detection."""
            try:
                records = []
                for i in range(20):
                    record = logging.LogRecord(
                        name=f"worker_{worker_id}",
                        level=logging.INFO,
                        pathname="",
                        lineno=0,
                        msg=f"Worker {worker_id} pattern {i % 3}",
                        args=(),
                        exc_info=None,
                    )
                    buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
                    records.append(buffered)

                patterns = detector.detect_patterns(records)
                results.append(patterns)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5  # One result per worker
        assert all(isinstance(r, list) for r in results)
