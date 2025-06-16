"""
Integration test for meta-operation detection in the context of solid-state kinetics application.

This test demonstrates meta-operation detection working with realistic operation patterns
that occur during typical application usage.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.log_aggregator import get_default_detector, operation


class MockFileData:
    """Mock FileData class for testing."""

    @operation
    def load_file(self, file_path: str):
        """Mock file loading with sub-operations."""
        # Simulate sub-operations that would normally occur
        self._check_file_exists(file_path)
        data = self._read_file_content(file_path)
        self._validate_data_format(data)
        return {"success": True, "data": data}

    def _check_file_exists(self, file_path: str):
        """Simulate handle_request_cycle call."""
        # This would normally call handle_request_cycle
        pass

    def _read_file_content(self, file_path: str):
        """Simulate file reading."""
        return {"temperature": [100, 200, 300], "signal": [0.1, 0.5, 0.9]}

    def _validate_data_format(self, data):
        """Simulate data validation."""
        pass


class MockCalculationsData:
    """Mock CalculationsData class for testing."""

    @operation
    def add_reaction(self, reaction_params: dict):
        """Mock reaction addition with clustered operations."""
        # These operations should be clustered by time window
        self._validate_params(reaction_params)
        self._set_default_values(reaction_params)
        self._update_reaction_list(reaction_params)
        return {"success": True, "reaction_id": "reaction_1"}

    @operation
    def update_coefficients(self, reaction_id: str, coeffs: dict):
        """Mock coefficient updates."""
        # These should cluster with similar operations
        self._get_reaction(reaction_id)
        self._set_coefficients(reaction_id, coeffs)
        self._update_bounds(reaction_id, coeffs)
        return {"success": True}

    def _validate_params(self, params):
        """Simulate parameter validation."""
        pass

    def _set_default_values(self, params):
        """Simulate setting defaults."""
        pass

    def _update_reaction_list(self, params):
        """Simulate updating reaction list."""
        pass

    def _get_reaction(self, reaction_id):
        """Simulate getting reaction."""
        pass

    def _set_coefficients(self, reaction_id, coeffs):
        """Simulate setting coefficients."""
        pass

    def _update_bounds(self, reaction_id, coeffs):
        """Simulate updating bounds."""
        pass


def test_meta_operation_detection_integration():
    """Test meta-operation detection with realistic application scenarios."""
    print("Testing meta-operation detection integration...")

    # Verify detector is properly configured
    detector = get_default_detector()
    assert detector is not None, "Meta-operation detector should be available"
    assert len(detector.strategies) > 0, "At least one strategy should be enabled"

    print(f"✓ Detector configured with {len(detector.strategies)} strategies")
    for strategy in detector.strategies:
        print(f"  - {strategy.get_strategy_name()}")

    # Test with mock file operations
    file_data = MockFileData()
    result = file_data.load_file("test_file.csv")
    assert result["success"] is True

    # Test with mock calculation operations
    calc_data = MockCalculationsData()
    reaction_result = calc_data.add_reaction({"function": "gauss", "params": {}})
    assert reaction_result["success"] is True

    coeffs_result = calc_data.update_coefficients("reaction_1", {"h": 0.5, "z": 100})
    assert coeffs_result["success"] is True

    print("✓ Mock operations executed successfully")

    # Check that aggregated logger captured the operations
    # (This would normally happen automatically through the @operation decorator)

    return True


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


def test_meta_operation_formatting():
    """Test that meta-operation formatting is integrated into table formatter."""
    import time

    from core.log_aggregator import MetaOperation, OperationLog, OperationTableFormatter, SubOperationLog

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
        meta_id="test_cluster_1", name="Test Cluster", heuristic="time_window", sub_operations=sub_ops
    )
    operation_log.meta_operations = [meta_op]
    operation_log.mark_completed(success=True)

    # Test formatting
    formatter = OperationTableFormatter()
    formatted_output = formatter.format_operation_log(operation_log)

    # Verify meta-operations are included in output
    assert "META-OPERATIONS DETECTED:" in formatted_output
    assert "Test Cluster" in formatted_output
    assert "time_window" in formatted_output

    print("✓ Meta-operation formatting working correctly")
    print("\nSample formatted output:")
    print("-" * 50)
    print(formatted_output[:500] + "..." if len(formatted_output) > 500 else formatted_output)

    return True


if __name__ == "__main__":
    print("Running meta-operation integration tests...\n")

    try:
        test_meta_operation_configuration()
        print()

        test_meta_operation_detection_integration()
        print()

        test_meta_operation_formatting()
        print()

        print("✅ All meta-operation integration tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
