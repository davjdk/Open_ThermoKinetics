"""
Operation monitoring component for tracking system operations flow.

This module provides monitoring for operation chains, request-response cycles,
and system state changes with performance analysis.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class OperationStatus(Enum):
    """Status of operation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class OperationMetrics:
    """Metrics for individual operation tracking."""

    operation_id: str
    """Unique operation identifier"""

    operation_type: str
    """Type of operation (DECONVOLUTION, UPDATE_VALUE, etc.)"""

    module: str
    """Module that initiated the operation"""

    start_time: datetime
    """When operation started"""

    end_time: Optional[datetime] = None
    """When operation completed"""

    status: OperationStatus = OperationStatus.PENDING
    """Current operation status"""

    duration_ms: Optional[float] = None
    """Operation duration in milliseconds"""

    parameters: Dict[str, Any] = field(default_factory=dict)
    """Operation parameters"""

    result: Optional[Any] = None
    """Operation result"""

    error_message: Optional[str] = None
    """Error message if operation failed"""

    parent_operation_id: Optional[str] = None
    """Parent operation ID for nested operations"""

    child_operation_ids: List[str] = field(default_factory=list)
    """Child operation IDs"""

    memory_usage_mb: Optional[float] = None
    """Memory usage at operation completion"""

    warnings: List[str] = field(default_factory=list)
    """Operation warnings"""


@dataclass
class OperationFlow:
    """Flow of related operations."""

    flow_id: str
    """Unique flow identifier"""

    root_operation_type: str
    """Type of root operation that started the flow"""

    start_time: datetime
    """When flow started"""

    end_time: Optional[datetime] = None
    """When flow completed"""

    operation_ids: List[str] = field(default_factory=list)
    """Ordered list of operation IDs in flow"""

    total_operations: int = 0
    """Total number of operations in flow"""

    completed_operations: int = 0
    """Number of completed operations"""

    failed_operations: int = 0
    """Number of failed operations"""

    total_duration_ms: float = 0.0
    """Total flow duration in milliseconds"""

    critical_path_ms: float = 0.0
    """Duration of critical path in milliseconds"""

    parallelism_factor: float = 1.0
    """Average parallelism factor (total_time / critical_path)"""

    status: OperationStatus = OperationStatus.RUNNING
    """Overall flow status"""


@dataclass
class OperationMonitoringConfig:
    """Configuration for operation monitoring."""

    enabled: bool = True
    """Whether operation monitoring is enabled"""

    max_operation_history: int = 10000
    """Maximum number of operations to keep in history"""

    max_flow_history: int = 1000
    """Maximum number of flows to keep in history"""

    operation_timeout_seconds: float = 300.0
    """Timeout for individual operations"""

    flow_timeout_seconds: float = 600.0
    """Timeout for operation flows"""

    enable_performance_tracking: bool = True
    """Whether to track operation performance"""

    enable_flow_analysis: bool = True
    """Whether to analyze operation flows"""

    enable_memory_tracking: bool = True
    """Whether to track memory usage"""

    slow_operation_threshold_ms: float = 1000.0
    """Threshold for slow operation warnings"""

    flow_analysis_window_seconds: float = 60.0
    """Time window for flow analysis"""

    log_level: str = "INFO"
    """Log level for operation monitoring"""


