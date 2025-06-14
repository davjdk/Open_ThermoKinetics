"""
Advanced operation decorator for automated operation logging        @operation(OperationType.LOAD_FILE)
        def load_file_method(self, *args, **kwargs):
            # Method implementation
            pass
This module provides the enhanced @operation decorator that integrates
with BaseSlots classes and OperationType enum for automatic operation detection.
"""

import functools
import inspect
import threading
from typing import Any, Callable, Optional, Type, TypeVar, Union

from src.core.app_settings import OperationType
from src.core.logger_config import logger

from .operation_logger import get_operation_logger

# Type variable for generic function decorating
F = TypeVar("F", bound=Callable[..., Any])


class OperationDecoratorError(Exception):
    """Exception raised by operation decorator."""

    pass


def operation(
    operation_type: Optional[Union[str, OperationType]] = None,
    auto_detect: bool = True,
    handle_exceptions: bool = True,
    preserve_metadata: bool = True,
) -> Callable[[F], F]:
    """
    Enhanced operation decorator with automatic OperationType integration.

    This decorator automatically marks operation boundaries for logging and
    integrates with the existing OperationLogger system. It supports:

    - Automatic operation type detection from OperationType enum
    - Exception handling and logging
    - Nested operation support
    - PyQt slot compatibility
    - Thread-safe operation

    Args:
        operation_type: Explicit operation type (string or OperationType enum)
        auto_detect: Enable automatic operation type detection from function name
        handle_exceptions: Whether to catch and log exceptions
        preserve_metadata: Whether to preserve original function metadata

    Returns:
        Decorated function with operation logging

    Usage:
        @operation
        def some_method(self, *args, **kwargs):
            # Method implementation
            pass        @operation("CUSTOM_OPERATION")
        def another_method(self, *args, **kwargs):
            # Method implementation
            pass

        @operation(OperationType.LOAD_FILE)
        def load_file_method(self, *args, **kwargs):
            # Method implementation
            pass
    """

    def decorator(func: F) -> F:
        # Get operation logger instance
        op_logger = get_operation_logger()

        # Determine operation name
        operation_name = _determine_operation_name(func, operation_type, auto_detect)

        # Preserve original function metadata
        if preserve_metadata:
            wrapper = functools.wraps(func)(_create_wrapper(func, op_logger, operation_name, handle_exceptions))
        else:
            wrapper = _create_wrapper(func, op_logger, operation_name, handle_exceptions)

        # Store operation metadata on the wrapper for introspection
        wrapper._operation_name = operation_name  # type: ignore
        wrapper._is_operation_decorated = True  # type: ignore
        wrapper._original_function = func  # type: ignore

        return wrapper  # type: ignore

    return decorator


def _determine_operation_name(
    func: Callable, operation_type: Optional[Union[str, OperationType]], auto_detect: bool
) -> str:
    """
    Determine the operation name for logging.

    Args:
        func: The function being decorated
        operation_type: Explicit operation type if provided
        auto_detect: Whether to auto-detect from function name

    Returns:
        Operation name string

    Raises:
        OperationDecoratorError: If operation name cannot be determined
    """
    # Use explicit operation type if provided
    if operation_type is not None:
        if isinstance(operation_type, OperationType):
            return operation_type.value
        elif isinstance(operation_type, str):
            return operation_type
        else:
            raise OperationDecoratorError(f"Invalid operation_type: {operation_type}")

    # Auto-detect from function name if enabled
    if auto_detect:
        operation_name = _auto_detect_operation_type(func.__name__)
        if operation_name:
            return operation_name

    # Fallback to function name conversion
    return _function_to_operation_name(func.__name__)


def _auto_detect_operation_type(function_name: str) -> Optional[str]:
    """
    Auto-detect operation type from function name using OperationType enum.

    Args:
        function_name: Name of the function to analyze

    Returns:
        Operation type string if detected, None otherwise
    """
    # Remove common prefixes/suffixes
    clean_name = function_name
    for prefix in ["_handle_", "handle_", "process_", "_process_"]:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix) :]
            break

    # Try exact match with OperationType values
    for op_type in OperationType:
        if clean_name.upper() == op_type.value.upper():
            return op_type.value

        # Try match without underscores
        if clean_name.upper().replace("_", "") == op_type.value.upper().replace("_", ""):
            return op_type.value  # Try partial matching for common patterns
    operation_patterns = {
        "add_reaction": OperationType.ADD_REACTION.value,
        "remove_reaction": OperationType.REMOVE_REACTION.value,
        "highlight_reaction": OperationType.HIGHLIGHT_REACTION.value,
        "deconvolution": OperationType.DECONVOLUTION.value,
        "model_based": OperationType.MODEL_BASED_CALCULATION.value,
        "model_fit": OperationType.MODEL_FIT_CALCULATION.value,
        "model_free": OperationType.MODEL_FREE_CALCULATION.value,
        "add_series": OperationType.ADD_NEW_SERIES.value,
        "delete_series": OperationType.DELETE_SERIES.value,
        "update_series": OperationType.UPDATE_SERIES.value,
        "load_file": OperationType.LOAD_FILE.value,
        "reset_file": OperationType.RESET_FILE_DATA.value,
        "to_a_t": OperationType.TO_A_T.value,
        "to_dtg": OperationType.TO_DTG.value,
        "import_reactions": OperationType.IMPORT_REACTIONS.value,
        "export_reactions": OperationType.EXPORT_REACTIONS.value,
        "stop_calculation": OperationType.STOP_CALCULATION.value,
        "update_value": OperationType.UPDATE_VALUE.value,
        "get_value": OperationType.GET_VALUE.value,
        "set_value": OperationType.SET_VALUE.value,
        "scheme_change": OperationType.SCHEME_CHANGE.value,
        "model_params_change": OperationType.MODEL_PARAMS_CHANGE.value,
    }

    for pattern, op_value in operation_patterns.items():
        if pattern.lower() in clean_name.lower():
            return op_value

    return None


