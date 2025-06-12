"""
Error expansion engine module for log aggregation system.

This module provides detailed error analysis with expanded context,
preceding operations analysis, and actionable recommendations.
"""

import logging
import re
import traceback
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional

from .buffer_manager import BufferedLogRecord


@dataclass
class ErrorContext:
    """Structured context information for error analysis."""

    error_record: BufferedLogRecord
    """The original error record being analyzed"""

    preceding_records: List[BufferedLogRecord] = field(default_factory=list)
    """Log records that occurred before the error"""

    following_records: List[BufferedLogRecord] = field(default_factory=list)
    """Log records that occurred after the error (if any)"""

    related_operations: List[BufferedLogRecord] = field(default_factory=list)
    """Log records related to the same operation or component"""

    error_trace: Optional[str] = None
    """Extracted stack trace or error trace information"""

    suggested_actions: List[str] = field(default_factory=list)
    """AI-generated suggestions for resolving the error"""

    error_classification: Optional[str] = None
    """Classification of error type (file_not_found, memory_error, etc.)"""

    context_keywords: List[str] = field(default_factory=list)
    """Keywords extracted from the error and context"""


@dataclass
class ErrorExpansionConfig:
    """Configuration for error expansion engine."""

    enabled: bool = True
    """Whether error expansion is enabled"""

    context_lines: int = 5
    """Number of preceding context lines to include"""

    trace_depth: int = 10
    """Maximum depth of operation trace to analyze"""

    immediate_expansion: bool = True
    """Whether to expand errors immediately when detected"""

    save_context: bool = True
    """Whether to save expanded context for later analysis"""

    error_threshold_level: str = "WARNING"
    """Minimum log level to trigger error expansion (WARNING/ERROR/CRITICAL)"""

    context_time_window: float = 10.0
    """Time window in seconds to look for related operations"""


