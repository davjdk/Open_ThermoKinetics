"""
Error handling system for sub-operation analysis and categorization.

This module provides comprehensive error analysis capabilities for the log aggregator,
including error categorization, severity assessment, and automated error reporting.

Key components:
- ErrorCategory: Enumeration of error types for classification
- ErrorSeverity: Severity levels for error prioritization
- ErrorAnalysis: Data structure for detailed error information
- SubOperationErrorHandler: Main error processing and analysis class

Architecture principles:
- Comprehensive categorization: Multiple error types for precise classification
- Contextual analysis: Extract relevant information for debugging
- Severity assessment: Prioritize errors by impact level
- Actionable insights: Provide suggestions for error resolution
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .sub_operation_log import SubOperationLog


class ErrorCategory(Enum):
    """Categories of errors that can occur in sub-operations."""

    COMMUNICATION_ERROR = "communication_error"
    DATA_VALIDATION_ERROR = "data_validation_error"
    FILE_OPERATION_ERROR = "file_operation_error"
    CALCULATION_ERROR = "calculation_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """Severity levels for sub-operation errors."""

    CRITICAL = "critical"  # Critical errors blocking operation
    HIGH = "high"  # Important errors affecting results
    MEDIUM = "medium"  # Moderate errors with possible workaround
    LOW = "low"  # Minor errors not affecting functionality


@dataclass
class ErrorAnalysis:
    """Comprehensive analysis of a sub-operation error."""

    error_type: ErrorCategory
    error_message: str
    error_context: Dict[str, Any]
    severity: ErrorSeverity
    suggested_action: Optional[str] = None
    technical_details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert error analysis to dictionary format."""
        return {
            "type": self.error_type.value,
            "message": self.error_message,
            "context": self.error_context,
            "severity": self.severity.value,
            "suggested_action": self.suggested_action,
            "technical_details": self.technical_details,
        }