def _function_to_operation_name(function_name: str) -> str:
    """
    Convert function name to operation name format.

    Args:
        function_name: Original function name

    Returns:
        Formatted operation name
    """
    # Remove common prefixes
    clean_name = function_name
    for prefix in ["_handle_", "handle_", "process_", "_process_"]:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix) :]
            break

    # Convert snake_case to UPPER_CASE
    return clean_name.upper()


def _create_wrapper(func: Callable, op_logger: Any, operation_name: str, handle_exceptions: bool) -> Callable[..., Any]:
    """
    Create the actual wrapper function for operation logging.

    Args:
        func: Original function to wrap
        op_logger: Operation logger instance
        operation_name: Name of the operation
        handle_exceptions: Whether to handle exceptions

    Returns:
        Wrapper function
    """

    def wrapper(*args, **kwargs):
        # Check if we're already in an operation context to handle nesting
        current_operation = op_logger.current_operation
        is_nested = current_operation is not None

        # Start operation logging
        operation_id = op_logger.start_operation(operation_name)

        try:
            # Add function call metadata
            op_logger.add_metric("function_name", func.__name__)
            op_logger.add_metric("module_name", func.__module__)
            op_logger.add_metric("is_nested", is_nested)

            # Add arguments metadata (with compression for large data)
            if args:
                op_logger.add_metric("args_count", len(args))
            if kwargs:
                op_logger.add_metric("kwargs_keys", list(kwargs.keys()))
                # Add specific parameter values that are commonly tracked
                for key in ["operation", "path_keys", "file_name", "params"]:
                    if key in kwargs:
                        op_logger.add_metric(f"param_{key}", kwargs[key])

            # Execute the original function
            result = func(*args, **kwargs)

            # Add result metadata if available
            if result is not None:
                op_logger.add_metric("has_result", True)
                op_logger.add_metric("result_type", type(result).__name__)

            # Log successful completion
            op_logger.end_operation(operation_id, "SUCCESS")
            return result

        except Exception as exc:
            # Log exception details
            op_logger.add_metric("exception_type", type(exc).__name__)
            op_logger.add_metric("exception_message", str(exc))

            # End operation with error status
            op_logger.end_operation(operation_id, "ERROR")

            # Re-raise exception unless explicitly handling
            if not handle_exceptions:
                raise

            # Log error and return None for handled exceptions
            logger.error(f"Operation {operation_name} failed: {exc}")
            return None

    return wrapper


def auto_decorate_baseslots_class(cls: Type) -> Type:
    """
    Automatically decorate all process_request methods in BaseSlots classes.

    This function applies the @operation decorator to process_request methods
    in BaseSlots subclasses, enabling automatic operation logging without
    manual decoration.

    Args:
        cls: Class to auto-decorate (should be BaseSlots subclass)

    Returns:
        Modified class with decorated methods
    """
    # Only process BaseSlots subclasses
    if not _is_baseslots_subclass(cls):
        return cls

    # Check if process_request method exists
    if hasattr(cls, "process_request") and callable(getattr(cls, "process_request")):
        original_method = getattr(cls, "process_request")

        # Only decorate if not already decorated
        if not getattr(original_method, "_is_operation_decorated", False):
            # Apply operation decorator with auto-detection
            decorated_method = operation(auto_detect=True)(original_method)
            setattr(cls, "process_request", decorated_method)

            logger.debug(f"Auto-decorated process_request method in {cls.__name__}")

    return cls


def _is_baseslots_subclass(cls: Type) -> bool:
    """
    Check if a class is a subclass of BaseSlots.

    Args:
        cls: Class to check

    Returns:
        True if class is BaseSlots subclass
    """
    try:
        # Import BaseSlots to check inheritance
        from src.core.base_signals import BaseSlots

        return inspect.isclass(cls) and issubclass(cls, BaseSlots)
    except ImportError:
        # BaseSlots not available, skip auto-decoration
        return False


# Thread-local storage for operation context
_local = threading.local()


def get_current_operation_context() -> Optional[str]:
    """
    Get the current operation context for the current thread.

    Returns:
        Current operation name if available, None otherwise
    """
    op_logger = get_operation_logger()
    current_op = op_logger.current_operation
    return current_op.operation_name if current_op else None


def is_operation_active() -> bool:
    """
    Check if an operation is currently active in this thread.

    Returns:
        True if an operation is active
    """
    return get_current_operation_context() is not None


# Compatibility aliases for existing code
def log_operation(operation_name: str):
    """
    Context manager for operation logging (compatibility alias).

    Args:
        operation_name: Name of the operation

    Returns:
        Operation context manager
    """
    op_logger = get_operation_logger()
    return op_logger.log_operation(operation_name)
