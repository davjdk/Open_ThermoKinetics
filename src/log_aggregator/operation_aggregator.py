"""
Operation aggregator module for log aggregation system.

This module provides operation cascade detection and aggregation,
grouping related system operations into single summary records
to reduce log verbosity while preserving critical information.
"""

import logging
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
    """Set of operations that can start a cascade"""  # Configuration for explicit mode support
    explicit_mode_enabled: bool = True
    """Enable explicit mode support"""

    operation_timeout: float = 30.0
    """Timeout for explicit operations in seconds"""

    detect_sub_operations: bool = True
    """Automatically detect sub-operations"""

    # Enhanced configuration for Stage 3 integration
    aggregate_error_operations: bool = False
    """Whether to aggregate operations that had errors"""

    long_operation_threshold_ms: float = 5000.0
    """Operations longer than this won't be aggregated (ms)"""

    max_sub_operations_for_aggregation: int = 10
    """Maximum sub-operations count for aggregation"""

    include_performance_metrics: bool = True
    """Include performance metrics in aggregated data"""

    include_custom_metrics: bool = True
    """Include custom domain metrics in aggregated data"""


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
        self._lock = threading.RLock()  # Current cascade being built
        self.current_group: Optional[OperationGroup] = None

        # Statistics
        self.stats = {
            "cascades_detected": 0,
            "operations_aggregated": 0,
            "total_operations_processed": 0,
            "compression_ratio": 0.0,
        }

        self._logger = LoggerManager.get_logger("log_aggregator.operation_aggregator")

    def process_record(self, record: BufferedLogRecord) -> Optional[OperationGroup]:
        """
        Process a log record and detect operation cascades.

        This method now only handles explicit mode operations.

        Args:
            record: Log record to process

        Returns:
            Completed OperationGroup if cascade is finished, None otherwise
        """
        with self._lock:
            self.stats["total_operations_processed"] += 1

            # Only handle explicit mode
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
                return None  # If not in explicit mode, just add to current group if it exists
            if self.current_group:
                self.current_group.add_record(record)

            return None

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

    # Enhanced methods for Stage 3 - OperationMonitor integration

    def integrate_with_operation_monitor(self, operation_monitor) -> None:
        """
        Integrate with OperationMonitor to collect enhanced metrics.

        Args:
            operation_monitor: The OperationMonitor instance to integrate with
        """
        self.operation_monitor = operation_monitor

    def create_group_from_operation_metrics(self, operation_metrics) -> OperationGroup:
        """
        Create OperationGroup from OperationMonitor metrics.

        Args:
            operation_metrics: OperationMetrics from enhanced tracking

        Returns:
            OperationGroup with enhanced metrics
        """
        group = OperationGroup(
            root_operation=operation_metrics.operation_type,
            start_time=operation_metrics.start_time,
            end_time=operation_metrics.end_time or operation_metrics.start_time,
            operation_count=1,
            actors=operation_metrics.components_involved,
            operations=[operation_metrics.operation_type],
            has_errors=operation_metrics.error_count > 0,
            has_warnings=operation_metrics.warning_count > 0,
            records=[],  # No raw log records in this case
        )

        # Enhanced fields for explicit mode
        group.operation_name = operation_metrics.operation_type
        group.explicit_mode = True
        group.request_count = operation_metrics.request_count
        group.custom_metrics = operation_metrics.custom_metrics.copy()
        group.sub_operations = operation_metrics.sub_operations.copy()

        return group

    def get_enhanced_aggregation_data(self, operation_metrics) -> Dict[str, any]:
        """
        Get enhanced aggregation data from operation metrics.

        Args:
            operation_metrics: Enhanced OperationMetrics

        Returns:
            Dictionary with aggregation data including enhanced metrics
        """
        if not operation_metrics:
            return {}

        base_data = {
            "operation_name": operation_metrics.operation_type,
            "duration_ms": operation_metrics.duration_ms,
            "start_time": operation_metrics.start_time,
            "end_time": operation_metrics.end_time,
            "status": operation_metrics.enhanced_status,
            "request_count": operation_metrics.request_count,
            "response_count": operation_metrics.response_count,
            "warning_count": operation_metrics.warning_count,
            "error_count": operation_metrics.error_count,
            "components_involved": list(operation_metrics.components_involved),
            "memory_usage_mb": operation_metrics.memory_usage_mb,
        }

        # Add custom metrics
        base_data.update(operation_metrics.custom_metrics)

        return base_data

    def should_aggregate_with_enhanced_metrics(self, operation_metrics) -> bool:
        """
        Determine if operation should be aggregated based on enhanced metrics.

        Args:
            operation_metrics: Enhanced OperationMetrics

        Returns:
            True if operation should be aggregated
        """
        # Don't aggregate operations with errors unless configured to do so
        if operation_metrics.error_count > 0 and not self.config.aggregate_error_operations:
            return False

        # Don't aggregate long-running operations
        if operation_metrics.duration_ms and operation_metrics.duration_ms > self.config.long_operation_threshold_ms:
            return False

        # Don't aggregate operations with many sub-operations
        if len(operation_metrics.sub_operations) > self.config.max_sub_operations_for_aggregation:
            return False

        return True

    def get_operation_summary_with_metrics(self, operation_metrics) -> str:
        """
        Generate operation summary including enhanced metrics.

        Args:
            operation_metrics: Enhanced OperationMetrics

        Returns:
            Formatted summary string
        """
        summary_parts = [
            f"Operation: {operation_metrics.operation_type}",
            f"Duration: {operation_metrics.duration_ms:.1f}ms",
            f"Status: {operation_metrics.enhanced_status}",
        ]

        if operation_metrics.request_count > 0:
            summary_parts.append(f"Requests: {operation_metrics.request_count}")

        if operation_metrics.custom_metrics:
            # Add key custom metrics to summary
            key_metrics = []
            for key, value in operation_metrics.custom_metrics.items():
                if key in ["file_count", "reaction_count", "final_mse", "iterations"]:
                    key_metrics.append(f"{key}={value}")

            if key_metrics:
                summary_parts.append(f"Metrics: {', '.join(key_metrics)}")

        if operation_metrics.components_involved:
            summary_parts.append(f"Components: {', '.join(list(operation_metrics.components_involved))}")

        return " | ".join(summary_parts)
