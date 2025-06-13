"""
Test implementation of Stage 3: Optimization Monitoring.

This test demonstrates the new monitoring capabilities including
optimization tracking, performance monitoring, and operation flow analysis.
"""

import logging
import time

from src.log_aggregator.aggregation_engine import AggregationEngine
from src.log_aggregator.operation_monitor import OperationMonitor, OperationMonitoringConfig
from src.log_aggregator.optimization_monitor import OptimizationMonitor, OptimizationMonitoringConfig
from src.log_aggregator.performance_monitor import PerformanceMonitor, PerformanceMonitoringConfig


def test_optimization_monitoring():
    """Test optimization monitoring functionality."""
    print("🚀 Testing Optimization Monitoring")
    print("-" * 40)

    config = OptimizationMonitoringConfig(update_interval=0.5, progress_report_interval=2.0, convergence_window=5)

    monitor = OptimizationMonitor(config)

    # Start a mock optimization
    monitor.start_optimization(
        operation_id="test_deconvolution_001",
        operation_type="DECONVOLUTION",
        max_iterations=100,
        parameters={"function_type": "ads", "reactions": 3},
    )

    # Simulate optimization progress
    for i in range(10):
        time.sleep(0.2)
        error = 1000 * (0.9**i)  # Decreasing error
        monitor.update_optimization(
            operation_id="test_deconvolution_001",
            iteration=i + 1,
            error=error,
            parameters={"current_coeffs": {"h": 0.1, "z": 250.0}},
        )

    # Complete optimization
    monitor.complete_optimization(operation_id="test_deconvolution_001", final_error=100.0)

    # Get statistics
    stats = monitor.get_statistics()
    print(f"✅ Optimization completed. Stats: {stats}")

    monitor.shutdown()
    print("")


def test_performance_monitoring():
    """Test performance monitoring functionality."""
    print("📊 Testing Performance Monitoring")
    print("-" * 40)

    config = PerformanceMonitoringConfig(
        collection_interval=1.0, memory_threshold_mb=100.0, processing_time_threshold_ms=50.0
    )

    monitor = PerformanceMonitor(config)

    # Simulate processing workload
    for i in range(5):
        start_time = monitor.record_processing_start()

        # Simulate work
        time.sleep(0.1)

        monitor.record_processing_end(start_time, records_processed=10, records_aggregated=3)
        monitor.record_component_timing("pattern_detection", 20.0)
        monitor.record_component_timing("aggregation", 15.0)
        monitor.record_buffer_size(50 + i * 10)

    time.sleep(1.5)  # Let monitoring thread collect metrics

    # Generate performance report
    report = monitor.generate_performance_report()
    print("📈 Performance Report:")
    print(report)

    # Get optimization suggestions
    suggestions = monitor.optimize_performance()
    if suggestions:
        print("💡 Performance Suggestions:")
        for category, suggestion in suggestions.items():
            print(f"  {category}: {suggestion}")

    monitor.shutdown()
    print("")


def test_operation_monitoring():
    """Test operation monitoring functionality."""
    print("🔄 Testing Operation Monitoring")
    print("-" * 40)

    config = OperationMonitoringConfig(
        operation_timeout_seconds=30.0, slow_operation_threshold_ms=100.0, enable_flow_analysis=True
    )

    monitor = OperationMonitor(config)

    # Simulate operation flow
    operations = [
        ("LOAD_FILE", "FileData", {"filename": "test.csv"}),
        ("GET_DF_DATA", "FileData", {"file_id": "test.csv"}),
        ("DECONVOLUTION", "Calculations", {"reactions": 3}),
        ("UPDATE_VALUE", "CalculationsData", {"path": ["test.csv", "reaction_0", "h"]}),
    ]

    operation_ids = []

    # Start operations
    for i, (op_type, module, params) in enumerate(operations):
        op_id = f"op_{op_type}_{i}"
        operation_ids.append(op_id)

        monitor.start_operation(operation_id=op_id, operation_type=op_type, module=module, parameters=params)

        # Simulate processing time
        time.sleep(0.05)

    # Complete operations
    for op_id in operation_ids:
        time.sleep(0.02)
        monitor.complete_operation(operation_id=op_id, result={"status": "success"})

    time.sleep(1.0)  # Let monitoring analyze

    # Generate operation report
    report = monitor.generate_operation_report()
    print("🔄 Operation Report:")
    print(report)

    # Get performance insights
    insights = monitor.get_performance_insights()
    if insights["recommendations"]:
        print("💡 Operation Insights:")
        for recommendation in insights["recommendations"]:
            print(f"  - {recommendation}")

    monitor.shutdown()
    print("")


def test_integrated_monitoring():
    """Test integrated monitoring in AggregationEngine."""
    print("🔧 Testing Integrated Monitoring")
    print("-" * 40)

    # Create aggregation engine with monitoring
    engine = AggregationEngine(
        min_pattern_entries=2,
        enable_optimization_monitoring=True,
        enable_performance_monitoring=True,
        enable_operation_monitoring=True,
    )
    # Simulate some processing
    import logging

    from src.log_aggregator.buffer_manager import BufferedLogRecord
    from src.log_aggregator.pattern_detector import LogPattern

    # Create mock patterns
    mock_record = logging.LogRecord(
        name="test_logger", level=logging.INFO, pathname="test.py", lineno=1, msg="Test message", args=(), exc_info=None
    )

    buffered_record = BufferedLogRecord(mock_record, timestamp=time.time())

    patterns = [
        LogPattern(
            pattern_id="test_pattern_1",
            template="Test message",
            records=[buffered_record, buffered_record],
            count=2,
            first_seen=time.time(),
            last_seen=time.time(),
        )
    ]

    # Process patterns with monitoring
    aggregated = engine.aggregate_patterns(patterns)

    print(f"✅ Processed {len(patterns)} patterns into {len(aggregated)} aggregations")

    # Generate monitoring report
    report = engine.generate_monitoring_report()
    print("📊 Integrated Monitoring Report:")
    print(report)

    # Get optimization suggestions
    suggestions = engine.optimize_performance()
    if suggestions:
        print("💡 Performance Optimization Suggestions:")
        for category, suggestion in suggestions.items():
            print(f"  {category}: {suggestion}")

    engine.shutdown_monitoring()
    print("")


def run_stage3_tests():
    """Run all Stage 3 monitoring tests."""
    print("🎯 STAGE 3: OPTIMIZATION MONITORING TESTS")
    print("=" * 60)
    print("")

    try:
        test_optimization_monitoring()
        test_performance_monitoring()
        test_operation_monitoring()
        test_integrated_monitoring()

        print("✅ ALL STAGE 3 TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    run_stage3_tests()
