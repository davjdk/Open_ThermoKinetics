"""
Operation aggregator module for log aggregation system.

This module provides operation cascade detection and aggregation,
grouping related system operations into single summary records
to reduce log verbosity while preserving critical information.
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

try:
    from src.core.logger_config import LoggerManager
except ImportError:
    from core.logger_config import LoggerManager

from .buffer_manager import BufferedLogRecord


@dataclass
class OperationGroup:
    """Group of related operations forming a cascade."""

    root_operation: str
    """The initiating operation that started the cascade"""

    start_time: datetime
    """When the cascade began"""

    end_time: datetime
    """When the cascade completed"""

    operation_count: int
    """Total number of operations in the cascade"""

    actors: Set[str] = field(default_factory=set)
    """Set of modules/components involved in the cascade"""

    operations: List[str] = field(default_factory=list)
    """List of all operations in chronological order"""

    request_ids: Set[str] = field(default_factory=set)
    """Set of request IDs if available"""

    has_errors: bool = False
    """Whether any operation in the cascade had errors"""

    has_warnings: bool = False
    """Whether any operation in the cascade had warnings"""

    records: List[BufferedLogRecord] = field(default_factory=list)
    """All log records in the cascade for error context"""


@dataclass
class OperationAggregationConfig:
    """Configuration for operation aggregation."""

    enabled: bool = True
    """Whether operation aggregation is enabled"""

    cascade_window: float = 1.0
    """Time window in seconds to group operations into cascades"""

    min_cascade_size: int = 3
    """Minimum number of operations to consider a cascade"""

    root_operations: Set[str] = field(
        default_factory=lambda: {
            "ADD_REACTION",
            "REMOVE_REACTION",
            "MODEL_BASED_CALCULATION",
            "DECONVOLUTION",
            "MODEL_FIT_CALCULATION",
            "MODEL_FREE_CALCULATION",
            "LOAD_FILE",
            "TO_DTG",
            "SMOOTH_DATA",
            "SUBTRACT_BACKGROUND",
            "GET_DF_DATA",
            "UPDATE_VALUE",
            "SET_VALUE",
        }
    )
    """Set of operations that can start a cascade"""


class OperationAggregator:
    """
    Aggregates operation cascades into summary records.

    Detects chains of related operations and groups them into
    single summary records to reduce log verbosity.
    """

    def __init__(self, config: Optional[OperationAggregationConfig] = None):
        """
        Initialize operation aggregator.

        Args:
            config: Configuration for aggregation behavior
        """
        self.config = config or OperationAggregationConfig()
        self._lock = threading.RLock()

        # Current cascade being built
        self.current_group: Optional[OperationGroup] = None
        # Statistics
        self.stats = {
            "cascades_detected": 0,
            "operations_aggregated": 0,
            "total_operations_processed": 0,
            "compression_ratio": 0.0,
        }  # Pattern detection for operations
        self.operation_patterns = [
            re.compile(r"handle_request_from_main_tab '(\w+)'"),
            re.compile(r"processing request '(\w+)'"),
            re.compile(r"emitting request.*'operation': <OperationType\.(\w+)"),
            re.compile(r"OPERATION (START|END): (\w+)"),
            re.compile(r"Processing operation '(\w+)'"),
            re.compile(r"operation '(\w+)' completed"),
            re.compile(r"operation '(\w+)' failed"),
        ]

        # Pattern for extracting actor (module/file name)
        self.actor_pattern = re.compile(r"(\w+)\.py:\d+")

        self._logger = LoggerManager.get_logger("log_aggregator.operation_aggregator")

    def process_record(self, record: BufferedLogRecord) -> Optional[OperationGroup]:
        """
        Process a log record and detect operation cascades.

        Args:
            record: Log record to process

        Returns:
            Completed OperationGroup if cascade is finished, None otherwise
        """
        with self._lock:
            self.stats["total_operations_processed"] += 1

            # Extract operation name and actor from record
            operation = self._extract_operation(record)
            actor = self._extract_actor(record)

            if not operation:
                # Not an operation record, check if we should close current group
                if self.current_group and self._is_cascade_expired(record.timestamp):
                    return self._close_current_group()
                return None  # Check if this is a root operation (starts new cascade)
            if operation in self.config.root_operations:
                # Close previous group if exists
                completed_group = None
                if self.current_group:
                    completed_group = self._close_current_group()

                # Start new group
                self._start_new_group(operation, record, actor)
                return completed_group

            # Add to current group if exists and within time window
            if self.current_group and not self._is_cascade_expired(record.timestamp):
                self._add_to_current_group(operation, record, actor)
            elif self.current_group and self._is_cascade_expired(record.timestamp):
                # Close expired group and start new one if this is a root operation
                completed_group = self._close_current_group()
                return completed_group

            return None

    def _extract_operation(self, record: BufferedLogRecord) -> Optional[str]:
        """Extract operation name from log record."""
        message = record.record.getMessage()

        for pattern in self.operation_patterns:
            match = pattern.search(message)
            if match:
                # Return the captured operation name
                groups = match.groups()
                if groups:
                    return groups[0] if groups[0] not in ("START", "END") else groups[1]

        return None

    def _extract_actor(self, record: BufferedLogRecord) -> str:
        """Extract actor (module name) from log record."""
        if hasattr(record.record, "pathname"):
            match = self.actor_pattern.search(record.record.pathname)
            if match:
                return match.group(1)

        # Fallback to logger name
        if hasattr(record.record, "name"):
            parts = record.record.name.split(".")
            if parts:
                return parts[-1]

        return "unknown"

    def _is_cascade_expired(self, timestamp: datetime) -> bool:
        """Check if current cascade has expired based on time window."""
        if not self.current_group:
            return False

        time_diff = (timestamp - self.current_group.end_time).total_seconds()
        return time_diff > self.config.cascade_window

    def _start_new_group(self, operation: str, record: BufferedLogRecord, actor: str) -> None:
        """Start a new operation group."""
        self.current_group = OperationGroup(
            root_operation=operation,
            start_time=record.timestamp,
            end_time=record.timestamp,
            operation_count=1,
            actors={actor},
            operations=[operation],
            has_errors=record.record.levelno >= logging.ERROR,
            has_warnings=record.record.levelno >= logging.WARNING,
            records=[record],
        )

    def _add_to_current_group(self, operation: str, record: BufferedLogRecord, actor: str) -> None:
        """Add operation to current group."""
        if not self.current_group:
            return

        self.current_group.operation_count += 1
        self.current_group.end_time = record.timestamp
        self.current_group.actors.add(actor)
        self.current_group.operations.append(operation)
        self.current_group.records.append(record)

        # Update error/warning status
        if record.record.levelno >= logging.ERROR:
            self.current_group.has_errors = True
        if record.record.levelno >= logging.WARNING:
            self.current_group.has_warnings = True

    def _close_current_group(self) -> Optional[OperationGroup]:
        """Close current group and return it if it meets cascade criteria."""
        if not self.current_group:
            return None

        group = self.current_group
        self.current_group = None

        # Check if group meets cascade criteria
        if group.operation_count >= self.config.min_cascade_size:
            self.stats["cascades_detected"] += 1
            self.stats["operations_aggregated"] += group.operation_count
            self._update_compression_ratio()
            return group

        return None

    def _update_compression_ratio(self) -> None:
        """Update compression ratio statistics."""
        if self.stats["total_operations_processed"] > 0:
            self.stats["compression_ratio"] = (
                self.stats["operations_aggregated"] / self.stats["total_operations_processed"]
            )

    def get_aggregated_record(self, group: OperationGroup) -> BufferedLogRecord:
        """
        Generate aggregated log record for operation group.

        Args:
            group: Operation group to create record for

        Returns:
            Aggregated log record
        """
        duration = (group.end_time - group.start_time).total_seconds()
        actors_str = ", ".join(sorted(group.actors))

        # Build status indicators
        status_indicators = []
        if group.has_errors:
            status_indicators.append("❌ ERRORS")
        if group.has_warnings:
            status_indicators.append("⚠️ WARNINGS")

        status_str = " | ".join(status_indicators) if status_indicators else "✅ SUCCESS"

        # Create summary message
        message = (
            f"🔄 OPERATION CASCADE: {group.root_operation} | "
            f"⏱️ {duration:.3f}s | "
            f"📊 {group.operation_count} operations | "
            f"🎭 Actors: {actors_str} | "
            f"{status_str}"
        )

        # Create log record
        log_record = logging.LogRecord(
            name="log_aggregator.operation_aggregator",
            level=logging.ERROR if group.has_errors else (logging.WARNING if group.has_warnings else logging.INFO),
            pathname="operation_aggregator.py",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )

        return BufferedLogRecord(record=log_record, timestamp=group.end_time, processed=True)

    def force_close_current_group(self) -> Optional[OperationGroup]:
        """Force close current group regardless of criteria."""
        with self._lock:
            return self._close_current_group()

    def get_stats(self) -> Dict[str, any]:
        """Get aggregation statistics."""
        with self._lock:
            return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self.stats = {
                "cascades_detected": 0,
                "operations_aggregated": 0,
                "total_operations_processed": 0,
                "compression_ratio": 0.0,
            }
