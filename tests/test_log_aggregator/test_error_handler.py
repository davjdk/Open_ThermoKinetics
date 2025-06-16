"""
Unit tests for the error handling system in log aggregator.

Tests cover:
- ErrorAnalysis data structure
- SubOperationErrorHandler functionality
- Integration with SubOperationLog
- Error categorization and severity determination
"""

from unittest.mock import Mock, patch

from src.core.log_aggregator.error_handler import ErrorAnalysis, ErrorCategory, ErrorSeverity, SubOperationErrorHandler
from src.core.log_aggregator.sub_operation_log import SubOperationLog


class TestErrorAnalysis:
    """Test cases for ErrorAnalysis dataclass."""

    def test_error_analysis_creation(self):
        """Test ErrorAnalysis dataclass creation."""
        error_analysis = ErrorAnalysis(
            error_type=ErrorCategory.DATA_VALIDATION_ERROR,
            error_message="Invalid data format",
            error_context={"operation": "GET_VALUE", "target": "file_data"},
            severity=ErrorSeverity.HIGH,
            suggested_action="Check data format",
            technical_details="Data validation failed at step 3",
        )

        assert error_analysis.error_type == ErrorCategory.DATA_VALIDATION_ERROR
        assert error_analysis.error_message == "Invalid data format"
        assert error_analysis.severity == ErrorSeverity.HIGH
        assert error_analysis.suggested_action == "Check data format"
        assert error_analysis.technical_details == "Data validation failed at step 3"

    def test_error_analysis_to_dict(self):
        """Test conversion to dictionary format."""
        error_analysis = ErrorAnalysis(
            error_type=ErrorCategory.FILE_OPERATION_ERROR,
            error_message="File not found",
            error_context={"file_path": "/test/path.csv"},
            severity=ErrorSeverity.CRITICAL,
            suggested_action="Check file path",
            technical_details="FileNotFoundError occurred",
        )

        result_dict = error_analysis.to_dict()

        expected = {
            "type": "file_operation_error",
            "message": "File not found",
            "context": {"file_path": "/test/path.csv"},
            "severity": "critical",
            "suggested_action": "Check file path",
            "technical_details": "FileNotFoundError occurred",
        }

        assert result_dict == expected


