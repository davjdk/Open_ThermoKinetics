"""
Aggregation engine module for log aggregation system.

This module provides the core aggregation logic that processes patterns
and creates aggregated log records for output.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from .buffer_manager import BufferedLogRecord
from .pattern_detector import LogPattern


@dataclass
class AggregatedLogRecord:
    """Represents an aggregated log record from multiple similar records."""

    pattern_id: str
    """Identifier of the pattern this aggregation represents"""

    template: str
    """Template message with placeholders"""

    count: int
    """Number of original records aggregated"""

    level: str
    """Log level of the aggregated records"""

    logger_name: str
    """Name of the logger that generated the records"""

    first_timestamp: datetime
    """Timestamp of the first record in aggregation"""

    last_timestamp: datetime
    """Timestamp of the last record in aggregation"""

    sample_messages: List[str]
    """Sample of original messages (up to 3)"""

    def to_log_message(self) -> str:
        """Convert aggregated record to a formatted log message."""
        time_span = self.last_timestamp - self.first_timestamp
        time_span_str = f"{time_span.total_seconds():.1f}s" if time_span.total_seconds() > 0 else "instant"

        message = f"[AGGREGATED {self.count}x over {time_span_str}] {self.template}"

        if len(self.sample_messages) > 1:
            message += f" (samples: {', '.join(self.sample_messages[:2])})"

        return message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "pattern_id": self.pattern_id,
            "template": self.template,
            "count": self.count,
            "level": self.level,
            "logger_name": self.logger_name,
            "first_timestamp": self.first_timestamp.isoformat(),
            "last_timestamp": self.last_timestamp.isoformat(),
            "time_span_seconds": (self.last_timestamp - self.first_timestamp).total_seconds(),
            "sample_messages": self.sample_messages,
        }


class AggregationEngine:
    """
    Core engine for aggregating log records based on detected patterns.

    This is a basic implementation for Stage 1. More sophisticated
    aggregation strategies will be added in later stages.
    """

    def __init__(self, min_pattern_entries: int = 2):
        """
        Initialize aggregation engine.

        Args:
            min_pattern_entries: Minimum number of entries required to create aggregation
        """
        self.min_pattern_entries = min_pattern_entries

        # Statistics
        self._total_patterns_processed = 0
        self._total_records_aggregated = 0
        self._total_aggregations_created = 0

    def aggregate_patterns(self, patterns: List[LogPattern]) -> List[AggregatedLogRecord]:
        """
        Aggregate detected patterns into aggregated log records.

        Args:
            patterns: List of detected patterns to aggregate

        Returns:
            List of aggregated log records
        """
        aggregated_records = []

        for pattern in patterns:
            if len(pattern.records) >= self.min_pattern_entries:
                aggregated = self._create_aggregated_record(pattern)
                aggregated_records.append(aggregated)

                # Update statistics
                self._total_patterns_processed += 1
                self._total_records_aggregated += len(pattern.records)
                self._total_aggregations_created += 1

        return aggregated_records

    def _create_aggregated_record(self, pattern: LogPattern) -> AggregatedLogRecord:
        """Create an aggregated record from a pattern."""
        if not pattern.records:
            raise ValueError("Cannot create aggregated record from empty pattern")

        # Get representative information from the first record
        first_record = pattern.records[0].record
        timestamps = [r.timestamp for r in pattern.records]

        # Extract sample messages (up to 3)
        sample_messages = []
        for record in pattern.records[:3]:
            message = record.record.getMessage()
            if message not in sample_messages:
                sample_messages.append(message)

        return AggregatedLogRecord(
            pattern_id=pattern.pattern_id,
            template=pattern.template,
            count=pattern.count,
            level=first_record.levelname,
            logger_name=first_record.name,
            first_timestamp=min(timestamps),
            last_timestamp=max(timestamps),
            sample_messages=sample_messages,
        )

    def process_records(
        self, records: List[BufferedLogRecord], patterns: List[LogPattern]
    ) -> List[AggregatedLogRecord]:
        """
        Process records and patterns to create aggregated output.

        Args:
            records: Original buffered records
            patterns: Detected patterns

        Returns:
            List of aggregated records ready for output
        """
        # For Stage 1, simply aggregate the patterns
        # In later stages, this might include more sophisticated logic
        return self.aggregate_patterns(patterns)

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        return {
            "total_patterns_processed": self._total_patterns_processed,
            "total_records_aggregated": self._total_records_aggregated,
            "total_aggregations_created": self._total_aggregations_created,
            "average_records_per_aggregation": (
                self._total_records_aggregated / self._total_aggregations_created
                if self._total_aggregations_created > 0
                else 0
            ),
        }

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self._total_patterns_processed = 0
        self._total_records_aggregated = 0
        self._total_aggregations_created = 0