class OperationMonitor:
    """
    Monitor for tracking system operations and flows.

    This component tracks individual operations, analyzes operation flows,
    and provides performance insights for system operations.
    """

    def __init__(self, config: OperationMonitoringConfig):
        """Initialize operation monitor."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Operation tracking
        self._active_operations: Dict[str, OperationMetrics] = {}
        self._operation_history: deque = deque(maxlen=config.max_operation_history)
        self._operations_by_type: Dict[str, List[str]] = defaultdict(list)

        # Flow tracking
        self._active_flows: Dict[str, OperationFlow] = {}
        self._flow_history: deque = deque(maxlen=config.max_flow_history)
        self._operation_to_flow: Dict[str, str] = {}

        # Performance statistics
        self._operation_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_duration_ms": 0.0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0.0,
                "avg_duration_ms": 0.0,
                "recent_durations": deque(maxlen=100),
            }
        )

        # Threading
        self._lock = threading.RLock()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()

        # Flow detection patterns
        self._flow_patterns = {
            "deconvolution_flow": ["LOAD_FILE", "GET_DF_DATA", "DECONVOLUTION"],
            "model_based_flow": ["MODEL_BASED_CALCULATION", "UPDATE_VALUE", "SET_VALUE"],
            "file_processing_flow": ["LOAD_FILE", "SMOOTH_DATA", "SUBTRACT_BACKGROUND"],
            "data_update_flow": ["UPDATE_VALUE", "GET_DF_DATA", "SET_VALUE"],
        }

        if self.config.enabled:
            self._start_monitoring_thread()

    def start_operation(
        self,
        operation_id: str,
        operation_type: str,
        module: str,
        parameters: Optional[Dict[str, Any]] = None,
        parent_operation_id: Optional[str] = None,
    ) -> None:
        """Start tracking a new operation."""
        if not self.config.enabled:
            return

        with self._lock:
            metrics = OperationMetrics(
                operation_id=operation_id,
                operation_type=operation_type,
                module=module,
                start_time=datetime.now(),
                parameters=parameters or {},
                parent_operation_id=parent_operation_id,
                status=OperationStatus.RUNNING,
            )

            self._active_operations[operation_id] = metrics
            self._operations_by_type[operation_type].append(operation_id)

            # Update parent operation
            if parent_operation_id and parent_operation_id in self._active_operations:
                self._active_operations[parent_operation_id].child_operation_ids.append(operation_id)

            # Try to associate with existing flow or create new flow
            flow_id = self._detect_or_create_flow(operation_type, operation_id)
            if flow_id:
                self._operation_to_flow[operation_id] = flow_id

            self.logger.debug(
                f"🚀 OPERATION STARTED: {operation_type} | ID: {operation_id} | "
                f"Module: {module} | Flow: {flow_id or 'None'}"
            )

    def complete_operation(
        self,
        operation_id: str,
        status: OperationStatus = OperationStatus.COMPLETED,
        result: Optional[Any] = None,
        error_message: Optional[str] = None,
        memory_usage_mb: Optional[float] = None,
    ) -> None:
        """Complete an operation."""
        if not self.config.enabled or operation_id not in self._active_operations:
            return

        with self._lock:
            metrics = self._active_operations[operation_id]
            metrics.end_time = datetime.now()
            metrics.status = status
            metrics.result = result
            metrics.error_message = error_message
            metrics.memory_usage_mb = memory_usage_mb

            # Calculate duration
            if metrics.end_time and metrics.start_time:
                duration = (metrics.end_time - metrics.start_time).total_seconds() * 1000
                metrics.duration_ms = duration

                # Update statistics
                self._update_operation_stats(metrics)  # Check for slow operations
                if self.config.enable_performance_tracking and duration > self.config.slow_operation_threshold_ms:
                    self.logger.warning(
                        f"⚠️ SLOW OPERATION: {metrics.operation_type} took {duration:.1f}ms "
                        f"(threshold: {self.config.slow_operation_threshold_ms}ms)"
                    )

            # Update flow
            flow_id = self._operation_to_flow.get(operation_id)
            if flow_id and flow_id in self._active_flows:
                self._update_flow_metrics(flow_id, metrics)

            # Move to history
            self._operation_history.append(metrics)
            del self._active_operations[operation_id]

            # Clean up operation type tracking
            if operation_id in self._operations_by_type[metrics.operation_type]:
                self._operations_by_type[metrics.operation_type].remove(operation_id)

            self.logger.debug(
                f"✅ OPERATION COMPLETED: {metrics.operation_type} | ID: {operation_id} | "
                f"Status: {status.value} | Duration: {metrics.duration_ms:.1f}ms"
            )

    def get_operation_status(self, operation_id: str) -> Optional[OperationMetrics]:
        """Get status of specific operation."""
        with self._lock:
            return self._active_operations.get(operation_id)

    def get_active_operations(self) -> Dict[str, OperationMetrics]:
        """Get all active operations."""
        with self._lock:
            return self._active_operations.copy()

    def get_active_flows(self) -> Dict[str, OperationFlow]:
        """Get all active flows."""
        with self._lock:
            return self._active_flows.copy()

    def get_operation_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get operation performance statistics."""
        with self._lock:
            return dict(self._operation_stats)

    def _detect_or_create_flow(self, operation_type: str, operation_id: str) -> Optional[str]:
        """Detect existing flow or create new flow for operation."""
        if not self.config.enable_flow_analysis:
            return None

        # Check if this operation matches any flow patterns
        for flow_pattern_name, pattern_operations in self._flow_patterns.items():
            if operation_type in pattern_operations:
                # Look for active flows that could include this operation
                for flow_id, flow in self._active_flows.items():
                    if flow.root_operation_type in pattern_operations and operation_type in pattern_operations:
                        flow.operation_ids.append(operation_id)
                        flow.total_operations += 1
                        return flow_id

                # Create new flow if this is a root operation
                if operation_type == pattern_operations[0]:
                    flow_id = f"flow_{operation_type}_{int(time.time() * 1000000)}"
                    flow = OperationFlow(
                        flow_id=flow_id,
                        root_operation_type=operation_type,
                        start_time=datetime.now(),
                        operation_ids=[operation_id],
                        total_operations=1,
                    )
                    self._active_flows[flow_id] = flow
                    return flow_id

        return None

    def _update_flow_metrics(self, flow_id: str, operation_metrics: OperationMetrics) -> None:
        """Update flow metrics when operation completes."""
        if flow_id not in self._active_flows:
            return

        flow = self._active_flows[flow_id]

        if operation_metrics.status == OperationStatus.COMPLETED:
            flow.completed_operations += 1
        elif operation_metrics.status == OperationStatus.FAILED:
            flow.failed_operations += 1

        # Update durations
        if operation_metrics.duration_ms:
            flow.total_duration_ms += operation_metrics.duration_ms

        # Check if flow is complete
        if flow.completed_operations + flow.failed_operations >= flow.total_operations:
            flow.end_time = datetime.now()
            if flow.start_time and flow.end_time:
                flow.critical_path_ms = (flow.end_time - flow.start_time).total_seconds() * 1000

            # Calculate parallelism factor
            if flow.critical_path_ms > 0:
                flow.parallelism_factor = flow.total_duration_ms / flow.critical_path_ms

            # Determine overall status
            if flow.failed_operations > 0:
                flow.status = OperationStatus.FAILED
            else:
                flow.status = OperationStatus.COMPLETED

            # Move to history
            self._flow_history.append(flow)
            del self._active_flows[flow_id]

            # Clean up operation-to-flow mapping
            for op_id in flow.operation_ids:
                self._operation_to_flow.pop(op_id, None)

            self.logger.info(
                f"🔄 FLOW COMPLETED: {flow.root_operation_type} | ID: {flow_id} | "
                f"Operations: {flow.total_operations} | Duration: {flow.critical_path_ms:.1f}ms | "
                f"Parallelism: {flow.parallelism_factor:.2f}x"
            )

    def _update_operation_stats(self, metrics: OperationMetrics) -> None:
        """Update operation statistics."""
        if not metrics.duration_ms:
            return

        stats = self._operation_stats[metrics.operation_type]
        stats["total_count"] += 1

        if metrics.status == OperationStatus.COMPLETED:
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1

        # Update duration statistics
        duration = metrics.duration_ms
        stats["total_duration_ms"] += duration
        stats["min_duration_ms"] = min(stats["min_duration_ms"], duration)
        stats["max_duration_ms"] = max(stats["max_duration_ms"], duration)
        stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_count"]

        # Add to recent durations
        stats["recent_durations"].append(duration)

    def _start_monitoring_thread(self) -> None:
        """Start the monitoring thread."""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True, name="OperationMonitor"
            )
            self._monitoring_thread.start()

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_monitoring.wait(5.0):  # Check every 5 seconds
            try:
                self._check_timeouts()
                self._analyze_flows()
            except Exception as e:
                self.logger.error(f"Error in operation monitoring loop: {e}")

    def _check_timeouts(self) -> None:
        """Check for timed out operations and flows."""
        current_time = datetime.now()

        with self._lock:
            # Check operation timeouts
            timed_out_operations = []
            for op_id, metrics in self._active_operations.items():
                elapsed = (current_time - metrics.start_time).total_seconds()
                if elapsed > self.config.operation_timeout_seconds:
                    timed_out_operations.append(op_id)

            for op_id in timed_out_operations:
                self.logger.warning(
                    f"⏰ OPERATION TIMEOUT: {self._active_operations[op_id].operation_type} "
                    f"| ID: {op_id} | Elapsed: {elapsed:.1f}s"
                )
                self.complete_operation(op_id, OperationStatus.TIMEOUT, error_message="Operation timed out")

            # Check flow timeouts
            timed_out_flows = []
            for flow_id, flow in self._active_flows.items():
                elapsed = (current_time - flow.start_time).total_seconds()
                if elapsed > self.config.flow_timeout_seconds:
                    timed_out_flows.append(flow_id)

            for flow_id in timed_out_flows:
                flow = self._active_flows[flow_id]
                self.logger.warning(
                    f"⏰ FLOW TIMEOUT: {flow.root_operation_type} | ID: {flow_id} | " f"Elapsed: {elapsed:.1f}s"
                )
                flow.status = OperationStatus.TIMEOUT
                flow.end_time = current_time
                self._flow_history.append(flow)
                del self._active_flows[flow_id]

    def _analyze_flows(self) -> None:
        """Analyze active flows for performance insights."""
        if not self.config.enable_flow_analysis:
            return

        current_time = datetime.now()

        with self._lock:
            for flow_id, flow in self._active_flows.items():
                elapsed = (current_time - flow.start_time).total_seconds()

                # Check for stuck flows
                if elapsed > 30 and flow.completed_operations == 0:
                    self.logger.warning(
                        f"⚠️ STUCK FLOW: {flow.root_operation_type} | ID: {flow_id} | "
                        f"No completed operations after {elapsed:.1f}s"
                    )

                # Check for inefficient flows
                if flow.total_operations > 5 and flow.parallelism_factor < 0.3:
                    self.logger.warning(
                        f"⚠️ INEFFICIENT FLOW: {flow.root_operation_type} | ID: {flow_id} | "
                        f"Low parallelism: {flow.parallelism_factor:.2f}x"
                    )

    def generate_operation_report(self) -> str:
        """Generate detailed operation report."""
        with self._lock:
            active_ops = len(self._active_operations)
            active_flows = len(self._active_flows)
            total_ops = len(self._operation_history)

            report_lines = [
                "🔧 OPERATION MONITORING REPORT",
                "=" * 50,
                f"📊 Active Operations: {active_ops}",
                f"🔄 Active Flows: {active_flows}",
                f"📈 Total Operations Processed: {total_ops}",
                "",
                "📋 OPERATION STATISTICS BY TYPE",
                "-" * 30,
            ]

            for op_type, stats in self._operation_stats.items():
                if stats["total_count"] > 0:
                    success_rate = (stats["success_count"] / stats["total_count"]) * 100
                    report_lines.extend(
                        [
                            f"{op_type}:",
                            f"  Total: {stats['total_count']} | Success: {success_rate:.1f}%",
                            f"  Avg Duration: {stats['avg_duration_ms']:.2f}ms",
                            f"  Min/Max: {stats['min_duration_ms']:.2f}ms / {stats['max_duration_ms']:.2f}ms",
                        ]
                    )

            if self._active_operations:
                report_lines.extend(["", "🔄 ACTIVE OPERATIONS", "-" * 20])
                for op_id, metrics in self._active_operations.items():
                    elapsed = (datetime.now() - metrics.start_time).total_seconds()
                    report_lines.append(f"{metrics.operation_type} | {op_id} | {elapsed:.1f}s | {metrics.module}")

            report_lines.append("=" * 50)
            return "\n".join(report_lines)

    def get_performance_insights(self) -> Dict[str, Any]:
        """Get performance insights and recommendations."""
        with self._lock:
            insights = {"slow_operations": [], "frequent_failures": [], "inefficient_flows": [], "recommendations": []}

            # Analyze slow operations
            for op_type, stats in self._operation_stats.items():
                if stats["avg_duration_ms"] > self.config.slow_operation_threshold_ms and stats["total_count"] > 10:
                    insights["slow_operations"].append(
                        {
                            "operation_type": op_type,
                            "avg_duration_ms": stats["avg_duration_ms"],
                            "count": stats["total_count"],
                        }
                    )

            # Analyze failure rates
            for op_type, stats in self._operation_stats.items():
                if stats["total_count"] > 5:
                    failure_rate = stats["failure_count"] / stats["total_count"]
                    if failure_rate > 0.1:  # More than 10% failure rate
                        insights["frequent_failures"].append(
                            {
                                "operation_type": op_type,
                                "failure_rate": failure_rate,
                                "total_count": stats["total_count"],
                                "failure_count": stats["failure_count"],
                            }
                        )

            # Generate recommendations
            if insights["slow_operations"]:
                insights["recommendations"].append(
                    "Consider optimizing slow operations or increasing timeout thresholds"
                )

            if insights["frequent_failures"]:
                insights["recommendations"].append(
                    "Investigate operations with high failure rates for stability issues"
                )

            if len(self._active_operations) > 50:
                insights["recommendations"].append("High number of active operations - consider optimizing concurrency")

            return insights

    def shutdown(self) -> None:
        """Shutdown operation monitor."""
        self._stop_monitoring.set()
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=1.0)  # Complete any remaining operations
        with self._lock:
            for op_id in list(self._active_operations.keys()):
                self.complete_operation(op_id, OperationStatus.FAILED, error_message="System shutdown")
