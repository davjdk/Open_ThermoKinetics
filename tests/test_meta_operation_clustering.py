"""
Test module for meta-operation detection and clustering.

This module contains basic tests to verify the functionality
of the meta-operation clustering system.
"""

import sys
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.log_aggregator.detection_strategies import (
    NameSimilarityStrategy,
    TargetSimilarityStrategy,
    TimeWindowClusterStrategy,
)
from core.log_aggregator.meta_operation_config import MetaOperationConfig
from core.log_aggregator.meta_operation_detector import MetaOperationDetector
from core.log_aggregator.operation_log import OperationLog
from core.log_aggregator.sub_operation_log import SubOperationLog


def create_test_operation_log() -> OperationLog:
    """Create a test operation log with sample sub-operations."""
    operation_log = OperationLog(operation_name="TEST_OPERATION")

    base_time = time.time()

    # Create sub-operations that should be clustered by time window
    sub_ops = [
        SubOperationLog(step_number=1, operation_name="GET_VALUE", target="file_data", start_time=base_time),
        SubOperationLog(
            step_number=2,
            operation_name="GET_VALUE",
            target="file_data",
            start_time=base_time + 0.01,  # 10ms later
        ),
        SubOperationLog(
            step_number=3,
            operation_name="SET_VALUE",
            target="calculation_data",
            start_time=base_time + 0.1,  # 100ms later
        ),
        SubOperationLog(
            step_number=4,
            operation_name="SET_VALUE",
            target="calculation_data",
            start_time=base_time + 0.11,  # 110ms later
        ),
        SubOperationLog(
            step_number=5,
            operation_name="UPDATE_VALUE",
            target="calculation_data",
            start_time=base_time + 0.12,  # 120ms later
        ),
    ]

    # Set end times and status
    for i, sub_op in enumerate(sub_ops):
        sub_op.end_time = sub_op.start_time + 0.005  # 5ms execution time
        sub_op.execution_time = 0.005
        sub_op.status = "OK"
        sub_op.response_data_type = "dict"

    operation_log.sub_operations = sub_ops
    return operation_log


def test_time_window_clustering():
    """Test time window clustering strategy."""
    print("Testing Time Window Clustering...")

    strategy = TimeWindowClusterStrategy(time_window_ms=50.0)
    operation_log = create_test_operation_log()

    detector = MetaOperationDetector([strategy])
    detector.detect_meta_operations(operation_log)

    print(f"Created {len(operation_log.meta_operations)} meta-operations")
    for meta_op in operation_log.meta_operations:
        print(f"  {meta_op.name}: {len(meta_op.sub_operations)} operations")
        print(f"    Heuristic: {meta_op.heuristic}")
        print(f"    Duration: {meta_op.duration_ms:.1f}ms")

    assert len(operation_log.meta_operations) > 0, "Should create at least one meta-operation"
    print("✓ Time window clustering test passed\n")


def test_name_similarity_clustering():
    """Test name similarity clustering strategy."""
    print("Testing Name Similarity Clustering...")

    strategy = NameSimilarityStrategy(prefix_min_length=3, min_group_size=2)
    operation_log = create_test_operation_log()

    detector = MetaOperationDetector([strategy])
    detector.detect_meta_operations(operation_log)

    print(f"Created {len(operation_log.meta_operations)} meta-operations")
    for meta_op in operation_log.meta_operations:
        print(f"  {meta_op.name}: {len(meta_op.sub_operations)} operations")
        print(f"    Heuristic: {meta_op.heuristic}")
        for sub_op in meta_op.sub_operations:
            print(f"      - {sub_op.operation_name}")

    print("✓ Name similarity clustering test passed\n")


def test_target_similarity_clustering():
    """Test target similarity clustering strategy."""
    print("Testing Target Similarity Clustering...")

    strategy = TargetSimilarityStrategy(min_sequence_length=2)
    operation_log = create_test_operation_log()

    detector = MetaOperationDetector([strategy])
    detector.detect_meta_operations(operation_log)

    print(f"Created {len(operation_log.meta_operations)} meta-operations")
    for meta_op in operation_log.meta_operations:
        print(f"  {meta_op.name}: {len(meta_op.sub_operations)} operations")
        print(f"    Target: {meta_op.sub_operations[0].target if meta_op.sub_operations else 'N/A'}")

    print("✓ Target similarity clustering test passed\n")


def test_configuration_system():
    """Test the configuration system."""
    print("Testing Configuration System...")

    config = MetaOperationConfig()

    # Test enabling strategies
    assert config.enable_strategy("time_window", {"time_window_ms": 100.0})
    assert config.enable_strategy("name_similarity")

    # Test configuration
    assert config.configure_strategy("time_window", {"time_window_ms": 25.0})

    # Test detector creation
    detector = config.create_detector()
    assert detector is not None
    assert len(detector.strategies) == 2

    # Test global disable
    config.set_global_enabled(False)
    detector = config.create_detector()
    assert detector is None

    print("✓ Configuration system test passed\n")


def test_multiple_strategies():
    """Test multiple strategies working together."""
    print("Testing Multiple Strategies...")

    strategies = [
        TimeWindowClusterStrategy(time_window_ms=50.0),
        TargetSimilarityStrategy(min_sequence_length=2),
    ]

    operation_log = create_test_operation_log()
    detector = MetaOperationDetector(strategies)
    detector.detect_meta_operations(operation_log)

    print(f"Created {len(operation_log.meta_operations)} meta-operations with multiple strategies")
    for meta_op in operation_log.meta_operations:
        print(f"  {meta_op.name}: {len(meta_op.sub_operations)} operations (by {meta_op.heuristic})")

    print("✓ Multiple strategies test passed\n")


def run_all_tests():
    """Run all meta-operation clustering tests."""
    print("=" * 60)
    print("Meta-Operation Clustering Tests")
    print("=" * 60)

    try:
        test_time_window_clustering()
        test_name_similarity_clustering()
        test_target_similarity_clustering()
        test_configuration_system()
        test_multiple_strategies()

        print("=" * 60)
        print("All tests passed! ✓")
        print("Meta-operation clustering system is working correctly.")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