class SubOperationErrorHandler:
    """
    Specialized handler for sub-operation error processing and detailed logging.

    Responsibilities:
    - Analyze different types of sub-operation errors
    - Extract detailed error information from response data
    - Format comprehensive error reports
    - Categorize errors by type and severity
    """

    def analyze_error(self, sub_operation: "SubOperationLog") -> ErrorAnalysis:
        """
        Perform comprehensive analysis of a sub-operation error.

        Args:
            sub_operation: SubOperationLog instance with error status

        Returns:
            ErrorAnalysis: Detailed error analysis
        """
        # Determine error category
        error_category = self.categorize_error_type(
            sub_operation.response_data_raw, sub_operation.operation_name, sub_operation.target
        )

        # Extract error context
        error_context = self.extract_error_context(sub_operation)

        # Determine severity
        severity = self.determine_severity(error_category, sub_operation.response_data_raw)

        # Extract error message
        error_message = self._extract_error_message(sub_operation.response_data_raw)

        # Create error analysis
        error_analysis = ErrorAnalysis(
            error_type=error_category,
            error_message=error_message,
            error_context=error_context,
            severity=severity,
            technical_details=self._extract_technical_details(sub_operation),
        )

        # Add suggested action
        error_analysis.suggested_action = self.suggest_action(error_analysis)

        return error_analysis

    def categorize_error_type(self, error_data: Any, operation_name: str, target: str) -> ErrorCategory:
        """
        Categorize error based on operation context and error data.

        Args:
            error_data: Raw error data from response
            operation_name: Name of the failed operation
            target: Target module of the operation

        Returns:
            ErrorCategory: Categorized error type
        """
        operation_name_upper = str(operation_name).upper()  # First analyze by error content (more specific)
        if isinstance(error_data, dict):
            error_msg = str(error_data.get("error", "")).lower()

            # Check for configuration keywords first (most specific)
            config_keywords = ["config", "setting", "parameter", "configuration"]
            if any(keyword in error_msg for keyword in config_keywords):
                return ErrorCategory.CONFIGURATION_ERROR

            communication_keywords = ["connection", "timeout", "communication", "network"]
            if any(keyword in error_msg for keyword in communication_keywords):
                return ErrorCategory.COMMUNICATION_ERROR

            file_keywords = ["file", "path", "directory", "permission", "access"]
            if any(keyword in error_msg for keyword in file_keywords):
                return ErrorCategory.FILE_OPERATION_ERROR

            validation_keywords = ["not found", "missing", "invalid", "validation", "format"]
            if any(keyword in error_msg for keyword in validation_keywords):
                return ErrorCategory.DATA_VALIDATION_ERROR

        # Then analyze by operation type (less specific)
        file_operations = ["LOAD", "SAVE", "EXPORT", "IMPORT", "READ", "WRITE"]
        if any(file_op in operation_name_upper for file_op in file_operations):
            return ErrorCategory.FILE_OPERATION_ERROR

        calc_operations = ["CALC", "FIT", "OPTIMIZATION", "DECONVOLUTION", "MODEL"]
        if any(calc_op in operation_name_upper for calc_op in calc_operations):
            return ErrorCategory.CALCULATION_ERROR

        config_operations = ["CONFIG", "SETTING", "PARAMETER"]
        if any(config_op in operation_name_upper for config_op in config_operations):
            return ErrorCategory.CONFIGURATION_ERROR

        data_operations = ["GET", "SET", "UPDATE", "VALIDATE", "CHECK"]
        if any(data_op in operation_name_upper for data_op in data_operations):
            return ErrorCategory.DATA_VALIDATION_ERROR

        return ErrorCategory.UNKNOWN_ERROR

    def extract_error_context(self, sub_operation: "SubOperationLog") -> Dict[str, Any]:
        """
        Extract contextual information about the error.

        Args:
            sub_operation: SubOperationLog instance

        Returns:
            Dict[str, Any]: Context information for debugging
        """
        context = {
            "operation": str(sub_operation.operation_name),
            "target": sub_operation.target,
            "step_number": sub_operation.step_number,
            "execution_time": sub_operation.execution_time,
            "request_kwargs": sub_operation.request_kwargs or {},
        }

        # Add timestamp information
        if sub_operation.start_time:
            context["start_time"] = sub_operation.start_time
        if sub_operation.end_time:
            context["end_time"] = sub_operation.end_time

        # Add error-specific context from response data
        if hasattr(sub_operation, "response_data_raw") and sub_operation.response_data_raw:
            if isinstance(sub_operation.response_data_raw, dict):
                # Extract relevant error context from response
                error_context = sub_operation.response_data_raw.get("error_context", {})
                if error_context:
                    context["response_error_context"] = error_context

        return context

    def determine_severity(self, error_category: ErrorCategory, error_data: Any) -> ErrorSeverity:
        """
        Determine error severity based on category and context.

        Args:
            error_category: Categorized error type
            error_data: Raw error data

        Returns:
            ErrorSeverity: Determined severity level
        """
        # Critical severity for certain categories
        if error_category == ErrorCategory.CALCULATION_ERROR:
            return ErrorSeverity.HIGH  # Calculation errors are important for results

        if error_category == ErrorCategory.FILE_OPERATION_ERROR:
            return ErrorSeverity.HIGH  # File operations are crucial for data integrity

        # Analyze error message for severity indicators
        if isinstance(error_data, dict):
            error_msg = str(error_data.get("error", "")).lower()

            critical_keywords = ["critical", "fatal", "abort", "crash"]
            if any(keyword in error_msg for keyword in critical_keywords):
                return ErrorSeverity.CRITICAL

            high_keywords = ["fail", "failure", "error", "exception"]
            if any(keyword in error_msg for keyword in high_keywords):
                return ErrorSeverity.HIGH

            medium_keywords = ["warning", "caution", "deprecated"]
            if any(keyword in error_msg for keyword in medium_keywords):
                return ErrorSeverity.MEDIUM

        # Default severity based on category
        severity_map = {
            ErrorCategory.COMMUNICATION_ERROR: ErrorSeverity.MEDIUM,
            ErrorCategory.DATA_VALIDATION_ERROR: ErrorSeverity.HIGH,
            ErrorCategory.CONFIGURATION_ERROR: ErrorSeverity.MEDIUM,
            ErrorCategory.UNKNOWN_ERROR: ErrorSeverity.LOW,
        }

        return severity_map.get(error_category, ErrorSeverity.MEDIUM)

    def suggest_action(self, error_analysis: ErrorAnalysis) -> Optional[str]:
        """
        Suggest corrective action based on error analysis.

        Args:
            error_analysis: Complete error analysis

        Returns:
            Optional[str]: Suggested action or None
        """
        actions = {
            ErrorCategory.FILE_OPERATION_ERROR: "Check file path and permissions.\
                Verify file format and existence.",
            ErrorCategory.DATA_VALIDATION_ERROR: "Validate input data format and values.\
                Check data integrity.",
            ErrorCategory.CALCULATION_ERROR: "Review calculation parameters and input data.\
                Check mathematical constraints.",
            ErrorCategory.COMMUNICATION_ERROR: "Verify system connectivity and retry operation.\
                Check network settings.",
            ErrorCategory.CONFIGURATION_ERROR: "Review configuration settings and parameters.\
                Reset to default if needed.",
            ErrorCategory.UNKNOWN_ERROR: "Review error details\
                and contact technical support if needed.",
        }

        base_action = actions.get(error_analysis.error_type)

        # Add severity-specific advice
        if error_analysis.severity == ErrorSeverity.CRITICAL:
            return f"{base_action} URGENT: Operation blocked - immediate attention required."
        elif error_analysis.severity == ErrorSeverity.HIGH:
            return f"{base_action} Important: This error may affect results significantly."

        return base_action

    def _extract_error_message(self, error_data: Any) -> str:
        """Extract human-readable error message from error data."""
        if error_data is None:
            return "No error data available"

        if isinstance(error_data, str):
            return error_data

        if isinstance(error_data, dict):
            # Try various common error message fields
            message_fields = ["error", "message", "error_message", "description"]
            for field in message_fields:
                if field in error_data and error_data[field]:
                    return str(error_data[field])

            # If no standard error field, try to extract from data field
            if "data" in error_data and isinstance(error_data["data"], dict):
                data = error_data["data"]
                for field in message_fields:
                    if field in data and data[field]:
                        return str(data[field])

        # Fallback to string representation
        return str(error_data)

    def _extract_technical_details(self, sub_operation: "SubOperationLog") -> Optional[str]:
        """Extract technical details for debugging purposes."""
        details = []

        # Add operation context
        details.append(f"Operation: {sub_operation.operation_name}")
        details.append(f"Target: {sub_operation.target}")
        details.append(f"Step: {sub_operation.step_number}")

        # Add timing information
        if sub_operation.execution_time:
            details.append(f"Execution time: {sub_operation.execution_time:.3f}s")

        # Add request parameters
        if sub_operation.request_kwargs:
            details.append(f"Request kwargs: {sub_operation.request_kwargs}")

        # Add exception information if available
        if hasattr(sub_operation, "exception_traceback") and sub_operation.exception_traceback:
            details.append(f"Exception traceback: {sub_operation.exception_traceback}")

        return " | ".join(details) if details else None
