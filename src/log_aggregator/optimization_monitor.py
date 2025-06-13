"""
Optimization monitoring component for tracking long-running calculations.

This module provides specialized monitoring for optimization processes including
deconvolution, model-based calculations, and other computationally intensive tasks.
"""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class OptimizationStatus(Enum):
    """Status of optimization process."""

    STARTING = "starting"
    RUNNING = "running"
    CONVERGING = "converging"
    STUCK = "stuck"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OptimizationMetrics:
    """Metrics for optimization process tracking."""

    operation_id: str
    """Unique identifier for the optimization operation"""

    operation_type: str
    """Type of optimization (DECONVOLUTION, MODEL_BASED_CALCULATION, etc.)"""

    start_time: datetime
    """When the optimization started"""

    last_update: datetime
    """Last time metrics were updated"""

    current_iteration: int = 0
    """Current iteration number"""

    max_iterations: int = 1000
    """Maximum number of iterations"""

    current_error: Optional[float] = None
    """Current error/objective function value"""

    best_error: Optional[float] = None
    """Best error achieved so far"""

    error_history: List[float] = field(default_factory=list)
    """History of error values for convergence analysis"""

    status: OptimizationStatus = OptimizationStatus.STARTING
    """Current status of optimization"""

    parameters: Dict[str, Any] = field(default_factory=dict)
    """Current parameter values"""

    progress_percentage: float = 0.0
    """Progress as percentage (0-100)"""

    estimated_time_remaining: Optional[float] = None
    """Estimated time remaining in seconds"""

    convergence_rate: Optional[float] = None
    """Rate of convergence (improvement per iteration)"""

    stall_count: int = 0
    """Number of consecutive iterations without improvement"""

    warnings: List[str] = field(default_factory=list)
    """List of warnings during optimization"""


@dataclass
class OptimizationMonitoringConfig:
    """Configuration for optimization monitoring."""

    enabled: bool = True
    """Whether optimization monitoring is enabled"""

    update_interval: float = 1.0
    """Interval in seconds between monitoring updates"""

    progress_report_interval: float = 10.0
    """Interval for progress reporting in seconds"""

    convergence_window: int = 10
    """Number of iterations to check for convergence"""

    stall_threshold: int = 50
    """Number of iterations without improvement to consider stalled"""

    min_improvement_threshold: float = 1e-6
    """Minimum improvement to consider progress"""

    max_error_history: int = 1000
    """Maximum number of error values to keep in history"""

    enable_convergence_analysis: bool = True
    """Whether to perform convergence analysis"""

    enable_time_estimation: bool = True
    """Whether to estimate remaining time"""

    enable_parameter_tracking: bool = True
    """Whether to track parameter changes"""

    log_level: str = "INFO"
    """Log level for optimization monitoring"""


