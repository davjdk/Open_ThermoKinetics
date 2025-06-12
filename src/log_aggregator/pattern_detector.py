"""
Pattern detection module for log aggregation system.

This module provides basic pattern detection capabilities for identifying
similar log records that can be aggregated together.
"""

import difflib
import re
from dataclasses import dataclass
from typing import Dict, List

from .buffer_manager import BufferedLogRecord


@dataclass
class LogPattern:
    """Represents a detected pattern in log records."""

    pattern_id: str
    """Unique identifier for this pattern"""

    template: str
    """Template message with placeholders for variable parts"""

    records: List[BufferedLogRecord]
    """List of log records that match this pattern"""

    count: int
    """Number of records matching this pattern"""

    first_seen: float
    """Timestamp when this pattern was first detected"""

    last_seen: float
    """Timestamp when this pattern was last seen"""

    def add_record(self, record: BufferedLogRecord) -> None:
        """Add a record to this pattern."""
        self.records.append(record)
        self.count += 1
        self.last_seen = record.timestamp.timestamp()


class PatternDetector:
    """
    Detects patterns in log records for aggregation.

    This is a basic implementation for Stage 1. More sophisticated
    pattern detection will be added in later stages.
    """

    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize pattern detector.

        Args:
            similarity_threshold: Minimum similarity ratio to consider messages as same pattern
        """
        self.similarity_threshold = similarity_threshold
        self._patterns: Dict[str, LogPattern] = {}
        self._next_pattern_id = 1

    def detect_patterns(self, records: List[BufferedLogRecord]) -> List[LogPattern]:
        """
        Detect patterns in a batch of log records.

        Args:
            records: List of buffered log records to analyze

        Returns:
            List of detected patterns with grouped records
        """
        if not records:
            return []

        # Group records by basic criteria first
        grouped_records = self._group_by_basic_criteria(records)

        # Detect patterns within each group
        detected_patterns = []
        for group_records in grouped_records.values():
            patterns = self._detect_patterns_in_group(group_records)
            detected_patterns.extend(patterns)

        return detected_patterns

    def _group_by_basic_criteria(self, records: List[BufferedLogRecord]) -> Dict[str, List[BufferedLogRecord]]:
        """Group records by level, logger name, and module."""
        groups: Dict[str, List[BufferedLogRecord]] = {}

        for record in records:
            log_record = record.record
            # Create grouping key from level, logger name, and module
            key = f"{log_record.levelname}:{log_record.name}:{getattr(log_record, 'module', 'unknown')}"

            if key not in groups:
                groups[key] = []
            groups[key].append(record)

        return groups

    def _detect_patterns_in_group(self, records: List[BufferedLogRecord]) -> List[LogPattern]:
        """Detect patterns within a homogeneous group of records."""
        if len(records) < 2:
            # Single records don't form patterns
            return []

        patterns = []
        unprocessed = records.copy()

        while unprocessed:
            current_record = unprocessed.pop(0)
            current_message = current_record.record.getMessage()

            # Find similar messages
            similar_records = [current_record]
            remaining = []

            for other_record in unprocessed:
                other_message = other_record.record.getMessage()
                similarity = self._calculate_similarity(current_message, other_message)

                if similarity >= self.similarity_threshold:
                    similar_records.append(other_record)
                else:
                    remaining.append(other_record)

            unprocessed = remaining

            # Create pattern if we have multiple similar records
            if len(similar_records) >= 2:  # Minimum for a pattern
                pattern = self._create_pattern(similar_records)
                patterns.append(pattern)

        return patterns

    def _calculate_similarity(self, message1: str, message2: str) -> float:
        """Calculate similarity ratio between two messages."""
        return difflib.SequenceMatcher(None, message1, message2).ratio()

    def _create_pattern(self, records: List[BufferedLogRecord]) -> LogPattern:
        """Create a pattern from similar records."""
        if not records:
            raise ValueError("Cannot create pattern from empty records list")

        # Generate pattern ID
        pattern_id = f"pattern_{self._next_pattern_id}"
        self._next_pattern_id += 1

        # Create template from the first message (simple approach for Stage 1)
        template = records[0].record.getMessage()

        # Find common parts and create a simple template
        if len(records) > 1:
            template = self._create_template(records)

        # Create pattern
        pattern = LogPattern(
            pattern_id=pattern_id,
            template=template,
            records=records.copy(),
            count=len(records),
            first_seen=min(r.timestamp.timestamp() for r in records),
            last_seen=max(r.timestamp.timestamp() for r in records),
        )

        return pattern

    def _create_template(self, records: List[BufferedLogRecord]) -> str:
        """Create a template message from similar records."""
        messages = [record.record.getMessage() for record in records]

        if not messages:
            return ""

        if len(messages) == 1:
            return messages[0]

        # Find the longest common substring approach
        # For Stage 1, use a simple approach - take the first message as template
        # and replace varying numbers with placeholders
        template = messages[0]

        # Simple number replacement (basic pattern for Stage 1)
        # Replace sequences of digits with {NUMBER}
        template = re.sub(r"\d+\.?\d*", "{NUMBER}", template)

        # Replace common variable patterns
        template = re.sub(r"\b[A-Fa-f0-9]{8,}\b", "{HASH}", template)  # Hex values
        template = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "{DATE}", template)  # Dates

        return template

    def get_pattern_statistics(self) -> Dict[str, int]:
        """Get statistics about detected patterns."""
        return {
            "total_patterns": len(self._patterns),
            "total_records": sum(p.count for p in self._patterns.values()),
            "average_records_per_pattern": (
                sum(p.count for p in self._patterns.values()) / len(self._patterns) if self._patterns else 0
            ),
        }

    def clear_patterns(self) -> None:
        """Clear all stored patterns."""
        self._patterns.clear()
        self._next_pattern_id = 1
