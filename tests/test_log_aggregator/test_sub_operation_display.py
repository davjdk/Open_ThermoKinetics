"""
Tests for sub-operation display functionality.

This module tests the new clean operation name functionality:
- Removing OperationType prefix from operation names
- Handling different formats of operation names
- Table formatter integration
"""

import time

from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.sub_operation_log import SubOperationLog
from src.core.log_aggregator.table_formatter import OperationTableFormatter


class TestSubOperationDisplay:
    """Test cases for clean operation name functionality."""

    def test_clean_operation_name_removes_operationtype_prefix(self):
        """Test that OperationType prefix is properly removed."""
        sub_op = SubOperationLog(
            step_number=1, operation_name="OperationType.CHECK_FILE_EXISTS", target="file_data", start_time=time.time()
        )
        assert sub_op.clean_operation_name == "CHECK_FILE_EXISTS"

    def test_clean_operation_name_handles_enum_string(self):
        """Test handling of enum string representation."""
        sub_op = SubOperationLog(
            step_number=1, operation_name="OperationType.GET_DF_DATA", target="file_data", start_time=time.time()
        )
        assert sub_op.clean_operation_name == "GET_DF_DATA"

    def test_clean_operation_name_fallback(self):
        """Test fallback to original name when no prefix."""
        sub_op = SubOperationLog(
            step_number=1, operation_name="CUSTOM_OPERATION", target="file_data", start_time=time.time()
        )
        assert sub_op.clean_operation_name == "CUSTOM_OPERATION"

    def test_clean_operation_name_with_dot_but_no_operationtype(self):
        """Test handling of names with dots but no OperationType prefix."""
        sub_op = SubOperationLog(
            step_number=1, operation_name="SomeModule.OPERATION", target="file_data", start_time=time.time()
        )
        assert sub_op.clean_operation_name == "SomeModule.OPERATION"

    def test_clean_operation_name_handles_enum_objects(self):
        """Test handling of actual OperationType enum objects."""
        from src.core.app_settings import OperationType

        sub_op = SubOperationLog(
            step_number=1,
            operation_name=OperationType.LOAD_FILE,
            target="file_data",
            start_time=time.time(),
        )
        assert sub_op.clean_operation_name == "LOAD_FILE"

        # Test another enum
        sub_op2 = SubOperationLog(
            step_number=2,
            operation_name=OperationType.ADD_REACTION,
            target="calculations_data",
            start_time=time.time(),
        )
        assert sub_op2.clean_operation_name == "ADD_REACTION"

    def test_operation_display_name_uses_clean_name(self):
        """Test that operation_display_name uses clean_operation_name."""
        sub_op = SubOperationLog(
            step_number=1, operation_name="OperationType.SET_VALUE", target="calculations_data", start_time=time.time()
        )
        assert sub_op.operation_display_name == "SET_VALUE"
        assert sub_op.operation_display_name == sub_op.clean_operation_name

    def test_table_formatter_uses_clean_names(self):
        """Test that table formatter uses clean operation names."""
        # Create operation log with sub-operations that have OperationType prefixes
        operation_log = OperationLog(operation_name="TEST_OPERATION", start_time=time.time())

        # Add sub-operations with OperationType prefixes
        sub_op1 = SubOperationLog(
            step_number=1, operation_name="OperationType.CHECK_FILE_EXISTS", target="file_data", start_time=time.time()
        )
        sub_op1.mark_completed({"data": True})

        sub_op2 = SubOperationLog(
            step_number=2, operation_name="OperationType.GET_DF_DATA", target="file_data", start_time=time.time()
        )
        sub_op2.mark_completed({"data": {"success": True}})

        operation_log.sub_operations = [sub_op1, sub_op2]
        operation_log.mark_completed(success=True)

        # Format with table formatter
        formatter = OperationTableFormatter()
        result = formatter.format_operation_log(operation_log)

        # Check that OperationType prefixes are not present in the output
        assert "OperationType.CHECK_FILE_EXISTS" not in result
        assert "OperationType.GET_DF_DATA" not in result

        # Check that clean names are present
        assert "CHECK_FILE_EXISTS" in result
        assert "GET_DF_DATA" in result

    def test_multiple_operationtype_formats(self):
        """Test handling of various OperationType formats."""
        test_cases = [
            ("OperationType.LOAD_FILE", "LOAD_FILE"),
            ("OperationType.ADD_REACTION", "ADD_REACTION"),
            ("OperationType.MODEL_BASED_CALCULATION", "MODEL_BASED_CALCULATION"),
            ("DIRECT_OPERATION", "DIRECT_OPERATION"),  # No prefix
            ("Other.MODULE_OP", "Other.MODULE_OP"),  # Different prefix
        ]

        for operation_name, expected_clean_name in test_cases:
            sub_op = SubOperationLog(
                step_number=1, operation_name=operation_name, target="test_target", start_time=time.time()
            )
            assert sub_op.clean_operation_name == expected_clean_name, (
                f"Failed for {operation_name}: expected {expected_clean_name}, " f"got {sub_op.clean_operation_name}"
            )

    def test_empty_and_none_operation_names(self):
        """Test handling of edge cases with operation names."""
        # Empty string
        sub_op1 = SubOperationLog(step_number=1, operation_name="", target="file_data", start_time=time.time())
        assert sub_op1.clean_operation_name == ""

        # Just the prefix
        sub_op2 = SubOperationLog(
            step_number=1, operation_name="OperationType.", target="file_data", start_time=time.time()
        )
        assert sub_op2.clean_operation_name == ""

        # Just OperationType
        sub_op3 = SubOperationLog(
            step_number=1, operation_name="OperationType", target="file_data", start_time=time.time()
        )
        assert sub_op3.clean_operation_name == "OperationType"
