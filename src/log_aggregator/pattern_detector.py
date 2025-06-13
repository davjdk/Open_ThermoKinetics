"""
Pattern detection module for log aggregation system.

This module provides basic pattern detection capabilities for identifying
similar log records that can be aggregated together.
"""

import difflib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .buffer_manager import BufferedLogRecord
from .safe_message_utils import safe_get_message, safe_get_message_for_comparison

# Enhanced pattern types for Stage 2
PATTERN_TYPES = {
    "plot_lines_addition": "Addition of lines to plot",
    "cascade_component_initialization": "Cascade component initialization",
    "request_response_cycle": "Request-response cycles",
    "file_operations": "File operations",
    "gui_updates": "GUI updates",
    "basic_similarity": "Basic similarity pattern",  # fallback for Stage 1 patterns
}


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

    pattern_type: str = "basic_similarity"
    """Type of the pattern (e.g., plot_lines_addition, basic_similarity)"""

    def add_record(self, record: BufferedLogRecord) -> None:
        """Add a record to this pattern."""
        self.records.append(record)
        self.count += 1
        self.last_seen = record.timestamp.timestamp()

    def get_table_suitable_flag(self) -> bool:
        """Check if this pattern is suitable for tabular representation."""
        # Basic LogPattern objects are generally suitable for tables
        return True


