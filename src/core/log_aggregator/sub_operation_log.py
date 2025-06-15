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
from typing import Any, Dict, Optional

import pandas as pd

from ..app_settings import OperationType


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
    if "success" in data or "error" in data:
        return "ErrorDict"
    return "dict"


def determine_operation_status(response_data: Optional[Dict], exception_occurred: bool = False) -> str:
    """
    Determine if a sub-operation was successful based on response data.

    Args:
        response_data: The response dictionary from handle_request_cycle
        exception_occurred: Whether an exception was caught during execution

    Returns:
        str: "OK" for success, "Error" for failure
    """
    if exception_occurred:
        return "Error"

    if response_data is None:
        return "Error"

    # Check if response contains data field
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

    # If we got here, assume operation was successful
    # (data exists and no explicit error indicators)
    return "OK"


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

    def __post_init__(self):
        """Initialize with default values if needed."""
        if self.request_kwargs is None:
            self.request_kwargs = {}

    def mark_completed(self, response_data: Optional[Dict], exception_info: Optional[str] = None) -> None:
        """
        Mark sub-operation as completed and analyze results.

        Args:
            response_data: The response dictionary from handle_request_cycle
            exception_info: Exception information if an error occurred
        """
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time

        # Determine status based on response and exceptions
        exception_occurred = exception_info is not None
        self.status = determine_operation_status(response_data, exception_occurred)

        if exception_info:
            self.error_message = exception_info
        elif self.status == "Error" and response_data:
            # Try to extract error message from response data
            data = response_data.get("data", {})
            if isinstance(data, dict) and "error" in data:
                self.error_message = str(data["error"])

        # Determine data type
        if response_data and "data" in response_data:
            self.data_type = get_data_type(response_data["data"])
        else:
            self.data_type = "None"

    @property
    def duration_ms(self) -> Optional[float]:
        """Get execution duration in milliseconds."""
        if self.execution_time is not None:
            return self.execution_time * 1000
        return None

    @property
    def operation_display_name(self) -> str:
        """Get a display-friendly operation name."""
        # Try to convert OperationType enum to string if possible
        try:
            if hasattr(OperationType, self.operation_name):
                return self.operation_name
            # If it's already a string from OperationType.value
            for op_type in OperationType:
                if op_type.value == self.operation_name:
                    return op_type.name
            return self.operation_name
        except Exception:
            return self.operation_name

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
