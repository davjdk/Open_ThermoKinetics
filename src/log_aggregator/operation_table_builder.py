"""
Operation table builder for converting operation metrics into structured tabular representation.

This module provides functionality for creating formatted tables from operation metrics,
supporting various table types and formatting options for different use cases.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .operation_monitor import OperationMetrics, OperationStatus


@dataclass
class OperationTableData:
    """Data structure for tabular representation of operation."""

    title: str
    """Table title"""

    headers: List[str]
    """Column headers"""

    rows: List[List[str]]
    """Table rows (each row is a list of cell values)"""

    summary: Optional[str] = None
    """Optional table summary/footer"""

    table_type: str = "operation_summary"
    """Type of table (operation_summary, metrics_detail, performance, etc.)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for table rendering"""


class OperationTableBuilder:
    """Builder for creating structured tables from operation metrics."""

    # Base columns for operation tables
    BASE_COLUMNS = [
        "Sub-Operation",  # Operation name
        "Start Time",  # Start time (HH:MM:SS)
        "Duration (s)",  # Duration in seconds
        "Component",  # Component executing operation
        "Status",  # Status (✅/⚠️/❌)
    ]

    # Optional columns based on available metrics
    OPTIONAL_COLUMNS = {
        "request_count": "Requests",
        "response_count": "Responses",
        "mse_value": "MSE",
        "r_squared": "R²",
        "file_count": "Files",
        "reaction_count": "Reactions",
        "heating_rates": "Heat Rates",
        "cpu_usage_avg": "CPU %",
        "memory_usage_mb": "Memory MB",
        "convergence_value": "Convergence",
        "iterations": "Iterations",
        "method": "Method",
    }

    # Status icons
    STATUS_ICONS = {
        OperationStatus.COMPLETED: "✅",
        OperationStatus.FAILED: "❌",
        OperationStatus.TIMEOUT: "⏰",
        OperationStatus.RUNNING: "🔄",
        OperationStatus.PENDING: "⏳",
    }

    def __init__(self):
        """Initialize table builder."""
        self.date_format = "%H:%M:%S"
        self.float_precision = 3

    def build_operation_summary_table(
        self, operations: List[OperationMetrics], title: str = "Operation Summary"
    ) -> OperationTableData:
        """
        Build summary table for list of operations.

        Args:
            operations: List of operation metrics
            title: Table title

        Returns:
            OperationTableData with formatted operation summary
        """
        if not operations:
            return OperationTableData(
                title=title,
                headers=self.BASE_COLUMNS,
                rows=[["No operations found", "", "", "", ""]],
                summary="0 operations total",
            )

        # Determine which optional columns to include
        available_metrics = self._get_available_metrics(operations)
        headers = self.BASE_COLUMNS.copy()

        # Add optional columns if metrics are available
        for metric_key, column_name in self.OPTIONAL_COLUMNS.items():
            if metric_key in available_metrics:
                headers.append(column_name)

        # Build rows
        rows = []
        for op in operations:
            row = self._build_operation_row(op, headers)
            rows.append(row)

        # Build summary
        summary = self._build_summary(operations)

        return OperationTableData(
            title=title,
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="operation_summary",
            metadata={
                "total_operations": len(operations),
                "available_metrics": available_metrics,
                "date_format": self.date_format,
            },
        )

    def build_metrics_detail_table(
        self, operation: OperationMetrics, title: Optional[str] = None
    ) -> OperationTableData:
        """
        Build detailed metrics table for single operation.

        Args:
            operation: Operation metrics
            title: Optional table title

        Returns:
            OperationTableData with detailed metrics
        """
        if title is None:
            title = f"Detailed Metrics: {operation.operation_type}"

        headers = ["Metric", "Value"]
        rows = []

        # Basic operation info
        rows.append(["Operation ID", operation.operation_id])
        rows.append(["Operation Type", operation.operation_type])
        rows.append(["Module", operation.module])
        rows.append(["Status", self._format_status(operation.status)])

        if operation.start_time:
            rows.append(["Start Time", operation.start_time.strftime("%Y-%m-%d %H:%M:%S")])

        if operation.end_time:
            rows.append(["End Time", operation.end_time.strftime("%Y-%m-%d %H:%M:%S")])

        if operation.duration_ms is not None:
            rows.append(["Duration", f"{operation.duration_ms:.{self.float_precision}f} ms"])

        # Metrics
        rows.append(["Requests", str(operation.request_count)])
        rows.append(["Responses", str(operation.response_count)])
        rows.append(["Warnings", str(operation.warning_count)])
        rows.append(["Errors", str(operation.error_count)])

        if operation.memory_usage_mb is not None:
            rows.append(["Memory Usage", f"{operation.memory_usage_mb:.{self.float_precision}f} MB"])

        # Components involved
        if operation.components_involved:
            components = ", ".join(sorted(operation.components_involved))
            rows.append(["Components", components])

        # Sub-operations
        if operation.sub_operations:
            sub_ops = ", ".join(operation.sub_operations)
            rows.append(["Sub-Operations", sub_ops])

        # Custom metrics
        for key, value in operation.custom_metrics.items():
            formatted_value = self._format_metric_value(value)
            rows.append([f"Custom: {key}", formatted_value])

        # Error message if exists
        if operation.error_message:
            rows.append(["Error Message", operation.error_message])

        return OperationTableData(
            title=title,
            headers=headers,
            rows=rows,
            table_type="metrics_detail",
            metadata={"operation_id": operation.operation_id, "operation_type": operation.operation_type},
        )

    def build_performance_metrics_table(
        self, operations: List[OperationMetrics], title: str = "Performance Metrics"
    ) -> OperationTableData:
        """
        Build performance-focused table.

        Args:
            operations: List of operation metrics
            title: Table title

        Returns:
            OperationTableData with performance metrics
        """
        headers = ["Operation", "Duration (ms)", "Memory (MB)", "CPU %", "Status", "Efficiency"]

        rows = []
        for op in operations:
            duration = f"{op.duration_ms:.{self.float_precision}f}" if op.duration_ms else "N/A"
            memory = f"{op.memory_usage_mb:.1f}" if op.memory_usage_mb else "N/A"
            cpu = self._get_custom_metric_value(op, "cpu_usage_percent", "N/A")
            status = self._format_status(op.status)
            efficiency = self._calculate_efficiency_rating(op)

            rows.append([op.operation_type, duration, memory, cpu, status, efficiency])

        # Calculate summary statistics
        summary = self._build_performance_summary(operations)

        return OperationTableData(
            title=title,
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="performance_metrics",
            metadata={"total_operations": len(operations), "performance_focused": True},
        )

    def build_domain_specific_table(
        self, operations: List[OperationMetrics], domain: str = "solid_state_kinetics", title: Optional[str] = None
    ) -> OperationTableData:
        """
        Build domain-specific table for solid-state kinetics operations.

        Args:
            operations: List of operation metrics
            domain: Domain type (solid_state_kinetics, etc.)
            title: Optional table title

        Returns:
            OperationTableData with domain-specific formatting
        """
        if title is None:
            title = "Solid-State Kinetics Analysis"

        if domain == "solid_state_kinetics":
            return self._build_kinetics_table(operations, title)
        else:
            # Fallback to general operation summary
            return self.build_operation_summary_table(operations, title)

    def _build_kinetics_table(self, operations: List[OperationMetrics], title: str) -> OperationTableData:
        """Build table specific to solid-state kinetics analysis."""
        headers = ["Analysis Step", "Duration (s)", "Files/Reactions", "Quality Metrics", "Status"]

        rows = []
        for op in operations:
            duration = f"{op.duration_ms/1000:.{self.float_precision}f}" if op.duration_ms else "N/A"

            # Combine file and reaction counts
            file_count = self._get_custom_metric_value(op, "file_count", 0)
            reaction_count = self._get_custom_metric_value(op, "reaction_count", 0)
            files_reactions = f"{file_count}F/{reaction_count}R"

            # Combine quality metrics
            mse = self._get_custom_metric_value(op, "mse_value")
            r_squared = self._get_custom_metric_value(op, "r_squared")
            quality = ""
            if mse is not None and r_squared is not None:
                quality = f"MSE: {mse:.6f}, R²: {r_squared:.4f}"
            elif r_squared is not None:
                quality = f"R²: {r_squared:.4f}"
            elif mse is not None:
                quality = f"MSE: {mse:.6f}"
            else:
                quality = "N/A"

            status = self._format_status(op.status)

            rows.append([op.operation_type, duration, files_reactions, quality, status])

        # Build kinetics-specific summary
        summary = self._build_kinetics_summary(operations)

        return OperationTableData(
            title=title,
            headers=headers,
            rows=rows,
            summary=summary,
            table_type="domain_specific",
            metadata={"domain": "solid_state_kinetics", "total_operations": len(operations)},
        )

    def build_tables(self, operations: List[OperationMetrics]) -> List[OperationTableData]:
        """
        Build all relevant tables for a given list of operations.

        Args:
            operations: List of operation metrics

        Returns:
            List of OperationTableData (summary, performance, domain-specific)
        """
        tables = []
        # General operation summary table
        tables.append(self.build_operation_summary_table(operations, title="Operation Summary"))
        # Performance metrics table
        tables.append(self.build_performance_metrics_table(operations, title="Performance Metrics"))
        # Domain-specific table (solid-state kinetics)
        tables.append(
            self.build_domain_specific_table(
                operations, domain="solid_state_kinetics", title="Solid-State Kinetics Analysis"
            )
        )
        return tables

    def _get_available_metrics(self, operations: List[OperationMetrics]) -> Set[str]:
        """Get set of available metrics across all operations."""
        available = set()

        for op in operations:
            # Check for standard metrics
            if op.request_count > 0:
                available.add("request_count")
            if op.response_count > 0:
                available.add("response_count")
            if op.memory_usage_mb is not None:
                available.add("memory_usage_mb")

            # Check custom metrics
            for key in op.custom_metrics.keys():
                if key in self.OPTIONAL_COLUMNS:
                    available.add(key)

        return available

    def _build_operation_row(self, operation: OperationMetrics, headers: List[str]) -> List[str]:
        """Build single row for operation."""
        row = []

        for header in headers:
            if header == "Sub-Operation":
                row.append(operation.operation_type)
            elif header == "Start Time":
                if operation.start_time:
                    row.append(operation.start_time.strftime(self.date_format))
                else:
                    row.append("N/A")
            elif header == "Duration (s)":
                if operation.duration_ms is not None:
                    row.append(f"{operation.duration_ms/1000:.{self.float_precision}f}")
                else:
                    row.append("N/A")
            elif header == "Component":
                if operation.components_involved:
                    row.append(", ".join(sorted(operation.components_involved)))
                else:
                    row.append(operation.module)
            elif header == "Status":
                row.append(self._format_status(operation.status))
            else:
                # Handle optional columns
                value = self._get_optional_column_value(operation, header)
                row.append(value)

        return row

    def _get_optional_column_value(self, operation: OperationMetrics, header: str) -> str:
        """Get value for optional column."""
        # Find the metric key for this header
        metric_key = None
        for key, column_name in self.OPTIONAL_COLUMNS.items():
            if column_name == header:
                metric_key = key
                break

        if metric_key is None:
            return "N/A"

        # Get value from custom metrics or standard fields
        if metric_key == "request_count":
            return str(operation.request_count)
        elif metric_key == "response_count":
            return str(operation.response_count)
        elif metric_key == "memory_usage_mb":
            if operation.memory_usage_mb is not None:
                return f"{operation.memory_usage_mb:.1f}"
            else:
                return "N/A"
        else:
            # Custom metric
            value = operation.custom_metrics.get(metric_key)
            return self._format_metric_value(value)

    def _format_metric_value(self, value: Any) -> str:
        """Format metric value for display."""
        if value is None:
            return "N/A"
        elif isinstance(value, float):
            return f"{value:.{self.float_precision}f}"
        elif isinstance(value, list):
            return ", ".join(str(v) for v in value)
        else:
            return str(value)

    def _format_status(self, status: OperationStatus) -> str:
        """Format operation status with icon."""
        icon = self.STATUS_ICONS.get(status, "❓")
        return f"{icon} {status.value.upper()}"

    def _get_custom_metric_value(self, operation: OperationMetrics, key: str, default=None):
        """Get custom metric value with default."""
        return operation.custom_metrics.get(key, default)

    def _calculate_efficiency_rating(self, operation: OperationMetrics) -> str:  # noqa: C901
        """Calculate efficiency rating based on performance metrics."""
        if operation.status != OperationStatus.COMPLETED:
            return "N/A"

        score = 0
        factors = 0

        # Duration factor (lower is better)
        if operation.duration_ms is not None:
            if operation.duration_ms < 1000:  # < 1 second
                score += 3
            elif operation.duration_ms < 5000:  # < 5 seconds
                score += 2
            elif operation.duration_ms < 10000:  # < 10 seconds
                score += 1
            factors += 1

        # Memory factor (lower is better)
        if operation.memory_usage_mb is not None:
            if operation.memory_usage_mb < 100:
                score += 3
            elif operation.memory_usage_mb < 500:
                score += 2
            elif operation.memory_usage_mb < 1000:
                score += 1
            factors += 1

        # Error/warning factor
        if operation.error_count == 0 and operation.warning_count == 0:
            score += 3
        elif operation.error_count == 0:
            score += 2
        elif operation.error_count < 3:
            score += 1
        factors += 1

        if factors == 0:
            return "N/A"

        avg_score = score / factors
        if avg_score >= 2.5:
            return "⭐⭐⭐ Excellent"
        elif avg_score >= 2.0:
            return "⭐⭐ Good"
        elif avg_score >= 1.5:
            return "⭐ Fair"
        else:
            return "⚠️ Poor"

    def _build_summary(self, operations: List[OperationMetrics]) -> str:
        """Build summary string for operations."""
        total = len(operations)
        completed = sum(1 for op in operations if op.status == OperationStatus.COMPLETED)
        failed = sum(1 for op in operations if op.status == OperationStatus.FAILED)
        timeout = sum(1 for op in operations if op.status == OperationStatus.TIMEOUT)

        total_duration = sum(op.duration_ms or 0 for op in operations) / 1000
        avg_duration = total_duration / total if total > 0 else 0

        summary_parts = [
            f"Total: {total} operations",
            f"Completed: {completed}",
            f"Failed: {failed}",
            f"Timeout: {timeout}",
            f"Total time: {total_duration:.{self.float_precision}f}s",
            f"Average: {avg_duration:.{self.float_precision}f}s",
        ]

        return " | ".join(summary_parts)

    def _build_performance_summary(self, operations: List[OperationMetrics]) -> str:
        """Build performance-focused summary."""
        completed_ops = [op for op in operations if op.status == OperationStatus.COMPLETED]

        if not completed_ops:
            return "No completed operations for performance analysis"

        # Calculate averages
        durations = [op.duration_ms for op in completed_ops if op.duration_ms is not None]
        memories = [op.memory_usage_mb for op in completed_ops if op.memory_usage_mb is not None]

        avg_duration = sum(durations) / len(durations) if durations else 0
        avg_memory = sum(memories) / len(memories) if memories else 0

        summary_parts = [
            f"Completed: {len(completed_ops)}/{len(operations)}",
            f"Avg Duration: {avg_duration:.{self.float_precision}f}ms",
            f"Avg Memory: {avg_memory:.1f}MB" if memories else "Memory: N/A",
        ]

        return " | ".join(summary_parts)

    def _build_kinetics_summary(self, operations: List[OperationMetrics]) -> str:
        """Build kinetics-specific summary."""
        total_files = sum(self._get_custom_metric_value(op, "file_count", 0) for op in operations)
        total_reactions = sum(self._get_custom_metric_value(op, "reaction_count", 0) for op in operations)

        # Count analysis types
        analysis_types = {}
        for op in operations:
            op_type = op.operation_type
            analysis_types[op_type] = analysis_types.get(op_type, 0) + 1

        summary_parts = [
            f"Files processed: {total_files}",
            f"Reactions analyzed: {total_reactions}",
            f"Analysis steps: {', '.join(f'{k}({v})' for k, v in analysis_types.items())}",
        ]

        return " | ".join(summary_parts)
