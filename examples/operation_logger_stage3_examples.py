"""
Example usage of refactored OperationLogger (Stage 3).

Demonstrates the new simplified architecture with automatic table generation,
enhanced error handling, and decorator integration.
"""

import time

from src.core.app_settings import OperationType
from src.log_aggregator.operation_logger import OperationLogger, log_operation, operation


def example_basic_usage():
    """Example of basic OperationLogger usage."""
    print("\n=== Basic OperationLogger Usage ===")

    # Create logger with table generation enabled
    logger = OperationLogger(enable_tables=True)
    # Start an operation manually
    logger.start_operation("LOAD_DATA_EXAMPLE")

    # Add some metrics
    logger.add_metric("file_name", "example_data.csv")
    logger.add_metric("file_size", 1024)
    logger.add_metric("processing_mode", "standard")

    # Simulate some work
    time.sleep(0.1)

    # End operation successfully
    logger.end_operation("SUCCESS")

    print("✅ Basic operation completed with automatic table generation")


def example_context_manager():
    """Example using context manager."""
    print("\n=== Context Manager Usage ===")

    logger = OperationLogger(enable_tables=True)

    with logger.log_operation("CONTEXT_OPERATION"):
        logger.add_metric("operation_type", "context_managed")
        logger.add_metric("timestamp", "2024-06-14")

        # Simulate nested operation
        with logger.log_operation("NESTED_OPERATION"):
            logger.add_metric("nested_data", {"key": "value"})
            time.sleep(0.05)

        time.sleep(0.05)

    print("✅ Context manager operations completed")


def example_decorator_usage():
    """Example using operation decorator."""
    print("\n=== Decorator Usage ===")

    logger = OperationLogger(enable_tables=True)

    @logger.operation("DECORATED_FUNCTION")
    def process_data(data_id: str, options: dict):
        """Simulated data processing function."""
        logger.add_metric("data_id", data_id)
        logger.add_metric("options_count", len(options))
        logger.add_metric("processing_result", "successful")

        # Simulate processing time
        time.sleep(0.1)

        return f"Processed {data_id}"

    # Call decorated function
    result = process_data("dataset_001", {"normalize": True, "filter": False})
    print(f"Function result: {result}")
    print("✅ Decorated function completed")


def example_error_handling():
    """Example of error handling."""
    print("\n=== Error Handling Example ===")

    logger = OperationLogger(enable_tables=True)

    # Example with context manager and exception
    try:
        with logger.log_operation("ERROR_PRONE_OPERATION"):
            logger.add_metric("attempt_number", 1)
            logger.add_metric("error_expected", True)

            # Simulate error
            raise ValueError("Simulated processing error")

    except ValueError as e:
        print(f"Caught expected error: {e}")

    # Example with manual error handling
    logger.start_operation("MANUAL_ERROR_HANDLING")
    logger.add_metric("validation_step", "input_check")

    try:
        # Simulate validation error
        if True:  # Simulate condition
            raise RuntimeError("Validation failed")
    except RuntimeError as e:
        error_info = {"type": type(e).__name__, "message": str(e), "context": "data_validation"}
        logger.end_operation("ERROR", error_info)

    print("✅ Error handling examples completed")


def example_data_compression():
    """Example of automatic data compression."""
    print("\n=== Data Compression Example ===")

    from src.log_aggregator.operation_logger import DataCompressionConfig

    # Configure compression
    compression_config = DataCompressionConfig(
        enabled=True,
        string_threshold=50,  # Lower threshold for demonstration
        dict_threshold=5,
    )

    logger = OperationLogger(enable_tables=True, compression_config=compression_config)

    with logger.log_operation("COMPRESSION_DEMO"):
        # Add large data that will be compressed
        long_string = "This is a very long string that exceeds the threshold " * 10
        large_dict = {f"key_{i}": f"value_{i}" for i in range(20)}

        logger.add_metric("long_description", long_string)
        logger.add_metric("large_config", large_dict)
        logger.add_metric("small_data", "this won't be compressed")

        time.sleep(0.05)

    print("✅ Data compression example completed")


def example_convenience_functions():
    """Example using convenience functions."""
    print("\n=== Convenience Functions Example ===")

    # Using convenience context manager
    with log_operation("CONVENIENCE_CONTEXT"):
        # This uses the global logger instance
        print("Using global logger instance...")
        time.sleep(0.05)

    # Using convenience decorator
    @operation("CONVENIENCE_DECORATOR")
    def utility_function(x: int, y: int) -> int:
        """A simple utility function."""
        return x * y

    result = utility_function(6, 7)
    print(f"Utility function result: {result}")
    print("✅ Convenience functions example completed")


def example_integration_scenario():
    """Example simulating integration with BaseSlots architecture."""
    print("\n=== Integration Scenario Example ===")

    logger = OperationLogger(enable_tables=True)

    # Simulate a complex operation like file loading in the main application
    with logger.log_operation("LOAD_FILE_SIMULATION"):
        logger.add_metric("operation_type", OperationType.LOAD_FILE.value)
        logger.add_metric("file_path", "/path/to/experiment.csv")
        logger.add_metric("actor", "FileData")

        # Simulate file validation
        with logger.log_operation("VALIDATE_FILE"):
            logger.add_metric("validation_steps", ["format", "headers", "data_types"])
            logger.add_metric("validation_result", "passed")
            time.sleep(0.02)

        # Simulate data parsing
        with logger.log_operation("PARSE_DATA"):
            logger.add_metric("rows_parsed", 1000)
            logger.add_metric("columns_detected", 4)
            logger.add_metric("parse_errors", 0)
            time.sleep(0.03)

        # Simulate data storage
        with logger.log_operation("STORE_DATA"):
            logger.add_metric("storage_format", "DataFrame")
            logger.add_metric("memory_usage", "2.5 MB")
            time.sleep(0.02)

        logger.add_metric("total_rows", 1000)
        logger.add_metric("load_success", True)

    print("✅ Integration scenario completed")


def main():
    """Run all examples."""
    print("🚀 OperationLogger Stage 3 Refactoring Examples")
    print("=" * 60)

    try:
        example_basic_usage()
        example_context_manager()
        example_decorator_usage()
        example_error_handling()
        example_data_compression()
        example_convenience_functions()
        example_integration_scenario()

        print("\n" + "=" * 60)
        print("🎉 All examples completed successfully!")
        print("📊 Notice the automatic ASCII table generation after each operation")
        print("🔄 Operations are properly nested and tracked")
        print("❌ Errors are captured with full context")
        print("📦 Large data is automatically compressed")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
