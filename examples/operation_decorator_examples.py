"""
Example usage of the enhanced @operation decorator.

This module demonstrates how to use the new operation decorator
with BaseSlots classes and automatic OperationType integration.
"""

from src.core.app_settings import OperationType
from src.core.base_signals import BaseSlots
from src.log_aggregator.operation_decorator import operation
from src.log_aggregator.operation_metaclass import operation_aware_class


# Example 1: Manual decoration with specific operation type
class ExampleDataOperations(BaseSlots):
    """Example data operations class with manual decoration."""

    def __init__(self, signals):
        super().__init__(actor_name="example_data_operations", signals=signals)

    @operation(OperationType.LOAD_FILE)
    def load_file(self, file_path: str):
        """Load a file with automatic operation logging."""
        print(f"Loading file: {file_path}")
        # Simulate file loading
        return {"status": "loaded", "path": file_path}

    @operation("CUSTOM_PROCESSING")
    def process_data(self, data):
        """Process data with custom operation name."""
        print(f"Processing data: {data}")
        return {"processed": True, "count": len(data) if hasattr(data, "__len__") else 1}

    @operation()  # Auto-detect from method name - вызываем как функцию
    def add_reaction(self, reaction_data):
        """Add reaction - operation type auto-detected as ADD_REACTION."""
        print(f"Adding reaction: {reaction_data}")
        return {"reaction_added": True}


# Example 2: Using operation-aware class decorator
@operation_aware_class
class ExampleCalculationOperations(BaseSlots):
    """Example calculation operations with automatic process_request decoration."""

    def __init__(self, signals):
        super().__init__(actor_name="example_calculation_operations", signals=signals)

    def process_request(self, params: dict):
        """Process request - automatically decorated with operation logging."""
        operation = params.get("operation")
        print(f"Processing operation: {operation}")

        if operation == OperationType.DECONVOLUTION.value:
            return self._handle_deconvolution(params)
        elif operation == OperationType.MODEL_BASED_CALCULATION.value:
            return self._handle_model_based(params)
        else:
            return {"error": "Unknown operation"}

    def _handle_deconvolution(self, params):
        """Handle deconvolution operation."""
        print("Performing deconvolution...")
        return {"deconvolution_result": "success"}

    def _handle_model_based(self, params):
        """Handle model-based calculation."""
        print("Performing model-based calculation...")
        return {"calculation_result": "completed"}


# Example 3: Using operation-aware class decorator instead of metaclass
@operation_aware_class
class ExampleFileOperations(BaseSlots):
    """Example file operations with automatic decoration via class decorator."""

    def __init__(self, signals):
        super().__init__(actor_name="example_file_operations", signals=signals)

    def process_request(self, params: dict):
        """Process request - automatically decorated by class decorator."""
        operation = params.get("operation")
        file_name = params.get("file_name")

        print(f"Processing file operation: {operation} for {file_name}")

        if operation == OperationType.RESET_FILE_DATA.value:
            return self._reset_file_data(file_name)
        elif operation == OperationType.TO_A_T.value:  # Fixed: using TO_A_T instead of DIFFERENTIAL
            return self._apply_differential(file_name)
        else:
            return {"status": "operation_not_supported"}

    def _reset_file_data(self, file_name):
        """Reset file data to original state."""
        print(f"Resetting file data: {file_name}")
        return {"reset": True, "file": file_name}

    def _apply_differential(self, file_name):
        """Apply differential operation to file data."""
        print(f"Applying differential to: {file_name}")
        return {"differential_applied": True, "file": file_name}


# Example 4: Nested operations
class ExampleNestedOperations(BaseSlots):
    """Example of nested operation handling."""

    def __init__(self, signals):
        super().__init__(actor_name="example_nested_operations", signals=signals)

    @operation("COMPLEX_WORKFLOW")
    def complex_workflow(self, data):
        """Complex workflow with nested operations."""
        print("Starting complex workflow...")

        # This will be a nested operation
        preprocessed = self.preprocess_data(data)

        # This will also be nested
        result = self.analyze_data(preprocessed)

        print("Complex workflow completed")
        return result

    @operation("PREPROCESS_DATA")
    def preprocess_data(self, data):
        """Preprocess data - will be nested when called from complex_workflow."""
        print("Preprocessing data...")
        return {"preprocessed": True, "data": data}

    @operation("ANALYZE_DATA")
    def analyze_data(self, data):
        """Analyze data - will be nested when called from complex_workflow."""
        print("Analyzing data...")
        return {"analysis": "complete", "results": data}


# Example 5: Exception handling
class ExampleErrorHandling(BaseSlots):
    """Example of exception handling with operation decorator."""

    def __init__(self, signals):
        super().__init__(actor_name="example_error_handling", signals=signals)

    @operation("SAFE_OPERATION", handle_exceptions=True)
    def safe_operation(self, data):
        """Operation that handles exceptions gracefully."""
        if not data:
            raise ValueError("Data cannot be empty")
        return {"processed": data}

    @operation("UNSAFE_OPERATION", handle_exceptions=False)
    def unsafe_operation(self, data):
        """Operation that propagates exceptions."""
        if not data:
            raise ValueError("Data cannot be empty")
        return {"processed": data}


# Example usage function
def demonstrate_operation_decorators():
    """Demonstrate the usage of operation decorators."""
    print("=== Operation Decorator Examples ===\n")

    # Mock signals for BaseSlots
    class MockSignals:
        def register_component(self, name, request_handler, response_handler):
            pass

    signals = MockSignals()

    # Example 1: Manual decoration
    print("1. Manual decoration examples:")
    data_ops = ExampleDataOperations(signals)
    data_ops.load_file("test_file.csv")
    data_ops.process_data([1, 2, 3, 4, 5])
    data_ops.add_reaction({"name": "reaction1", "type": "ads"})

    print("\n2. Operation-aware class decorator:")
    calc_ops = ExampleCalculationOperations(signals)
    calc_ops.process_request({"operation": OperationType.DECONVOLUTION.value})

    print("\n3. Operation-aware class decorator:")
    file_ops = ExampleFileOperations(signals)
    file_ops.process_request({"operation": OperationType.RESET_FILE_DATA.value, "file_name": "test.csv"})

    print("\n4. Nested operations:")
    nested_ops = ExampleNestedOperations(signals)
    nested_ops.complex_workflow({"sample": "data"})

    print("\n5. Exception handling:")
    error_ops = ExampleErrorHandling(signals)

    # Safe operation (exceptions handled)
    result1 = error_ops.safe_operation(None)  # Will return None
    print(f"Safe operation result: {result1}")

    # Unsafe operation (exceptions propagated)
    try:
        error_ops.unsafe_operation(None)  # Will raise ValueError
    except ValueError as e:
        print(f"Caught exception from unsafe operation: {e}")

    print("\n=== Examples completed ===")


if __name__ == "__main__":
    demonstrate_operation_decorators()
