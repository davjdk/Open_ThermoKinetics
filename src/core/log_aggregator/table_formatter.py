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
    - Error blocks for operations with failures"""

    def __init__(
        self,
        table_format: str = "grid",
        max_cell_width: int = 50,
        include_error_details: bool = True,
        max_error_context_items: int = 5,
    ):
        """
        Initialize the table formatter.

        Args:
            table_format: Tabulate table format (grid, plain, simple, etc.)
            max_cell_width: Maximum width for table cells to prevent overly wide output
            include_error_details: Whether to include detailed error blocks
            max_error_context_items: Maximum number of context items to display"""
        self.table_format = table_format
        self.max_cell_width = max_cell_width
        self.include_error_details = include_error_details
        self.max_error_context_items = max_error_context_items
        self._operation_counter = 0  # Simple counter for unique operation IDs

    def format_operation_log(self, operation_log: OperationLog) -> str:
        """
        Format a complete operation log into a readable table format.

        Args:
            operation_log: The OperationLog instance to format

        Returns:
            str: Complete formatted operation log
        """
        if operation_log is None:
            return "No operation data available."

        # Increment operation counter for unique ID
        self._operation_counter += 1
        operation_id = self._operation_counter

        parts = []

        # 1. Header separator
        parts.append("=" * 80)

        # 2. Operation header
        header = self._format_operation_header(operation_log, operation_id)
        parts.append(header)
        parts.append("")  # Empty line        # 3. Meta-operations summary (if available)
        if hasattr(operation_log, "meta_operations") and operation_log.meta_operations:
            meta_summary = self._format_meta_operations_summary(operation_log.meta_operations)
            parts.append(meta_summary)
            parts.append("")  # Empty line

        # 4. Sub-operations table
        if operation_log.sub_operations:
            table = self._format_sub_operations_table(operation_log.sub_operations)
            parts.append(table)
        else:
            parts.append("No sub-operations recorded.")
        parts.append("")  # Empty line

        # 4. Error details block (NEW)
        if self.include_error_details:
            error_block = self._format_error_details_block(operation_log)
            if error_block:
                parts.append(error_block)
                parts.append("")  # Empty line

        # 5. Main operation error block (if operation failed)
        if operation_log.status == "error" and operation_log.exception_info:
            main_error_block = self._format_error_block(operation_log.exception_info)
            parts.append(main_error_block)
            parts.append("")  # Empty line

        # 6. Operation summary
        summary = self._format_operation_summary(operation_log, operation_id)
        parts.append(summary)

        # 7. Footer separator
        parts.append("=" * 80)

        return "\n".join(parts) + "\n"

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
        ]  # Build table data
        table_data = []
        for sub_op in sub_operations:
            row = [
                sub_op.step_number,
                sub_op.clean_operation_name,
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

    def _format_meta_operations_summary(self, meta_operations) -> str:
        """
        Format meta-operations summary for display.

        Args:
            meta_operations: List of MetaOperation objects

        Returns:
            str: Formatted meta-operations summary
        """
        if not meta_operations:
            return ""

        lines = ["META-OPERATIONS DETECTED:"]

        for i, meta_op in enumerate(meta_operations, 1):
            # Basic info line
            duration_ms = meta_op.duration_ms or 0
            success_rate = (
                (meta_op.successful_operations_count / meta_op.operations_count * 100)
                if meta_op.operations_count > 0
                else 0
            )

            summary_line = (
                f"  {i}. {meta_op.name} ({meta_op.heuristic}): "
                f"{meta_op.operations_count} ops, {duration_ms:.1f}ms, "
                f"{success_rate:.0f}% success"
            )
            lines.append(summary_line)

            # Operation details (compact)
            if meta_op.sub_operations:
                step_numbers = [str(op.step_number) for op in meta_op.sub_operations]
                if len(step_numbers) <= 5:
                    steps_text = ", ".join(step_numbers)
                else:
                    steps_text = f"{', '.join(step_numbers[:3])}, ... {len(step_numbers)-3} more"
                lines.append(f"     Steps: {steps_text}")

        return "\n".join(lines)

    def _format_error_details_block(self, operation_log: OperationLog) -> str:
        """
        Format detailed error information for sub-operations with errors.

        Args:
            operation_log: The operation log data

        Returns:
            str: Formatted error details block
        """
        error_sub_operations = [
            sub_op
            for sub_op in operation_log.sub_operations
            if sub_op.status == "Error" and sub_op.has_detailed_error()
        ]

        if not error_sub_operations:
            return ""

        lines = ["ERROR DETAILS:"]
        lines.append("─" * 77)  # Separator line

        for sub_op in error_sub_operations:
            error_block = self._format_single_error_details(sub_op)
            lines.append(error_block)
            lines.append("")  # Empty line between errors

        lines.append("─" * 77)  # Bottom separator

        return "\n".join(lines)

    def _format_single_error_details(self, sub_operation) -> str:
        """
        Format detailed information for a single sub-operation error.

        Args:
            sub_operation: SubOperationLog with error details

        Returns:
            str: Formatted error information"""
        if not sub_operation.has_detailed_error():
            return (
                f"Step {sub_operation.step_number}: {sub_operation.clean_operation_name} → "
                f"{sub_operation.target}\n  Error: {sub_operation.get_error_summary()}"
            )

        error_details = sub_operation.error_details
        lines = []

        # Header line
        lines.append(f"Step {sub_operation.step_number}: {sub_operation.clean_operation_name} → {sub_operation.target}")

        # Error type and severity
        lines.append(f"  Error Type: {error_details.error_type.value.upper()}")
        lines.append(f"  Severity: {error_details.severity.value.upper()}")

        # Error message
        lines.append(f"  Message: {error_details.error_message}")

        # Context information
        if error_details.error_context:
            lines.append("  Context:")
            context_items = list(error_details.error_context.items())[: self.max_error_context_items]
            for key, value in context_items:
                lines.append(f"    - {key}: {value}")

        # Technical details
        if error_details.technical_details:
            lines.append(f"  Technical Details: {error_details.technical_details}")

        # Suggested action
        if error_details.suggested_action:
            lines.append(f"  Suggested Action: {error_details.suggested_action}")

        return "\n".join(lines)

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
