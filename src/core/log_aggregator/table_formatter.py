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
from typing import Dict, List, Optional

from tabulate import tabulate

from .base_signals_formatter import BaseSignalsBurstFormatter
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

        # Initialize BaseSignals formatter for specialized formatting
        self.base_signals_formatter = BaseSignalsBurstFormatter(self._formatting_config.get("base_signals_burst", {}))

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

    def _format_error_details_block(self, operation_log: OperationLog) -> str:
        """
        Format detailed error information for sub-operations with errors.

        Args:
            operation_log: The operation log data        Returns:
            str: Formatted error details block
        """
        error_sub_operations = [
            sub_op
            for sub_op in operation_log.sub_operations
            if sub_op.status == "Error" and hasattr(sub_op, "error_details") and sub_op.error_details
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
            str: Formatted error information
        """
        if not hasattr(sub_operation, "error_details") or not sub_operation.error_details:
            return (
                f"Step {sub_operation.step_number}: {sub_operation.clean_operation_name} → "
                f"{sub_operation.target}\n  Error: {getattr(sub_operation, 'error_message', 'Unknown error')}"
            )

        error_details = sub_operation.error_details
        lines = []

        # Header line
        lines.append(f"Step {sub_operation.step_number}: {sub_operation.clean_operation_name} → {sub_operation.target}")

        # Error details
        if isinstance(error_details, dict):
            for key, value in error_details.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append(f"  Error: {error_details}")

        return "\n".join(lines)

    def _format_meta_operations_summary(self, meta_operations) -> str:
        """
        Format meta-operations summary for display with BaseSignals support.

        Args:
            meta_operations: List of MetaOperation objects

        Returns:
            str: Formatted meta-operations summary
        """
        if not meta_operations:
            return ""

        lines = ["META-OPERATIONS DETECTED:"]

        for i, meta_op in enumerate(meta_operations, 1):
            if meta_op.strategy_name == "BaseSignalsBurst":
                lines.append(self._format_base_signals_meta_summary(i, meta_op))
            else:
                lines.append(self._format_generic_meta_summary(i, meta_op))

        return "\n".join(lines)

    def _format_base_signals_meta_summary(self, index: int, meta_op: MetaOperation) -> str:
        """Specialized formatting for BaseSignals burst summary."""
        # Use the specialized formatter for enhanced display
        return self.base_signals_formatter.format_with_visual_indicators(meta_op)

    def _format_generic_meta_summary(self, index: int, meta_op: MetaOperation) -> str:
        """Generic formatting for non-BaseSignals meta operations."""
        duration_ms = meta_op.duration_ms or 0

        success_rate = (
            (meta_op.successful_operations_count / meta_op.operations_count * 100)
            if meta_op.operations_count > 0
            else 0
        )

        summary_line = (
            f"  {index}. {meta_op.name} ({meta_op.strategy_name}): "
            f"{meta_op.operations_count} ops, {duration_ms:.1f}ms, "
            f"{success_rate:.0f}% success"
        )  # Operation details (compact)
        if meta_op.sub_operations:
            step_numbers = [str(op.step_number) for op in meta_op.sub_operations]
            if len(step_numbers) <= 5:
                steps_text = ", ".join(step_numbers)
            else:
                steps_text = f"{', '.join(step_numbers[:3])}, ... {len(step_numbers)-3} more"
            summary_line += f"\n     Steps: {steps_text}"

        return summary_line

    def _extract_burst_type(self, meta_op: MetaOperation) -> str:
        """Extract burst type from meta operation."""
        if hasattr(meta_op, "description") and meta_op.description:
            description = meta_op.description
            if "Parameter_Update_Burst" in description:
                return "Parameter Update Burst"
            elif "Add_Reaction_Burst" in description:
                return "Add Reaction Burst"
            elif "Highlight_Reaction_Burst" in description:
                return "Highlight Reaction Burst"
            elif "Generic_Signal_Burst" in description:
                return "Generic Signal Burst"

        # Fallback to analyzing operation names
        if hasattr(meta_op, "operations") and meta_op.operations:
            operation_names = [op.operation_name for op in meta_op.operations]
            if any("UPDATE_VALUE" in str(name) for name in operation_names):
                return "Parameter Update Burst"
            elif operation_names.count("SET_VALUE") >= 2:
                return "Add Reaction Burst"

        return "BaseSignals Burst"

    def _extract_real_actor(self, meta_op: MetaOperation) -> str:
        """Extract real actor from meta operation context."""
        if hasattr(meta_op, "description") and meta_op.description:
            # Look for (from actor) pattern in description
            if "(from " in meta_op.description and ")" in meta_op.description:
                start = meta_op.description.find("(from ") + 6
                end = meta_op.description.find(")", start)
                if end > start:
                    return meta_op.description[start:end]

        # Look for real actor in operations context
        if hasattr(meta_op, "operations") and meta_op.operations:
            for op in meta_op.operations:
                if hasattr(op, "caller_info") and op.caller_info:
                    caller = op.caller_info
                    if isinstance(caller, dict):
                        filename = caller.get("filename", "")
                        lineno = caller.get("lineno", 0)
                        if filename and lineno:
                            return f"{filename}:{lineno}"
                    elif isinstance(caller, str) and caller != "base_signals.py:51":
                        return caller

        return ""

    def _extract_duration_from_summary(self, summary: str) -> str:
        """Extract duration information from summary string."""
        if not summary:
            return ""

        # Look for patterns like "3 мс", "45.0ms", "0.003s"
        import re

        # Match milliseconds patterns
        ms_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:мс|ms)", summary)
        if ms_match:
            ms_value = float(ms_match.group(1))
            return f"{ms_value:.1f}ms"

        # Match seconds patterns
        s_match = re.search(r"(\d+(?:\.\d+)?)\s*[sс]", summary)
        if s_match:
            s_value = float(s_match.group(1))
            return f"{s_value * 1000:.1f}ms"

        return ""

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
        Format rows for a single meta-operation with BaseSignals support.

        Args:
            meta_op: MetaOperation instance to format

        Returns:
            List[Dict]: List of table row dictionaries
        """
        rows = []

        if meta_op.strategy_name == "BaseSignalsBurst":
            rows.extend(self._format_base_signals_burst_rows(meta_op))
        elif self.config.compact_meta_view:
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

    def _format_base_signals_burst_rows(self, meta_op: MetaOperation) -> List[Dict]:
        """Format BaseSignals burst with specialized representation."""
        rows = []

        # Determine if we should use compact or expanded format
        operations_count = len(meta_op.operations)
        use_compact = (
            operations_count <= self._formatting_config.get("base_signals_burst", {}).get("expand_threshold", 5)
            or self._formatting_config.get("base_signals_burst", {}).get("default_view") == "compact"
        )

        if use_compact:
            # Compact format: single row with aggregated info
            rows.append(self._create_base_signals_summary_row(meta_op))
        else:
            # Expanded format: header + individual operations
            rows.append(self._create_base_signals_header_row(meta_op))
            for i, sub_op in enumerate(meta_op.operations):
                is_last = i == len(meta_op.operations) - 1
                rows.append(self._create_base_signals_operation_row(sub_op, is_last))

        return rows

    def _create_base_signals_summary_row(self, meta_op: MetaOperation) -> Dict:
        """Create compact summary row for BaseSignals burst."""
        if not meta_op.operations:
            return {
                "Step": "?",
                "Sub-operation": "⚡ Empty BaseSignals Burst",
                "Target": "unknown",
                "Result data type": "unknown",
                "Status": "Empty",
                "Time, s": 0.0,
                "start_time": 0,
            }

        # Aggregate information
        first_step = min(op.step_number for op in meta_op.operations)
        last_step = max(op.step_number for op in meta_op.operations)
        step_range = f"► {first_step}-{last_step}" if first_step != last_step else f"► {first_step}"

        burst_type = self._extract_burst_type(meta_op)

        # Target distribution
        targets = list({op.target for op in meta_op.operations})
        target_display = "mixed" if len(targets) > 1 else targets[0] if targets else "unknown"

        # Status aggregation
        all_success = all(op.status == "OK" for op in meta_op.operations)
        status = "OK" if all_success else "Mixed"

        # Duration calculation
        total_duration = sum(op.duration_ms or 0 for op in meta_op.operations) / 1000.0

        return {
            "Step": step_range,
            "Sub-operation": f"{burst_type} ({len(meta_op.operations)} ops)",
            "Target": target_display,
            "Result data type": "mixed",
            "Status": status,
            "Time, s": f"{total_duration:.3f}",
            "start_time": min(op.start_time for op in meta_op.operations),
            "is_meta": True,
            "expandable": True,
            "meta_operations": meta_op.operations,
        }

    def _create_base_signals_header_row(self, meta_op: MetaOperation) -> Dict:
        """Create header row for expanded BaseSignals burst."""
        burst_type = self._extract_burst_type(meta_op)
        real_actor = self._extract_real_actor(meta_op)

        header_text = f">>> {burst_type} (Meta-cluster: BaseSignalsBurst)"
        if real_actor:
            header_text += f" from {real_actor}"

        return {
            "Step": "",
            "Sub-operation": header_text,
            "Target": "",
            "Result data type": "",
            "Status": "",
            "Time, s": "",
            "start_time": min(op.start_time for op in meta_op.operations) if meta_op.operations else 0,
            "is_header": True,
        }

    def _create_base_signals_operation_row(self, sub_op: SubOperationLog, is_last: bool = False) -> Dict:
        """Create individual operation row for BaseSignals burst."""
        # Use base signals shortened target name
        target_display = "base_sig" if "base_signals" in str(sub_op.target) else sub_op.target

        return {
            "Step": str(sub_op.step_number),
            "Sub-operation": sub_op.clean_operation_name,
            "Target": target_display,
            "Result data type": sub_op.data_type,
            "Status": sub_op.status,
            "Time, s": f"{sub_op.execution_time:.3f}",
            "start_time": sub_op.start_time,
            "is_indented": True,
        }

    def format_base_signals_burst_json(self, meta_operation: MetaOperation) -> Dict:
        """JSON representation of BaseSignals burst for API integration."""
        operations = meta_operation.operations if hasattr(meta_operation, "operations") else []

        return {
            "meta_id": meta_operation.meta_id,
            "strategy": "BaseSignalsBurst",
            "burst_type": self._determine_burst_type_from_operations(operations),
            "real_actor": self._extract_real_actor(meta_operation),
            "summary": meta_operation.summary if hasattr(meta_operation, "summary") else "",
            "metrics": {
                "operation_count": len(operations),
                "duration_ms": self._calculate_total_duration(operations),
                "target_distribution": self._calculate_target_distribution(operations),
                "temporal_characteristics": self._calculate_temporal_characteristics(operations),
            },
            "operations": [
                {
                    "step": op.step_number,
                    "operation": op.operation_name,
                    "target": op.target,
                    "duration_ms": op.duration_ms or 0,
                    "status": op.status,
                    "timestamp": op.start_time,
                }
                for op in operations
            ],
        }

    def _determine_burst_type_from_operations(self, operations: List) -> str:
        """Determine burst type from operation patterns."""
        if not operations:
            return "Empty_Burst"

        operation_names = [op.operation_name for op in operations if hasattr(op, "operation_name")]

        # Parameter Update pattern
        if any("UPDATE_VALUE" in str(name) for name in operation_names):
            return "Parameter_Update_Burst"

        # Add Reaction pattern
        if operation_names.count("SET_VALUE") >= 2 and "UPDATE_VALUE" in str(operation_names):
            return "Add_Reaction_Burst"

        # Highlight pattern
        if any("GET_DF_DATA" in str(name) for name in operation_names) and any(
            "HIGHLIGHT" in str(name) for name in operation_names
        ):
            return "Highlight_Reaction_Burst"

        return "Generic_Signal_Burst"

    def _calculate_total_duration(self, operations: List) -> float:
        """Calculate total duration of operations in milliseconds."""
        return sum(getattr(op, "duration_ms", 0) or 0 for op in operations)

    def _calculate_target_distribution(self, operations: List) -> Dict[str, int]:
        """Calculate distribution of operations by target."""
        targets = {}
        for op in operations:
            if hasattr(op, "target"):
                target = op.target
                targets[target] = targets.get(target, 0) + 1
        return targets

    def _calculate_temporal_characteristics(self, operations: List) -> Dict:
        """Calculate temporal characteristics of the operations."""
        if not operations:
            return {}

        start_times = [getattr(op, "start_time", 0) for op in operations if hasattr(op, "start_time")]
        if not start_times:
            return {}

        min_time = min(start_times)
        max_time = max(start_times)
        total_span = (max_time - min_time) * 1000  # Convert to ms

        # Calculate gaps between consecutive operations
        start_times.sort()
        gaps = [(start_times[i + 1] - start_times[i]) * 1000 for i in range(len(start_times) - 1)]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0

        return {
            "total_span_ms": total_span,
            "average_gap_ms": avg_gap,
            "max_gap_ms": max_gap,
            "operations_per_second": len(operations) / (total_span / 1000) if total_span > 0 else 0,
        }

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
                "start_time": 0,
            }

        # Get first step number in group
        first_step = min(op.step_number for op in meta_op.sub_operations)

        # Aggregate data
        targets = list({op.target for op in meta_op.sub_operations})
        data_types = list({op.data_type for op in meta_op.sub_operations})
        statuses = list({op.status for op in meta_op.sub_operations})

        # Calculate duration
        total_duration = sum(op.execution_time for op in meta_op.sub_operations)

        # Format aggregated values
        target_display = "mixed" if len(targets) > 1 else targets[0] if targets else "unknown"
        data_type_display = "mixed" if len(data_types) > 1 else data_types[0] if data_types else "unknown"
        status_display = "OK" if all(s == "OK" for s in statuses) else "Mixed"

        return {
            "Step": f"► {first_step}-{first_step + len(meta_op.sub_operations) - 1}",
            "Sub-operation": f"{self.config.meta_operation_symbol} {meta_op.name} ({len(meta_op.sub_operations)} ops)",
            "Target": target_display,
            "Result data type": data_type_display,
            "Status": status_display,
            "Time, s": f"{total_duration:.3f}",
            "start_time": min(op.start_time for op in meta_op.sub_operations),
        }

    def _create_indented_operation_row(self, sub_op: SubOperationLog, is_last: bool = False) -> Dict:
        """Create indented row for operation within meta-operation."""
        return {
            "Step": f"  {sub_op.step_number}",
            "Sub-operation": f"  {sub_op.clean_operation_name}",
            "Target": sub_op.target,
            "Result data type": sub_op.data_type,
            "Status": sub_op.status,
            "Time, s": f"{sub_op.execution_time:.3f}",
            "start_time": sub_op.start_time,
        }

    def _create_meta_operation_header_row(self, meta_op: MetaOperation) -> Dict:
        """Create header row for meta-operation in expanded mode."""
        return {
            "Step": "",
            "Sub-operation": f">>> {meta_op.name} (Meta-cluster: {meta_op.strategy_name})",
            "Target": "",
            "Result data type": "",
            "Status": "",
            "Time, s": "",
            "start_time": min(op.start_time for op in meta_op.sub_operations) if meta_op.sub_operations else 0,
            "is_header": True,
        }

    def _build_table_from_rows(self, table_rows: List[Dict]) -> str:
        """Build formatted table from row dictionaries."""
        if not table_rows:
            return "No operations recorded."

        # Convert to tabulate format
        headers = ["Step", "Sub-operation", "Target", "Result data type", "Status", "Time, s"]
        table_data = []

        for row in table_rows:
            table_data.append(
                [
                    row.get("Step", ""),
                    row.get("Sub-operation", ""),
                    row.get("Target", ""),
                    row.get("Result data type", ""),
                    row.get("Status", ""),
                    row.get("Time, s", ""),
                ]
            )

        return tabulate(table_data, headers=headers, tablefmt=self.table_format, stralign="left")

    def _format_single_operation_row(self, sub_op: SubOperationLog) -> Dict:
        """Format a single operation that's not part of a meta-operation."""
        return {
            "Step": str(sub_op.step_number),
            "Sub-operation": sub_op.clean_operation_name,
            "Target": sub_op.target,
            "Result data type": sub_op.data_type,
            "Status": sub_op.status,
            "Time, s": f"{sub_op.execution_time:.3f}",
            "start_time": sub_op.start_time,
        }


def format_operation_log(operation_log: OperationLog, config: Optional[FormatterConfig] = None, **kwargs) -> str:
    """
    Standalone function for formatting operation logs with BaseSignals support.

    Args:
        operation_log: The operation log to format
        config: Optional formatter configuration
        **kwargs: Additional formatting options

    Returns:
        str: Formatted operation log
    """
    formatter = OperationTableFormatter(config=config, **kwargs)
    return formatter.format_operation_log(operation_log)
