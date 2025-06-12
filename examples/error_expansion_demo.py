"""
Example demonstrating ErrorExpansionEngine functionality.

This script shows how to use the error expansion engine to get detailed
error analysis with context and actionable recommendations.
"""

import logging
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from log_aggregator import AggregatingHandler, AggregationConfig


def setup_logging_with_error_expansion():
    """Set up logging with error expansion enabled."""
    # Configure aggregation with error expansion
    config = AggregationConfig()
    config.error_expansion_enabled = True
    config.error_context_lines = 5
    config.error_threshold_level = "WARNING"
    config.buffer_size = 10
    config.flush_interval = 2.0

    # Create console handler as target
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))

    # Create aggregating handler with error expansion
    aggregating_handler = AggregatingHandler(target_handler=console_handler, config=config)

    # Set up logger
    logger = logging.getLogger("example_app")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(aggregating_handler)

    return logger, aggregating_handler


def simulate_application_with_errors():
    """Simulate an application that generates various types of errors."""
    logger, handler = setup_logging_with_error_expansion()

    print("=== Error Expansion Engine Demo ===\n")
    print("Simulating application with various error types...\n")

    # Normal operation messages (context)
    logger.info("Application starting up")
    logger.info("Loading configuration from config.json")
    logger.info("Initializing GUI components")
    time.sleep(0.5)

    # File not found error
    print("1. File Not Found Error:")
    logger.error("File not found: data.csv cannot be opened")
    time.sleep(1)

    # Add some context for next error
    logger.info("Starting data processing")
    logger.info("Allocating memory for calculation buffers")
    logger.debug("Setting matrix size to 1000x1000")
    time.sleep(0.5)

    # Memory error
    print("\n2. Memory Error:")
    logger.error("Memory allocation failed during matrix calculation")
    time.sleep(1)

    # GUI context
    logger.info("Updating plot_canvas display")
    logger.info("Refreshing main_window widgets")
    time.sleep(0.5)

    # GUI error
    print("\n3. GUI Error:")
    logger.warning("Widget display error in main_window plot rendering")
    time.sleep(1)

    # Calculation context
    logger.info("Processing deconvolution operation")
    logger.info("Running optimization algorithm")
    time.sleep(0.5)

    # Calculation error
    print("\n4. Calculation Error:")
    logger.error("Division by zero in deconvolution calculation at step 42")
    time.sleep(1)

    # Operation context
    logger.info("Processing request from calculation_data_operations")
    logger.debug("Handling OperationType.UPDATE_VALUE request")
    time.sleep(0.5)

    # Operation error
    print("\n5. Operation Error:")
    logger.warning("Unknown operation OperationType.INVALID_OP received")
    time.sleep(1)

    # Data processing context
    logger.info("Loading CSV file with pandas")
    logger.info("Parsing data columns")
    time.sleep(0.5)

    # Data error
    print("\n6. Data Error:")
    logger.error("Invalid data format in reaction_data.csv: missing temperature column")
    time.sleep(1)

    # Print statistics
    print("\n=== Error Expansion Statistics ===")
    stats = handler.get_statistics()
    print(f"Total records received: {stats['handler']['total_records_received']}")
    print(f"Errors expanded: {stats['handler']['errors_expanded']}")
    print(f"Error expansion enabled: {stats['handler']['error_expansion_enabled']}")

    if "error_expansion" in stats:
        error_stats = stats["error_expansion"]
        print(f"Errors analyzed: {error_stats['errors_analyzed']}")
        print(f"Contexts generated: {error_stats['contexts_generated']}")
        print(f"Suggestions created: {error_stats['suggestions_created']}")
        print(f"Classifications made: {error_stats['classifications_made']}")

    # Demonstrate toggling error expansion
    print("\n=== Disabling Error Expansion ===")
    handler.toggle_error_expansion(False)
    logger.error("This error will not be expanded")

    print("\n=== Re-enabling Error Expansion ===")
    handler.toggle_error_expansion(True)
    logger.error("This error will be expanded again")

    # Clean up
    handler.close()


def demonstrate_error_classification():
    """Demonstrate error classification capabilities."""
    from log_aggregator.error_expansion import ErrorExpansionEngine

    print("\n=== Error Classification Demo ===")

    engine = ErrorExpansionEngine()

    test_messages = [
        "File not found: data.csv cannot be opened",
        "Memory allocation failed during matrix calculation",
        "Widget display error in main_window",
        "Division by zero in deconvolution calculation",
        "Unknown operation OperationType.INVALID_OP",
        "Invalid data format in CSV file",
        "This is just a normal message",
    ]

    for message in test_messages:
        keywords = engine._extract_keywords(message.lower())
        classification = engine._classify_error(message.lower(), keywords)
        print(f"Message: {message}")
        print(f"Classification: {classification or 'No classification'}")
        print(f"Keywords: {keywords}")
        print()


if __name__ == "__main__":
    # Run the main demo
    simulate_application_with_errors()

    # Run classification demo
    demonstrate_error_classification()

    print("\nDemo completed. Check the output above to see expanded error messages.")
