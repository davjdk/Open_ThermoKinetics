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
from typing import Any, Dict, List, Optional

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
    - Meta-operations grouping and visualization
    """

    def __init__(
        self,
        config: FormatterConfig = None,
        table_format: str = "grid",
        max_cell_width: int = 50,
        include_error_details: bool = True,
        max_error_context_items: int = 5,
        minimalist_mode: bool = False,
        formatting_config: Optional[Dict] = None,
    ):
        """
        Initialize the table formatter.

        Args:
            config: FormatterConfig instance for meta-operations support
            table_format: Tabulate table format (grid, plain, simple, etc.)
            max_cell_width: Maximum width for table cells to prevent overly wide output
            include_error_details: Whether to include detailed error blocks
            max_error_context_items: Maximum number of context items to display
            minimalist_mode: Whether to use minimalist formatting mode
            formatting_config: Optional configuration dictionary for header formatting
        """

        # Store minimalist mode setting
        self.minimalist_mode = minimalist_mode  # Load formatting configuration
        if formatting_config is None:
            from .meta_operation_config import META_OPERATION_CONFIG

            self._formatting_config = META_OPERATION_CONFIG["formatting"].copy()
        else:
            self._formatting_config = formatting_config.copy()

        # Validate formatting configuration
        from .meta_operation_config import validate_formatting_config

        self._formatting_config = validate_formatting_config(self._formatting_config)

        # Apply minimalist settings if enabled
        if minimalist_mode or self._formatting_config.get("mode") == "minimalist":
            from .meta_operation_config import META_OPERATION_CONFIG

            minimalist_settings = META_OPERATION_CONFIG.get("minimalist_settings", {})
            self._formatting_config.update(minimalist_settings)
            # Re-validate after applying minimalist settings
            self._formatting_config = validate_formatting_config(self._formatting_config)

        # Use config if provided, otherwise create default with legacy parameters
        if config is not None:
            self.config = config
        else:  # Use table_format from configuration if in minimalist mode
            effective_table_format = (
                self._formatting_config.get("table_format", table_format) if minimalist_mode else table_format
            )
            self.config = FormatterConfig(
                table_format=effective_table_format,
                max_cell_width=max_cell_width,
                include_error_details=include_error_details,
                max_error_context_items=max_error_context_items,
            )  # Legacy compatibility
        self.table_format = self.config.table_format
        self.max_cell_width = self.config.max_cell_width
        self.include_error_details = self.config.include_error_details
        self.max_error_context_items = self.config.max_error_context_items
        self._operation_counter = 0  # Simple counter for unique operation IDs

    def format_operation_log(self, operation_log: OperationLog) -> str:  # noqa: C901
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

        # Check if decorative borders should be shown
        show_borders = self._formatting_config.get("show_decorative_borders", True)

        # 1. Header separator (only in standard mode)
        if show_borders:
            parts.append("=" * 80)

        # 2. Operation header
        header = self._format_operation_header(operation_log, operation_id)
        parts.append(header)

        # Empty line after header (only in standard mode)
        if show_borders:
            parts.append("")  # Empty line# 3. Sub-operations table (with meta-operations support)
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
        parts.append(summary)  # 6. Footer separator (only in standard mode)
        show_footer = self._formatting_config.get("show_completion_footer", True)
        if show_footer:
            footer = self._format_operation_footer(operation_log)
            parts.append(footer)

            if show_borders:
                parts.append("=" * 80)

        # Add table separator in minimalist mode instead of footer
        if not show_footer:
            separator = self._formatting_config.get("table_separator", "")
            if separator:
                parts.append(separator)

        return "\n".join(parts)

    def _format_operation_header(self, operation_log: OperationLog, operation_id: int) -> str:
        """
        Format the operation header with name, ID, and start timestamp.

        Supports both standard and minimalist header formats based on configuration.

        Args:
            operation_log: The operation log data
            operation_id: Unique operation identifier

        Returns:
            str: Formatted header string
        """
        start_time = datetime.fromtimestamp(operation_log.start_time or time.time())
        timestamp_str = start_time.strftime("%Y-%m-%d %H:%M:%S")  # Determine header format from configuration
        header_format = self._formatting_config.get("header_format", "standard")

        if header_format == "source_based" and operation_log.source_module and operation_log.source_line:
            # Minimalist format: module.py:line "OPERATION" (id=X, timestamp)
            source_info = self._format_source_info(operation_log)
            return f'{source_info} "{operation_log.operation_name}" (id={operation_id}, {timestamp_str})'
        else:
            # Standard format: Operation "NAME" – STARTED (id=X, timestamp)
            return f'Operation "{operation_log.operation_name}" – STARTED (id={operation_id}, {timestamp_str})'

    def _format_source_info(self, operation_log: OperationLog) -> str:
        """
        Format source information (module and line number) for minimalist headers.

        Args:
            operation_log: The operation log data

        Returns:
            str: Formatted source info string
        """
        if not operation_log.source_module or not operation_log.source_line:
            return "unknown:0"

        # Truncate long module names for readability
        module_name = operation_log.source_module
        if len(module_name) > 25:  # Limit for readability
            module_name = "..." + module_name[-22:]

        return f"{module_name}:{operation_log.source_line}"

    def _should_use_minimalist_header(self) -> bool:
        """
        Determine if minimalist header format should be used.

        Returns:
            bool: True if minimalist header should be used
        """
        return (
            self._formatting_config.get("mode") == "minimalist"
            or self._formatting_config.get("header_format") == "source_based"
        )

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

        # Determine table format based on configuration
        table_format = self._get_table_format()

        try:
            formatted_table = tabulate(
                table_data, headers=headers, tablefmt=table_format, colalign=column_alignment, floatfmt=".3f"
            )
            return formatted_table
        except Exception:
            # Fallback to simple formatting if tabulate fails
            return self._format_simple_table(headers, table_data)

    def _get_table_format(self) -> str:
        """Determine table format based on configuration."""
        if self._formatting_config.get("mode") == "minimalist":
            return "pipe"  # Minimalist format using pipe symbols
        else:
            return self._formatting_config.get("table_format", self.table_format)  # Standard format

    def _format_operation_summary(self, operation_log: OperationLog, operation_id: int) -> str:
        """
        Format the operation summary with statistics.

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

        return stats_line

    def _format_operation_footer(self, operation_log: OperationLog) -> str:
        """
        Format the operation footer with completion status.

        Args:
            operation_log: The operation log data

        Returns:
            str: Formatted footer string
        """
        # Format completion line with status
        status_text = "successful" if operation_log.status == "success" else "with error"
        completion_line = f'Operation "{operation_log.operation_name}" – COMPLETED (status: {status_text})'

        return completion_line

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
        Format meta-operations summary for display with specialized formatters.

        Args:
            meta_operations: List of MetaOperation objects

        Returns:
            str: Formatted meta-operations summary
        """
        if not meta_operations:
            return ""

        lines = ["META-OPERATIONS DETECTED:"]

        for i, meta_op in enumerate(meta_operations, 1):
            # Use specialized formatter if available
            formatter = self._get_meta_operation_formatter(meta_op)

            if formatter == self._format_base_signals_burst_meta_operation:
                # Use BaseSignalsMetaBurst formatter
                specialized_lines = formatter(meta_op)
                lines.extend(specialized_lines)
            else:
                # Use generic formatting
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

    def _get_meta_operation_formatter(self, meta_operation: "MetaOperation") -> callable:
        """
        Return appropriate formatter for meta-operation.

        Args:
            meta_operation: Meta-operation to format

        Returns:
            callable: Formatting method
        """
        if meta_operation.meta_id.startswith("base_signals_burst_"):
            return self._format_base_signals_burst_meta_operation
        elif meta_operation.meta_id.startswith("time_window_"):
            return self._format_time_window_meta_operation
        else:
            return self._format_generic_meta_operation

    def _format_base_signals_burst_meta_operation(self, meta_operation: "MetaOperation") -> List[str]:
        """
        Specialized formatting for BaseSignalsMetaBurst.

        Args:
            meta_operation: Meta-operation of BaseSignalsMetaBurst type

        Returns:
            List[str]: Formatted lines
        """
        # Check that this is actually BaseSignalsMetaBurst
        if not meta_operation.meta_id.startswith("base_signals_burst_"):
            return self._format_generic_meta_operation(meta_operation)

        # Get configuration for BaseSignalsMetaBurst
        config = self.config.base_signals_burst if hasattr(self.config, "base_signals_burst") else {}

        # Create specialized formatter
        burst_formatter = BaseSignalsBurstFormatter(config)

        # Format cluster
        return burst_formatter.format_cluster(meta_operation, self)

    def _format_time_window_meta_operation(self, meta_operation: "MetaOperation") -> List[str]:
        """Format time window meta-operation (placeholder for existing logic)."""
        # This can be extended later for specific time window formatting
        return self._format_generic_meta_operation(meta_operation)

    def _format_generic_meta_operation(self, meta_operation: "MetaOperation") -> List[str]:
        """
        Generic formatting for meta-operations.

        Args:
            meta_operation: Meta-operation to format

        Returns:
            List[str]: Formatted lines
        """
        lines = []

        # Basic meta-operation info
        description = meta_operation.description or meta_operation.strategy_name
        lines.append(f"► {description} ({len(meta_operation.sub_operations)} operations)")

        # Show operations if not too many
        if len(meta_operation.sub_operations) <= 10:
            for i, sub_op in enumerate(meta_operation.sub_operations, 1):
                op_line = f"  {i}. {sub_op.operation_name} → {sub_op.target} ({sub_op.status})"
                lines.append(op_line)

        return lines


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


class BaseSignalsBurstFormatter:
    """
    Specialized formatter for displaying BaseSignalsMetaBurst clusters.

    This formatter provides enhanced display capabilities for BaseSignals operation
    clusters with proper noise operation marking and detailed summary information.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the BaseSignalsBurst formatter.

        Args:
            config: Configuration dictionary for BaseSignalsMetaBurst formatting
        """
        self.config = config
        self.noise_marker = config.get("noise_marker", "[*]")
        self.show_noise_markers = config.get("show_noise_markers", True)

    def format_cluster(self, meta_operation: "MetaOperation", table_formatter: "OperationTableFormatter") -> List[str]:
        """
        Format BaseSignalsMetaBurst cluster for output.

        Args:
            meta_operation: Meta-operation to format
            table_formatter: Main table formatter instance

        Returns:
            List[str]: Formatted cluster lines
        """
        lines = []

        # Cluster header
        header = self._format_cluster_header(meta_operation)
        lines.append(header)

        # Detailed operations (if not collapsed)
        if not self._is_collapsed(meta_operation):
            detail_lines = self._format_cluster_details(meta_operation, table_formatter)
            lines.extend(detail_lines)

        # Cluster summary
        if self.config.get("show_detailed_summary", True):
            summary = self._format_cluster_summary(meta_operation)
            lines.append(summary)

        return lines

    def _format_cluster_header(self, meta_operation: "MetaOperation") -> str:
        """Format cluster header with visual markers."""
        # Use description from strategy
        description = meta_operation.description or "BaseSignalsBurst"

        # Add visual markers
        cluster_id = meta_operation.meta_id.split("_")[-1]  # Last part of ID
        header = f"⚡ [{cluster_id}] {description}"

        return header

    def _format_cluster_details(
        self, meta_operation: "MetaOperation", table_formatter: "OperationTableFormatter"
    ) -> List[str]:
        """Format detailed list of cluster operations."""
        lines = []

        # Sort operations by time/step
        sorted_operations = sorted(meta_operation.sub_operations, key=lambda x: x.step_number)

        for i, sub_op in enumerate(sorted_operations, 1):
            # Determine if operation is noise
            is_noise = not self._is_base_signals_operation(sub_op)

            # Format operation line
            op_line = self._format_sub_operation(sub_op, i, is_noise, table_formatter)
            lines.append(op_line)

        return lines

    def _format_sub_operation(
        self, sub_op: "SubOperationLog", index: int, is_noise: bool, table_formatter: "OperationTableFormatter"
    ) -> str:
        """Format individual sub-operation with noise markers."""
        # Get basic formatting through main formatter
        basic_data = {
            "step": sub_op.step_number,
            "operation": str(sub_op.operation_name)[:20] + "..."
            if len(str(sub_op.operation_name)) > 20
            else str(sub_op.operation_name),
            "target": str(sub_op.target),
            "data_type": sub_op.result_data_type,
            "status": sub_op.status,
            "duration": f"{sub_op.duration_ms:.3f}" if sub_op.duration_ms else "0.000",
        }  # Format as basic table row
        base_format = (
            f"{basic_data['operation']:<20} | {basic_data['target']:<10} | "
            f"{basic_data['data_type']:<15} | {basic_data['status']:<8} | {basic_data['duration']:>8}s"
        )

        # Add indentation and markers
        indent = "    "  # Indentation for sub-operations

        if is_noise and self.show_noise_markers:
            # Add noise marker
            noise_marker = f"{self.noise_marker} "
            formatted_line = f"{indent}{index:2d}. {noise_marker}{base_format}"
        else:
            formatted_line = f"{indent}{index:2d}. {base_format}"

        return formatted_line

    def _format_cluster_summary(self, meta_operation: "MetaOperation") -> str:
        """Format cluster summary with statistics."""
        operations = meta_operation.sub_operations

        # Calculate statistics
        total_ops = len(operations)
        base_signals_ops = sum(1 for op in operations if self._is_base_signals_operation(op))
        noise_ops = total_ops - base_signals_ops

        # Calculate timing
        if operations:
            start_times = [op.start_time for op in operations if op.start_time]
            end_times = [op.end_time or op.start_time for op in operations if op.start_time]
            if start_times and end_times:
                start_time = min(start_times)
                end_time = max(end_times)
                duration_ms = int((end_time - start_time) * 1000) if start_time and end_time else 0
            else:
                duration_ms = 0
        else:
            duration_ms = 0

        # Form summary
        summary_parts = [
            f"Итого: {total_ops} операций",
            f"base_signals: {base_signals_ops}",
        ]

        if noise_ops > 0:
            summary_parts.append(f"шум: {noise_ops}")

        summary_parts.append(f"время: {duration_ms} мс")

        summary = f"    └─ {', '.join(summary_parts)}"
        return summary

    def _is_base_signals_operation(self, sub_op: "SubOperationLog") -> bool:
        """Check if operation is a base_signals operation."""
        # Use same logic as in strategy
        return (
            sub_op.target == "base_signals"
            or "base_signals" in str(sub_op.target).lower()
            or "signal" in sub_op.operation_name.lower()
            if sub_op.operation_name
            else False
        )

    def _is_collapsed(self, meta_operation: "MetaOperation") -> bool:
        """Determine if cluster should be collapsed."""
        return self.config.get("collapsed_by_default", True)

    def format_compact_base_signals_burst(self, meta_operation: "MetaOperation") -> str:
        """Compact display of BaseSignalsMetaBurst."""
        description = meta_operation.description or "BaseSignalsBurst"
        op_count = len(meta_operation.sub_operations)

        return f"⚡ {description} ({op_count} ops)"

    def format_json_base_signals_burst(self, meta_operation: "MetaOperation") -> Dict[str, Any]:
        """JSON representation of BaseSignalsMetaBurst."""
        operations = meta_operation.sub_operations

        return {
            "type": "BaseSignalsMetaBurst",
            "meta_id": meta_operation.meta_id,
            "description": meta_operation.description,
            "statistics": {
                "total_operations": len(operations),
                "base_signals_operations": sum(1 for op in operations if self._is_base_signals_operation(op)),
                "noise_operations": sum(1 for op in operations if not self._is_base_signals_operation(op)),
                "duration_ms": self._calculate_duration_ms(operations),
            },
            "operations": [self._operation_to_dict(op) for op in operations],
        }

    def _calculate_duration_ms(self, operations: List["SubOperationLog"]) -> int:
        """Calculate total duration in milliseconds."""
        if not operations:
            return 0

        start_times = [op.start_time for op in operations if op.start_time]
        end_times = [op.end_time or op.start_time for op in operations if op.start_time]

        if start_times and end_times:
            start_time = min(start_times)
            end_time = max(end_times)
            return int((end_time - start_time) * 1000) if start_time and end_time else 0
        return 0

    def _operation_to_dict(self, sub_op: "SubOperationLog") -> Dict[str, Any]:
        """Convert SubOperationLog to dictionary."""
        return {
            "step_number": sub_op.step_number,
            "operation_name": sub_op.operation_name,
            "target": sub_op.target,
            "result_data_type": sub_op.result_data_type,
            "status": sub_op.status,
            "duration_ms": sub_op.duration_ms,
            "is_base_signals": self._is_base_signals_operation(sub_op),
        }

    def apply_noise_styling(self, operation_text: str, is_noise: bool) -> str:
        """
        Apply styling for noise operations.

        Args:
            operation_text: Original operation text
            is_noise: Whether operation is noise

        Returns:
            str: Styled text
        """
        if not is_noise or not self.config.get("show_noise_markers", True):
            return operation_text

        marker_style = self.config.get("noise_marker_style", "asterisk")
        from .formatter_config import NOISE_MARKER_STYLES

        marker = NOISE_MARKER_STYLES.get(marker_style, "[*]")

        # Additional styling (color, italic) if supported by terminal
        if self.config.get("use_color", False):
            return f"\033[90m{marker}\033[0m {operation_text}"  # Gray color
        else:
            return f"{marker} {operation_text}"
