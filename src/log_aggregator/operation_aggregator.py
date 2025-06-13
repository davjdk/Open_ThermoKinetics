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
from .safe_message_utils import safe_get_message


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

    # New fields for explicit mode support
    operation_name: str = None
    """Explicit name of the operation (for explicit mode)"""

    explicit_mode: bool = False
    """Flag indicating if this group was created in explicit mode"""

    request_count: int = 0
    """Number of requests in the operation"""

    custom_metrics: Dict[str, any] = field(default_factory=dict)
    """Custom metrics collected during operation"""

    sub_operations: List[str] = field(default_factory=list)
    """List of detected sub-operations"""

    def add_record(self, record: BufferedLogRecord) -> None:
        """Add a log record to this operation group."""
        self.records.append(record)
        self.operation_count += 1
        self.end_time = record.timestamp

        # Extract actor from record
        if hasattr(record.record, "pathname"):
            import re

            actor_pattern = re.compile(r"(\w+)\.py:\d+")
            match = actor_pattern.search(record.record.pathname)
            if match:
                self.actors.add(match.group(1))

        # Update error/warning status
        if record.record.levelno >= logging.ERROR:
            self.has_errors = True
        if record.record.levelno >= logging.WARNING:
            self.has_warnings = True


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

    # New configuration options for explicit mode
    explicit_mode_enabled: bool = True
    """Enable explicit mode support"""

    auto_mode_enabled: bool = True
    """Enable automatic mode support"""

    operation_timeout: float = 30.0
    """Timeout for explicit operations in seconds"""

    detect_sub_operations: bool = True
    """Automatically detect sub-operations"""

    merge_nested_operations: bool = True
    """Merge nested operations into parent operation"""


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

            # If in explicit mode, all records go to current group
            if self.is_explicit_mode():
                self.current_group.add_record(record)
                # Detect sub-operations
                if self.config.detect_sub_operations:
                    sub_op = self._detect_sub_operations(record)
                    if sub_op and sub_op not in self.current_group.sub_operations:
                        self.current_group.sub_operations.append(sub_op)
                        # Count handle_request_cycle calls
                        if "handle_request_cycle" in safe_get_message(record.record):
                            self.current_group.request_count += 1
                return None

            # Otherwise use existing automatic mode logic
            return self._process_automatic_mode(record)

    def _process_automatic_mode(self, record: BufferedLogRecord) -> Optional[OperationGroup]:
        """Process record using automatic mode logic."""
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
        message = safe_get_message(record.record)

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

    # New methods for explicit mode support
    def start_operation(self, name: str) -> None:
        """
        Start a new group of operations in explicit mode.

        Args:
            name: Name of the operation to start
        """
        with self._lock:
            # Close current group if open
            if self.current_group:
                self._close_current_group()

            # Create new group in explicit mode
            import time

            self.current_group = OperationGroup(
                root_operation=name,
                operation_name=name,
                start_time=datetime.fromtimestamp(time.time()),
                end_time=datetime.fromtimestamp(time.time()),
                operation_count=0,
                explicit_mode=True,
                actors=set(),
                operations=[],
                records=[],
                sub_operations=[],
                custom_metrics={},
                request_count=0,
            )

    def end_operation(self) -> Optional[OperationGroup]:
        """
        End the current operation in explicit mode.

        Returns:
            Completed OperationGroup if in explicit mode, None otherwise
        """
        with self._lock:
            if self.current_group and self.current_group.explicit_mode:
                import time

                self.current_group.end_time = datetime.fromtimestamp(time.time())
                completed_group = self.current_group
                self.current_group = None

                # Generate operation table for explicit operations
                self._generate_operation_table(completed_group)

                return completed_group
            return None

    def is_explicit_mode(self) -> bool:
        """
        Check if aggregator is in explicit mode.

        Returns:
            True if currently in explicit mode, False otherwise
        """
        return self.current_group is not None and self.current_group.explicit_mode

    def _detect_sub_operations(self, record: BufferedLogRecord) -> Optional[str]:
        """
        Detect sub-operation based on log record content.

        Args:
            record: Log record to analyze

        Returns:
            Detected sub-operation name or None
        """
        message = safe_get_message(record.record)

        # Analyze patterns for handle_request_cycle calls
        if "handle_request_cycle" not in message:
            return self._detect_non_request_operations(message)

        # Extract OperationType from handle_request_cycle messages
        operation_types = {
            "OperationType.GET_ALL_DATA": "GET_ALL_DATA",
            "OperationType.ADD_NEW_SERIES": "ADD_NEW_SERIES",
            "OperationType.GET_SERIES": "GET_SERIES",
            "OperationType.UPDATE_SERIES": "UPDATE_SERIES",
            "OperationType.MODEL_FREE_CALCULATION": "MODEL_FREE_CALCULATION",
            "OperationType.MODEL_FIT_CALCULATION": "MODEL_FIT_CALCULATION",
            "OperationType.DECONVOLUTION": "DECONVOLUTION",
        }

        for pattern, operation in operation_types.items():
            if pattern in message:
                return operation

        # Generic handle_request_cycle pattern
        return "handle_request_cycle"

    def _detect_non_request_operations(self, message: str) -> Optional[str]:
        """Detect non-request sub-operations."""
        if "Data Processing" in message or "data processing" in message:
            return "Data Processing"
        if "UI Updates" in message or "ui updates" in message:
            return "UI Updates"
        return None

    def _generate_operation_table(self, group: OperationGroup) -> None:
        """
        Generate operation table for completed group.

        Args:
            group: Completed operation group
        """
        # This method will be expanded in later stages
        # For now, just log the operation summary
        duration = (group.end_time - group.start_time).total_seconds()

        self._logger.info(
            f"Operation table for {group.operation_name}: "
            f"Duration: {duration:.3f}s, "
            f"Sub-operations: {len(group.sub_operations)}, "
            f"Requests: {group.request_count}, "
            f"Records: {len(group.records)}"
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
