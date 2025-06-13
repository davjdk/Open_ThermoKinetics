"""Test safe handling in ValueAggregator component."""

import logging
from datetime import datetime

from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.value_aggregator import ValueAggregator


class TestValueAggregatorSafety:
    """Test ValueAggregator's safe handling of problematic messages."""

    def test_value_aggregator_with_format_errors(self):
        """Test ValueAggregator handles formatting errors gracefully."""
        aggregator = ValueAggregator()

        # Test cases with various formatting problems
        test_cases = [
            ("Value: %d", ("not_a_number",)),  # Type mismatch
            ("Array: %s, Count: %d", ([1, 2, 3],)),  # Missing second argument
            ("Data: %s %s %s", ("a", "b")),  # Too few arguments
            ("Simple: %s", ("text", "extra")),  # Too many arguments
            ("No format", ()),  # No formatting at all
        ]

        for msg, args in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())

            # Should not raise exception
            result = aggregator.process_message(buffered)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_value_aggregator_with_large_data(self):
        """Test ValueAggregator with large data structures."""
        aggregator = ValueAggregator()

        # Create large data structure
        large_list = list(range(10000))
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}

        test_cases = [
            ("Large list: %s", (large_list,)),
            ("Large dict: %s", (large_dict,)),
            ("Mixed large data: %s %s", (large_list, large_dict)),
        ]

        for msg, args in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())

            # Should handle large data without issues
            result = aggregator.process_message(buffered)
            assert isinstance(result, str)

    def test_value_aggregator_with_none_values(self):
        """Test ValueAggregator with None and empty values."""
        aggregator = ValueAggregator()

        test_cases = [
            ("None value: %s", (None,)),
            ("Empty string: %s", ("",)),
            ("Zero: %d", (0,)),
            ("False: %s", (False,)),
            ("Empty list: %s", ([],)),
            ("Empty dict: %s", ({},)),
        ]

        for msg, args in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())

            result = aggregator.process_message(buffered)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_value_aggregator_unicode_handling(self):
        """Test ValueAggregator with Unicode characters."""
        aggregator = ValueAggregator()

        test_cases = [
            ("Unicode message: %s", ("тестовое сообщение",)),
            ("Emoji: %s", ("🚀 запуск системы",)),
            ("Mixed: %s %d", ("тест", 42)),
            ("Chinese: %s", ("测试消息",)),
            ("Arabic: %s", ("رسالة اختبار",)),
        ]

        for msg, args in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())

            result = aggregator.process_message(buffered)
            assert isinstance(result, str)
            # Should preserve Unicode content
            if args and isinstance(args[0], str):
                # Some Unicode content should be preserved
                assert len(result) > 0

    def test_value_aggregator_circular_references(self):
        """Test ValueAggregator with circular references."""
        aggregator = ValueAggregator()

        # Create circular reference
        circular_dict = {"self": None}
        circular_dict["self"] = circular_dict

        circular_list = [None]
        circular_list[0] = circular_list

        test_cases = [
            ("Circular dict: %s", (circular_dict,)),
            ("Circular list: %s", (circular_list,)),
        ]

        for msg, args in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())

            # Should handle circular references without infinite recursion
            result = aggregator.process_message(buffered)
            assert isinstance(result, str)

    def test_value_aggregator_memory_efficiency(self):
        """Test ValueAggregator doesn't consume excessive memory."""
        aggregator = ValueAggregator()

        # Process many messages with large data
        for i in range(100):
            large_data = list(range(1000))  # 1000 elements each time
            record = logging.LogRecord(
                name="memory_test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Large data iteration %d: %s",
                args=(i, large_data),
                exc_info=None,
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())

            result = aggregator.process_message(buffered)
            assert isinstance(result, str)

        # Aggregator should not hold references to all the large data
        # This is more of a smoke test - memory leaks would show up in longer runs

    def test_value_aggregator_concurrent_safety(self):
        """Test ValueAggregator thread safety."""
        import threading

        aggregator = ValueAggregator()
        results = []
        errors = []

        def worker(worker_id: int):
            """Worker function for concurrent testing."""
            try:
                for i in range(50):
                    record = logging.LogRecord(
                        name=f"worker_{worker_id}",
                        level=logging.INFO,
                        pathname="",
                        lineno=0,
                        msg=f"Worker {worker_id} message {i}: %s",
                        args=(f"data_{i}",),
                        exc_info=None,
                    )
                    buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
                    result = aggregator.process_message(buffered)
                    results.append(result)
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
        assert len(results) == 250  # 5 workers * 50 messages each
        assert all(isinstance(r, str) for r in results)
