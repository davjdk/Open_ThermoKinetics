"""
Table formatting module for operation logs aggregation.

This module provides the OperationTableFormatter class for formatting
aggregated operation logs into human-readable tabular format using tabulate.

Key components:
- OperationTableFormatter: Main class for formatting operation logs
- Table structure with columns: Step, Sub-operation, Target, Data Type, Status, Duration
- Operation header and summary formatting
- Error handling and edge cases support
"""

import time
from datetime import datetime
from typing import List

from tabulate import tabulate

from .operation_log import OperationLog
from .sub_operation_log import SubOperationLog


class OperationTableFormatter:
    """
    Formatter for creating human-readable tables from operation logs.

    This class handles the complete formatting pipeline:
    - Operation headers with unique IDs and timestamps
    - Sub-operations table with proper column alignment
    - Operation summary with statistics
    - Error blocks for operations with failures
    """

    def __init__(self, table_format: str = "grid", max_cell_width: int = 50):
        """
        Initialize the table formatter.

        Args:
            table_format: Tabulate table format (grid, plain, simple, etc.)
            max_cell_width: Maximum width for table cells to prevent overly wide output
        """
        self.table_format = table_format
        self.max_cell_width = max_cell_width
        self._operation_counter = 0  # Simple counter for unique operation IDs

    def format_operation_log(self, operation_log: OperationLog) -> str:
        """
        Format a complete operation log into a readable table format.

        Args:
            operation_log: The OperationLog instance to format

        Returns:
            str: Formatted operation log as a string
        """
        if operation_log is None:
            return "No operation data available."

        # Increment operation counter for unique ID
        self._operation_counter += 1
        operation_id = self._operation_counter

        # Build formatted output parts
        parts = []

        # 1. Operation header
        header = self._format_operation_header(operation_log, operation_id)
        parts.append(header)

        # 2. Sub-operations table (if any)
        if operation_log.sub_operations:
            sub_ops_table = self._format_sub_operations_table(operation_log.sub_operations)
            parts.append(sub_ops_table)
        else:
            parts.append("No sub-operations recorded.")

        # 3. Error block (if operation failed)
        if operation_log.status == "error" and operation_log.exception_info:
            error_block = self._format_error_block(operation_log.exception_info)
            parts.append(error_block)

        # 4. Operation summary
        summary = self._format_operation_summary(operation_log, operation_id)
        parts.append(summary)

        # Join all parts with empty lines for readability
        return "\n\n".join(parts) + "\n"

    def _format_operation_header(self, operation_log: OperationLog, operation_id: int) -> str:
        """
        Format the operation header with name, ID, and start timestamp.

        Args:
            operation_log: The operation log data
            operation_id: Unique operation identifier

        Returns:
            str: Formatted header string
        """
        start_time = datetime.fromtimestamp(operation_log.start_time or time.time())
        timestamp_str = start_time.strftime("%Y-%m-%d %H:%M:%S")

        return f'Operation "{operation_log.operation_name}" – STARTED (id={operation_id}, {timestamp_str})'

    def _format_sub_operations_table(self, sub_operations: List[SubOperationLog]) -> str:
        """
        Format sub-operations into a tabulated table.

        Args:
            sub_operations: List of SubOperationLog instances

        Returns:
            str: Formatted table string
        """
        if not sub_operations:
            return "No sub-operations to display."  # Define table headers
        headers = [
            "Step",  # Step number
            "Sub-operation",  # Sub-operation name
            "Target",  # Target
            "Result data type",  # Result data type
            "Status",  # Status (OK/Error)
            "Time, s",  # Duration in seconds
        ]

        # Build table data
        table_data = []
        for sub_op in sub_operations:
            row = [
                sub_op.step_number,
                self._truncate_text(sub_op.operation_name, 20),
                self._truncate_text(sub_op.target, 15),
                self._truncate_text(sub_op.data_type or "unknown", 20),
                sub_op.status,
                f"{sub_op.duration_ms / 1000:.3f}" if sub_op.duration_ms is not None else "N/A",
            ]
            table_data.append(row)  # Format table with proper alignment
        column_alignment = ["right", "left", "left", "left", "center", "right"]

        try:
            formatted_table = tabulate(
                table_data, headers=headers, tablefmt=self.table_format, colalign=column_alignment, floatfmt=".3f"
            )
            return formatted_table
        except Exception:
            # Fallback to simple formatting if tabulate fails
            return self._format_simple_table(headers, table_data)

    def _format_operation_summary(self, operation_log: OperationLog, operation_id: int) -> str:
        """
        Format the operation summary with statistics and final status.

        Args:
            operation_log: The operation log data
            operation_id: Unique operation identifier

        Returns:
            str: Formatted summary string
        """
        total_steps = operation_log.sub_operations_count
        successful_steps = operation_log.successful_sub_operations_count
        failed_steps = operation_log.failed_sub_operations_count
        total_time = (operation_log.duration_ms or 0) / 1000  # Convert to seconds        # Format statistics line
        stats_line = (
            f"SUMMARY: steps {total_steps}, successful {successful_steps}, "
            f"with errors {failed_steps}, total time {total_time:.3f} s."
        )

        # Format completion line with status
        status_text = "successful" if operation_log.status == "success" else "with error"
        completion_line = f'Operation "{operation_log.operation_name}" – COMPLETED (status: {status_text})'

        return f"{stats_line}\n{completion_line}"

    def _format_error_block(self, exception_info: str) -> str:
        """
        Format error information block for failed operations.

        Args:
            exception_info: Exception information string

        Returns:
            str: Formatted error block
        """
        # Truncate very long error messages
        truncated_error = self._truncate_text(exception_info, 200)

        return f"ERROR: {truncated_error}"

    def _format_simple_table(self, headers: List[str], table_data: List[List]) -> str:
        """
        Fallback simple table formatting when tabulate fails.

        Args:
            headers: Table column headers
            table_data: Table row data

        Returns:
            str: Simple formatted table
        """
        lines = []

        # Add headers
        header_line = " | ".join(f"{header:^15}" for header in headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # Add data rows
        for row in table_data:
            row_line = " | ".join(f"{str(cell):^15}" for cell in row)
            lines.append(row_line)

        return "\n".join(lines)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        Truncate text to maximum length with ellipsis if needed.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length

        Returns:
            str: Truncated text
        """
        if text is None:
            return "N/A"

        text_str = str(text)
        if len(text_str) <= max_length:
            return text_str

        return text_str[: max_length - 3] + "..."

    def set_table_format(self, table_format: str) -> None:
        """
        Change the table format for future formatting operations.

        Args:
            table_format: New tabulate table format
        """
        self.table_format = table_format

    def get_available_formats(self) -> List[str]:
        """
        Get list of available tabulate table formats.

        Returns:
            List of available format names
        """
        return [
            "plain",
            "simple",
            "github",
            "grid",
            "fancy_grid",
            "pipe",
            "orgtbl",
            "jira",
            "presto",
            "pretty",
            "psql",
            "rst",
            "mediawiki",
            "moinmoin",
            "youtrack",
            "html",
            "unsafehtml",
            "latex",
            "latex_raw",
            "latex_booktabs",
            "textile",
        ]


# Global formatter instance for use across the module
default_formatter = OperationTableFormatter()


def format_operation_log(operation_log: OperationLog) -> str:
    """
    Convenience function to format an operation log using the default formatter.

    Args:
        operation_log: The OperationLog instance to format

    Returns:
        str: Formatted operation log as a string
    """
    return default_formatter.format_operation_log(operation_log)
