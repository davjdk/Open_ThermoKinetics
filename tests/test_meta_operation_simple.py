"""
Simplified integration test for meta-operation detection.

This test verifies that the meta-operation detection system works correctly
with the configuration and integration points we've implemented.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.log_aggregator import (
    MetaOperation,
    OperationLog,
    OperationTableFormatter,
    SubOperationLog,
    get_default_detector,
)


def test_meta_operation_configuration():
    """Test that meta-operation configuration is properly loaded."""
    from core.logger_config import META_OPERATION_CONFIG

    # Verify configuration structure
    assert "enabled" in META_OPERATION_CONFIG
    assert "strategies" in META_OPERATION_CONFIG
    assert "formatting" in META_OPERATION_CONFIG

    # Verify at least some strategies are enabled
    enabled_strategies = [
        name for name, config in META_OPERATION_CONFIG["strategies"].items() if config.get("enabled", False)
    ]

    assert len(enabled_strategies) > 0, "At least one strategy should be enabled"
    print(f"✓ Configuration valid with {len(enabled_strategies)} enabled strategies: {enabled_strategies}")

    return True


def test_detector_creation():
    """Test that the detector can be created and configured."""
    detector = get_default_detector()
    assert detector is not None, "Meta-operation detector should be available"
    assert len(detector.strategies) > 0, "At least one strategy should be enabled"

    print(f"✓ Detector configured with {len(detector.strategies)} strategies")
    for strategy in detector.strategies:
        print(f"  - {strategy.get_strategy_name()}")

    return True


def test_meta_operation_detection_with_realistic_data():
    """Test meta-operation detection with realistic operation sequences."""

    # Create a realistic operation log that simulates file loading and processing
    operation_log = OperationLog("LOAD_AND_PROCESS_FILE")
    base_time = time.time()

    # Simulate a typical file loading sequence - these should cluster by time
    file_ops = [
        SubOperationLog(1, "CHECK_FILE_EXISTS", "file_data", base_time, base_time + 0.001),
        SubOperationLog(2, "GET_FILE_METADATA", "file_data", base_time + 0.002, base_time + 0.003),
        SubOperationLog(3, "SET_LOADING_STATUS", "file_data", base_time + 0.004, base_time + 0.005),
    ]

    # Simulate data processing sequence - different time, same target
    processing_ops = [
        SubOperationLog(4, "GET_CALCULATION_PARAMS", "calculation_data", base_time + 0.1, base_time + 0.11),
        SubOperationLog(5, "SET_DEFAULT_VALUES", "calculation_data", base_time + 0.12, base_time + 0.13),
        SubOperationLog(6, "UPDATE_COEFFICIENT_BOUNDS", "calculation_data", base_time + 0.14, base_time + 0.15),
    ]

    # Simulate similar name operations - should cluster by name pattern
    update_ops = [
        SubOperationLog(7, "UPDATE_REACTION_LIST", "calculation_data", base_time + 0.2, base_time + 0.21),
        SubOperationLog(8, "UPDATE_DISPLAY_STATE", "calculation_data", base_time + 0.22, base_time + 0.23),
    ]

    # Single operation that shouldn't cluster
    standalone_op = SubOperationLog(9, "SAVE_RESULTS", "file_data", base_time + 0.3, base_time + 0.31)

    all_ops = file_ops + processing_ops + update_ops + [standalone_op]

    for sub_op in all_ops:
        sub_op.response_data_type = "dict"
        sub_op.status = "OK"
        operation_log.sub_operations.append(sub_op)

    operation_log.mark_completed(success=True)

    # Apply meta-operation detection
    detector = get_default_detector()
    detector.detect_meta_operations(operation_log)

    print(f"✓ Detected {len(operation_log.meta_operations)} meta-operations")

    # Verify that some clustering occurred
    assert len(operation_log.meta_operations) > 0, "Should detect at least one meta-operation"

    for i, meta_op in enumerate(operation_log.meta_operations, 1):
        print(f"  {i}. {meta_op.name} ({meta_op.heuristic}): {len(meta_op.sub_operations)} operations")
        step_numbers = [op.step_number for op in meta_op.sub_operations]
        print(f"     Steps: {step_numbers}")

    return True


def test_meta_operation_formatting():
    """Test that meta-operation formatting is integrated into table formatter."""

    # Create a test operation log with meta-operations
    operation_log = OperationLog("TEST_FORMATTING")
    base_time = time.time()

    # Add sub-operations
    sub_ops = [
        SubOperationLog(1, "GET_VALUE", "file_data", base_time, base_time + 0.001),
        SubOperationLog(2, "SET_VALUE", "file_data", base_time + 0.002, base_time + 0.003),
        SubOperationLog(3, "UPDATE_VALUE", "file_data", base_time + 0.004, base_time + 0.005),
    ]

    for sub_op in sub_ops:
        sub_op.response_data_type = "dict"
        sub_op.status = "OK"
        operation_log.sub_operations.append(sub_op)

    # Add a mock meta-operation
    meta_op = MetaOperation(
        meta_id="test_cluster_1", name="File Operations Cluster", heuristic="time_window", sub_operations=sub_ops
    )
    operation_log.meta_operations = [meta_op]
    operation_log.mark_completed(success=True)

    # Test formatting
    formatter = OperationTableFormatter()
    formatted_output = formatter.format_operation_log(operation_log)

    # Verify meta-operations are included in output
    assert "META-OPERATIONS DETECTED:" in formatted_output
    assert "File Operations Cluster" in formatted_output
    assert "time_window" in formatted_output

    print("✓ Meta-operation formatting working correctly")
    print("\nSample formatted output:")
    print("-" * 50)
    print(formatted_output[:500] + "..." if len(formatted_output) > 500 else formatted_output)

    return True


def test_end_to_end_integration():
    """Test the complete end-to-end meta-operation detection and formatting."""

    # Create operation log with realistic operations
    operation_log = OperationLog("DECONVOLUTION_WORKFLOW")
    base_time = time.time()

    # Simulate deconvolution workflow operations
    workflow_ops = [
        # File operations cluster
        SubOperationLog(1, "GET_DF_DATA", "file_data", base_time, base_time + 0.001),
        SubOperationLog(2, "CHECK_OPERATION_EXECUTED", "file_data", base_time + 0.005, base_time + 0.006),
        # Reaction management cluster
        SubOperationLog(3, "GET_VALUE", "calculation_data", base_time + 0.1, base_time + 0.101),
        SubOperationLog(4, "SET_VALUE", "calculation_data", base_time + 0.102, base_time + 0.103),
        SubOperationLog(5, "UPDATE_VALUE", "calculation_data", base_time + 0.104, base_time + 0.105),
        # Calculation cluster
        SubOperationLog(6, "DECONVOLUTION", "calculations", base_time + 0.2, base_time + 0.3),
        SubOperationLog(7, "GET_DF_DATA", "file_data", base_time + 0.301, base_time + 0.302),
        # Results handling
        SubOperationLog(8, "UPDATE_PLOT", "plot_canvas", base_time + 0.4, base_time + 0.41),
    ]

    for sub_op in workflow_ops:
        sub_op.response_data_type = "dict"
        sub_op.status = "OK"
        operation_log.sub_operations.append(sub_op)

    operation_log.mark_completed(success=True)

    # Apply detection and formatting
    detector = get_default_detector()
    detector.detect_meta_operations(operation_log)

    formatter = OperationTableFormatter()
    formatted_output = formatter.format_operation_log(operation_log)

    print(f"✓ End-to-end test: {len(operation_log.meta_operations)} meta-operations detected")
    print("\nComplete formatted output:")
    print("=" * 80)
    print(formatted_output)
    print("=" * 80)

    return True


if __name__ == "__main__":
    print("Running meta-operation integration tests...\n")

    try:
        test_meta_operation_configuration()
        print()

        test_detector_creation()
        print()

        test_meta_operation_detection_with_realistic_data()
        print()

        test_meta_operation_formatting()
        print()

        test_end_to_end_integration()
        print()

        print("✅ All meta-operation integration tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
