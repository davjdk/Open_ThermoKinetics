"""
Tests for comprehensive OperationType coverage.

This module tests that all OperationType enum values work correctly
with the operation logging system.
"""

import pytest

from src.core.app_settings import OperationType
from src.core.log_aggregator import operation


class TestOperationTypeCoverage:
    """Test cases for all OperationType enum values."""

    def test_all_operation_types_work_with_decorator(self, all_operation_types, mock_aggregated_logger):
        """Test that all OperationType values work with @operation decorator."""

        for op_type in all_operation_types:
            # Create a test function for each operation type
            @operation(op_type.value)
            def test_operation():
                return f"executed_{op_type.value}"

            # Execute the operation
            result = test_operation()

            # Verify it executed correctly
            assert result == f"executed_{op_type.value}"

        # Verify all operations were logged
        assert mock_aggregated_logger.log_operation.call_count == len(all_operation_types)

    def test_operation_type_enum_values_as_strings(self, mock_aggregated_logger):
        """Test using OperationType enum values directly as strings."""

        # Test a few representative OperationType values
        test_operations = [
            OperationType.LOAD_FILE,
            OperationType.DECONVOLUTION,
            OperationType.MODEL_BASED_CALCULATION,
            OperationType.ADD_REACTION,
            OperationType.GET_VALUE,
        ]

        for op_type in test_operations:

            @operation(op_type.value)
            def enum_operation():
                return f"enum_test_{op_type.value}"

            result = enum_operation()
            assert result == f"enum_test_{op_type.value}"

        assert mock_aggregated_logger.log_operation.call_count == len(test_operations)

    def test_operation_names_in_logs(self, all_operation_types, mock_aggregated_logger):
        """Test that operation names appear correctly in logs."""

        # Test first 5 operations to avoid too many calls
        test_operations = all_operation_types[:5]

        for op_type in test_operations:

            @operation(op_type.value)
            def named_operation():
                return "success"

            named_operation()

        # Verify operation names are in the logged operations
        logged_operations = [call[0][0] for call in mock_aggregated_logger.log_operation.call_args_list]

        for i, op_type in enumerate(test_operations):
            assert logged_operations[i].operation_name == op_type.value

    def test_operation_type_validation(self):
        """Test that OperationType enum contains expected operations."""
        # Verify key operations are present
        expected_operations = [
            "load_file",
            "deconvolution",
            "model_based_calculation",
            "model_fit_calculation",
            "model_free_calculation",
            "add_reaction",
            "remove_reaction",
            "get_value",
            "set_value",
            "update_value",
        ]

        operation_values = [op.value for op in OperationType]

        for expected_op in expected_operations:
            assert expected_op in operation_values, f"Missing operation: {expected_op}"

    def test_operation_type_completeness(self, all_operation_types):
        """Test that all OperationType values are unique and well-formed."""
        # Check for uniqueness
        operation_values = [op.value for op in all_operation_types]
        assert len(operation_values) == len(set(operation_values)), "Duplicate operation values found"

        # Check that all values are non-empty strings
        for op_type in all_operation_types:
            assert isinstance(op_type.value, str), f"Operation {op_type} value is not a string"
            assert len(op_type.value) > 0, f"Operation {op_type} has empty value"
            assert "_" in op_type.value or op_type.value.islower(), f"Operation {op_type} not in snake_case"

    @pytest.mark.parametrize(
        "operation_type",
        [
            OperationType.LOAD_FILE,
            OperationType.GET_VALUE,
            OperationType.SET_VALUE,
            OperationType.DECONVOLUTION,
            OperationType.MODEL_BASED_CALCULATION,
        ],
    )
    def test_parametrized_operation_types(self, operation_type, mock_aggregated_logger):
        """Test individual operation types with parametrization."""

        @operation(operation_type.value)
        def parametrized_operation():
            return f"parametrized_{operation_type.value}"

        result = parametrized_operation()
        assert result == f"parametrized_{operation_type.value}"

        # Verify logging occurred
        mock_aggregated_logger.log_operation.assert_called()
        logged_operation = mock_aggregated_logger.log_operation.call_args[0][0]
        assert logged_operation.operation_name == operation_type.value

    def test_operation_type_string_formatting(self, all_operation_types):
        """Test that operation type strings are properly formatted for logging."""
        for op_type in all_operation_types:
            # Test that operation type values work as log identifiers
            assert op_type.value.replace("_", " ").replace("-", " ").isascii()
            assert not op_type.value.startswith("_")
            assert not op_type.value.endswith("_")
            assert "__" not in op_type.value  # No double underscores

    def test_model_operation_types_coverage(self, mock_aggregated_logger):
        """Test coverage of model-related operation types specifically."""
        model_operations = [
            OperationType.MODEL_BASED_CALCULATION,
            OperationType.MODEL_FIT_CALCULATION,
            OperationType.MODEL_FREE_CALCULATION,
            OperationType.GET_MODEL_FIT_REACTION_DF,
            OperationType.GET_MODEL_FREE_REACTION_DF,
            OperationType.PLOT_MODEL_FIT_RESULT,
            OperationType.PLOT_MODEL_FREE_RESULT,
        ]

        for op_type in model_operations:

            @operation(op_type.value)
            def model_operation():
                return f"model_{op_type.value}"

            result = model_operation()
            assert result == f"model_{op_type.value}"

        assert mock_aggregated_logger.log_operation.call_count == len(model_operations)

    def test_data_operation_types_coverage(self, mock_aggregated_logger):
        """Test coverage of data-related operation types."""
        data_operations = [
            OperationType.LOAD_FILE,
            OperationType.GET_VALUE,
            OperationType.SET_VALUE,
            OperationType.REMOVE_VALUE,
            OperationType.UPDATE_VALUE,
            OperationType.GET_DF_DATA,
            OperationType.GET_ALL_DATA,
            OperationType.GET_FULL_DATA,
            OperationType.RESET_FILE_DATA,
        ]

        for op_type in data_operations:

            @operation(op_type.value)
            def data_operation():
                return f"data_{op_type.value}"

            result = data_operation()
            assert result == f"data_{op_type.value}"

        assert mock_aggregated_logger.log_operation.call_count == len(data_operations)

    def test_calculation_operation_types_coverage(self, mock_aggregated_logger):
        """Test coverage of calculation-related operation types."""
        calc_operations = [
            OperationType.DECONVOLUTION,
            OperationType.MODEL_BASED_CALCULATION,
            OperationType.MODEL_FIT_CALCULATION,
            OperationType.MODEL_FREE_CALCULATION,
            OperationType.STOP_CALCULATION,
            OperationType.CALCULATION_FINISHED,
        ]

        for op_type in calc_operations:

            @operation(op_type.value)
            def calc_operation():
                return f"calc_{op_type.value}"

            result = calc_operation()
            assert result == f"calc_{op_type.value}"

        assert mock_aggregated_logger.log_operation.call_count == len(calc_operations)

    def test_series_operation_types_coverage(self, mock_aggregated_logger):
        """Test coverage of series-related operation types."""
        series_operations = [
            OperationType.ADD_NEW_SERIES,
            OperationType.DELETE_SERIES,
            OperationType.UPDATE_SERIES,
            OperationType.GET_SERIES,
            OperationType.GET_ALL_SERIES,
            OperationType.GET_SERIES_VALUE,
            OperationType.RENAME_SERIES,
            OperationType.SELECT_SERIES,
        ]

        for op_type in series_operations:

            @operation(op_type.value)
            def series_operation():
                return f"series_{op_type.value}"

            result = series_operation()
            assert result == f"series_{op_type.value}"

        assert mock_aggregated_logger.log_operation.call_count == len(series_operations)
