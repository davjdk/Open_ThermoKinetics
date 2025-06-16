"""
Tests for meta-operation detection strategies.

This module contains tests for all detection strategies to verify
they correctly identify and group related sub-operations.
"""

from typing import List

import pytest

from src.core.log_aggregator.detection_strategies import (
    FrequencyThresholdStrategy,
    NameSimilarityStrategy,
    SequenceCountStrategy,
    TargetClusterStrategy,
    TargetSimilarityStrategy,
    TimeWindowClusterStrategy,
)
from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.sub_operation_log import SubOperationLog


class TestTimeWindowClusterStrategy:
    """Test time-based clustering strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = TimeWindowClusterStrategy(time_window_ms=50.0)

    def test_operations_within_time_window_are_clustered(self):
        """Test that operations within time window are grouped together."""
        # Create operations with timestamps within 50ms window
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "SET_VALUE", "file_data", 10.020),  # 20ms later
            SubOperationLog(3, "UPDATE_VALUE", "file_data", 10.045),  # 45ms from first
            SubOperationLog(4, "GET_VALUE", "series_data", 10.200),  # 200ms later
        ]

        # Set end times
        for i, op in enumerate(ops):
            op.end_time = op.start_time + 0.001
            op.execution_time = 0.001

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # Test clustering for operations within window
        result1 = self.strategy.detect(ops[0], context)
        result2 = self.strategy.detect(ops[1], context)
        result3 = self.strategy.detect(ops[2], context)
        result4 = self.strategy.detect(ops[3], context)

        # First three operations should be in same cluster
        assert result1 is not None
        assert result2 == result1  # Same cluster ID
        assert result3 == result1  # Same cluster ID

        # Fourth operation should be separate (or None)
        assert result4 != result1

    def test_single_operation_not_clustered(self):
        """Test that single operations are not clustered."""
        ops = [SubOperationLog(1, "GET_VALUE", "file_data", 10.000)]
        ops[0].end_time = ops[0].start_time + 0.001
        ops[0].execution_time = 0.001

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        result = self.strategy.detect(ops[0], context)
        assert result is None

    def test_configure_time_window(self):
        """Test configuration of time window parameter."""
        self.strategy.configure(time_window_ms=100.0)
        assert self.strategy.time_window_ms == 100.0


class TestNameSimilarityStrategy:
    """Test name-based clustering strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = NameSimilarityStrategy(
            name_pattern="GET_.*|SET_.*|UPDATE_.*", prefix_length=3, case_sensitive=False
        )

    def test_operations_with_similar_prefixes_are_clustered(self):
        """Test that operations with same prefix are grouped."""
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "GET_DF_DATA", "file_data", 10.020),
            SubOperationLog(3, "SET_VALUE", "file_data", 10.040),
            SubOperationLog(4, "SET_CONFIG", "file_data", 10.060),
            SubOperationLog(5, "LOAD_FILE", "file_data", 10.080),
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # Test clustering
        result1 = self.strategy.detect(ops[0], context)  # GET_VALUE
        result2 = self.strategy.detect(ops[1], context)  # GET_DF_DATA
        result3 = self.strategy.detect(ops[2], context)  # SET_VALUE
        result4 = self.strategy.detect(ops[3], context)  # SET_CONFIG
        result5 = self.strategy.detect(ops[4], context)  # LOAD_FILE

        # GET operations should be clustered together
        assert result1 is not None
        assert result2 == result1

        # SET operations should be clustered together
        assert result3 is not None
        assert result4 == result3

        # LOAD operation should be different or None (only one)
        assert result5 != result1
        assert result5 != result3

    def test_regex_pattern_matching(self):
        """Test regex pattern matching functionality."""
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "SET_CONFIG", "file_data", 10.020),
            SubOperationLog(3, "UPDATE_STATUS", "file_data", 10.040),
            SubOperationLog(4, "CALCULATE_RESULT", "file_data", 10.060),
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops  # Operations matching pattern should be clustered
        result1 = self.strategy.detect(ops[0], context)  # GET_VALUE - matches pattern
        result2 = self.strategy.detect(ops[1], context)  # SET_CONFIG - matches pattern
        result3 = self.strategy.detect(ops[2], context)  # UPDATE_STATUS - matches pattern
        # CALCULATE_RESULT - no match, not used in assertions

        # Pattern matching should take precedence over prefix matching
        assert result1 is not None and "name_pattern" in result1
        assert result2 is not None and "name_pattern" in result2
        assert result3 is not None and "name_pattern" in result3
        assert result1 == result2 == result3

    def test_case_sensitivity(self):
        """Test case sensitivity configuration."""
        self.strategy = NameSimilarityStrategy(case_sensitive=True)

        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "GET_DATA", "file_data", 10.010),  # Same prefix, same case
            SubOperationLog(3, "get_value", "file_data", 10.020),  # Different case
            SubOperationLog(4, "get_data", "file_data", 10.030),  # Different case
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        result1 = self.strategy.detect(ops[0], context)  # GET_VALUE
        result2 = self.strategy.detect(ops[1], context)  # GET_DATA
        result3 = self.strategy.detect(ops[2], context)  # get_value
        result4 = self.strategy.detect(ops[3], context)  # get_data

        # With case sensitivity, uppercase and lowercase should form separate groups
        assert result1 is not None  # Uppercase GET group
        assert result2 == result1  # Same uppercase GET group
        assert result3 is not None  # Lowercase get group
        assert result4 == result3  # Same lowercase get group
        assert result1 != result3  # Different groups due to case sensitivity