class ErrorExpansionEngine:
    """
    Engine for detailed error analysis with expanded context.

    Provides automatic classification of errors, context analysis,
    and generation of actionable recommendations.
    """

    def __init__(self, config: ErrorExpansionConfig = None):
        """
        Initialize error expansion engine.

        Args:
            config: Configuration for error expansion behavior
        """
        self.config = config or ErrorExpansionConfig()

        # Error classification patterns
        self.error_patterns = {
            "file_not_found": {
                "keywords": ["file not found", "no such file", "cannot open", "does not exist", "path"],
                "context_keywords": ["loading", "opening", "reading", "import", "load_file"],
                "suggestions": [
                    "Check if the file exists at the specified path",
                    "Verify the file path is correct",
                    "Check file access permissions",
                    "Ensure the file extension is correct",
                ],
            },
            "memory_error": {
                "keywords": ["memory error", "out of memory", "allocation failed", "memoryerror"],
                "context_keywords": ["matrix", "calculation", "array", "data processing"],
                "suggestions": [
                    "Reduce the size of processed data",
                    "Close unused applications to free memory",
                    "Check available system memory",
                    "Consider processing data in smaller chunks",
                ],
            },
            "gui_error": {
                "keywords": ["widget", "window", "display", "render", "qt", "pyqt", "gui"],
                "context_keywords": ["main_window", "plot_canvas", "sidebar", "tab"],
                "suggestions": [
                    "Restart the GUI component",
                    "Check window state and visibility",
                    "Update the display rendering",
                    "Verify Qt event loop is running",
                ],
            },
            "calculation_error": {
                "keywords": ["division by zero", "invalid value", "nan", "inf", "overflow", "underflow"],
                "context_keywords": ["calculation", "deconvolution", "optimization", "model"],
                "suggestions": [
                    "Check input data for invalid values",
                    "Verify calculation parameters are correct",
                    "Check boundary conditions and constraints",
                    "Ensure numerical stability of the algorithm",
                ],
            },
            "data_error": {
                "keywords": ["invalid data", "data format", "parse error", "conversion error"],
                "context_keywords": ["csv", "dataframe", "file_data", "parsing"],
                "suggestions": [
                    "Verify data file format and encoding",
                    "Check for missing or invalid data values",
                    "Ensure data columns match expected format",
                    "Validate data types and ranges",
                ],
            },
            "operation_error": {
                "keywords": ["operation failed", "unknown operation", "invalid operation"],
                "context_keywords": ["operationtype", "request", "process_request"],
                "suggestions": [
                    "Check if the operation type is supported",
                    "Verify operation parameters are correct",
                    "Ensure the component can handle this operation",
                    "Check operation registration and routing",
                ],
            },
        }

        # Statistics
        self.stats = {
            "errors_analyzed": 0,
            "contexts_generated": 0,
            "suggestions_created": 0,
            "classifications_made": 0,
        }

    def expand_error(
        self, error_record: BufferedLogRecord, context_records: List[BufferedLogRecord]
    ) -> BufferedLogRecord:
        """
        Expand error with detailed context analysis.

        Args:
            error_record: The error record to expand
            context_records: Available context records for analysis

        Returns:
            Expanded error record with detailed context
        """
        # Create error context
        context = self._analyze_error_context(error_record, context_records)

        # Generate expanded message
        expanded_message = self._generate_expanded_message(context)

        # Create new log record with expanded information
        expanded_record = self._create_expanded_record(error_record, expanded_message, context)

        # Update statistics
        self.stats["errors_analyzed"] += 1
        self.stats["contexts_generated"] += 1
        if context.suggested_actions:
            self.stats["suggestions_created"] += 1
        if context.error_classification:
            self.stats["classifications_made"] += 1

        return expanded_record

    def _analyze_error_context(
        self, error_record: BufferedLogRecord, context_records: List[BufferedLogRecord]
    ) -> ErrorContext:
        """
        Analyze error context and extract relevant information.

        Args:
            error_record: The error record to analyze
            context_records: Available context records

        Returns:
            ErrorContext with analyzed information
        """
        context = ErrorContext(error_record=error_record)

        # Extract error information
        error_message = error_record.record.getMessage().lower()
        context.context_keywords = self._extract_keywords(error_message)

        # Classify error type
        context.error_classification = self._classify_error(error_message, context.context_keywords)

        # Find related operations and context
        context.preceding_records = self._find_preceding_context(error_record, context_records)
        context.related_operations = self._find_related_operations(error_record, context_records)

        # Extract trace information
        context.error_trace = self._extract_error_trace(error_record)  # Generate suggestions
        context.suggested_actions = self._generate_suggestions(
            context.error_classification, context.context_keywords, error_record
        )

        return context

    def _classify_error(self, error_message: str, context_keywords: List[str]) -> Optional[str]:
        """
        Classify error based on message content and context.

        Args:
            error_message: The error message text
            context_keywords: Keywords extracted from context

        Returns:
            Error classification or None if no match
        """
        # Ensure message is lowercase for consistent matching
        message_lower = error_message.lower()

        # Check for specific file_not_found patterns first (highest priority)
        file_patterns = ["file not found", "no such file", "cannot open"]
        if any(phrase in message_lower for phrase in file_patterns):
            return "file_not_found"

        # Then check for other specific patterns in order of priority
        best_match = None
        best_score = 0

        # Define priority order for error types
        priority_order = ["memory_error", "gui_error", "calculation_error", "operation_error", "data_error"]

        for error_type in priority_order:
            if error_type not in self.error_patterns:
                continue

            pattern = self.error_patterns[error_type]
            score = 0

            # Check for keyword matches
            for keyword in pattern["keywords"]:
                if keyword in message_lower:
                    score += 2

            # Check for context keyword matches
            for keyword in pattern["context_keywords"]:
                if keyword in message_lower or any(keyword in ck for ck in context_keywords):
                    score += 1

            if score > best_score:
                best_score = score
                best_match = error_type

        return best_match if best_score > 0 else None

    def _extract_keywords(self, message: str) -> List[str]:
        """
        Extract relevant keywords from error message.

        Args:
            message: Error message text

        Returns:
            List of extracted keywords
        """
        # Extract file names, operation types, and component names
        keywords = []

        # File names with extensions
        file_matches = re.findall(r"\b\w+\.\w+\b", message)
        keywords.extend(file_matches)

        # Operation types
        operation_matches = re.findall(r"operationtype\.\w+", message, re.IGNORECASE)
        keywords.extend(operation_matches)

        # Component names (words ending with common suffixes)
        component_matches = re.findall(r"\b\w+(?:_data|_operations|_handler|_engine|_manager)\b", message)
        keywords.extend(component_matches)

        # Python module/class names
        module_matches = re.findall(r"\b[a-z_]+\.py\b", message)
        keywords.extend(module_matches)

        return list(set(keywords))  # Remove duplicates

    def _find_preceding_context(
        self, error_record: BufferedLogRecord, context_records: List[BufferedLogRecord]
    ) -> List[BufferedLogRecord]:
        """
        Find log records that occurred before the error for context.

        Args:
            error_record: The error record
            context_records: Available context records

        Returns:
            List of preceding context records
        """
        error_time = error_record.timestamp
        time_window = timedelta(seconds=self.config.context_time_window)

        preceding = []
        for record in context_records:
            if record.timestamp < error_time and error_time - record.timestamp <= time_window:
                preceding.append(record)

        # Sort by timestamp and return most recent ones
        preceding.sort(key=lambda x: x.timestamp, reverse=True)
        return preceding[: self.config.context_lines]

    def _find_related_operations(
        self, error_record: BufferedLogRecord, context_records: List[BufferedLogRecord]
    ) -> List[BufferedLogRecord]:
        """
        Find log records related to the same operation or component.

        Args:
            error_record: The error record
            context_records: Available context records

        Returns:
            List of related operation records
        """
        error_message = error_record.record.getMessage().lower()
        error_keywords = self._extract_keywords(error_message)

        related = []
        for record in context_records:
            record_message = record.record.getMessage().lower()
            record_keywords = self._extract_keywords(record_message)

            # Check for common keywords
            common_keywords = set(error_keywords) & set(record_keywords)
            if common_keywords:
                related.append(record)

        # Sort by relevance (number of common keywords)
        related.sort(
            key=lambda x: len(set(self._extract_keywords(x.record.getMessage().lower())) & set(error_keywords)),
            reverse=True,
        )
        return related[: self.config.trace_depth]

    def _extract_error_trace(self, error_record: BufferedLogRecord) -> Optional[str]:
        """
        Extract stack trace or error trace information.

        Args:
            error_record: The error record

        Returns:
            Extracted trace information or None
        """
        # Check if the record has exception info
        if error_record.record.exc_info:
            return "".join(traceback.format_exception(*error_record.record.exc_info))

        # Look for trace patterns in the message
        message = error_record.record.getMessage()

        # Extract file and line number information
        trace_pattern = r"(\w+\.py):(\d+)"
        matches = re.findall(trace_pattern, message)
        if matches:
            return f"Location: {matches[0][0]}:{matches[0][1]}"

        return None

    def _generate_suggestions(
        self, error_classification: Optional[str], context_keywords: List[str], error_record: BufferedLogRecord
    ) -> List[str]:
        """
        Generate actionable suggestions based on error analysis.

        Args:
            error_classification: Type of error classified
            context_keywords: Keywords from context analysis
            error_record: The original error record

        Returns:
            List of suggested actions
        """
        suggestions = []

        # Add pattern-based suggestions
        if error_classification and error_classification in self.error_patterns:
            suggestions.extend(
                self.error_patterns[error_classification]["suggestions"]
            )  # Add context-specific suggestions
        # File-specific suggestions
        if any(keyword in context_keywords for keyword in ["file", "csv", "json"]):
            suggestions.append("Verify file format and encoding are correct")

        # GUI-specific suggestions
        if any(keyword in context_keywords for keyword in ["main_window", "widget", "qt"]):
            suggestions.append("Check GUI component state and initialization")

        # Add location-specific suggestion
        file_name = getattr(error_record.record, "filename", None)
        line_no = getattr(error_record.record, "lineno", None)
        if file_name and line_no:
            suggestions.append(f"Check code in file {file_name}:{line_no}")

        return suggestions

    def _generate_expanded_message(self, context: ErrorContext) -> str:  # noqa: C901
        """
        Generate formatted expanded error message.

        Args:
            context: Error context information

        Returns:
            Formatted expanded error message
        """
        lines = []
        lines.append("=" * 80)
        lines.append("🚨 DETAILED ERROR ANALYSIS - " + context.error_record.record.levelname)
        lines.append("=" * 80)

        # Basic error information
        lines.append(f"📍 Location: {context.error_record.record.filename}:{context.error_record.record.lineno}")
        lines.append(f"⏰ Time: {context.error_record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"💬 Message: {context.error_record.record.getMessage()}")
        lines.append("")

        # Error classification
        if context.error_classification:
            lines.append(f"🏷️  Error Type: {context.error_classification.replace('_', ' ').title()}")
            lines.append("")

        # Preceding context
        if context.preceding_records:
            lines.append("📋 PRECEDING CONTEXT:")
            lines.append("-" * 40)
            for i, record in enumerate(context.preceding_records[-5:], 1):
                time_ago = (context.error_record.timestamp - record.timestamp).total_seconds()
                lines.append(f"  {i}. [{record.record.levelname}] {record.record.getMessage()} ({time_ago:.1f}s ago)")
            lines.append("")

        # Related operations
        if context.related_operations:
            lines.append("🔗 RELATED OPERATIONS:")
            lines.append("-" * 40)
            for i, record in enumerate(context.related_operations[:3], 1):
                lines.append(
                    f"  {i}. [{record.record.levelname}] {record.record.filename}:\
                        {record.record.lineno} - {record.record.getMessage()}"
                )
            lines.append("")

        # Error trace
        if context.error_trace:
            lines.append("📊 ERROR TRACE:")
            lines.append("-" * 40)
            for line in context.error_trace.split("\n")[:5]:  # Limit trace lines
                if line.strip():
                    lines.append(f"  {line.strip()}")
            lines.append("")

        # Suggested actions
        if context.suggested_actions:
            lines.append("💡 SUGGESTED ACTIONS:")
            lines.append("-" * 40)
            for i, suggestion in enumerate(context.suggested_actions, 1):
                lines.append(f"  {i}. {suggestion}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def _create_expanded_record(
        self, original_record: BufferedLogRecord, expanded_message: str, context: ErrorContext
    ) -> BufferedLogRecord:
        """
        Create new log record with expanded information.

        Args:
            original_record: Original error record
            expanded_message: Expanded error message
            context: Error context information

        Returns:
            New BufferedLogRecord with expanded information
        """
        # Create new log record
        new_record = logging.LogRecord(
            name=original_record.record.name,
            level=original_record.record.levelno,
            pathname=original_record.record.pathname,
            lineno=original_record.record.lineno,
            msg=expanded_message,
            args=(),
            exc_info=original_record.record.exc_info,
        )

        # Add custom attributes for context
        new_record.error_expansion = True
        new_record.original_message = original_record.record.getMessage()
        new_record.error_classification = context.error_classification
        new_record.suggestion_count = len(context.suggested_actions)
        new_record.context_records_count = len(context.preceding_records)

        return BufferedLogRecord(record=new_record, timestamp=original_record.timestamp)

    def is_error_record(self, record: BufferedLogRecord) -> bool:
        """
        Check if record represents an error that should be expanded.

        Args:
            record: Log record to check

        Returns:
            True if record should be expanded
        """
        if not self.config.enabled:
            return False
        # Check log level threshold
        threshold_levels = {"WARNING": 30, "ERROR": 40, "CRITICAL": 50}

        threshold = threshold_levels.get(self.config.error_threshold_level, 30)
        return record.record.levelno >= threshold

    def get_statistics(self) -> Dict[str, int]:
        """
        Get error expansion statistics.

        Returns:
            Dictionary with statistics
        """
        return dict(self.stats)

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        for key in self.stats:
            self.stats[key] = 0
