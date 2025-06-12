"""
Buffer management module for log aggregation system.

This module handles in-memory buffering of log records with time-based
and size-based flushing mechanisms.
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, List


@dataclass
class BufferedLogRecord:
    """Container for log record with additional metadata for processing."""

    record: logging.LogRecord
    timestamp: datetime
    processed: bool = False

    def __post_init__(self):
        """Ensure timestamp is set if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BufferManager:
    """
    Manages buffering of log records with automatic flushing.

    Provides thread-safe operations for adding records and retrieving
    them for processing based on size and time thresholds.
    """

    def __init__(self, max_size: int = 100, flush_interval: float = 5.0):
        """
        Initialize buffer manager.

        Args:
            max_size: Maximum number of records to buffer before forcing flush
            flush_interval: Time in seconds between automatic flushes
        """
        self.max_size = max_size
        self.flush_interval = flush_interval

        self._buffer: Deque[BufferedLogRecord] = deque()
        self._context_buffer: Deque[BufferedLogRecord] = deque(maxlen=50)  # For error context
        self._lock = threading.RLock()
        self._last_flush_time = time.time()

        # Statistics
        self._total_records_added = 0
        self._total_flushes = 0
        self._total_records_processed = 0

    def add_record(self, record: logging.LogRecord) -> None:
        """
        Add a log record to the buffer.

        Args:
            record: LogRecord to add to buffer
        """
        with self._lock:
            buffered_record = BufferedLogRecord(record=record, timestamp=datetime.now())
            self._buffer.append(buffered_record)
            self._context_buffer.append(buffered_record)  # Also add to context buffer
            self._total_records_added += 1

    def should_process(self) -> bool:
        """
        Check if buffer should be processed.

        Returns:
            True if buffer should be processed based on size or time thresholds
        """
        with self._lock:
            # Check size threshold
            if len(self._buffer) >= self.max_size:
                return True

            # Check time threshold
            time_since_last_flush = time.time() - self._last_flush_time
            if time_since_last_flush >= self.flush_interval and len(self._buffer) > 0:
                return True

            return False

    def get_records_for_processing(self) -> List[BufferedLogRecord]:
        """
        Get all buffered records for processing and clear the buffer.

        Returns:
            List of buffered log records ready for processing
        """
        with self._lock:
            if not self._buffer:
                return []

            # Get all records from buffer
            records = list(self._buffer)
            self._buffer.clear()

            # Update statistics
            self._total_flushes += 1
            self._total_records_processed += len(records)
            self._last_flush_time = time.time()

            return records

    def get_buffer_size(self) -> int:
        """Get current number of records in buffer."""
        with self._lock:
            return len(self._buffer)

    def clear_buffer(self) -> int:
        """
        Clear all records from buffer.

        Returns:
            Number of records that were cleared
        """
        with self._lock:
            cleared_count = len(self._buffer)
            self._buffer.clear()
            return cleared_count

    def get_recent_context(self, max_records: int = 20) -> List[BufferedLogRecord]:
        """
        Get recent records for error context analysis.

        Args:
            max_records: Maximum number of recent records to return

        Returns:
            List of recent log records for context analysis
        """
        with self._lock:
            # Return last N records from context buffer
            return list(self._context_buffer)[-max_records:]

    def get_statistics(self) -> dict:
        """
        Get buffer management statistics.

        Returns:
            Dictionary with buffer statistics
        """
        with self._lock:
            return {
                "current_buffer_size": len(self._buffer),
                "max_buffer_size": self.max_size,
                "total_records_added": self._total_records_added,
                "total_flushes": self._total_flushes,
                "total_records_processed": self._total_records_processed,
                "time_since_last_flush": time.time() - self._last_flush_time,
                "flush_interval": self.flush_interval,
            }

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        with self._lock:
            self._total_records_added = 0
            self._total_flushes = 0
            self._total_records_processed = 0
            self._last_flush_time = time.time()
