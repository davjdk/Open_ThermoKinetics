"""
Sub-operation logging data structures for operation tracking.

This module defines the data structures used to capture and store information
about sub-operations (handle_request_cycle calls) within main operations.

Key components:
- SubOperationLog: Data structure for individual sub-operation information
- Helper functions for data type analysis and status determination
"""

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

import pandas as pd

if TYPE_CHECKING:
    from .error_handler import ErrorAnalysis


def get_data_type(data: Any) -> str:
    """
    Determine the type of data returned by a sub-operation.

    Args:
        data: The data object to analyze

    Returns:
        str: Human-readable type description
    """
    if data is None:
        return "None"

    if isinstance(data, bool):
        return "bool"

    if isinstance(data, int):
        return "int"

    if isinstance(data, float):
        return "float"

    if isinstance(data, str):
        return "str"

    if isinstance(data, pd.DataFrame):
        return "DataFrame"

    if isinstance(data, dict):
        return _get_dict_type(data)

    if isinstance(data, list):
        return "list"

    if hasattr(data, "__call__"):
        return "function"

    return type(data).__name__


def _get_dict_type(data: Dict) -> str:
    """Helper function to determine dict type."""
    # Only classify as ErrorDict if it has explicit error structure
    if "success" in data or "error" in data:
        # If it has error structure but the main content is data, it's just dict
        if len(data) > 1 and any(key not in ["success", "error", "message"] for key in data):
            return "dict"
        return "ErrorDict"
    return "dict"


def _handle_dict_response(response_data: dict) -> str:
    """Handle dictionary response format."""
    # Check for wrapped data structure first
    if "data" in response_data:
        data = response_data.get("data")
        if data is None:
            return "Error"

        # Check for explicit success/error structure
        if isinstance(data, dict):
            # Look for success field
            if "success" in data:
                return "OK" if data["success"] else "Error"
            # Look for error field
            if "error" in data:
                return "Error" if data["error"] else "OK"

        # If data is boolean, use it directly
        if isinstance(data, bool):
            return "OK" if data else "Error"

        # If we got here, assume operation was successful
        return "OK"

    # Check for direct success/error structure (no "data" wrapper)
    if "success" in response_data:
        return "OK" if response_data["success"] else "Error"

    if "error" in response_data:
        return "Error" if response_data["error"] else "OK"

    # If it's a non-empty dict without explicit success/error indicators,
    # assume it contains valid data and is successful
    if response_data:
        return "OK"

    # Empty dict is considered an error
    return "Error"


def _handle_non_dict_response(response_data: Any) -> str:
    """Handle non-dictionary response format."""
    if isinstance(response_data, bool):
        return "OK" if response_data else "Error"

    # For pandas DataFrames, check if it's empty or not None
    if isinstance(response_data, pd.DataFrame):
        try:
            return "OK" if not response_data.empty else "Error"
        except Exception:
            return "OK"  # If any error checking DataFrame, assume it's OK if it exists

    # For other non-dict types, consider them successful if not None
    return "OK" if response_data is not None else "Error"


def determine_operation_status(response_data: Any, exception_occurred: bool = False) -> str:
    """
    Determine if a sub-operation was successful based on response data.

    Args:
        response_data: The response data from handle_request_cycle (can be dict, bool, or other types)
        exception_occurred: Whether an exception was caught during execution

    Returns:
        str: "OK" for success, "Error" for failure
    """
    if exception_occurred:
        return "Error"

    if response_data is None:
        return "Error"

    if isinstance(response_data, dict):
        return _handle_dict_response(response_data)
    else:
        return _handle_non_dict_response(response_data)