class TestTargetSimilarityStrategy:
    """Test target-based clustering strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = TargetSimilarityStrategy(min_sequence_length=2)

    def test_consecutive_operations_with_same_target_are_clustered(self):
        """Test that consecutive operations with same target are grouped."""
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "SET_VALUE", "file_data", 10.020),
            SubOperationLog(3, "UPDATE_VALUE", "file_data", 10.040),
            SubOperationLog(4, "GET_VALUE", "series_data", 10.060),
            SubOperationLog(5, "SET_VALUE", "series_data", 10.080),
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # Test clustering
        result1 = self.strategy.detect(ops[0], context)
        result2 = self.strategy.detect(ops[1], context)
        result3 = self.strategy.detect(ops[2], context)
        result4 = self.strategy.detect(ops[3], context)
        result5 = self.strategy.detect(ops[4], context)

        # file_data operations should be clustered
        assert result1 is not None
        assert result2 == result1
        assert result3 == result1

        # series_data operations should be clustered
        assert result4 is not None
        assert result5 == result4

        # Different targets should have different cluster IDs
        assert result1 != result4

    def test_single_target_operation_not_clustered(self):
        """Test that single operations with a target are not clustered."""
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "SET_VALUE", "series_data", 10.020),  # Different target
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        result1 = self.strategy.detect(ops[0], context)
        result2 = self.strategy.detect(ops[1], context)

        # Single operations should not be clustered
        assert result1 is None
        assert result2 is None


class TestSequenceCountStrategy:
    """Test sequence count clustering strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = SequenceCountStrategy(min_sequence=3, status_filter=["OK", "Error"])

    def test_consecutive_similar_operations_are_clustered(self):
        """Test that consecutive operations of same type are grouped."""
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000, status="OK"),
            SubOperationLog(2, "GET_VALUE", "file_data", 10.020, status="OK"),
            SubOperationLog(3, "GET_VALUE", "file_data", 10.040, status="OK"),
            SubOperationLog(4, "GET_VALUE", "file_data", 10.060, status="OK"),
            SubOperationLog(5, "SET_VALUE", "file_data", 10.080, status="OK"),
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # Test clustering - first 4 operations should be clustered
        result1 = self.strategy.detect(ops[0], context)
        result2 = self.strategy.detect(ops[1], context)
        result3 = self.strategy.detect(ops[2], context)
        result4 = self.strategy.detect(ops[3], context)
        result5 = self.strategy.detect(ops[4], context)

        # First four GET_VALUE operations should be clustered
        assert result1 is not None
        assert result2 == result1
        assert result3 == result1
        assert result4 == result1

        # SET_VALUE operation should not be clustered (only 1)
        assert result5 is None

    def test_error_sequences_are_clustered(self):
        """Test that sequences of error operations are grouped."""
        ops = [
            SubOperationLog(1, "LOAD_FILE", "file_data", 10.000, status="Error"),
            SubOperationLog(2, "LOAD_FILE", "file_data", 10.020, status="Error"),
            SubOperationLog(3, "LOAD_FILE", "file_data", 10.040, status="Error"),
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # All error operations should be clustered
        result1 = self.strategy.detect(ops[0], context)
        result2 = self.strategy.detect(ops[1], context)
        result3 = self.strategy.detect(ops[2], context)

        assert result1 is not None
        assert result2 == result1
        assert result3 == result1
        assert "Error" in result1


class TestFrequencyThresholdStrategy:
    """Test frequency threshold clustering strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = FrequencyThresholdStrategy(
            freq_threshold=5, freq_window_ms=1000, operation_whitelist=["GET_VALUE", "SET_VALUE"]
        )

    def test_high_frequency_operations_are_clustered(self):
        """Test that high-frequency operations are grouped."""
        # Create 6 GET_VALUE operations within 1 second
        ops = []
        base_time = 10.000
        for i in range(6):
            op = SubOperationLog(i + 1, "GET_VALUE", "file_data", base_time + i * 0.1)
            op.end_time = op.start_time + 0.001
            ops.append(op)

        # Add one operation outside the window
        ops.append(SubOperationLog(7, "GET_VALUE", "file_data", base_time + 2.0))

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # Operations within the high-frequency window should be clustered
        results = []
        for op in ops[:6]:  # First 6 operations
            result = self.strategy.detect(op, context)
            results.append(result)

        # All operations in high-frequency window should have same cluster ID
        assert all(r is not None for r in results)
        assert all(r == results[0] for r in results)

        # Operation outside window should not be clustered with others
        result_outside = self.strategy.detect(ops[6], context)
        assert result_outside != results[0]

    def test_whitelist_filtering(self):
        """Test that only whitelisted operations are considered."""
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "GET_VALUE", "file_data", 10.100),
            SubOperationLog(3, "GET_VALUE", "file_data", 10.200),
            SubOperationLog(4, "GET_VALUE", "file_data", 10.300),
            SubOperationLog(5, "GET_VALUE", "file_data", 10.400),
            SubOperationLog(6, "LOAD_FILE", "file_data", 10.500),  # Not in whitelist
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops  # GET_VALUE operations should be considered for clustering
        # (We don't need to assert the result, just verify it doesn't crash)
        self.strategy.detect(ops[0], context)

        # LOAD_FILE operation should not be considered (not in whitelist)
        result_load = self.strategy.detect(ops[5], context)

        assert result_load is None  # Not in whitelist


class TestTargetClusterStrategy:
    """Test enhanced target clustering with gap tolerance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = TargetClusterStrategy(
            target_list=["file_data", "series_data", "calculation_data"],
            max_gap=1,
            strict_sequence=False,
            min_cluster_size=2,
        )

    def test_target_clustering_with_gaps(self):
        """Test that target operations are clustered despite gaps."""
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "SET_VALUE", "file_data", 10.020),
            SubOperationLog(3, "UPDATE_VALUE", "series_data", 10.040),  # Gap
            SubOperationLog(4, "SAVE_DATA", "file_data", 10.060),  # Back to file_data
            SubOperationLog(5, "GET_VALUE", "file_data", 10.080),
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # file_data operations should be clustered despite the gap
        result1 = self.strategy.detect(ops[0], context)  # file_data
        result2 = self.strategy.detect(ops[1], context)  # file_data
        result3 = self.strategy.detect(ops[2], context)  # series_data
        result4 = self.strategy.detect(ops[3], context)  # file_data
        result5 = self.strategy.detect(ops[4], context)  # file_data

        # file_data operations should share cluster ID
        assert result1 is not None
        assert result2 == result1
        assert result4 == result1
        assert result5 == result1

        # series_data operation should be separate (only 1)
        assert result3 is None  # Single operation, below min_cluster_size

    def test_strict_sequence_mode(self):
        """Test strict sequence mode without gap tolerance."""
        self.strategy.configure(strict_sequence=True)

        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "SET_VALUE", "file_data", 10.020),
            SubOperationLog(3, "UPDATE_VALUE", "series_data", 10.040),  # Breaks sequence
            SubOperationLog(4, "SAVE_DATA", "file_data", 10.060),
            SubOperationLog(5, "GET_VALUE", "file_data", 10.080),
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # In strict mode, gap should break the cluster
        result1 = self.strategy.detect(ops[0], context)  # file_data
        result2 = self.strategy.detect(ops[1], context)  # file_data
        result4 = self.strategy.detect(ops[3], context)  # file_data after gap
        result5 = self.strategy.detect(ops[4], context)  # file_data

        # First two should be clustered
        assert result1 is not None
        assert result2 == result1

        # Operations after gap should form new cluster
        assert result4 is not None
        assert result5 == result4
        assert result4 != result1  # Different cluster

    def test_target_list_filtering(self):
        """Test that only specified targets are considered."""
        ops = [
            SubOperationLog(1, "GET_VALUE", "file_data", 10.000),
            SubOperationLog(2, "SET_VALUE", "file_data", 10.020),
            SubOperationLog(3, "UPDATE_VALUE", "unknown_target", 10.040),  # Not in list
            SubOperationLog(4, "SAVE_DATA", "unknown_target", 10.060),
        ]

        context = OperationLog("TEST_OPERATION")
        context.sub_operations = ops

        # file_data operations should be clustered
        result1 = self.strategy.detect(ops[0], context)
        result2 = self.strategy.detect(ops[1], context)

        # unknown_target operations should not be considered
        result3 = self.strategy.detect(ops[2], context)
        result4 = self.strategy.detect(ops[3], context)

        assert result1 is not None
        assert result2 == result1
        assert result3 is None  # Not in target_list
        assert result4 is None  # Not in target_list


