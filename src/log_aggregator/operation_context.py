"""
Context manager for operation logging and tracking.

This module provides a convenient context manager for tracking operations
with the enhanced OperationMonitor, allowing easy integration with existing code.
"""

import logging
from contextlib import contextmanager
from typing import Any, Optional

from .operation_monitor import OperationMonitor

# Global operation monitor instance
_operation_monitor: Optional[OperationMonitor] = None


def set_operation_monitor(monitor: OperationMonitor) -> None:
    """Set the global operation monitor instance."""
    global _operation_monitor
    _operation_monitor = monitor


def get_operation_monitor() -> Optional[OperationMonitor]:
    """Get the global operation monitor instance."""
    return _operation_monitor


@contextmanager
def log_operation(operation_name: str, **initial_metrics):
    """
    Context manager for tracking operations with enhanced metrics.

    Usage:
        with log_operation("DECONVOLUTION", reaction_count=3):
            # Perform deconvolution
            # Metrics are automatically tracked
            pass

    Args:
        operation_name: Name of the operation to track
        **initial_metrics: Initial custom metrics to set
    """
    monitor = get_operation_monitor()
    if not monitor:
        # If no monitor is available, just yield without tracking
        yield
        return

    # Start operation tracking
    monitor.start_operation_tracking(operation_name)

    # Add initial metrics
    for key, value in initial_metrics.items():
        monitor.add_custom_metric(key, value)

    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting operation: {operation_name}")

    try:
        yield monitor
    except Exception as e:
        # Track error
        if monitor.current_operation:
            monitor.track_log_level("ERROR", f"Operation failed: {str(e)}")
        logger.error(f"❌ Operation {operation_name} failed: {str(e)}")
        raise
    finally:
        # End operation tracking
        completed_operation = monitor.end_operation_tracking()
        if completed_operation:
            logger.info(
                f"✅ Operation {operation_name} completed: "
                f"status={completed_operation.enhanced_status}, "
                f"duration={completed_operation.duration_ms:.1f}ms"
            )


def track_operation_metric(key: str, value: Any) -> None:
    """
    Add a custom metric to the current operation.

    Args:
        key: Metric name
        value: Metric value
    """
    monitor = get_operation_monitor()
    if monitor:
        monitor.add_custom_metric(key, value)


def track_operation_request(source: str, target: str, operation: str) -> None:
    """
    Track a request in the current operation.

    Args:
        source: Source component
        target: Target component
        operation: Operation type
    """
    monitor = get_operation_monitor()
    if monitor:
        monitor.track_request(source, target, operation)


def track_operation_response(source: str, target: str, operation: str) -> None:
    """
    Track a response in the current operation.

    Args:
        source: Source component
        target: Target component
        operation: Operation type
    """
    monitor = get_operation_monitor()
    if monitor:
        monitor.track_response(source, target, operation)


def track_data_operation(operation_type: str, **data_info) -> None:
    """
    Track data operation metrics.

    Args:
        operation_type: Type of data operation
        **data_info: Data operation information
    """
    monitor = get_operation_monitor()
    if monitor:
        monitor.track_data_operation_metrics(operation_type, data_info)


def track_optimization_result(
    iteration_count: int = None, convergence: float = None, method: str = None, mse: float = None, **kwargs
) -> None:
    """
    Track optimization results.

    Args:
        iteration_count: Number of iterations performed
        convergence: Convergence value achieved
        method: Optimization method used
        mse: Mean squared error
        **kwargs: Additional optimization metrics
    """
    monitor = get_operation_monitor()
    if not monitor:
        return

    optimization_data = {}
    if iteration_count is not None:
        optimization_data["iteration_count"] = iteration_count
    if convergence is not None:
        optimization_data["convergence_value"] = convergence
    if method is not None:
        optimization_data["optimization_method"] = method
    if mse is not None:
        optimization_data["mse"] = mse

    # Add any additional metrics
    optimization_data.update(kwargs)

    monitor.track_optimization_metrics(optimization_data)


# Example usage patterns for integration with MainWindow operations
def example_integration_patterns():
    """
    Example patterns for integrating operation tracking with existing code.
    This function is for documentation purposes only.
    """

    # Pattern 1: Simple operation tracking
    def add_new_series_example(self, params):
        with log_operation("ADD_NEW_SERIES"):  # Extract files and heating rates
            selected_files = self._extract_files_from_params(params)

            # Track initial metrics
            track_operation_metric("file_count", len(selected_files))
            track_operation_metric("heating_rates", [rate for _, rate, _ in selected_files])

            # Perform operation - get data and process
            self.handle_request_cycle("file_data", "GET_ALL_DATA", file_name="all_files")

            # Track requests/responses automatically via handle_request_cycle integration
            result = self.handle_request_cycle("series_data", "ADD_NEW_SERIES", **params)

            return result

    # Pattern 2: Deconvolution operation tracking
    def handle_deconvolution_example(self, params):
        with log_operation("DECONVOLUTION") as monitor:
            # Get current data
            file_name = params.get("file_name")
            monitor.add_custom_metric("target_file", file_name)

            # Perform deconvolution calculation
            result = self.handle_request_cycle("calculations", "DECONVOLUTION", **params)

            # Track results
            if "reaction_count" in result:
                track_operation_metric("reactions_found", result["reaction_count"])
            if "mse" in result:
                track_operation_metric("final_mse", result["mse"])

            return result

    # Pattern 3: Model-based calculation tracking
    def model_based_calculation_example(self, params):
        with log_operation("MODEL_BASED_CALCULATION"):
            # Track calculation settings
            track_operation_metric("method", params.get("method", "differential_evolution"))

            # Perform calculation
            result = self.handle_request_cycle("calculations", "MODEL_BASED_CALCULATION", **params)

            # Track optimization results
            if "optimization_result" in result:
                opt_result = result["optimization_result"]
                track_optimization_result(
                    iteration_count=opt_result.get("nit"),
                    convergence=opt_result.get("fun"),
                    method=params.get("method"),
                )

            return result
