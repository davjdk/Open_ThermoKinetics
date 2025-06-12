"""
Tests for BufferManager module.
"""

import logging
import time
from datetime import datetime

from src.log_aggregator.buffer_manager import BufferedLogRecord, BufferManager


class TestBufferedLogRecord:
    """Test cases for BufferedLogRecord class."""

    def test_buffered_log_record_creation(self):
        """Test creation of BufferedLogRecord."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
        )
        timestamp = datetime.now()

        buffered = BufferedLogRecord(record=record, timestamp=timestamp)

        assert buffered.record == record
        assert buffered.timestamp == timestamp
        assert buffered.processed is False

    def test_buffered_log_record_auto_timestamp(self):
        """Test automatic timestamp setting."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
        )

        buffered = BufferedLogRecord(record=record, timestamp=None)

        assert buffered.timestamp is not None
        assert isinstance(buffered.timestamp, datetime)


class TestBufferManager:
    """Test cases for BufferManager class."""

    def test_buffer_manager_initialization(self):
        """Test BufferManager initialization."""
        manager = BufferManager(max_size=50, flush_interval=3.0)

        assert manager.max_size == 50
        assert manager.flush_interval == 3.0
        assert manager.get_buffer_size() == 0

    def test_add_record(self):
        """Test adding records to buffer."""
        manager = BufferManager()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
        )

        manager.add_record(record)

        assert manager.get_buffer_size() == 1
        stats = manager.get_statistics()
        assert stats["total_records_added"] == 1

    def test_should_process_size_threshold(self):
        """Test size-based processing trigger."""
        manager = BufferManager(max_size=2, flush_interval=1000.0)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
        )

        # Add records up to threshold
        assert manager.should_process() is False

        manager.add_record(record)
        assert manager.should_process() is False

        manager.add_record(record)
        assert manager.should_process() is True

    def test_should_process_time_threshold(self):
        """Test time-based processing trigger."""
        manager = BufferManager(max_size=1000, flush_interval=0.1)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
        )

        manager.add_record(record)
        assert manager.should_process() is False

        # Wait for time threshold
        time.sleep(0.15)
        assert manager.should_process() is True

    def test_get_records_for_processing(self):
        """Test retrieving records for processing."""
        manager = BufferManager()
        records = []

        for i in range(3):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0, msg=f"test message {i}", args=(), exc_info=None
            )
            records.append(record)
            manager.add_record(record)

        assert manager.get_buffer_size() == 3

        # Get records for processing
        buffered_records = manager.get_records_for_processing()

        assert len(buffered_records) == 3
        assert manager.get_buffer_size() == 0  # Buffer should be cleared

        # Check that records are properly wrapped
        for i, buffered in enumerate(buffered_records):
            assert isinstance(buffered, BufferedLogRecord)
            assert buffered.record.getMessage() == f"test message {i}"

    def test_clear_buffer(self):
        """Test clearing buffer."""
        manager = BufferManager()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
        )

        manager.add_record(record)
        manager.add_record(record)
        assert manager.get_buffer_size() == 2

        cleared_count = manager.clear_buffer()

        assert cleared_count == 2
        assert manager.get_buffer_size() == 0

    def test_statistics(self):
        """Test statistics collection."""
        manager = BufferManager()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
        )

        # Initial statistics
        stats = manager.get_statistics()
        assert stats["total_records_added"] == 0
        assert stats["total_flushes"] == 0
        assert stats["total_records_processed"] == 0

        # Add records and process
        manager.add_record(record)
        manager.add_record(record)

        stats = manager.get_statistics()
        assert stats["total_records_added"] == 2
        assert stats["current_buffer_size"] == 2  # Process records
        manager.get_records_for_processing()

        stats = manager.get_statistics()
        assert stats["total_flushes"] == 1
        assert stats["total_records_processed"] == 2
        assert stats["current_buffer_size"] == 0

    def test_reset_statistics(self):
        """Test resetting statistics."""
        manager = BufferManager()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
        )

        manager.add_record(record)
        manager.get_records_for_processing()

        # Statistics should be non-zero
        stats = manager.get_statistics()
        assert stats["total_records_added"] > 0
        assert stats["total_flushes"] > 0

        # Reset and verify
        manager.reset_statistics()

        stats = manager.get_statistics()
        assert stats["total_records_added"] == 0
        assert stats["total_flushes"] == 0
        assert stats["total_records_processed"] == 0