@pytest.fixture
def sample_operations() -> List[SubOperationLog]:
    """Create sample operations for testing."""
    return [
        SubOperationLog(1, "GET_VALUE", "file_data", 10.000, status="OK"),
        SubOperationLog(2, "SET_VALUE", "file_data", 10.020, status="OK"),
        SubOperationLog(3, "UPDATE_VALUE", "file_data", 10.025, status="OK"),
        SubOperationLog(4, "GET_VALUE", "file_data", 10.030, status="OK"),
        SubOperationLog(5, "SAVE_DATA", "file_data", 10.040, status="OK"),
        SubOperationLog(6, "GET_VALUE", "series_data", 10.200, status="OK"),
        SubOperationLog(7, "SET_VALUE", "series_data", 10.220, status="OK"),
        SubOperationLog(8, "UPDATE_VALUE", "series_data", 10.225, status="OK"),
    ]


def test_integration_multiple_strategies(sample_operations):
    """Test that multiple strategies can work together without conflicts."""
    context = OperationLog("TEST_OPERATION")
    context.sub_operations = sample_operations

    # Initialize multiple strategies
    time_strategy = TimeWindowClusterStrategy(time_window_ms=50.0)
    target_strategy = TargetSimilarityStrategy(min_sequence_length=2)
    name_strategy = NameSimilarityStrategy(name_pattern="GET_.*|SET_.*")

    strategies = [time_strategy, target_strategy, name_strategy]

    # Apply all strategies to each operation
    results = {}
    for strategy in strategies:
        strategy_name = strategy.get_strategy_name()
        results[strategy_name] = []

        for op in sample_operations:
            result = strategy.detect(op, context)
            results[strategy_name].append(result)

    # Verify that strategies produce consistent results
    # (Each strategy should identify some clusters)
    for strategy_name, strategy_results in results.items():
        # At least some operations should be clustered by each strategy
        non_none_results = [r for r in strategy_results if r is not None]
        assert len(non_none_results) > 0, f"Strategy {strategy_name} found no clusters"


if __name__ == "__main__":
    pytest.main([__file__])
    pytest.main([__file__])
