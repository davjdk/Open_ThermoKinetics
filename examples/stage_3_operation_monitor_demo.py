"""
Demonstration of Stage 3 enhanced OperationMonitor metrics functionality.

This script demonstrates the enhanced metrics collection, custom metrics tracking,
and log message parsing capabilities implemented in Stage 3.
"""

import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.log_aggregator.operation_aggregator import OperationAggregationConfig, OperationAggregator
from src.log_aggregator.operation_context import (
    log_operation,
    set_operation_monitor,
    track_data_operation,
    track_operation_metric,
    track_optimization_result,
)
from src.log_aggregator.operation_monitor import LogMetricsExtractor, OperationMonitor, OperationMonitoringConfig


def setup_logging():
    """Setup logging for demonstration."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    return logging.getLogger(__name__)


def demonstrate_metrics_extractor():
    """Demonstrate LogMetricsExtractor functionality."""
    print("\n" + "=" * 60)
    print("STAGE 3 DEMO: LogMetricsExtractor")
    print("=" * 60)

    extractor = LogMetricsExtractor()

    # Test various log messages
    test_messages = [
        "handle_request_cycle processing OperationType.DECONVOLUTION request",
        "operation completed in 2.5 seconds with excellent results",
        "processing 5 files for deconvolution analysis",
        "found 3 reactions with MSE: 0.00123 and R²: 0.9876",
        "Current CPU usage: 45.6% and memory usage: 512.3 MB",
        "optimization finished after 150 iterations with convergence: 0.00001",
        "heating rate: 10.0 K/min used for analysis",
    ]

    for message in test_messages:
        metrics = extractor.extract_metrics(message)
        print(f"Message: {message}")
        print(f"Extracted metrics: {metrics}")
        print()


def demonstrate_enhanced_operation_tracking():
    """Demonstrate enhanced operation tracking."""
    print("\n" + "=" * 60)
    print("STAGE 3 DEMO: Enhanced Operation Tracking")
    print("=" * 60)

    # Create enhanced monitor
    config = OperationMonitoringConfig(
        enabled=True,
        max_operation_history=100,
        operation_timeout_seconds=30.0,
    )
    monitor = OperationMonitor(config)
    set_operation_monitor(monitor)

    # Example 1: Simple operation tracking
    print("1. Simple Operation Tracking:")
    monitor.start_operation_tracking("DECONVOLUTION")
    monitor.add_custom_metric("file_name", "test_data.csv")
    monitor.add_custom_metric("reaction_count", 3)
    monitor.track_request("GUI", "CalculationEngine", "DECONVOLUTION")
    monitor.track_response("CalculationEngine", "GUI", "DECONVOLUTION")
    monitor.track_log_level("INFO", "Processing completed with MSE: 0.00123")

    completed = monitor.end_operation_tracking()
    print(f"Completed operation: {completed.operation_type}")
    print(f"Duration: {completed.duration_ms:.1f}ms")
    print(f"Status: {completed.enhanced_status}")
    print(f"Custom metrics: {completed.custom_metrics}")
    print(f"Components: {completed.components_involved}")
    print()

    # Example 2: Nested operations
    print("2. Nested Operations:")
    monitor.start_operation_tracking("ADD_NEW_SERIES")
    monitor.add_custom_metric("files_count", 3)

    # Start nested operation
    monitor.start_operation_tracking("LOAD_FILE")
    monitor.add_custom_metric("file_name", "heating_rate_3.csv")
    nested_completed = monitor.end_operation_tracking()
    print(f"Nested operation completed: {nested_completed.operation_type}")

    # Parent operation continues
    monitor.add_custom_metric("total_reactions", 12)
    parent_completed = monitor.end_operation_tracking()
    print(f"Parent operation completed: {parent_completed.operation_type}")
    print(f"Parent metrics: {parent_completed.custom_metrics}")
    print()

    return monitor


def demonstrate_context_manager():
    """Demonstrate context manager usage."""
    print("\n" + "=" * 60)
    print("STAGE 3 DEMO: Context Manager Usage")
    print("=" * 60)

    setup_logging()

    # Example 1: Successful operation
    print("1. Successful Operation:")
    with log_operation("MODEL_BASED_CALCULATION", method="differential_evolution"):
        track_operation_metric("series_name", "test_series")
        track_operation_metric("heating_rates", [3, 5, 10])

        # Simulate some work
        time.sleep(0.1)

        # Track optimization results
        track_optimization_result(
            iteration_count=150, convergence=0.00001, method="differential_evolution", mse=0.00123
        )

        # Track data operation
        track_data_operation("MODEL_BASED_CALCULATION", method="differential_evolution", reaction_count=4)

    print("Operation completed successfully!")
    print()

    # Example 2: Operation with error
    print("2. Operation with Error:")
    try:
        with log_operation("DECONVOLUTION", file_name="test.csv"):
            track_operation_metric("reaction_count", 3)
            # Simulate error
            raise ValueError("Invalid data format")
    except ValueError as e:
        print(f"Operation failed with error: {e}")

    print()


def demonstrate_aggregator_integration():
    """Demonstrate integration with OperationAggregator."""
    print("\n" + "=" * 60)
    print("STAGE 3 DEMO: Aggregator Integration")
    print("=" * 60)

    # Create monitor and aggregator
    monitor_config = OperationMonitoringConfig(enabled=True)
    monitor = OperationMonitor(monitor_config)

    aggregator_config = OperationAggregationConfig(
        aggregate_error_operations=False,
        include_performance_metrics=True,
        include_custom_metrics=True,
    )
    aggregator = OperationAggregator(aggregator_config)
    aggregator.integrate_with_operation_monitor(monitor)

    # Simulate operation with metrics
    monitor.start_operation_tracking("MODEL_FIT_CALCULATION")
    monitor.add_custom_metric("method", "Coats-Redfern")
    monitor.add_custom_metric("reaction_count", 2)
    monitor.add_custom_metric("r_squared", 0.9876)
    monitor.track_request("GUI", "Calculator", "MODEL_FIT")
    monitor.track_response("Calculator", "GUI", "MODEL_FIT")

    operation_metrics = monitor.end_operation_tracking()

    # Get enhanced aggregation data
    aggregation_data = aggregator.get_enhanced_aggregation_data(operation_metrics)
    print("Enhanced aggregation data:")
    for key, value in aggregation_data.items():
        print(f"  {key}: {value}")
    print()  # Create operation group from metrics
    operation_group = aggregator.create_group_from_operation_metrics(operation_metrics)
    print("Operation group created:")
    print(f"  Root operation: {operation_group.root_operation}")
    print(f"  Custom metrics: {operation_group.custom_metrics}")
    print(f"  Request count: {operation_group.request_count}")
    print(f"  Explicit mode: {operation_group.explicit_mode}")
    print()

    # Get operation summary
    summary = aggregator.get_operation_summary_with_metrics(operation_metrics)
    print(f"Operation summary: {summary}")
    print()


def demonstrate_performance_metrics():
    """Demonstrate performance metrics collection."""
    print("\n" + "=" * 60)
    print("STAGE 3 DEMO: Performance Metrics")
    print("=" * 60)

    config = OperationMonitoringConfig(enabled=True)
    monitor = OperationMonitor(config)

    monitor.start_operation_tracking("PERFORMANCE_TEST")

    # Add performance metrics (will try to use psutil if available)
    monitor.add_performance_metrics()

    # Add custom domain metrics
    monitor.track_data_operation_metrics(
        "DECONVOLUTION", {"reaction_count": 4, "mse": 0.00045, "r_squared": 0.9876, "method": "ads"}
    )

    # Add optimization metrics
    monitor.track_optimization_metrics(
        {
            "iteration_count": 200,
            "convergence_value": 0.00001,
            "optimization_method": "differential_evolution",
            "mse": 0.00123,
        }
    )

    completed = monitor.end_operation_tracking()

    print("Performance and domain metrics collected:")
    for key, value in completed.custom_metrics.items():
        print(f"  {key}: {value}")
    print()

    # Get metrics for aggregation
    aggregation_metrics = monitor.get_operation_metrics_for_aggregation()
    print("Metrics ready for aggregation:")
    for key, value in aggregation_metrics.items():
        if key != "components":  # Skip empty components for cleaner output
            print(f"  {key}: {value}")
    print()


def main():
    """Run all demonstrations."""
    print("STAGE 3 ENHANCED OPERATION MONITOR DEMONSTRATION")
    print("This demo showcases the enhanced metrics collection capabilities")
    print("implemented in Stage 3 of the log aggregation system.")

    demonstrate_metrics_extractor()
    demonstrate_enhanced_operation_tracking()
    demonstrate_context_manager()
    demonstrate_aggregator_integration()
    demonstrate_performance_metrics()

    print("\n" + "=" * 60)
    print("STAGE 3 DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nKey Stage 3 features demonstrated:")
    print("✅ Enhanced OperationMetrics with custom metrics")
    print("✅ LogMetricsExtractor for automatic metric parsing")
    print("✅ Nested operation tracking with stack management")
    print("✅ Context manager for easy operation tracking")
    print("✅ Integration with OperationAggregator")
    print("✅ Performance and domain-specific metrics")
    print("✅ Timeout handling and status management")
    print("✅ Request/response tracking")
    print("✅ Error and warning counting")
    print("✅ Automatic metrics extraction from log messages")


if __name__ == "__main__":
    main()
