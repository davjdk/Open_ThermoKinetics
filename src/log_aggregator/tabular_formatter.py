"""
Tabular formatter module for log aggregation system.

This module provides the TabularFormatter class that converts aggregated patterns
into structured ASCII tables with adaptive formatting for improved readability.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from .buffer_manager import BufferedLogRecord
from .config import TabularFormattingConfig
from .pattern_detector import LogPattern, PatternGroup
from .safe_message_utils import safe_get_message


@dataclass
class TableData:
    """Represents structured data for table formatting."""

    title: str
    """Title displayed above the table"""

    headers: List[str]
    """Column headers for the table"""

    rows: List[List[str]]
    """Data rows, each row is a list of cell values"""

    summary: Optional[str] = None
    """Optional summary text displayed below the table"""

    table_type: str = "generic"
    """Type identifier for specialized formatting"""


class TabularFormatter:
    """
    Formatter for converting aggregated patterns into ASCII tables.

    This class provides specialized formatting for different pattern types,
    creating structured, readable tables with adaptive column widths.
    """

    def __init__(self, config: Optional[TabularFormattingConfig] = None):
        """
        Initialize tabular formatter.

        Args:
            config: Configuration for table formatting behavior
        """
        self.config = config or TabularFormattingConfig()

        # Pattern type to formatting method mapping
        self._formatters = {
            "plot_lines_addition": self._create_plot_lines_table,
            "cascade_component_initialization": self._create_initialization_table,
            "request_response_cycle": self._create_request_response_table,
            "file_operations": self._create_file_operations_table,
            "gui_updates": self._create_gui_updates_table,
        }

    def format_patterns_as_tables(self, patterns: List[Union[PatternGroup, LogPattern]]) -> List[BufferedLogRecord]:
        """
        Format aggregated patterns as ASCII tables.

        Args:
            patterns: List of pattern groups to format

        Returns:
            List of log records containing formatted tables
        """
        if not self.config.enabled:
            return []

        table_records = []

        for pattern in patterns:
            if not self._should_format_pattern(pattern):
                continue

            try:
                table_data = self._create_table_for_pattern(pattern)
                if table_data and table_data.rows:
                    formatted_table = self._format_ascii_table(table_data)
                    table_record = self._create_table_record(formatted_table, pattern)
                    table_records.append(table_record)

            except Exception as e:
                # Log formatting error but continue processing
                error_msg = f"Error formatting table for {pattern.pattern_type}: {e}"
                error_record = self._create_error_record(error_msg)
                table_records.append(error_record)

        return table_records

    def _should_format_pattern(self, pattern: Union[PatternGroup, LogPattern]) -> bool:
        """Check if pattern should be formatted as table."""
        if hasattr(pattern, "get_table_suitable_flag") and not pattern.get_table_suitable_flag():
            return False

        return (
            pattern.pattern_type in self.config.auto_format_patterns
            and pattern.count >= 2
            and len(pattern.records) <= self.config.max_rows_per_table
        )

    def _create_table_for_pattern(self, pattern: Union[PatternGroup, LogPattern]) -> Optional[TableData]:
        """Create table data for a specific pattern type."""
        formatter = self._formatters.get(pattern.pattern_type, self._create_generic_table)
        return formatter(pattern)

    def _create_plot_lines_table(self, pattern: Union[PatternGroup, LogPattern]) -> TableData:
        """Create table for plot lines addition pattern."""
        headers = ["#", "Line Name", "Time", "Duration (ms)", "Status"]
        rows = []

        start_time = self._get_start_time_ms(pattern)

        for i, record in enumerate(pattern.records[: self.config.max_rows_per_table], 1):
            line_name = self._extract_line_name(safe_get_message(record.record))
            record_time_ms = record.timestamp.timestamp() * 1000
            relative_time = record_time_ms - start_time
            duration = relative_time if i > 1 else 0.0

            row = [str(i), line_name, f"+{relative_time:.1f}ms", f"{duration:.1f}", "✅ Success"]
            rows.append(row)

        end_time = self._get_end_time_ms(pattern)
        total_duration = end_time - start_time
        avg_duration = total_duration / len(pattern.records) if pattern.records else 0

        summary = (
            f"📊 Total: {len(pattern.records)} kinetic model lines added in "
            f"{total_duration:.1f}ms (avg: {avg_duration:.1f}ms per line)"
        )

        return TableData(
            title="📊 Plot Lines Addition Summary",
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="plot_lines_addition",
        )

    def toggle_tabular_format(self, enabled: bool) -> None:
        """Enable or disable tabular formatting."""
        self.config.enabled = enabled

    def _create_initialization_table(self, pattern: Union[PatternGroup, LogPattern]) -> TableData:
        """Create table for component initialization cascade pattern."""
        headers = ["Step", "Component", "Time", "Duration (ms)", "Status"]
        rows = []

        start_time = self._get_start_time_ms(pattern)

        for i, record in enumerate(pattern.records[: self.config.max_rows_per_table], 1):
            component_name = self._extract_component_name(safe_get_message(record.record))
            record_time_ms = record.timestamp.timestamp() * 1000
            relative_time = record_time_ms - start_time

            # Calculate duration between consecutive components
            if i > 1:
                prev_time = pattern.records[i - 2].timestamp.timestamp() * 1000
                duration = record_time_ms - prev_time
            else:
                duration = 0.0

            row = [str(i), component_name, f"+{relative_time:.1f}ms", f"{duration:.1f}", "✅ OK"]
            rows.append(row)

        end_time = self._get_end_time_ms(pattern)
        total_duration = end_time - start_time
        summary = f"📊 Initialization cascade: {len(pattern.records)} components in {total_duration:.1f}ms"

        return TableData(
            title="🔧 Component Initialization Cascade",
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="initialization",
        )

    def _create_request_response_table(self, pattern: PatternGroup) -> TableData:
        """Create table for request-response cycles pattern."""
        headers = ["#", "Operation", "Time", "Duration (ms)", "Status"]
        rows = []

        # Group request-response pairs
        pairs = self._group_request_response_pairs(pattern.records)

        for i, (request, response) in enumerate(pairs[: self.config.max_rows_per_table], 1):
            operation = self._extract_operation_type(safe_get_message(request.record))
            time_str = request.timestamp.strftime("%H:%M:%S.%f")[:-3]

            if response:
                duration = (response.timestamp.timestamp() - request.timestamp.timestamp()) * 1000
                status = "✅ Complete"
            else:
                duration = 0.0
                status = "⏳ Pending"

            row = [str(i), operation, time_str, f"{duration:.1f}", status]
            rows.append(row)

        avg_duration = sum(float(row[3]) for row in rows) / len(rows) if rows else 0
        summary = f"📊 Request-Response cycles: {len(rows)} operations, avg: {avg_duration:.1f}ms"

        return TableData(
            title="🔄 Request-Response Cycles",
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="request_response",
        )

    def _create_file_operations_table(self, pattern: PatternGroup) -> TableData:
        """Create table for file operations pattern."""
        headers = ["#", "Operation", "File", "Time", "Status"]
        rows = []

        for i, record in enumerate(pattern.records[: self.config.max_rows_per_table], 1):
            operation = self._extract_file_operation(safe_get_message(record.record))
            file_name = self._extract_file_name(safe_get_message(record.record))
            time_str = record.timestamp.strftime("%H:%M:%S.%f")[:-3]

            row = [str(i), operation, file_name, time_str, "✅ Success"]
            rows.append(row)  # Count operation types
        operations = [self._extract_file_operation(safe_get_message(r.record)) for r in pattern.records]
        operation_counts = {}
        for op in operations:
            operation_counts[op] = operation_counts.get(op, 0) + 1

        count_str = ", ".join([f"{op}: {count}" for op, count in operation_counts.items()])
        summary = f"📊 File operations: {count_str}"

        return TableData(
            title="📁 File Operations Summary",
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="file_operations",
        )

    def _create_gui_updates_table(self, pattern: Union[PatternGroup, LogPattern]) -> TableData:
        """Create table for GUI updates pattern."""
        headers = ["#", "Component", "Update Type", "Time", "Duration (ms)"]
        rows = []

        start_time = self._get_start_time_ms(pattern)

        for i, record in enumerate(pattern.records[: self.config.max_rows_per_table], 1):
            component = self._extract_gui_component(safe_get_message(record.record))
            update_type = self._extract_gui_update_type(safe_get_message(record.record))
            record_time_ms = record.timestamp.timestamp() * 1000
            relative_time = record_time_ms - start_time

            # Calculate duration between updates
            if i > 1:
                prev_time = pattern.records[i - 2].timestamp.timestamp() * 1000
                duration = record_time_ms - prev_time
            else:
                duration = 0.0

            row = [str(i), component, update_type, f"+{relative_time:.1f}ms", f"{duration:.1f}"]
            rows.append(row)

        end_time = self._get_end_time_ms(pattern)
        total_duration = end_time - start_time
        summary = f"📊 GUI updates: {len(pattern.records)} operations in {total_duration:.1f}ms"

        return TableData(
            title="🖥️ GUI Updates Batch",
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="gui_updates",
        )

    def _create_generic_table(self, pattern: Union[PatternGroup, LogPattern]) -> TableData:
        """Create generic table for unspecified pattern types."""
        headers = ["#", "Message", "Time", "Logger"]
        rows = []
        for i, record in enumerate(pattern.records[: self.config.max_rows_per_table], 1):
            time_str = record.timestamp.strftime("%H:%M:%S.%f")[:-3]
            message = safe_get_message(record.record)
            if len(message) > 50:
                message = message[:50] + "..."

            row = [str(i), message, time_str, record.record.name]
            rows.append(row)

        summary = f"📊 Generic pattern: {len(pattern.records)} records of type '{pattern.pattern_type}'"

        return TableData(
            title=f"📋 {pattern.pattern_type.replace('_', ' ').title()} Pattern",
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="generic",
        )

    def _format_ascii_table(self, table_data: TableData) -> str:  # noqa: C901
        """Format table data as ASCII table with borders."""
        if not table_data.rows:
            return f"┌─ {table_data.title} ─┐\n│ No data available │\n└─────────────────────┘"

        # Calculate column widths
        col_widths = self._calculate_column_widths(table_data.headers, table_data.rows)
        total_width = sum(col_widths) + len(col_widths) * 3 + 1  # borders and padding

        # Ensure table fits within max width
        if total_width > self.config.max_table_width:
            col_widths = self._adjust_column_widths(col_widths, table_data.headers, table_data.rows)
            total_width = sum(col_widths) + len(col_widths) * 3 + 1

        # Build table
        lines = []

        # Title bar
        title_line = f"│ {table_data.title:<{total_width-4}} │"
        lines.append(f"┌{'─' * (total_width-2)}┐")
        lines.append(title_line)
        lines.append(f"├{'─' * (total_width-2)}┤")

        # Headers
        header_cells = []
        for header, width in zip(table_data.headers, col_widths):
            header_cells.append(f"{header:<{width}}")
        header_line = "│ " + " │ ".join(header_cells) + " │"
        lines.append(header_line)

        # Header separator
        separator_parts = []
        for i, width in enumerate(col_widths):
            if i == 0:
                separator_parts.append("├" + "─" * (width + 2))
            elif i == len(col_widths) - 1:
                separator_parts.append("┼" + "─" * (width + 2) + "┤")
            else:
                separator_parts.append("┼" + "─" * (width + 2))
        lines.append("".join(separator_parts))

        # Data rows
        for row in table_data.rows:
            row_cells = []
            for cell, width in zip(row, col_widths):
                # Truncate cell if too long
                if len(cell) > width:
                    cell = cell[: width - 3] + "..."
                row_cells.append(f"{cell:<{width}}")

            row_line = "│ " + " │ ".join(row_cells) + " │"
            lines.append(row_line)

        # Bottom border
        lines.append(f"└{'─' * (total_width-2)}┘")

        # Summary
        if table_data.summary and self.config.include_summaries:
            lines.append(table_data.summary)

        return "\n".join(lines)

    def _calculate_column_widths(self, headers: List[str], rows: List[List[str]]) -> List[int]:
        """Calculate optimal column widths based on content."""
        if not rows:
            return [len(header) for header in headers]

        widths = [len(header) for header in headers]

        for row in rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(cell)))

        return widths

    def _adjust_column_widths(self, col_widths: List[int], headers: List[str], rows: List[List[str]]) -> List[int]:
        """Adjust column widths to fit within max table width."""
        max_content_width = self.config.max_table_width - len(col_widths) * 3 - 1
        current_width = sum(col_widths)

        if current_width <= max_content_width:
            return col_widths

        # Proportionally reduce column widths
        reduction_ratio = max_content_width / current_width
        adjusted_widths = [max(8, int(width * reduction_ratio)) for width in col_widths]

        return adjusted_widths

    def _group_request_response_pairs(
        self, records: List[BufferedLogRecord]
    ) -> List[Tuple[BufferedLogRecord, Optional[BufferedLogRecord]]]:
        """Group request and response records into pairs."""
        pairs = []
        request = None

        for record in records:
            if "request" in safe_get_message(record.record).lower():
                if request:  # Previous request without response
                    pairs.append((request, None))
                request = record
            elif "response" in safe_get_message(record.record).lower() and request:
                pairs.append((request, record))
                request = None

        if request:  # Final request without response
            pairs.append((request, None))

        return pairs

    # Extraction helper methods
    def _extract_line_name(self, message: str) -> str:
        """Extract line name from plot addition message."""
        patterns = [
            r"line[s]?\s+['\"]([^'\"]+)['\"]",
            r"adding\s+([A-Z0-9/_]+)",
            r"plot[ting]*\s+([A-Z0-9/_]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)

        # Fallback: look for common kinetic model names
        kinetic_models = ["F1/3", "F3/4", "F3/2", "F2", "F3", "A2", "A3", "D1", "R2", "R3"]
        for model in kinetic_models:
            if model in message:
                return model

        return "Unknown"

    def _extract_component_name(self, message: str) -> str:
        """Extract component name from initialization message."""
        patterns = [
            r"initializing\s+([A-Za-z0-9_]+)",
            r"creating\s+([A-Za-z0-9_]+)",
            r"([A-Za-z0-9_]+)\s+initialized",
            r"([A-Za-z]+(?:Manager|Tab|Widget|Framework))",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)

        return "Unknown"

    def _extract_operation_type(self, message: str) -> str:
        """Extract operation type from request message."""
        patterns = [
            r"[Oo]peration[:\s]+([A-Z_]+)",  # Operation: UPDATE_VALUE
            r"([A-Z]+(?:_[A-Z]+)*)\s+request\s+sent",  # SET_VALUE request sent
            r"([A-Z]+(?:_[A-Z]+)*)\s+request",  # SET_VALUE request (fallback)
            r"[Rr]equest[:\s]+([A-Z_]+)",  # Request: GET_VALUE
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return "UNKNOWN"

    def _extract_file_name(self, message: str) -> str:
        """Extract file name from file operation message."""
        patterns = [
            r"file[:\s]+['\"]([^'\"]+\.[a-zA-Z0-9]+)['\"]",
            r"loading\s+([^\s]+\.[a-zA-Z0-9]+)",
            r"([A-Za-z0-9_]+\.[a-zA-Z0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)

        return "Unknown"

    def _extract_file_operation(self, message: str) -> str:
        """Extract operation type from file message."""
        if "load" in message.lower():
            return "Load"
        elif "save" in message.lower():
            return "Save"
        elif "process" in message.lower():
            return "Process"
        elif "export" in message.lower():
            return "Export"
        elif "import" in message.lower():
            return "Import"
        else:
            return "Unknown"

    def _extract_gui_component(self, message: str) -> str:
        """Extract GUI component name from update message."""
        components = [
            "PlotCanvas",
            "SideBar",
            "SubSideBar",
            "MainTab",
            "CoefficientsView",
            "ReactionTable",
            "ModelScheme",
            "ConsoleWidget",
            "MainWindow",
        ]

        for component in components:
            if component.lower() in message.lower():
                return component

        return "Unknown"

    def _extract_gui_update_type(self, message: str) -> str:
        """Extract GUI update type from message."""
        if "add" in message.lower():
            return "AddLine"
        elif "update" in message.lower():
            return "Update"
        elif "set" in message.lower():
            return "SetActive"
        elif "receive" in message.lower():
            return "Received"
        elif "refresh" in message.lower():
            return "Refresh"
        else:
            return "Unknown"

    def _create_table_record(self, formatted_table: str, pattern: PatternGroup) -> BufferedLogRecord:
        """Create a log record containing the formatted table."""
        from datetime import datetime
        from logging import LogRecord

        log_record = LogRecord(
            name="log_aggregator.tabular_formatter",
            level=20,  # INFO level
            pathname="",
            lineno=0,
            msg=formatted_table,
            args=(),
            exc_info=None,
        )

        return BufferedLogRecord(record=log_record, timestamp=datetime.now())

    def _create_error_record(self, error_message: str) -> BufferedLogRecord:
        """Create a log record for formatting errors."""
        from datetime import datetime
        from logging import LogRecord

        log_record = LogRecord(
            name="log_aggregator.tabular_formatter",
            level=40,  # ERROR level
            pathname="",
            lineno=0,
            msg=f"[TABULAR_FORMAT_ERROR] {error_message}",
            args=(),
            exc_info=None,
        )

        return BufferedLogRecord(record=log_record, timestamp=datetime.now())

    def _get_start_time_ms(self, pattern: Union[PatternGroup, LogPattern]) -> float:
        """Get start time in milliseconds for both LogPattern and PatternGroup."""
        if hasattr(pattern, "start_time"):
            # PatternGroup
            return pattern.start_time.timestamp() * 1000
        else:
            # LogPattern
            return pattern.first_seen * 1000

    def _get_end_time_ms(self, pattern: Union[PatternGroup, LogPattern]) -> float:
        """Get end time in milliseconds for both LogPattern and PatternGroup."""
        if hasattr(pattern, "end_time"):
            # PatternGroup
            return pattern.end_time.timestamp() * 1000
        else:
            # LogPattern
            return pattern.last_seen * 1000
