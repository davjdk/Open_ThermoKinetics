"""
Aggregation engine module for log aggregation system.

This module provides the core aggregation logic that processes patterns
and creates aggregated log records for output.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from .buffer_manager import BufferedLogRecord
from .config import OperationMonitoringConfig, OptimizationMonitoringConfig, PerformanceMonitoringConfig
from .operation_monitor import OperationMonitor
from .optimization_monitor import OptimizationMonitor
from .pattern_detector import LogPattern, PatternGroup
from .performance_monitor import PerformanceMonitor
from .safe_message_utils import safe_get_message


@dataclass
class AggregatedLogRecord:
    """Represents an aggregated log record from multiple similar records."""

    pattern_id: str
    """Identifier of the pattern this aggregation represents"""

    template: str
    """Template message with placeholders"""

    count: int
    """Number of original records aggregated"""

    level: str
    """Log level of the aggregated records"""

    logger_name: str
    """Name of the logger that generated the records"""

    first_timestamp: datetime
    """Timestamp of the first record in aggregation"""

    last_timestamp: datetime
    """Timestamp of the last record in aggregation"""

    sample_messages: List[str]
    """Sample of original messages (up to 3)"""

    def to_log_message(self) -> str:
        """Convert aggregated record to a formatted log message."""
        time_span = self.last_timestamp - self.first_timestamp
        time_span_str = f"{time_span.total_seconds():.1f}s" if time_span.total_seconds() > 0 else "instant"

        message = f"[AGGREGATED {self.count}x over {time_span_str}] {self.template}"

        if len(self.sample_messages) > 1:
            message += f" (samples: {', '.join(self.sample_messages[:2])})"

        return message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "pattern_id": self.pattern_id,
            "template": self.template,
            "count": self.count,
            "level": self.level,
            "logger_name": self.logger_name,
            "first_timestamp": self.first_timestamp.isoformat(),
            "last_timestamp": self.last_timestamp.isoformat(),
            "time_span_seconds": (self.last_timestamp - self.first_timestamp).total_seconds(),
            "sample_messages": self.sample_messages,
        }


class AggregationEngine:
    """
    Core engine for aggregating log records based on detected patterns.

    Enhanced with Stage 3 monitoring capabilities for optimization,
    performance, and operation tracking.
    """

    def __init__(
        self,
        min_pattern_entries: int = 2,
        enable_optimization_monitoring: bool = True,
        enable_performance_monitoring: bool = True,
        enable_operation_monitoring: bool = True,
    ):
        """
        Initialize aggregation engine with monitoring capabilities.

        Args:
            min_pattern_entries: Minimum number of entries required to create aggregation
            enable_optimization_monitoring: Whether to enable optimization monitoring
            enable_performance_monitoring: Whether to enable performance monitoring
            enable_operation_monitoring: Whether to enable operation monitoring
        """
        self.min_pattern_entries = min_pattern_entries

        # Initialize monitoring components
        self.optimization_monitor = None
        self.performance_monitor = None
        self.operation_monitor = None

        if enable_optimization_monitoring:
            self.optimization_monitor = OptimizationMonitor(OptimizationMonitoringConfig())

        if enable_performance_monitoring:
            self.performance_monitor = PerformanceMonitor(PerformanceMonitoringConfig())

        if enable_operation_monitoring:
            self.operation_monitor = OperationMonitor(OperationMonitoringConfig())

        # Statistics
        self._total_patterns_processed = 0
        self._total_records_aggregated = 0
        self._total_aggregations_created = 0

    def aggregate_patterns(self, patterns: List[LogPattern]) -> List[AggregatedLogRecord]:
        """
        Aggregate detected patterns into aggregated log records with performance monitoring.

        Args:
            patterns: List of detected patterns to aggregate

        Returns:
            List of aggregated log records
        """
        # Start monitoring
        monitoring_context = self._start_aggregation_monitoring(patterns)

        try:
            aggregated_records = self._process_patterns(patterns)
            self._complete_aggregation_monitoring(monitoring_context, aggregated_records)
            return aggregated_records
        except Exception as e:
            self._handle_aggregation_error(monitoring_context, e)
            raise

    def _start_aggregation_monitoring(self, patterns: List[LogPattern]) -> Dict[str, Any]:
        """Start monitoring for aggregation process."""
        context = {"operation_id": f"aggregate_patterns_{id(patterns)}"}

        if self.performance_monitor:
            context["start_time"] = self.performance_monitor.record_processing_start()

        if self.operation_monitor:
            self.operation_monitor.start_operation(
                operation_id=context["operation_id"],
                operation_type="PATTERN_AGGREGATION",
                module="AggregationEngine",
                parameters={"pattern_count": len(patterns)},
            )

        return context

    def _process_patterns(self, patterns: List[LogPattern]) -> List[AggregatedLogRecord]:
        """Process patterns into aggregated records."""
        aggregated_records = []

        for pattern in patterns:
            if len(pattern.records) >= self.min_pattern_entries:
                aggregated = self._process_single_pattern(pattern)
                aggregated_records.append(aggregated)
                self._update_aggregation_statistics(pattern)

        return aggregated_records

    def _process_single_pattern(self, pattern: LogPattern) -> AggregatedLogRecord:
        """Process a single pattern with performance tracking."""
        pattern_start = None
        if self.performance_monitor:
            pattern_start = self.performance_monitor.record_processing_start()

        aggregated = self._create_aggregated_record(pattern)

        if self.performance_monitor and pattern_start:
            self.performance_monitor.record_processing_end(
                pattern_start, records_processed=1, records_aggregated=len(pattern.records)
            )
            duration_ms = (self.performance_monitor.record_processing_start() - pattern_start) * 1000
            self.performance_monitor.record_component_timing("aggregation", duration_ms)

        return aggregated

    def _update_aggregation_statistics(self, pattern: LogPattern) -> None:
        """Update aggregation statistics."""
        self._total_patterns_processed += 1
        self._total_records_aggregated += len(pattern.records)
        self._total_aggregations_created += 1

    def _complete_aggregation_monitoring(
        self, context: Dict[str, Any], aggregated_records: List[AggregatedLogRecord]
    ) -> None:
        """Complete monitoring for successful aggregation."""
        if self.operation_monitor:
            self.operation_monitor.complete_operation(
                operation_id=context["operation_id"], result={"aggregated_count": len(aggregated_records)}
            )

        if self.performance_monitor and context.get("start_time"):
            self.performance_monitor.record_processing_end(
                context["start_time"],
                records_processed=len(aggregated_records),
                records_aggregated=len(aggregated_records),
            )

    def _handle_aggregation_error(self, context: Dict[str, Any], error: Exception) -> None:
        """Handle aggregation errors in monitoring."""
        if self.operation_monitor:
            self.operation_monitor.complete_operation(
                operation_id=context["operation_id"], status="FAILED", error_message=str(error)
            )

    def _create_aggregated_record(self, pattern: LogPattern) -> AggregatedLogRecord:
        """Create an aggregated record from a pattern."""
        if not pattern.records:
            raise ValueError("Cannot create aggregated record from empty pattern")

        # Get representative information from the first record
        first_record = pattern.records[0].record
        timestamps = [r.timestamp for r in pattern.records]

        # Extract sample messages (up to 3)
        sample_messages = []

        for record in pattern.records[:3]:
            message = safe_get_message(record.record)
            if message not in sample_messages:
                sample_messages.append(message)

        return AggregatedLogRecord(
            pattern_id=pattern.pattern_id,
            template=pattern.template,
            count=pattern.count,
            level=first_record.levelname,
            logger_name=first_record.name,
            first_timestamp=min(timestamps),
            last_timestamp=max(timestamps),
            sample_messages=sample_messages,
        )

    def process_records(
        self, records: List[BufferedLogRecord], patterns: List[LogPattern]
    ) -> List[AggregatedLogRecord]:
        """
        Process records and patterns to create aggregated output.

        Args:
            records: Original buffered records
            patterns: Detected patterns

        Returns:
            List of aggregated records ready for output
        """
        # For Stage 1, simply aggregate the patterns
        # In later stages, this might include more sophisticated logic
        return self.aggregate_patterns(patterns)

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        return {
            "total_patterns_processed": self._total_patterns_processed,
            "total_records_aggregated": self._total_records_aggregated,
            "total_aggregations_created": self._total_aggregations_created,
            "average_records_per_aggregation": (
                self._total_records_aggregated / self._total_aggregations_created
                if self._total_aggregations_created > 0
                else 0
            ),
        }

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self._total_patterns_processed = 0
        self._total_records_aggregated = 0
        self._total_aggregations_created = 0

    def aggregate_pattern_groups(self, pattern_groups: List[PatternGroup]) -> List[AggregatedLogRecord]:
        """
        Aggregate detected pattern groups into aggregated log records.

        Args:
            pattern_groups: List of detected pattern groups to aggregate

        Returns:
            List of aggregated log records with enhanced metadata
        """
        aggregated_records = []

        for pattern_group in pattern_groups:
            if len(pattern_group.records) >= self.min_pattern_entries:
                aggregated = self._create_aggregated_record_from_group(pattern_group)
                aggregated_records.append(aggregated)

                # Update statistics
                self._total_patterns_processed += 1
                self._total_records_aggregated += len(pattern_group.records)
                self._total_aggregations_created += 1

        return aggregated_records

    def _create_aggregated_record_from_group(self, pattern_group: PatternGroup) -> AggregatedLogRecord:
        """Create an aggregated record from a pattern group with enhanced metadata."""
        if not pattern_group.records:
            raise ValueError("Cannot create aggregated record from empty pattern group")

        # Get representative information from the first record
        first_record = pattern_group.records[0].record
        timestamps = [r.timestamp for r in pattern_group.records]

        # Extract sample messages (up to 3)
        sample_messages = []

        for record in pattern_group.records[:3]:
            message = safe_get_message(record.record)
            if message not in sample_messages:
                sample_messages.append(message)

        # Create enhanced template based on pattern type
        template = self._create_enhanced_template(pattern_group)

        return AggregatedLogRecord(
            pattern_id=f"{pattern_group.pattern_type}_{pattern_group.count}",
            template=template,
            count=pattern_group.count,
            level=first_record.levelname,
            logger_name=first_record.name,
            first_timestamp=min(timestamps),
            last_timestamp=max(timestamps),
            sample_messages=sample_messages,
        )

    def _create_enhanced_template(self, pattern_group: PatternGroup) -> str:
        """Create an enhanced template message based on pattern type and metadata."""
        pattern_type = pattern_group.pattern_type
        metadata = pattern_group.metadata

        if pattern_type == "plot_lines_addition":
            line_names = metadata.get("line_names", [])
            return f"Adding plot lines: {', '.join(line_names[:3])}{'...' if len(line_names) > 3 else ''}"

        elif pattern_type == "cascade_component_initialization":
            components = metadata.get("components", [])
            return f"Cascade initialization: {' → '.join(components[:3])}{'...' if len(components) > 3 else ''}"

        elif pattern_type == "request_response_cycle":
            req_count = metadata.get("request_count", 0)
            resp_count = metadata.get("response_count", 0)
            return f"Request-response cycle: {req_count} requests, {resp_count} responses"

        elif pattern_type == "file_operations":
            operations = metadata.get("operation_types", [])
            extensions = metadata.get("file_extensions", [])
            return f"File operations: {', '.join(operations)} on {', '.join(extensions)} files"

        elif pattern_type == "gui_updates":
            update_types = metadata.get("update_types", [])
            return f"GUI updates: {', '.join(update_types)}"

        else:
            # Fallback for basic similarity patterns
            if pattern_group.records:
                return safe_get_message(pattern_group.records[0].record)
            return "Unknown pattern"

    def get_pattern_type_statistics(self, pattern_groups: List[PatternGroup]) -> Dict[str, Any]:
        """Get statistics grouped by pattern types."""
        stats = {}

        for pattern_group in pattern_groups:
            pattern_type = pattern_group.pattern_type

            if pattern_type not in stats:
                stats[pattern_type] = {
                    "count": 0,
                    "total_records": 0,
                    "table_suitable": 0,
                    "avg_duration_ms": 0,
                    "total_duration_ms": 0,
                }

            stats[pattern_type]["count"] += 1
            stats[pattern_type]["total_records"] += pattern_group.count
            stats[pattern_type]["total_duration_ms"] += pattern_group.duration.total_seconds() * 1000

            if pattern_group.get_table_suitable_flag():
                stats[pattern_type]["table_suitable"] += 1

        # Calculate averages
        for pattern_type, data in stats.items():
            if data["count"] > 0:
                data["avg_duration_ms"] = data["total_duration_ms"]
                data["avg_records_per_group"] = data["total_records"] / data["count"]

        return stats

    def process_enhanced_records(
        self, records: List[BufferedLogRecord], pattern_groups: List[PatternGroup]
    ) -> List[AggregatedLogRecord]:
        """
        Process records and pattern groups to create enhanced aggregated output.

        Args:
            records: Original buffered records
            pattern_groups: Detected pattern groups with metadata

        Returns:
            List of aggregated records ready for output
        """
        return self.aggregate_pattern_groups(pattern_groups)

    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics."""
        stats = {
            "aggregation_stats": self.get_statistics(),
            "optimization_monitoring_enabled": self.optimization_monitor is not None,
            "performance_monitoring_enabled": self.performance_monitor is not None,
            "operation_monitoring_enabled": self.operation_monitor is not None,
        }

        if self.optimization_monitor:
            stats["optimization_stats"] = self.optimization_monitor.get_statistics()

        if self.performance_monitor:
            stats["performance_stats"] = self.performance_monitor.get_performance_summary()

        if self.operation_monitor:
            stats["operation_stats"] = self.operation_monitor.get_operation_statistics()

        return stats

    def generate_monitoring_report(self) -> str:
        """Generate comprehensive monitoring report."""
        report_lines = ["🔧 AGGREGATION ENGINE MONITORING REPORT", "=" * 60]

        # Basic aggregation stats
        basic_stats = self.get_statistics()
        report_lines.extend(
            [
                "📊 AGGREGATION STATISTICS",
                f"Patterns Processed: {basic_stats['total_patterns_processed']}",
                f"Records Aggregated: {basic_stats['total_records_aggregated']}",
                f"Aggregations Created: {basic_stats['total_aggregations_created']}",
                f"Avg Records/Aggregation: {basic_stats['average_records_per_aggregation']:.2f}",
                "",
            ]
        )

        # Performance monitoring report
        if self.performance_monitor:
            performance_report = self.performance_monitor.generate_performance_report()
            report_lines.extend(["📈 PERFORMANCE MONITORING", performance_report, ""])

        # Operation monitoring report
        if self.operation_monitor:
            operation_report = self.operation_monitor.generate_operation_report()
            report_lines.extend(["🔄 OPERATION MONITORING", operation_report, ""])

        # Optimization monitoring summary
        if self.optimization_monitor:
            opt_stats = self.optimization_monitor.get_statistics()
            report_lines.extend(
                [
                    "🚀 OPTIMIZATION MONITORING",
                    f"Active Optimizations: {opt_stats['active_optimizations']}",
                    f"Completed Optimizations: {opt_stats['completed_optimizations']}",
                    f"Total Optimization Time: {opt_stats['total_optimization_time']:.2f}s",
                    f"Avg Optimization Time: {opt_stats['average_optimization_time']:.2f}s",
                    "",
                ]
            )

        report_lines.append("=" * 60)
        return "\n".join(report_lines)

    def optimize_performance(self) -> Dict[str, str]:
        """Get performance optimization suggestions."""
        suggestions = {}

        if self.performance_monitor:
            perf_suggestions = self.performance_monitor.optimize_performance()
            suggestions.update(perf_suggestions)

        if self.operation_monitor:
            op_insights = self.operation_monitor.get_performance_insights()
            if op_insights["recommendations"]:
                suggestions["operation_monitoring"] = "; ".join(op_insights["recommendations"])

        # Add aggregation-specific suggestions
        stats = self.get_statistics()
        if stats["average_records_per_aggregation"] < 2:
            suggestions["aggregation_efficiency"] = (
                "Low aggregation efficiency. Consider reducing min_pattern_entries threshold."
            )

        return suggestions

    def shutdown_monitoring(self) -> None:
        """Shutdown all monitoring components."""
        if self.optimization_monitor:
            self.optimization_monitor.shutdown()

        if self.performance_monitor:
            self.performance_monitor.shutdown()

        if self.operation_monitor:
            self.operation_monitor.shutdown()
