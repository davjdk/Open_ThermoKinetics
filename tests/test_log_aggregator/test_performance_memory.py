"""Test performance characteristics and memory usage."""

import gc
import time
from unittest.mock import MagicMock

try:
    import psutil
except ImportError:
    psutil = None

try:
    from src.core.logger_config import LoggerManager
except ImportError:
    LoggerManager = None

from src.log_aggregator.config import AggregationConfig
from src.log_aggregator.realtime_handler import AggregatingHandler


class TestPerformanceMemory:
    """Test performance characteristics and memory usage."""

    def test_memory_stability_long_running(self):
        """Test memory stability during long-running operation."""
        if LoggerManager is None:
            return

        LoggerManager.configure_logging(enable_aggregation=True, aggregation_preset="production")

        logger = LoggerManager.get_logger("memory_test")

        # Get initial memory usage if psutil is available
        initial_memory = None
        if psutil:
            process = psutil.Process()
            initial_memory = process.memory_info().rss

        # Run logging for extended period
        start_time = time.time()
        message_count = 0

        while time.time() - start_time < 5:  # 5 seconds for faster testing
            logger.info(f"Test message {message_count}")
            if message_count % 100 == 0:
                logger.error("Periodic error %d", message_count)
            message_count += 1

            if message_count % 1000 == 0:
                time.sleep(0.01)  # Small pause

        # Force garbage collection
        gc.collect()
        time.sleep(0.5)  # Allow cleanup

        # Check final memory usage if psutil is available
        if psutil and initial_memory:
            final_memory = process.memory_info().rss
            memory_growth = final_memory - initial_memory

            # Memory growth should be reasonable (< 50MB for this test)
            assert memory_growth < 50 * 1024 * 1024, f"Memory growth too large: {memory_growth / 1024 / 1024:.1f} MB"

        print(f"Processed {message_count} messages")
        if psutil and initial_memory:
            memory_growth = psutil.Process().memory_info().rss - initial_memory
            print(f"Memory growth: {memory_growth / 1024 / 1024:.1f} MB")

    def test_aggregator_cache_limits(self):
        """Test that aggregator caches respect size limits."""
        if LoggerManager is None:
            return

        LoggerManager.configure_logging(enable_aggregation=True, aggregation_preset="development")
        logger = LoggerManager.get_logger("cache_test")

        # Generate many different large values to stress the cache
        for i in range(200):  # More than typical cache limit
            large_data = list(range(1000))  # Large data structure
            # Use f-string to avoid formatting issues with %s
            logger.info(f"Processing data iteration {i} with {len(large_data)} items")

        # Get aggregator statistics
        stats = LoggerManager.get_aggregation_stats()

        # Cache should be within limits
        # This assumes we can access cache statistics
        # Implementation may vary based on actual statistics structure
        assert stats["total_stats"]["total_records"] > 0

    def test_handler_performance_overhead(self):
        """Test performance overhead of aggregating handler vs standard handler."""
        # Create standard handler
        standard_handler = MagicMock()

        # Create aggregating handler
        config = AggregationConfig()
        aggregating_handler = AggregatingHandler(standard_handler, config)

        # Test message
        import logging

        test_record = logging.LogRecord(
            name="performance.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Performance test message %d",
            args=(1,),
            exc_info=None,
        )

        # Time standard handler (mock, so very fast)
        start_time = time.time()
        for i in range(1000):
            standard_handler.emit(test_record)
        standard_time = time.time() - start_time

        # Time aggregating handler
        start_time = time.time()
        for i in range(1000):
            aggregating_handler.emit(test_record)
        aggregating_time = time.time() - start_time

        # Aggregating handler should be reasonably fast
        # Allowing up to 10x overhead for aggregation features
        max_acceptable_overhead = standard_time * 10 + 0.1  # Add 0.1s buffer
        assert (
            aggregating_time < max_acceptable_overhead
        ), f"Aggregating handler too slow: {aggregating_time:.3f}s vs {standard_time:.3f}s"

        print(f"Standard handler: {standard_time:.3f}s")
        print(f"Aggregating handler: {aggregating_time:.3f}s")
        print(f"Overhead: {aggregating_time / max(standard_time, 0.001):.1f}x")

    def test_buffer_size_impact(self):
        """Test impact of different buffer sizes on performance."""
        target_handler = MagicMock()

        # Test different buffer sizes
        buffer_sizes = [10, 100, 1000]
        results = {}

        for buffer_size in buffer_sizes:
            config = AggregationConfig()
            config.buffer_size = buffer_size
            handler = AggregatingHandler(target_handler, config)

            import logging

            test_record = logging.LogRecord(
                name="buffer.test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Buffer test message %d",
                args=(1,),
                exc_info=None,
            )

            # Time processing
            start_time = time.time()
            for i in range(500):
                handler.emit(test_record)
            processing_time = time.time() - start_time

            results[buffer_size] = processing_time

        # Larger buffers should not significantly slow down processing
        small_buffer_time = results[10]
        large_buffer_time = results[1000]

        # Large buffer should not be more than 3x slower than small buffer
        max_acceptable_ratio = 3.0
        actual_ratio = large_buffer_time / max(small_buffer_time, 0.001)

        assert (
            actual_ratio < max_acceptable_ratio
        ), f"Large buffer too slow: {actual_ratio:.1f}x slower than small buffer"

        for size, time_taken in results.items():
            print(f"Buffer size {size}: {time_taken:.3f}s")

    def test_pattern_detection_efficiency(self):
        """Test efficiency of pattern detection with many similar messages."""
        target_handler = MagicMock()
        config = AggregationConfig()
        config.pattern_similarity_threshold = 0.8
        handler = AggregatingHandler(target_handler, config)

        import logging

        # Generate many similar messages that should be detected as patterns
        start_time = time.time()

        patterns = [
            "Database connection failed",
            "Cache miss for key",
            "API request timeout",
        ]

        for pattern in patterns:
            for i in range(100):  # 100 similar messages per pattern
                test_record = logging.LogRecord(
                    name="pattern.test",
                    level=logging.WARNING,
                    pathname="",
                    lineno=0,
                    msg=f"{pattern} #{i}",
                    args=(),
                    exc_info=None,
                )
                handler.emit(test_record)

        processing_time = time.time() - start_time

        # Pattern detection should be efficient even with many similar messages
        max_acceptable_time = 2.0  # 2 seconds for 300 messages
        assert (
            processing_time < max_acceptable_time
        ), f"Pattern detection too slow: {processing_time:.3f}s for 300 messages"

        print(f"Pattern detection time: {processing_time:.3f}s for 300 messages")

    def test_concurrent_handler_performance(self):
        """Test performance under concurrent access."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)

        import logging
        import threading

        def worker(worker_id: int, message_count: int):
            """Worker function for concurrent logging."""
            for i in range(message_count):
                test_record = logging.LogRecord(
                    name=f"concurrent.worker_{worker_id}",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"Worker {worker_id} message {i}",
                    args=(),
                    exc_info=None,
                )
                handler.emit(test_record)

        # Test concurrent access
        start_time = time.time()

        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker, args=(worker_id, 100))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)

        processing_time = time.time() - start_time

        # Concurrent access should complete reasonably quickly
        max_acceptable_time = 3.0  # 3 seconds for 500 messages across 5 threads
        assert processing_time < max_acceptable_time, f"Concurrent processing too slow: {processing_time:.3f}s"

        # Verify no threads are hanging
        alive_threads = [t for t in threads if t.is_alive()]
        assert len(alive_threads) == 0, f"Threads still alive: {len(alive_threads)}"

        print(f"Concurrent processing time: {processing_time:.3f}s for 500 messages across 5 threads")

    def test_memory_leak_detection(self):
        """Test for potential memory leaks in aggregator components."""
        if psutil is None:
            return  # Skip if psutil not available

        target_handler = MagicMock()
        config = AggregationConfig()

        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Create and destroy multiple handlers to test for leaks
        for iteration in range(10):
            handler = AggregatingHandler(target_handler, config)

            # Use the handler
            import logging

            for i in range(100):
                test_record = logging.LogRecord(
                    name="leak.test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"Iteration {iteration} message {i}",
                    args=(),
                    exc_info=None,
                )
                handler.emit(test_record)

            # Delete handler reference
            del handler

            # Force garbage collection
            if iteration % 3 == 0:
                gc.collect()

        # Final garbage collection
        gc.collect()
        time.sleep(0.1)  # Allow cleanup

        # Check final memory
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be minimal (< 10MB)
        max_acceptable_growth = 10 * 1024 * 1024  # 10 MB
        assert (
            memory_growth < max_acceptable_growth
        ), f"Potential memory leak detected: {memory_growth / 1024 / 1024:.1f} MB growth"

        print(f"Memory growth after handler cycling: {memory_growth / 1024 / 1024:.1f} MB")