class TestSubOperationErrorHandler:
    """Test cases for SubOperationErrorHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = SubOperationErrorHandler()

    def test_categorize_file_operation_error(self):
        """Test categorization of file operation errors."""
        # Test LOAD operation
        category = self.error_handler.categorize_error_type({"error": "file not found"}, "LOAD_FILE", "file_data")
        assert category == ErrorCategory.FILE_OPERATION_ERROR

        # Test IMPORT operation
        category = self.error_handler.categorize_error_type(
            {"error": "import failed"}, "IMPORT_REACTIONS", "calculations_data"
        )
        assert category == ErrorCategory.FILE_OPERATION_ERROR

    def test_categorize_calculation_error(self):
        """Test categorization of calculation errors."""
        # Test DECONVOLUTION operation
        category = self.error_handler.categorize_error_type(
            {"error": "optimization failed"}, "DECONVOLUTION", "calculations"
        )
        assert category == ErrorCategory.CALCULATION_ERROR

        # Test MODEL_FIT operation
        category = self.error_handler.categorize_error_type(
            {"error": "fitting error"}, "MODEL_FIT_CALCULATION", "series_data"
        )
        assert category == ErrorCategory.CALCULATION_ERROR

    def test_categorize_data_validation_error(self):
        """Test categorization of data validation errors."""
        # Test GET operation
        category = self.error_handler.categorize_error_type(
            {"error": "value not found"}, "GET_VALUE", "calculations_data"
        )
        assert category == ErrorCategory.DATA_VALIDATION_ERROR

        # Test based on error message content
        category = self.error_handler.categorize_error_type({"error": "invalid data format"}, "UNKNOWN_OP", "target")
        assert category == ErrorCategory.DATA_VALIDATION_ERROR

    def test_categorize_communication_error(self):
        """Test categorization of communication errors."""
        category = self.error_handler.categorize_error_type(
            {"error": "connection timeout"}, "SYNC_DATA", "remote_service"
        )
        assert category == ErrorCategory.COMMUNICATION_ERROR

    def test_categorize_configuration_error(self):
        """Test categorization of configuration errors."""
        category = self.error_handler.categorize_error_type(
            {"error": "invalid configuration parameter"}, "SET_CONFIG", "settings"
        )
        assert category == ErrorCategory.CONFIGURATION_ERROR

    def test_categorize_unknown_error(self):
        """Test categorization of unknown errors."""
        category = self.error_handler.categorize_error_type(
            {"error": "something went wrong"}, "UNKNOWN_OP", "unknown_target"
        )
        assert category == ErrorCategory.UNKNOWN_ERROR

    def test_extract_error_context(self):
        """Test extraction of error context information."""
        sub_operation = SubOperationLog(
            step_number=1,
            operation_name="GET_VALUE",
            target="file_data",
            start_time=1640995200.0,
            end_time=1640995201.5,
            execution_time=1.5,
            request_kwargs={"path_keys": ["test.csv", "reaction_0"]},
        )

        context = self.error_handler.extract_error_context(sub_operation)

        assert context["operation"] == "GET_VALUE"
        assert context["target"] == "file_data"
        assert context["step_number"] == 1
        assert context["execution_time"] == 1.5
        assert context["request_kwargs"] == {"path_keys": ["test.csv", "reaction_0"]}
        assert context["start_time"] == 1640995200.0
        assert context["end_time"] == 1640995201.5

    def test_determine_severity(self):
        """Test severity determination logic."""
        # Test CRITICAL severity for critical keywords
        severity = self.error_handler.determine_severity(
            ErrorCategory.UNKNOWN_ERROR, {"error": "critical system failure"}
        )
        assert severity == ErrorSeverity.CRITICAL

        # Test HIGH severity for calculation errors
        severity = self.error_handler.determine_severity(
            ErrorCategory.CALCULATION_ERROR, {"error": "computation failed"}
        )
        assert severity == ErrorSeverity.HIGH

        # Test HIGH severity for file operations
        severity = self.error_handler.determine_severity(
            ErrorCategory.FILE_OPERATION_ERROR, {"error": "file access denied"}
        )
        assert severity == ErrorSeverity.HIGH

        # Test MEDIUM severity for configuration errors
        severity = self.error_handler.determine_severity(
            ErrorCategory.CONFIGURATION_ERROR, {"error": "invalid setting"}
        )
        assert severity == ErrorSeverity.MEDIUM

    def test_suggest_action(self):
        """Test suggested action generation."""
        error_analysis = ErrorAnalysis(
            error_type=ErrorCategory.FILE_OPERATION_ERROR,
            error_message="File not found",
            error_context={},
            severity=ErrorSeverity.HIGH,
        )

        action = self.error_handler.suggest_action(error_analysis)
        assert "Check file path and permissions" in action
        assert "Important: This error may affect results significantly" in action

        # Test CRITICAL severity
        error_analysis.severity = ErrorSeverity.CRITICAL
        action = self.error_handler.suggest_action(error_analysis)
        assert "URGENT: Operation blocked - immediate attention required" in action

    def test_analyze_error_comprehensive(self):
        """Test comprehensive error analysis."""
        sub_operation = SubOperationLog(
            step_number=2,
            operation_name="LOAD_FILE",
            target="file_data",
            start_time=1640995200.0,
            status="Error",
            response_data_raw={"error": "File not found: /path/to/file.csv"},
            request_kwargs={"file_path": "/path/to/file.csv"},
        )

        analysis = self.error_handler.analyze_error(sub_operation)

        assert analysis.error_type == ErrorCategory.FILE_OPERATION_ERROR
        assert "File not found" in analysis.error_message
        assert analysis.severity == ErrorSeverity.HIGH
        assert "Check file path and permissions" in analysis.suggested_action
        assert "LOAD_FILE" in analysis.technical_details


class TestSubOperationLogIntegration:
    """Test integration of error handling with SubOperationLog."""

    def test_sub_operation_log_error_analysis(self):
        """Test automatic error analysis in SubOperationLog."""
        sub_operation = SubOperationLog(
            step_number=1,
            operation_name="GET_VALUE",
            target="calculations_data",
            start_time=1640995200.0,
            status="Error",
            response_data_raw={"error": "Invalid data keys"},
        )

        # Trigger error analysis
        sub_operation._analyze_error_if_needed()

        assert sub_operation.has_detailed_error()
        assert sub_operation.error_details is not None
        assert sub_operation.error_details.error_type == ErrorCategory.DATA_VALIDATION_ERROR

    def test_has_detailed_error(self):
        """Test detailed error detection."""
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )

        # Initially no detailed error
        assert not sub_operation.has_detailed_error()

        # Add error details
        sub_operation.error_details = ErrorAnalysis(
            error_type=ErrorCategory.UNKNOWN_ERROR,
            error_message="Test error",
            error_context={},
            severity=ErrorSeverity.LOW,
        )

        assert sub_operation.has_detailed_error()

    def test_get_error_summary(self):
        """Test error summary generation."""
        sub_operation = SubOperationLog(
            step_number=1, operation_name="TEST_OP", target="test_target", start_time=1640995200.0
        )

        # Test with detailed error
        sub_operation.error_details = ErrorAnalysis(
            error_type=ErrorCategory.DATA_VALIDATION_ERROR,
            error_message="This is a very long error message that should be truncated",
            error_context={},
            severity=ErrorSeverity.HIGH,
        )

        summary = sub_operation.get_error_summary()
        assert "data_validation_error" in summary
        assert "This is a very long error m..." in summary

        # Test with basic error message
        sub_operation.error_details = None
        sub_operation.error_message = "Short error message"

        summary = sub_operation.get_error_summary()
        assert summary == "Short error message"  # Test with long basic error message
        long_message = "This is a very long basic error message that should be truncated at fifty characters"
        sub_operation.error_message = long_message

        summary = sub_operation.get_error_summary()
        assert len(summary) <= 53  # 50 characters + "..."

        # Test with no error information
        sub_operation.error_message = None

        summary = sub_operation.get_error_summary()
        assert summary == "Unknown error"

    @patch("src.core.log_aggregator.error_handler.SubOperationErrorHandler")
    def test_mark_completed_with_error_analysis(self, mock_handler_class):
        """Test mark_completed method with error analysis integration."""
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        mock_analysis = ErrorAnalysis(
            error_type=ErrorCategory.CALCULATION_ERROR,
            error_message="Calculation failed",
            error_context={},
            severity=ErrorSeverity.HIGH,
        )
        mock_handler.analyze_error.return_value = mock_analysis

        sub_operation = SubOperationLog(
            step_number=1, operation_name="DECONVOLUTION", target="calculations", start_time=1640995200.0
        )

        # Mark as completed with error
        response_data = {"error": "Optimization failed"}
        sub_operation.mark_completed(response_data, exception_info="RuntimeError: Failed")

        assert sub_operation.status == "Error"
        assert sub_operation.response_data_raw == response_data
        assert sub_operation.exception_traceback == "RuntimeError: Failed"

        # Verify error analysis was called
        mock_handler.analyze_error.assert_called_once_with(sub_operation)
        assert sub_operation.error_details == mock_analysis