class OptimizationMonitor:
    """
    Monitor for tracking optimization processes in real-time.

    This component tracks long-running optimization calculations and provides
    detailed progress reports, convergence analysis, and performance metrics.
    """

    def __init__(self, config: OptimizationMonitoringConfig):
        """Initialize optimization monitor."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Active optimizations
        self._active_optimizations: Dict[str, OptimizationMetrics] = {}
        self._optimization_callbacks: Dict[str, List[Callable]] = defaultdict(list)

        # Monitoring thread
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._lock = threading.RLock()

        # Statistics
        self._completed_optimizations: List[OptimizationMetrics] = []
        self._total_optimization_time = 0.0
        self._total_iterations = 0

        if self.config.enabled:
            self._start_monitoring_thread()

    def start_optimization(
        self,
        operation_id: str,
        operation_type: str,
        max_iterations: int = 1000,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Start monitoring a new optimization process."""
        if not self.config.enabled:
            return

        with self._lock:
            metrics = OptimizationMetrics(
                operation_id=operation_id,
                operation_type=operation_type,
                start_time=datetime.now(),
                last_update=datetime.now(),
                max_iterations=max_iterations,
                parameters=parameters or {},
                status=OptimizationStatus.STARTING,
            )

            self._active_optimizations[operation_id] = metrics

            self.logger.info(
                f"🚀 OPTIMIZATION STARTED: {operation_type} | ID: {operation_id} | " f"Max iterations: {max_iterations}"
            )

    def update_optimization(
        self,
        operation_id: str,
        iteration: Optional[int] = None,
        error: Optional[float] = None,
        parameters: Optional[Dict[str, Any]] = None,
        status: Optional[OptimizationStatus] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update optimization metrics."""
        if not self.config.enabled or operation_id not in self._active_optimizations:
            return

        with self._lock:
            metrics = self._active_optimizations[operation_id]
            metrics.last_update = datetime.now()

            if iteration is not None:
                metrics.current_iteration = iteration
                metrics.progress_percentage = min(100.0, (iteration / metrics.max_iterations) * 100)

            if error is not None:
                metrics.current_error = error
                metrics.error_history.append(error)

                # Keep error history within limits
                if len(metrics.error_history) > self.config.max_error_history:
                    metrics.error_history = metrics.error_history[-self.config.max_error_history :]

                # Update best error
                if metrics.best_error is None or error < metrics.best_error:
                    metrics.best_error = error
                    metrics.stall_count = 0
                else:
                    metrics.stall_count += 1

            if parameters is not None and self.config.enable_parameter_tracking:
                metrics.parameters.update(parameters)

            if status is not None:
                metrics.status = status

            # Analyze convergence and update status
            self._analyze_convergence(metrics)

            # Estimate remaining time
            if self.config.enable_time_estimation:
                self._estimate_remaining_time(metrics)

    def complete_optimization(
        self,
        operation_id: str,
        status: OptimizationStatus = OptimizationStatus.COMPLETED,
        final_error: Optional[float] = None,
        final_parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Complete an optimization process."""
        if not self.config.enabled or operation_id not in self._active_optimizations:
            return

        with self._lock:
            metrics = self._active_optimizations[operation_id]
            metrics.status = status
            metrics.last_update = datetime.now()

            if final_error is not None:
                metrics.current_error = final_error
                metrics.error_history.append(final_error)

            if final_parameters is not None and self.config.enable_parameter_tracking:
                metrics.parameters.update(final_parameters)

            # Calculate final statistics
            duration = (metrics.last_update - metrics.start_time).total_seconds()

            # Move to completed optimizations
            self._completed_optimizations.append(metrics)
            del self._active_optimizations[operation_id]

            # Update global statistics
            self._total_optimization_time += duration
            self._total_iterations += metrics.current_iteration

            # Generate completion report
            self._generate_completion_report(metrics, duration)

            # Call callbacks
            for callback in self._optimization_callbacks.get(operation_id, []):
                try:
                    callback(metrics)
                except Exception as e:
                    self.logger.error(f"Error in optimization callback: {e}")

    def get_optimization_status(self, operation_id: str) -> Optional[OptimizationMetrics]:
        """Get current status of optimization."""
        with self._lock:
            return self._active_optimizations.get(operation_id)

    def get_active_optimizations(self) -> Dict[str, OptimizationMetrics]:
        """Get all active optimizations."""
        with self._lock:
            return self._active_optimizations.copy()

    def add_optimization_callback(self, operation_id: str, callback: Callable) -> None:
        """Add callback for optimization completion."""
        self._optimization_callbacks[operation_id].append(callback)

    def _start_monitoring_thread(self) -> None:
        """Start the monitoring thread."""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True, name="OptimizationMonitor"
            )
            self._monitoring_thread.start()

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        last_progress_report = time.time()

        while not self._stop_monitoring.wait(self.config.update_interval):
            try:
                current_time = time.time()

                # Generate progress reports
                if (current_time - last_progress_report) >= self.config.progress_report_interval:
                    self._generate_progress_reports()
                    last_progress_report = current_time

                # Check for stalled optimizations
                self._check_stalled_optimizations()

            except Exception as e:
                self.logger.error(f"Error in optimization monitoring loop: {e}")

    def _analyze_convergence(self, metrics: OptimizationMetrics) -> None:
        """Analyze convergence of optimization."""
        if not self.config.enable_convergence_analysis or len(metrics.error_history) < 2:
            return

        # Calculate convergence rate over recent iterations
        recent_window = min(self.config.convergence_window, len(metrics.error_history))
        if recent_window >= 2:
            recent_errors = metrics.error_history[-recent_window:]
            start_error = recent_errors[0]
            end_error = recent_errors[-1]

            if start_error > 0:
                improvement = (start_error - end_error) / start_error
                metrics.convergence_rate = improvement / recent_window

        # Check if optimization is converging
        if metrics.stall_count >= self.config.stall_threshold:
            if metrics.status == OptimizationStatus.RUNNING:
                metrics.status = OptimizationStatus.STUCK
                metrics.warnings.append(f"Optimization stalled after {metrics.stall_count} iterations")
        elif metrics.convergence_rate and metrics.convergence_rate > self.config.min_improvement_threshold:
            if metrics.status in [OptimizationStatus.STARTING, OptimizationStatus.STUCK]:
                metrics.status = OptimizationStatus.CONVERGING
        elif metrics.status == OptimizationStatus.STARTING:
            metrics.status = OptimizationStatus.RUNNING

    def _estimate_remaining_time(self, metrics: OptimizationMetrics) -> None:
        """Estimate remaining time for optimization."""
        if metrics.current_iteration == 0:
            return

        elapsed_time = (metrics.last_update - metrics.start_time).total_seconds()
        avg_time_per_iteration = elapsed_time / metrics.current_iteration

        remaining_iterations = max(0, metrics.max_iterations - metrics.current_iteration)
        metrics.estimated_time_remaining = remaining_iterations * avg_time_per_iteration

    def _check_stalled_optimizations(self) -> None:
        """Check for stalled optimizations and update their status."""
        current_time = datetime.now()

        with self._lock:
            for operation_id, metrics in self._active_optimizations.items():
                # Check if optimization hasn't been updated for too long
                time_since_update = (current_time - metrics.last_update).total_seconds()

                if time_since_update > 60:  # 1 minute without update
                    if metrics.status not in [OptimizationStatus.STUCK, OptimizationStatus.FAILED]:
                        metrics.status = OptimizationStatus.STUCK
                        metrics.warnings.append(f"No updates for {time_since_update:.1f} seconds")

    def _generate_progress_reports(self) -> None:
        """Generate progress reports for active optimizations."""
        with self._lock:
            for operation_id, metrics in self._active_optimizations.items():
                self._generate_progress_report(metrics)

    def _generate_progress_report(self, metrics: OptimizationMetrics) -> None:
        """Generate progress report for single optimization."""
        duration = (metrics.last_update - metrics.start_time).total_seconds()

        # Create status emoji
        status_emoji = {
            OptimizationStatus.STARTING: "🚀",
            OptimizationStatus.RUNNING: "⚡",
            OptimizationStatus.CONVERGING: "📈",
            OptimizationStatus.STUCK: "⚠️",
            OptimizationStatus.COMPLETED: "✅",
            OptimizationStatus.FAILED: "❌",
            OptimizationStatus.CANCELLED: "🛑",
        }.get(metrics.status, "❓")

        # Build progress message
        progress_parts = [
            f"{status_emoji} {metrics.operation_type}",
            f"ID: {metrics.operation_id}",
            f"Progress: {metrics.progress_percentage:.1f}%",
            f"Iteration: {metrics.current_iteration}/{metrics.max_iterations}",
            f"Duration: {duration:.1f}s",
        ]

        if metrics.current_error is not None:
            progress_parts.append(f"Error: {metrics.current_error:.6e}")

        if metrics.estimated_time_remaining is not None:
            progress_parts.append(f"ETA: {metrics.estimated_time_remaining:.1f}s")

        if metrics.convergence_rate is not None:
            progress_parts.append(f"Conv. rate: {metrics.convergence_rate:.6e}")

        progress_message = " | ".join(progress_parts)

        # Log with appropriate level
        if metrics.status in [OptimizationStatus.STUCK, OptimizationStatus.FAILED]:
            self.logger.warning(progress_message)
        else:
            self.logger.info(progress_message)

        # Log warnings
        for warning in metrics.warnings:
            self.logger.warning(f"⚠️ {metrics.operation_type} {metrics.operation_id}: {warning}")
        metrics.warnings.clear()  # Clear warnings after logging

    def _generate_completion_report(self, metrics: OptimizationMetrics, duration: float) -> None:
        """Generate completion report for optimization."""
        status_emoji = {
            OptimizationStatus.COMPLETED: "✅",
            OptimizationStatus.FAILED: "❌",
            OptimizationStatus.CANCELLED: "🛑",
        }.get(metrics.status, "❓")

        report_parts = [
            f"{status_emoji} {metrics.operation_type} COMPLETED",
            f"ID: {metrics.operation_id}",
            f"Duration: {duration:.2f}s",
            f"Iterations: {metrics.current_iteration}",
            f"Avg time/iter: {duration/max(1, metrics.current_iteration):.3f}s",
        ]

        if metrics.current_error is not None:
            report_parts.append(f"Final error: {metrics.current_error:.6e}")

        if metrics.best_error is not None:
            report_parts.append(f"Best error: {metrics.best_error:.6e}")

        completion_message = " | ".join(report_parts)

        if metrics.status == OptimizationStatus.COMPLETED:
            self.logger.info(completion_message)
        else:
            self.logger.error(completion_message)

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimization monitoring statistics."""
        with self._lock:
            active_count = len(self._active_optimizations)
            completed_count = len(self._completed_optimizations)

            return {
                "active_optimizations": active_count,
                "completed_optimizations": completed_count,
                "total_optimization_time": self._total_optimization_time,
                "total_iterations": self._total_iterations,
                "average_optimization_time": (self._total_optimization_time / max(1, completed_count)),
                "average_iterations_per_optimization": (self._total_iterations / max(1, completed_count)),
                "monitoring_enabled": self.config.enabled,
            }

    def shutdown(self) -> None:
        """Shutdown optimization monitor."""
        self._stop_monitoring.set()
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=1.0)