@dataclass
class SubOperationLog:
    """
    Data structure for storing sub-operation execution information.

    Captures detailed information about a single handle_request_cycle call
    within a parent operation, including timing, parameters, and results.
    """

    step_number: int
    operation_name: str
    target: str
    start_time: float
    end_time: Optional[float] = None
    execution_time: Optional[float] = None
    status: str = "running"  # "OK", "Error", "running"
    data_type: str = "unknown"
    error_message: Optional[str] = None
    request_kwargs: Dict[str, Any] = None

    # New fields for enhanced error handling
    error_details: Optional["ErrorAnalysis"] = None
    exception_traceback: Optional[str] = None
    response_data_raw: Optional[Any] = None  # For error analysis

    def __post_init__(self):
        """Initialize with default values if needed."""
        if self.request_kwargs is None:
            self.request_kwargs = {}

        # If status is Error and no detailed information - analyze
        if self.status == "Error" and self.error_details is None:
            self._analyze_error_if_needed()

    def _analyze_error_if_needed(self):
        """Analyze error details if status is Error and no details exist."""
        # Only analyze if we don't already have error details and we have either response data or exception info
        if self.error_details is None and (self.response_data_raw is not None or self.exception_traceback is not None):
            # Import here to avoid circular imports
            from .error_handler import SubOperationErrorHandler

            error_handler = SubOperationErrorHandler()
            self.error_details = error_handler.analyze_error(self)

    def has_detailed_error(self) -> bool:
        """Check if detailed error information is available."""
        return self.error_details is not None

    def get_error_summary(self) -> str:
        """Get brief error description for table display."""
        max_length = 53  # Maximum total length including "..."

        if self.error_details:
            error_type = self.error_details.error_type.value
            prefix = f"{error_type}: "
            # Calculate available space for message (max_length - prefix - "...")
            available_space = max_length - len(prefix) - 3  # 3 for "..."
            if len(self.error_details.error_message) > available_space:
                message = self.error_details.error_message[:available_space]
                return f"{prefix}{message}..."
            else:
                return f"{prefix}{self.error_details.error_message}"
        elif self.error_message:
            if len(self.error_message) > 50:
                return self.error_message[:50] + "..."
            else:
                return self.error_message
        elif self.exception_traceback:
            if len(self.exception_traceback) > 50:
                return self.exception_traceback[:50] + "..."
            else:
                return self.exception_traceback
        else:
            return "Unknown error"

    def mark_completed(self, response_data: Optional[Dict], exception_info: Optional[str] = None) -> None:
        """
        Mark sub-operation as completed and analyze results.

        Args:
            response_data: The response dictionary from handle_request_cycle
            exception_info: Exception information if an error occurred
        """
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time

        # Store raw response data for error analysis
        self.response_data_raw = response_data

        # Store exception information if available
        if exception_info:
            self.exception_traceback = exception_info

        # Determine status based on response and exceptions
        exception_occurred = exception_info is not None
        self.status = determine_operation_status(response_data, exception_occurred)

        if exception_info:
            self.error_message = exception_info
        elif self.status == "Error" and response_data is not None:
            # Try to extract error message from response data
            if isinstance(response_data, dict):
                data = response_data.get("data", {})
                if isinstance(data, dict) and "error" in data:
                    self.error_message = str(data["error"])  # Determine data type
        if response_data is not None:
            if isinstance(response_data, dict) and "data" in response_data:
                self.data_type = get_data_type(response_data["data"])
            else:
                self.data_type = get_data_type(response_data)
        else:
            self.data_type = "None"

        # Analyze error if status is Error
        if self.status == "Error":
            self._analyze_error_if_needed()

    @property
    def duration_ms(self) -> Optional[float]:
        """Get execution duration in milliseconds."""
        if self.execution_time is not None:
            return self.execution_time * 1000
        return None

    @property
    def clean_operation_name(self) -> str:
        """
        Get operation name without OperationType prefix.

        Returns:
            str: Clean operation name (e.g., 'CHECK_FILE_EXISTS' instead of 'OperationType.CHECK_FILE_EXISTS')
        """
        # Convert enum to string if needed
        operation_name_str = str(self.operation_name)

        # Handle OperationType enum objects
        if hasattr(self.operation_name, "name"):
            # This is likely an enum object, return the enum name
            return self.operation_name.name

        # Handle string representations
        if operation_name_str.startswith("OperationType."):
            return operation_name_str[len("OperationType.") :]

        # Handle enum string representation
        if "." in operation_name_str:
            parts = operation_name_str.split(".")
            if len(parts) >= 2 and parts[0] == "OperationType":
                return parts[1]

        # Fallback to original name if no prefix found
        return operation_name_str

    @property
    def operation_display_name(self) -> str:
        """Get a display-friendly operation name."""
        return self.clean_operation_name

    def to_dict(self) -> Dict[str, Any]:
        """Convert sub-operation log to dictionary format."""
        return {
            "step": self.step_number,
            "operation": self.operation_display_name,
            "target": self.target,
            "data_type": self.data_type,
            "status": self.status,
            "time_ms": round(self.duration_ms, 3) if self.duration_ms else 0.0,
            "error": self.error_message or "",
        }

    def __str__(self) -> str:
        """Return a clean string representation for logging without response_data_raw."""
        return (
            f"SubOperationLog(step={self.step_number}, op={self.operation_name}, "
            f"target={self.target}, status={self.status}, type={self.data_type})"
        )

    def __repr__(self) -> str:
        """Return a representation without response_data_raw to keep logs clean."""
        return (
            f"SubOperationLog(step_number={self.step_number}, "
            f"operation_name={self.operation_name}, target={self.target}, "
            f"start_time={self.start_time}, end_time={self.end_time}, "
            f"status={self.status}, data_type={self.data_type})"
        )
