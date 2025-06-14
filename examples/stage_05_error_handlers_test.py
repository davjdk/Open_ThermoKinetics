"""
Test script for Stage 5: Error Handler Interface implementation.

This script demonstrates the error handling capabilities of the OperationLogger
with custom error handlers for different scenarios.
"""

from src.log_aggregator.operation_error_handler import (
    DefaultOperationErrorHandler,
    FileRollbackErrorHandler,
    GuiOperationErrorHandler,
)
from src.log_aggregator.operation_logger import get_operation_logger, log_operation


def test_default_error_handler():
    """Test default error handler functionality."""
    print("\n=== Testing Default Error Handler ===")

    # Get operation logger and register default handler
    op_logger = get_operation_logger()
    default_handler = DefaultOperationErrorHandler()
    op_logger.register_error_handler(default_handler)

    try:
        with log_operation("TEST_DEFAULT_ERROR_HANDLER"):
            op_logger.add_metric("test_metric", "test_value")
            raise ValueError("This is a test error for default handler")
    except ValueError:
        print("✅ Default error handler test completed")


def test_gui_error_handler():
    """Test GUI error handler functionality."""
    print("\n=== Testing GUI Error Handler ===")

    # Get operation logger and register GUI handler
    op_logger = get_operation_logger()
    gui_handler = GuiOperationErrorHandler(show_dialogs=True, auto_recovery=True)
    op_logger.register_error_handler(gui_handler)

    try:
        with log_operation("TEST_GUI_ERROR_HANDLER"):
            op_logger.add_metric("user_action", "load_file")
            raise FileNotFoundError("Test file not found for GUI handler")
    except FileNotFoundError:
        print("✅ GUI error handler test completed")


def test_file_rollback_handler():
    """Test file rollback error handler functionality."""
    print("\n=== Testing File Rollback Error Handler ===")

    # Get operation logger and register rollback handler
    op_logger = get_operation_logger()
    rollback_handler = FileRollbackErrorHandler(enable_rollback=True)
    op_logger.register_error_handler(rollback_handler)

    try:
        with log_operation("TEST_FILE_ROLLBACK_HANDLER"):
            op_logger.add_metric("files_modified", 2)
            # Simulate file operation that fails
            rollback_handler.create_file_snapshot("/test/file1.csv")
            rollback_handler.create_file_snapshot("/test/file2.csv")
            raise PermissionError("Permission denied for file rollback test")
    except PermissionError:
        print("✅ File rollback error handler test completed")


def test_multiple_handlers():
    """Test multiple error handlers working together."""
    print("\n=== Testing Multiple Error Handlers ===")

    # Get operation logger and register multiple handlers
    op_logger = get_operation_logger()

    # Clear existing handlers for clean test
    op_logger._error_handlers.clear()

    # Register multiple handlers
    default_handler = DefaultOperationErrorHandler()
    gui_handler = GuiOperationErrorHandler(show_dialogs=False, auto_recovery=False)
    rollback_handler = FileRollbackErrorHandler(enable_rollback=False)

    op_logger.register_error_handler(gui_handler)  # Will handle first
    op_logger.register_error_handler(rollback_handler)  # Won't be called if GUI handles
    op_logger.register_error_handler(default_handler)  # Won't be called if GUI handles

    try:
        with log_operation("TEST_MULTIPLE_HANDLERS"):
            op_logger.add_metric("handler_count", 3)
            raise KeyError("Test error for multiple handlers")
    except KeyError:
        print("✅ Multiple error handlers test completed")


def test_error_recovery():
    """Test error recovery functionality."""
    print("\n=== Testing Error Recovery ===")

    # Get operation logger
    op_logger = get_operation_logger()

    # Create a GUI handler with auto-recovery enabled
    recovery_handler = GuiOperationErrorHandler(show_dialogs=False, auto_recovery=True)

    # Clear existing handlers and add recovery handler
    op_logger._error_handlers.clear()
    op_logger.register_error_handler(recovery_handler)

    try:
        with log_operation("TEST_ERROR_RECOVERY"):
            op_logger.add_metric("recovery_test", True)
            # This error type is marked as recoverable in GuiOperationErrorHandler
            raise ValueError("Recoverable error for testing")
    except ValueError:
        print("✅ Error recovery test completed")


if __name__ == "__main__":
    print("🚀 Stage 5: Error Handler Interface Testing")
    print("=" * 50)

    # Run all tests
    test_default_error_handler()
    test_gui_error_handler()
    test_file_rollback_handler()
    test_multiple_handlers()
    test_error_recovery()

    print("\n🎉 All error handler tests completed!")
    print("Check the logs for detailed error handling output.")
