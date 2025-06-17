"""
BaseSignals burst formatting module with visual indicators and color coding.

This module provides specialized formatting for BaseSignals burst operations
with visual indicators, color coding, and configurable display modes.
"""

from typing import Dict, List, Optional

from .meta_operation import MetaOperation


class BaseSignalsBurstFormatter:
    """Specialized formatter for BaseSignals bursts with visual enhancements."""

    # Visual indicators for different burst types
    BURST_TYPE_COLORS = {
        "Parameter_Update_Burst": "🔄",  # Blue - parameter updates
        "Add_Reaction_Burst": "➕",  # Green - adding reactions
        "Highlight_Reaction_Burst": "🎯",  # Yellow - highlighting
        "Generic_Signal_Burst": "⚡",  # Gray - generic operations
    }

    # Status indicators for operation results
    STATUS_INDICATORS = {"all_success": "✅", "mixed": "⚠️", "all_failed": "❌"}

    # Color codes for different contexts (console, GUI, etc.)
    META_OPERATION_COLORS = {
        "BaseSignalsBurst": {
            "header_bg": "#E3F2FD",  # Light blue
            "border": "#1976D2",  # Blue
            "text": "#0D47A1",  # Dark blue
        },
        "TimeWindowCluster": {
            "header_bg": "#E8F5E8",  # Light green
            "border": "#4CAF50",  # Green
            "text": "#1B5E20",  # Dark green
        },
    }

    def __init__(self, formatting_config: Optional[Dict] = None):
        """
        Initialize BaseSignals formatter with configuration.

        Args:
            formatting_config: Optional configuration for formatting behavior
        """
        self.config = formatting_config or {}

    def format_with_visual_indicators(self, meta_operation: MetaOperation) -> str:
        """Format BaseSignals burst with visual indicators."""
        burst_type = self._determine_burst_type(meta_operation.operations)
        status = self._determine_aggregate_status(meta_operation.operations)

        icon = self.BURST_TYPE_COLORS.get(burst_type, "⚡")
        status_icon = self.STATUS_INDICATORS.get(status, "")

        summary = getattr(meta_operation, "summary", "") or self._generate_summary(meta_operation)
        return f"{icon} {status_icon} {summary}"

    def format_compact_representation(self, meta_operation: MetaOperation) -> str:
        """
        Create compact representation for BaseSignals burst.

        Format: Operation "NAME" (id=X) - STATUS
        ⚡ BaseSignals Burst: N операций (TYPES), duration, actor: source
        Total: 1 meta-operation, N steps, duration
        """
        operations = getattr(meta_operation, "operations", [])
        burst_type = self._determine_burst_type(operations)
        duration_ms = sum(getattr(op, "duration_ms", 0) or 0 for op in operations)
        real_actor = self._extract_real_actor(meta_operation)

        # Extract operation types for summary
        operation_types = self._get_unique_operation_types(operations)
        types_summary = ", ".join(operation_types[:3])  # Show first 3 types
        if len(operation_types) > 3:
            types_summary += "..."

        actor_info = f"actor: {real_actor}" if real_actor else "actor: не задан"

        icon = self.BURST_TYPE_COLORS.get(burst_type, "⚡")

        return (
            f"{icon} BaseSignals Burst: {len(operations)} операций "
            f"({types_summary}), {duration_ms:.0f} мс, {actor_info}"
        )

    def format_performance_indicators(self, meta_operation: MetaOperation) -> str:
        """Format performance indicators for BaseSignals burst."""
        operations = getattr(meta_operation, "operations", [])
        if not operations:
            return ""

        indicators = []

        # Calculate operations density (ops/second)
        total_duration = self._calculate_total_duration_seconds(operations)
        if total_duration > 0:
            density = len(operations) / total_duration
            indicators.append(f"Density: {density:.1f} ops/s")

        # Calculate efficiency (clustering ratio)
        efficiency = len(operations) / (len(operations) + 1)
        indicators.append(f"Efficiency: {efficiency:.1%}")

        # Target distribution
        target_dist = self._calculate_target_distribution(operations)
        if len(target_dist) > 1:
            dist_summary = ", ".join(f"{target}({count})" for target, count in target_dist.items())
            indicators.append(f"Targets: {dist_summary}")

        # Max gap calculation
        max_gap = self._calculate_max_gap_ms(operations)
        if max_gap > 0:
            indicators.append(f"max gap {max_gap:.1f}ms")

        return " | ".join(indicators)

    def get_optimal_format(self, meta_operation: MetaOperation, context: Dict) -> str:
        """Determine optimal format based on context and operation count."""
        operations = getattr(meta_operation, "operations", [])
        op_count = len(operations)

        # For console output - compact format
        if context.get("output_type") == "console":
            return "compact" if op_count <= 3 else "collapsed"

        # For GUI - detailed format with expandability
        if context.get("output_type") == "gui":
            return "expandable"

        # For logs - tabular format
        if context.get("output_type") == "log":
            return "table"

        return "compact"  # Default

    def _determine_burst_type(self, operations: List) -> str:
        """Determine burst type from operation patterns."""
        if not operations:
            return "Generic_Signal_Burst"

        operation_names = [getattr(op, "operation_name", "") for op in operations]

        # Parameter Update pattern: includes UPDATE_VALUE
        if any("UPDATE_VALUE" in str(name) for name in operation_names):
            return "Parameter_Update_Burst"

        # Add Reaction pattern: multiple SET_VALUE operations
        if operation_names.count("SET_VALUE") >= 2:
            return "Add_Reaction_Burst"

        # Highlight pattern: GET_DF_DATA + HIGHLIGHT operations
        if any("GET_DF_DATA" in str(name) for name in operation_names) and any(
            "HIGHLIGHT" in str(name) for name in operation_names
        ):
            return "Highlight_Reaction_Burst"

        return "Generic_Signal_Burst"

    def _determine_aggregate_status(self, operations: List) -> str:
        """Determine aggregate status of operations."""
        if not operations:
            return "empty"

        statuses = [getattr(op, "status", "Unknown") for op in operations]
        unique_statuses = set(statuses)

        if len(unique_statuses) == 1:
            return "all_success" if "OK" in unique_statuses else "all_failed"
        else:
            return "mixed"

    def _extract_real_actor(self, meta_operation: MetaOperation) -> str:
        """Extract real actor from meta operation context."""
        # Check for real actor in description
        description = getattr(meta_operation, "description", "") or ""
        if "(from " in description and ")" in description:
            start = description.find("(from ") + 6
            end = description.find(")", start)
            if end > start:
                return description[start:end]

        # Check operations for caller info
        operations = getattr(meta_operation, "operations", [])
        for op in operations:
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

    def _get_unique_operation_types(self, operations: List) -> List[str]:
        """Get unique operation types from operations list."""
        types = set()
        for op in operations:
            if hasattr(op, "operation_name"):
                types.add(str(op.operation_name))
        return sorted(types)

    def _calculate_total_duration_seconds(self, operations: List) -> float:
        """Calculate total duration in seconds."""
        total_ms = sum(getattr(op, "duration_ms", 0) or 0 for op in operations)
        return total_ms / 1000.0

    def _calculate_target_distribution(self, operations: List) -> Dict[str, int]:
        """Calculate distribution of operations by target."""
        targets = {}
        for op in operations:
            if hasattr(op, "target"):
                target = str(op.target)
                targets[target] = targets.get(target, 0) + 1
        return targets

    def _calculate_max_gap_ms(self, operations: List) -> float:
        """Calculate maximum gap between consecutive operations."""
        if len(operations) < 2:
            return 0.0

        start_times = [getattr(op, "start_time", 0) for op in operations if hasattr(op, "start_time")]
        if len(start_times) < 2:
            return 0.0

        start_times.sort()
        gaps = [(start_times[i + 1] - start_times[i]) * 1000 for i in range(len(start_times) - 1)]
        return max(gaps) if gaps else 0.0

    def _generate_summary(self, meta_operation: MetaOperation) -> str:
        """Generate summary if not provided."""
        operations = getattr(meta_operation, "operations", [])
        burst_type = self._determine_burst_type(operations)
        duration_ms = sum(getattr(op, "duration_ms", 0) or 0 for op in operations)

        return f"{burst_type}: {len(operations)} operations, {duration_ms:.1f}ms"