@dataclass
class PatternGroup:
    """Represents a group of patterns with enhanced metadata for advanced analysis."""

    pattern_type: str
    """Type of the pattern (plot_lines_addition, cascade_component_initialization, etc.)"""

    records: List[BufferedLogRecord]
    """List of log records that belong to this pattern group"""

    start_time: datetime
    """When this pattern group was first detected"""

    end_time: datetime
    """When this pattern group was last updated"""

    metadata: Dict[str, Any]
    """Additional metadata specific to the pattern type"""

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}

    @property
    def duration(self) -> timedelta:
        """Duration of the pattern group."""
        return self.end_time - self.start_time

    @property
    def count(self) -> int:
        """Number of records in this pattern group."""
        return len(self.records)

    def add_record(self, record: BufferedLogRecord) -> None:
        """Add a record to this pattern group."""
        self.records.append(record)
        self.end_time = record.timestamp

    def get_table_suitable_flag(self) -> bool:
        """Check if this pattern group is suitable for tabular representation."""
        return self.metadata.get("table_suitable", False)


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
            current_message = safe_get_message_for_comparison(current_record.record)

            # Find similar messages
            similar_records = [current_record]
            remaining = []

            for other_record in unprocessed:
                other_message = safe_get_message_for_comparison(other_record.record)
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

        # Determine pattern type based on first record
        pattern_type = self._get_enhanced_pattern_key(records[0])

        # Create template from the first message (simple approach for Stage 1)
        template = safe_get_message(records[0].record)

        # Find common parts and create a simple template
        if len(records) > 1:
            template = self._create_template(records)

        # Create pattern
        pattern = LogPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            template=template,
            records=records.copy(),
            count=len(records),
            first_seen=min(r.timestamp.timestamp() for r in records),
            last_seen=max(r.timestamp.timestamp() for r in records),
        )

        return pattern

    def _create_template(self, records: List[BufferedLogRecord]) -> str:
        """Create a template message from similar records."""
        messages = [safe_get_message(record.record) for record in records]

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

    def detect_pattern_groups(self, records: List[BufferedLogRecord]) -> List[PatternGroup]:
        """
        Detect enhanced pattern groups with metadata.

        Args:
            records: List of buffered log records to analyze

        Returns:
            List of pattern groups with enhanced metadata
        """
        if not records:
            return []

        # Group records by enhanced patterns
        grouped_records = self._group_by_enhanced_patterns(records)

        # Process each group to create PatternGroup objects
        pattern_groups = []
        for pattern_type, group_records in grouped_records.items():
            if len(group_records) >= 2:  # Minimum for a pattern
                pattern_group = self._create_pattern_group(pattern_type, group_records)
                pattern_groups.append(pattern_group)

        return pattern_groups

    def _group_by_enhanced_patterns(self, records: List[BufferedLogRecord]) -> Dict[str, List[BufferedLogRecord]]:
        """Group records by enhanced pattern types."""
        groups: Dict[str, List[BufferedLogRecord]] = {}

        for record in records:
            pattern_key = self._get_enhanced_pattern_key(record)

            if pattern_key not in groups:
                groups[pattern_key] = []
            groups[pattern_key].append(record)

        return groups

    def _get_enhanced_pattern_key(self, record: BufferedLogRecord) -> str:
        """Determine the enhanced pattern type for a record."""
        message = safe_get_message(record.record)
        message_lower = message.lower()

        # Check for plot lines addition pattern
        if "Adding a new line" in message and "to the plot" in message:
            return "plot_lines_addition"

        # Check for cascade initialization pattern
        if "Initializing" in message and hasattr(record.record, "module"):
            return "cascade_component_initialization"

        # Check for request-response cycle pattern
        if any(keyword in message_lower for keyword in ["request", "response", "handling", "processing"]):
            return "request_response_cycle"

        # Check for file operations pattern
        if any(keyword in message_lower for keyword in ["loading", "saving", "reading", "writing", "file"]):
            return "file_operations"

        # Check for GUI updates pattern
        if any(keyword in message_lower for keyword in ["updating", "refreshing", "redrawing", "widget", "gui"]):
            return "gui_updates"

        # Fallback to basic similarity pattern
        return "basic_similarity"

    def _create_pattern_group(self, pattern_type: str, records: List[BufferedLogRecord]) -> PatternGroup:
        """Create a PatternGroup from records of the same enhanced pattern type."""
        if not records:
            raise ValueError("Cannot create pattern group from empty records list")

        start_time = min(r.timestamp for r in records)
        end_time = max(r.timestamp for r in records)

        # Generate metadata based on pattern type
        metadata = self._generate_pattern_metadata(pattern_type, records)

        return PatternGroup(
            pattern_type=pattern_type,
            records=records.copy(),
            start_time=start_time,
            end_time=end_time,
            metadata=metadata,
        )

    def _generate_pattern_metadata(self, pattern_type: str, records: List[BufferedLogRecord]) -> Dict[str, Any]:
        """Generate metadata for a specific pattern type."""
        metadata = {
            "table_suitable": True,  # Most enhanced patterns are table suitable
            "record_count": len(records),
            "time_span_ms": (max(r.timestamp for r in records) - min(r.timestamp for r in records)).total_seconds()
            * 1000,
        }

        if pattern_type == "plot_lines_addition":
            metadata.update(self._extract_plot_lines_metadata(records))
        elif pattern_type == "cascade_component_initialization":
            metadata.update(self._extract_cascade_metadata(records))
        elif pattern_type == "request_response_cycle":
            metadata.update(self._extract_request_response_metadata(records))
        elif pattern_type == "file_operations":
            metadata.update(self._extract_file_operations_metadata(records))
        elif pattern_type == "gui_updates":
            metadata.update(self._extract_gui_updates_metadata(records))
        else:
            # Basic similarity pattern - less suitable for tables
            metadata["table_suitable"] = False

        return metadata

    def _extract_plot_lines_metadata(self, records: List[BufferedLogRecord]) -> Dict[str, Any]:
        """Extract metadata specific to plot lines addition pattern."""
        line_names = []

        for record in records:
            message = safe_get_message(record.record)
            # Extract line name from message like "Adding a new line 'F1/3' to the plot."
            match = re.search(r"Adding a new line '([^']+)' to the plot", message)
            if match:
                line_names.append(match.group(1))

        total_time = (max(r.timestamp for r in records) - min(r.timestamp for r in records)).total_seconds() * 1000
        avg_line_time = total_time / len(records) if records else 0

        return {"line_names": line_names, "unique_lines": len(set(line_names)), "avg_line_time": avg_line_time}

    def _extract_cascade_metadata(self, records: List[BufferedLogRecord]) -> Dict[str, Any]:
        """Extract metadata specific to cascade initialization pattern."""
        components = []

        for record in records:
            message = safe_get_message(record.record)
            # Extract component name from message like "Initializing UserGuideTab"
            match = re.search(r"Initializing (\w+)", message)
            if match:
                components.append(match.group(1))

        return {
            "components": components,
            "initialization_order": components,  # preserves order from records
            "cascade_depth": len(components),
        }

    def _extract_request_response_metadata(self, records: List[BufferedLogRecord]) -> Dict[str, Any]:
        """Extract metadata specific to request-response cycle pattern."""
        request_count = 0
        response_count = 0

        for record in records:
            message = safe_get_message(record.record).lower()
            if "request" in message:
                request_count += 1
            elif "response" in message:
                response_count += 1

        return {
            "request_count": request_count,
            "response_count": response_count,
            "cycle_balance": abs(request_count - response_count),
        }

    def _extract_file_operations_metadata(self, records: List[BufferedLogRecord]) -> Dict[str, Any]:
        """Extract metadata specific to file operations pattern."""
        operation_types = set()
        file_extensions = set()

        for record in records:
            message = safe_get_message(record.record).lower()

            # Detect operation type
            if "loading" in message or "reading" in message:
                operation_types.add("read")
            elif "saving" in message or "writing" in message:
                operation_types.add("write")

            # Extract file extensions
            extensions = re.findall(r"\.(\w+)", message)
            file_extensions.update(extensions)

        return {
            "operation_types": list(operation_types),
            "file_extensions": list(file_extensions),
            "unique_operations": len(operation_types),
        }

    def _extract_gui_updates_metadata(self, records: List[BufferedLogRecord]) -> Dict[str, Any]:
        """Extract metadata specific to GUI updates pattern."""
        update_types = set()

        for record in records:
            message = safe_get_message(record.record).lower()

            if "updating" in message:
                update_types.add("update")
            elif "refreshing" in message:
                update_types.add("refresh")
            elif "redrawing" in message:
                update_types.add("redraw")

        return {"update_types": list(update_types), "unique_update_types": len(update_types)}
