"""
Operation monitoring component for tracking system operations flow.

This module provides monitoring for operation chains, request-response cycles,
and system state changes with performance analysis.
"""

import logging
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


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

    # New enhanced metrics for Stage 3
    request_count: int = 0
    """Number of requests made during operation"""

    response_count: int = 0
    """Number of responses received during operation"""

    warning_count: int = 0
    """Number of warnings during operation"""

    error_count: int = 0
    """Number of errors during operation"""

    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    """Custom domain-specific metrics"""

    components_involved: Set[str] = field(default_factory=set)
    """Set of components involved in operation"""

    sub_operations: List[str] = field(default_factory=list)
    """List of detected sub-operations"""

    @property
    def enhanced_status(self) -> str:
        """Enhanced status based on errors/warnings"""
        if self.error_count > 0:
            return "ERROR"
        elif self.warning_count > 0:
            return "WARNING"
        else:
            return "SUCCESS"


@dataclass
class LogMetricsExtractor:
    """Extractor for metrics from log messages."""

    METRIC_PATTERNS = {
        r"handle_request_cycle.*OperationType\.(\w+)": "sub_operation",
        r"operation.*completed.*?(\d+\.?\d*)\s*seconds": "duration",
        r"operation.*completed.*?(\d+\.?\d*)\s*ms": "duration",
        r"processing (\d+) files": "file_count",
        r"(\d+) reactions found": "reaction_count",
        r"found (\d+) reactions": "reaction_count",
        r"MSE:\s*(\d+\.?\d*)": "mse_value",
        r"R²:\s*(\d+\.?\d*)": "r_squared",
        r"heating rate:\s*(\d+\.?\d*)": "heating_rate",
        r"iterations:\s*(\d+)": "iteration_count",
        r"convergence:\s*(\d+\.?\d*)": "convergence_value",
        r"method:\s*([A-Za-z_-]+)": "optimization_method",
        r"cpu usage:\s*(\d+\.?\d*)%?": "cpu_usage",
        r"memory.*?(\d+\.?\d*)\s*MB": "memory_usage_mb",
    }

    @classmethod
    def extract_metrics(cls, message: str) -> Dict[str, Any]:
        """Extract metrics from log message."""
        metrics = {}

        for pattern, metric_name in cls.METRIC_PATTERNS.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                value = match.group(1)
                # Try to convert to number
                try:
                    metrics[metric_name] = float(value) if "." in value else int(value)
                except ValueError:
                    metrics[metric_name] = value

        return metrics


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

        # Enhanced metrics tracking for Stage 3
        self.current_operation: Optional[OperationMetrics] = None
        self.completed_operations: List[OperationMetrics] = []
        self.operation_stack: List[OperationMetrics] = []  # For nested operations
        self.metrics_extractor = LogMetricsExtractor()

        # Flow detection patterns
        self._flow_patterns = {
            "deconvolution_flow": ["LOAD_FILE", "GET_DF_DATA", "DECONVOLUTION"],
            "model_based_flow": ["MODEL_BASED_CALCULATION", "UPDATE_VALUE", "SET_VALUE"],
            "file_processing_flow": ["LOAD_FILE", "SMOOTH_DATA", "SUBTRACT_BACKGROUND"],
            "data_update_flow": ["UPDATE_VALUE", "GET_DF_DATA", "SET_VALUE"],
        }

        if self.config.enabled:
            self._start_monitoring_thread()

    def reset(self) -> None:
        """Reset the operation monitor to clean state."""
        with self._lock:
            self._active_operations.clear()
            self._operation_history.clear()
            self._operations_by_type.clear()
            self._active_flows.clear()
            self._flow_history.clear()
            self._operation_to_flow.clear()
            self._operation_stats.clear()
            self.current_operation = None
            self.completed_operations.clear()
            self.operation_stack.clear()

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

    # Enhanced methods for Stage 3 - Operation Metrics Collection

    def start_operation_tracking(self, name: str) -> None:
        """Start tracking new operation with enhanced metrics."""
        # If there's current operation, save it to stack for nested operations
        if self.current_operation:
            self.operation_stack.append(self.current_operation)

        self.current_operation = OperationMetrics(
            operation_id=f"op_{name}_{int(time.time() * 1000000)}",
            operation_type=name,
            module="enhanced_tracking",
            start_time=datetime.now(),
            status=OperationStatus.RUNNING,
        )

    def end_operation_tracking(self) -> Optional[OperationMetrics]:
        """End tracking current operation and return metrics."""
        if not self.current_operation:
            return None

        self.current_operation.end_time = datetime.now()
        if self.current_operation.start_time and self.current_operation.end_time:
            duration = (self.current_operation.end_time - self.current_operation.start_time).total_seconds() * 1000
            self.current_operation.duration_ms = duration

        # Set final status based on error/warning counts only if not already set to a terminal state
        if self.current_operation.status == OperationStatus.RUNNING:
            if self.current_operation.error_count > 0:
                self.current_operation.status = OperationStatus.FAILED
            else:
                self.current_operation.status = OperationStatus.COMPLETED

        completed = self.current_operation
        self.completed_operations.append(completed)

        # Restore previous operation from stack
        self.current_operation = self.operation_stack.pop() if self.operation_stack else None

        return completed

    def add_custom_metric(self, key: str, value: Any) -> None:
        """Add custom metric to current operation."""
        if self.current_operation:
            self.current_operation.custom_metrics[key] = value

    def track_request(self, source: str, target: str, operation: str) -> None:
        """Track request in current operation."""
        if self.current_operation:
            self.current_operation.request_count += 1
            self.current_operation.components_involved.add(source)
            self.current_operation.components_involved.add(target)

        # Call existing tracking logic if available
        if hasattr(self, "_track_request_original"):
            self._track_request_original(source, target, operation)

    def track_response(self, source: str, target: str, operation: str) -> None:
        """Track response in current operation."""
        if self.current_operation:
            self.current_operation.response_count += 1

        # Call existing tracking logic if available
        if hasattr(self, "_track_response_original"):
            self._track_response_original(source, target, operation)

    def track_log_level(self, level: str, message: str = "") -> None:
        """Track log level and extract metrics from message."""
        if not self.current_operation:
            return

        if level == "WARNING":
            self.current_operation.warning_count += 1
        elif level == "ERROR":
            self.current_operation.error_count += 1

        # Extract metrics from log message if provided
        if message:
            extracted_metrics = self.metrics_extractor.extract_metrics(message)
            for key, value in extracted_metrics.items():
                self.add_custom_metric(key, value)

    def add_performance_metrics(self) -> None:
        """Add performance metrics to current operation."""
        if not self.current_operation:
            return

        try:
            import psutil

            # CPU and memory usage
            cpu_usage = psutil.cpu_percent()
            memory_info = psutil.virtual_memory()

            self.add_custom_metric("cpu_usage_percent", cpu_usage)
            self.add_custom_metric("memory_usage_mb", memory_info.used / 1024 / 1024)
            self.add_custom_metric("memory_available_mb", memory_info.available / 1024 / 1024)

        except ImportError:
            # psutil not available, skip performance metrics
            pass

    def track_optimization_metrics(self, optimization_data: dict) -> None:
        """Track optimization-specific metrics."""
        if not self.current_operation:
            return

        if "iteration_count" in optimization_data:
            self.add_custom_metric("iterations", optimization_data["iteration_count"])

        if "convergence_value" in optimization_data:
            self.add_custom_metric("convergence", optimization_data["convergence_value"])

        if "optimization_method" in optimization_data:
            self.add_custom_metric("method", optimization_data["optimization_method"])

        if "mse" in optimization_data:
            self.add_custom_metric("final_mse", optimization_data["mse"])

    def track_data_operation_metrics(self, operation_type: str, data_info: dict) -> None:
        """Track data operation specific metrics."""
        if not self.current_operation:
            return

        # Dispatch to specific handlers based on operation type
        if operation_type == "ADD_NEW_SERIES":
            self._track_series_metrics(data_info)
        elif operation_type == "DECONVOLUTION":
            self._track_deconvolution_metrics(data_info)
        elif operation_type in ["MODEL_FIT_CALCULATION", "MODEL_FREE_CALCULATION"]:
            self._track_calculation_metrics(data_info)

    def _track_series_metrics(self, data_info: dict) -> None:
        """Track metrics for series operations."""
        if "file_count" in data_info:
            self.add_custom_metric("files_processed", data_info["file_count"])
        if "heating_rates" in data_info:
            self.add_custom_metric("heating_rates", data_info["heating_rates"])

    def _track_deconvolution_metrics(self, data_info: dict) -> None:
        """Track metrics for deconvolution operations."""
        if "reaction_count" in data_info:
            self.add_custom_metric("reactions_found", data_info["reaction_count"])
        if "mse" in data_info:
            self.add_custom_metric("final_mse", data_info["mse"])
        if "r_squared" in data_info:
            self.add_custom_metric("r_squared", data_info["r_squared"])

    def _track_calculation_metrics(self, data_info: dict) -> None:
        """Track metrics for calculation operations."""
        if "method" in data_info:
            self.add_custom_metric("calculation_method", data_info["method"])
        if "reaction_count" in data_info:
            self.add_custom_metric("reactions_analyzed", data_info["reaction_count"])

    def get_operation_metrics_for_aggregation(self) -> Dict[str, Any]:
        """Get operation metrics for aggregation table."""
        if not self.current_operation:
            return {}

        return {
            "operation_name": self.current_operation.operation_type,
            "duration": self.current_operation.duration_ms,
            "request_count": self.current_operation.request_count,
            "response_count": self.current_operation.response_count,
            "warning_count": self.current_operation.warning_count,
            "error_count": self.current_operation.error_count,
            "status": self.current_operation.enhanced_status,
            "components": list(self.current_operation.components_involved),
            **self.current_operation.custom_metrics,
        }

    def check_operation_timeout(self, timeout_seconds: float = 30.0) -> None:
        """Check timeout for current operation."""
        if not self.current_operation:
            return

        current_time = datetime.now()
        elapsed = (current_time - self.current_operation.start_time).total_seconds()

        if elapsed > timeout_seconds:
            self.logger.warning(f"Operation {self.current_operation.operation_type} timed out after {timeout_seconds}s")
            self.add_custom_metric("timeout", True)
            self.current_operation.status = OperationStatus.TIMEOUT
            self.end_operation_tracking()

    def extract_metrics_from_logs(self, log_records: List[Any]) -> None:
        """Extract metrics from a batch of log records."""
        if not self.current_operation:
            return

        for record in log_records:
            if hasattr(record, "getMessage"):
                message = record.getMessage()
                # Extract metrics and track log levels
                self.track_log_level(record.levelname, message)

    # End of enhanced methods for Stage 3

    # Original monitoring methods that were preserved
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

    def _analyze_flows(self) -> None:
        """Analyze active flows for performance insights."""
        if not self.config.enable_flow_analysis:
            return

        current_time = datetime.now()

        with self._lock:
            for flow_id, flow in self._active_flows.items():
                elapsed = (current_time - flow.start_time).total_seconds()  # Check for stuck flows
                if elapsed > 30 and flow.completed_operations == 0:
                    self.logger.warning(
                        f"⚠️ STUCK FLOW: {flow.root_operation_type} | ID: {flow_id} | "
                        f"No completed operations after {elapsed:.1f}s"
                    )

    def get_completed_operations(self) -> List[OperationMetrics]:
        """Get list of completed operations."""
        with self._lock:
            return self.completed_operations.copy()

    def shutdown(self) -> None:
        """Shutdown operation monitor."""
        self._stop_monitoring.set()
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=1.0)

        # Complete any remaining operations
        with self._lock:
            for op_id in list(self._active_operations.keys()):
                self.complete_operation(op_id, OperationStatus.FAILED, error_message="System shutdown")


# Global instance for ease of use
operation_monitor = OperationMonitor(OperationMonitoringConfig())
