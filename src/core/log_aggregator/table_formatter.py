"""
Table formatting module for operation logs aggregation.

This module provides the OperationTableFormatter class for formatting
aggregated operation logs into human-readable tabular format using tabulate.

Key components:
- OperationTableFormatter: Main class for formatting operation logs
- Table structure with columns: Step, Sub-operation, Target, Data Type, Status, Duration
- Operation header and summary formatting
- Error handling and edge cases support
- Meta-operations support with configurable grouping and visualization
"""

import time
from datetime import datetime
from typing import Dict, List

from tabulate import tabulate

from .formatter_config import FormatterConfig
from .meta_operation import MetaOperation
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
    - Meta-operations grouping and visualization"""

    def __init__(
        self,
        config: FormatterConfig = None,
        table_format: str = "grid",
        max_cell_width: int = 50,
        include_error_details: bool = True,
        max_error_context_items: int = 5,
    ):
        """
        Initialize the table formatter.

        Args:
            config: FormatterConfig instance for meta-operations support
            table_format: Tabulate table format (grid, plain, simple, etc.)
            max_cell_width: Maximum width for table cells to prevent overly wide output
            include_error_details: Whether to include detailed error blocks
            max_error_context_items: Maximum number of context items to display"""

        # Use config if provided, otherwise create default with legacy parameters
        if config is not None:
            self.config = config
        else:
            self.config = FormatterConfig(
                table_format=table_format,
                max_cell_width=max_cell_width,
                include_error_details=include_error_details,
                max_error_context_items=max_error_context_items,
            )
        # Legacy compatibility
        self.table_format = self.config.table_format
        self.max_cell_width = self.config.max_cell_width
        self.include_error_details = self.config.include_error_details
        self.max_error_context_items = self.config.max_error_context_items
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
        parts.append("")  # Empty line        # 3. Sub-operations table (with meta-operations support)
        if operation_log.sub_operations:
            if (
                self.config.group_meta_operations
                and hasattr(operation_log, "meta_operations")
                and operation_log.meta_operations
            ):
                # Add meta-operations summary first
                meta_summary = self._format_meta_operations_summary(operation_log.meta_operations)
                if meta_summary:
                    parts.append(meta_summary)
                    parts.append("")  # Empty line

                # Format with meta-operations grouping
                table = self._format_with_meta_operations(operation_log)
            else:
                # Traditional flat formatting
                table = self._format_flat_table(operation_log)
            parts.append(table)
        else:
            parts.append("No sub-operations recorded.")
        parts.append("")  # Empty line

        # 4. Error details block
        if self.config.include_error_details:
            error_block = self._format_error_details_block(operation_log)
            if error_block:
                parts.append(error_block)
                parts.append("")  # Empty line        # 5. Summary section
        summary = self._format_operation_summary(operation_log, operation_id)
        parts.append(summary)

        # 6. Footer separator
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
        total_time = (operation_log.duration_ms or 0) / 1000  # Convert to seconds

        # Check for meta-operations
        meta_ops_info = ""
        if (
            self.config.group_meta_operations
            and hasattr(operation_log, "meta_operations")
            and operation_log.meta_operations
        ):
            meta_count = len(operation_log.meta_operations)
            grouped_ops = sum(len(meta_op.sub_operations) for meta_op in operation_log.meta_operations)
            meta_ops_info = f", meta-operations {meta_count}, grouped {grouped_ops}/{total_steps} ops"

        # Format statistics line
        stats_line = (
            f"SUMMARY: steps {total_steps}, successful {successful_steps}, "
            f"with errors {failed_steps}, total time {total_time:.3f} s{meta_ops_info}."
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

        for i, meta_op in enumerate(meta_operations, 1):  # Basic info line
            duration_ms = meta_op.duration_ms or 0

            success_rate = (
                (meta_op.successful_operations_count / meta_op.operations_count * 100)
                if meta_op.operations_count > 0
                else 0
            )

            summary_line = (
                f"  {i}. {meta_op.name} ({meta_op.strategy_name}): "
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

    def set_output_mode(self, mode: str) -> None:
        """
        Dynamically change output mode for meta-operations formatting.

        Args:
            mode: Output mode name (compact, expanded, debug, minimal)
        """
        from .formatter_config import MODE_CONFIGS

        if mode in MODE_CONFIGS:
            mode_settings = MODE_CONFIGS[mode]
            for key, value in mode_settings.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

    def _format_with_meta_operations(self, operation_log: OperationLog) -> str:
        """
        Format operation log table with meta-operations grouping.

        Args:
            operation_log: The OperationLog instance with meta_operations

        Returns:
            str: Formatted table with grouped meta-operations
        """
        # Determine operations that are grouped in meta-operations
        grouped_operations = set()
        for meta_op in operation_log.meta_operations:
            grouped_operations.update(op.step_number for op in meta_op.sub_operations)

        # Collect table rows
        table_rows = []

        # Add meta-operations
        for meta_op in operation_log.meta_operations:
            table_rows.extend(self._format_meta_operation_rows(meta_op))

        # Add ungrouped operations
        for sub_op in operation_log.sub_operations:
            if sub_op.step_number not in grouped_operations:
                table_rows.append(self._format_single_operation_row(sub_op))

        # Sort by start time
        table_rows.sort(key=lambda row: row.get("start_time", 0))

        # Build final table
        return self._build_table_from_rows(table_rows)

    def _format_flat_table(self, operation_log: OperationLog) -> str:
        """
        Format operation log in traditional flat table format.

        Args:
            operation_log: The OperationLog instance

        Returns:
            str: Formatted flat table
        """
        return self._format_sub_operations_table(operation_log.sub_operations)

    def _format_meta_operation_rows(self, meta_op: MetaOperation) -> List[Dict]:
        """
        Format rows for a single meta-operation.

        Args:
            meta_op: MetaOperation instance to format

        Returns:
            List[Dict]: List of table row dictionaries
        """
        rows = []

        if self.config.compact_meta_view:
            # Compact representation
            rows.append(self._create_meta_operation_summary_row(meta_op))

            # Individual operations details (optional)
            if self.config.show_individual_ops and len(meta_op.sub_operations) <= self.config.max_operations_inline:
                for sub_op in meta_op.sub_operations:
                    rows.append(self._create_indented_operation_row(sub_op))

        else:
            # Expanded representation
            rows.append(self._create_meta_operation_header_row(meta_op))
            for i, sub_op in enumerate(meta_op.sub_operations):
                is_last = i == len(meta_op.sub_operations) - 1
                rows.append(self._create_indented_operation_row(sub_op, is_last))

        return rows

    def _create_meta_operation_summary_row(self, meta_op: MetaOperation) -> Dict:
        """
        Create summary row for meta-operation.

        Args:
            meta_op: MetaOperation instance

        Returns:
            Dict: Row data for summary representation
        """
        # Handle empty meta-operations
        if not meta_op.sub_operations:
            return {
                "Step": "?",
                "Sub-operation": f"{self.config.meta_operation_symbol} {meta_op.name}",
                "Target": "unknown",
                "Result data type": "unknown",
                "Status": "Empty",
                "Time, s": 0.0,
            }

        # Get first step number in group
        first_step = min(op.step_number for op in meta_op.sub_operations)

        # Aggregate data
        targets = list({op.target for op in meta_op.sub_operations})
        data_types = list({op.data_type for op in meta_op.sub_operations})
        statuses = list({op.status for op in meta_op.sub_operations})

        # Create summaries
        target_summary = targets[0] if len(targets) == 1 else "mixed"
        data_type_summary = data_types[0] if len(data_types) == 1 else "mixed"
        status_summary = statuses[0] if len(statuses) == 1 else "mixed"

        # Meta-operation symbol
        symbol = self.config.meta_operation_symbol

        return {
            "step": f"{symbol} {first_step}",
            "sub_operation": meta_op.description,
            "target": target_summary[:10] + "." if len(target_summary) > 10 else target_summary,
            "result_data_type": data_type_summary,
            "status": status_summary,
            "time": f"{meta_op.total_execution_time:.3f}" if meta_op.total_execution_time else "0.000",
            "start_time": meta_op.start_time or 0,
        }

    def _create_meta_operation_header_row(self, meta_op: MetaOperation) -> Dict:
        """
        Create header row for expanded meta-operation view.

        Args:
            meta_op: MetaOperation instance

        Returns:
            Dict: Row data for header representation
        """
        first_step = min(op.step_number for op in meta_op.sub_operations)
        symbol = "◣"  # Expanded view symbol

        return {
            "step": f"{symbol} {first_step}",
            "sub_operation": f"◣ {meta_op.description}",
            "target": meta_op.get_targets_summary(),
            "result_data_type": meta_op.get_data_types_summary(),
            "status": meta_op.get_status_summary(),
            "time": f"{meta_op.total_execution_time:.3f}" if meta_op.total_execution_time else "0.000",
            "start_time": meta_op.start_time or 0,
        }

    def _create_indented_operation_row(self, sub_op: SubOperationLog, is_last: bool = False) -> Dict:
        """
        Create indented row for individual operation within meta-operation.

        Args:
            sub_op: SubOperationLog instance
            is_last: Whether this is the last operation in the group

        Returns:
            Dict: Row data for indented representation
        """
        indent = " " * self.config.indent_size
        branch_symbol = "└" if is_last else "├"

        return {
            "step": f"{indent}{branch_symbol}",
            "sub_operation": sub_op.operation_name,
            "target": sub_op.target,
            "result_data_type": sub_op.data_type,
            "status": sub_op.status,
            "time": f"{sub_op.execution_time:.3f}" if sub_op.execution_time else "0.000",
            "start_time": sub_op.start_time,
        }

    def _format_single_operation_row(self, sub_op: SubOperationLog) -> Dict:
        """
        Format a single operation that's not part of any meta-operation.

        Args:
            sub_op: SubOperationLog instance

        Returns:
            Dict: Row data for single operation
        """
        return {
            "step": str(sub_op.step_number),
            "sub_operation": sub_op.operation_name,
            "target": sub_op.target,
            "result_data_type": sub_op.data_type,
            "status": sub_op.status,
            "time": f"{sub_op.execution_time:.3f}" if sub_op.execution_time else "0.000",
            "start_time": sub_op.start_time,
        }

    def _build_table_from_rows(self, table_rows: List[Dict]) -> str:
        """
        Build final table from prepared row data.

        Args:
            table_rows: List of row dictionaries

        Returns:
            str: Formatted table string
        """
        if not table_rows:
            return "No operations recorded."

        # Prepare data for tabulate
        headers = ["Step", "Sub-operation", "Target", "Result data type", "Status", "Time, s"]

        table_data = []
        for row in table_rows:
            table_data.append(
                [row["step"], row["sub_operation"], row["target"], row["result_data_type"], row["status"], row["time"]]
            )

        # Format table
        try:
            return tabulate(
                table_data,
                headers=headers,
                tablefmt=self.config.table_format,
                maxcolwidths=[8, self.config.max_cell_width, 10, 20, 10, 11],
            )
        except Exception:
            # Fallback to simple format
            return self._format_simple_table(table_data, headers)


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
