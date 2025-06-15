"""
End-to-end integration tests for the log aggregator module.

This module tests the complete workflow of operation logging from
decoration to file output, ensuring all components work together.
"""

import pytest

from src.core.log_aggregator import operation


class TestEndToEndIntegration:
    """Test complete workflows from operation execution to log output."""

    def test_complete_operation_logging_workflow(self, mock_aggregated_logger, sample_test_class):
        """Test complete workflow: operation -> logging -> file output."""
        # Create instance of test class
        test_instance = sample_test_class()

        # Execute operation that should trigger logging
        result = test_instance.operation_with_subops()

        # Verify operation executed correctly
        assert result is True

        # Verify that log_operation was called on the mock logger
        assert mock_aggregated_logger.log_operation.called

        # Get the operation log that was passed to the logger
        call_args = mock_aggregated_logger.log_operation.call_args
        assert call_args is not None

        operation_log = call_args[0][0]  # First argument of the call        # Verify operation log properties
        assert operation_log.operation_name == "OPERATION_WITH_SUBOPS"
        assert operation_log.status == "success"
        assert len(operation_log.sub_operations) == 2

        # Verify sub-operations
        sub_ops = operation_log.sub_operations
        assert sub_ops[0].operation_name == "GET_VALUE"
        assert sub_ops[0].target == "file_data"
        assert sub_ops[1].operation_name == "SET_VALUE"
        assert sub_ops[1].target == "calculations"

    def test_operation_with_error_integration(self, mock_aggregated_logger, sample_test_class):
        """Test integration workflow when operation fails."""
        # Create instance of test class
        test_instance = sample_test_class()

        # Execute operation that fails
        with pytest.raises(RuntimeError, match="Test operation error"):
            test_instance.operation_with_error()

        # Verify error was logged
        assert mock_aggregated_logger.log_operation.called

        call_args = mock_aggregated_logger.log_operation.call_args
        operation_log = call_args[0][0]

        assert operation_log.operation_name == "OPERATION_WITH_ERROR"
        assert operation_log.status == "error"
        assert operation_log.exception_info is not None
        assert "RuntimeError: Test operation error" in operation_log.exception_info
        assert len(operation_log.sub_operations) == 1  # Should have one sub-op before error

    def test_nested_operations_integration(self, mock_aggregated_logger, sample_test_class):
        """Test integration with nested sub-operations."""
        # Execute operation with many sub-operations
        test_instance = sample_test_class()
        result = test_instance.nested_operations()

        assert result is True

        # Verify that log_operation was called
        assert mock_aggregated_logger.log_operation.called

        # Get the operation log that was passed to the logger
        call_args = mock_aggregated_logger.log_operation.call_args
        assert call_args is not None

        operation_log = call_args[0][0]

        # Verify operation log properties
        assert operation_log.operation_name == "NESTED_OPERATIONS"
        assert operation_log.status == "success"
        assert (
            len(operation_log.sub_operations) == 5
        )  # Based on the nested_operations method        # Verify all sub-operations are present
        sub_ops = operation_log.sub_operations
        assert all(sub_op.status == "OK" for sub_op in sub_ops)

    def test_multiple_operations_same_session(self, mock_aggregated_logger, sample_test_class):
        """Test multiple operations in the same session."""
        test_instance = sample_test_class()

        # Execute multiple different operations
        result1 = test_instance.simple_operation()
        result2 = test_instance.operation_with_subops()
        result3 = test_instance.nested_operations()

        assert result1 == "success"
        assert result2 is True
        assert result3 is True  # Verify that log_operation was called multiple times
        assert mock_aggregated_logger.log_operation.call_count == 3

        # Get all the operation logs that were passed to the logger
        call_args_list = mock_aggregated_logger.log_operation.call_args_list
        operation_names = [args[0][0].operation_name for args in call_args_list]

        # All operations should be logged
        assert "SIMPLE_OPERATION" in operation_names
        assert "OPERATION_WITH_SUBOPS" in operation_names
        assert "NESTED_OPERATIONS" in operation_names

    def test_concurrent_operations_integration(self, mock_aggregated_logger):
        """Test concurrent operations integration."""
        import threading

        def thread_operation(thread_id):
            @operation(f"CONCURRENT_OP_{thread_id}")
            def concurrent_op():
                return f"thread_{thread_id}_result"

            return concurrent_op()

        # Execute operations concurrently
        threads = []
        results = {}

        def run_operation(thread_id):
            results[thread_id] = thread_operation(thread_id)

        for i in range(3):
            thread = threading.Thread(target=run_operation, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all operations completed
        assert len(results) == 3
        for i in range(3):
            assert results[i] == f"thread_{i}_result"

        # Verify all operations were logged
        assert mock_aggregated_logger.log_operation.call_count == 3

        # Verify operation names in call args
        call_args = [call[0][0] for call in mock_aggregated_logger.log_operation.call_args_list]
        operation_names = [op.operation_name for op in call_args]

        for i in range(3):
            assert f"CONCURRENT_OP_{i}" in operation_names


class TestRealWorldScenarios:
    """Test realistic application scenarios."""

    def test_file_loading_scenario(self, mock_aggregated_logger):
        """Test a realistic file loading scenario."""

        class FileOperations:
            def handle_request_cycle(self, target, operation, **kwargs):
                # Simulate realistic responses
                if operation == "LOAD_FILE":
                    return {"data": True}
                elif operation == "GET_DF_DATA":
                    return {"data": [[1, 2, 3], [4, 5, 6]]}
                elif operation == "SET_VALUE":
                    return {"data": {"success": True}}
                return {"data": "unknown"}

            @operation("FILE_LOADING_WORKFLOW")
            def load_and_process_file(self, file_path):
                # Simulate realistic file loading workflow
                self.handle_request_cycle("file_data", "LOAD_FILE", path=file_path)
                self.handle_request_cycle("file_data", "GET_DF_DATA", columns=["temp", "mass"])
                self.handle_request_cycle(
                    "calculations", "SET_VALUE", path_keys=[file_path, "metadata"], value={"loaded": True}
                )
                return True

        file_ops = FileOperations()
        result = file_ops.load_and_process_file("test_file.csv")

        assert result is True
        mock_aggregated_logger.log_operation.assert_called_once()

        # Check operation details
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]
        assert operation_log.operation_name == "FILE_LOADING_WORKFLOW"
        assert len(operation_log.sub_operations) == 3
        assert operation_log.status == "success"

    def test_calculation_scenario(self, mock_aggregated_logger):
        """Test a realistic calculation scenario."""

        class CalculationOperations:
            def handle_request_cycle(self, target, operation, **kwargs):
                # Simulate calculation responses
                if operation == "GET_VALUE":
                    return {"data": [1.0, 2.0, 3.0]}
                elif operation == "DECONVOLUTION":
                    return {"data": {"success": True, "peaks": 3}}
                elif operation == "UPDATE_VALUE":
                    return {"data": {"success": True}}
                return {"data": "calculation_result"}

            @operation("DECONVOLUTION_CALCULATION")
            def perform_deconvolution(self, file_name):
                # Get data
                self.handle_request_cycle("file_data", "GET_VALUE", path_keys=[file_name, "temperature"])
                self.handle_request_cycle("file_data", "GET_VALUE", path_keys=[file_name, "heat_flow"])

                # Perform calculation
                self.handle_request_cycle(
                    "calculations", "DECONVOLUTION", file_name=file_name, method="gaussian"
                )  # Update results
                self.handle_request_cycle(
                    "calculations", "UPDATE_VALUE", path_keys=[file_name, "results"], value={"completed": True}
                )
                return True

        calc_ops = CalculationOperations()
        result = calc_ops.perform_deconvolution("sample.csv")

        assert result is True
        mock_aggregated_logger.log_operation.assert_called_once()

        # Check operation details
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]
        assert operation_log.operation_name == "DECONVOLUTION_CALCULATION"
        assert len(operation_log.sub_operations) == 4
        assert operation_log.status == "success"

    def test_error_recovery_scenario(self, mock_aggregated_logger):
        """Test error recovery in realistic scenario."""

        class ErrorProneOperations:
            def handle_request_cycle(self, target, operation, **kwargs):
                if operation == "GET_VALUE":
                    return {"data": [1, 2, 3]}
                elif operation == "FAILING_OPERATION":
                    raise ValueError("Simulated calculation error")
                return {"data": "success"}

            @operation("ERROR_RECOVERY_TEST")
            def operation_with_recovery(self):
                # Start with successful operations
                self.handle_request_cycle("file_data", "GET_VALUE", path=["test"])

                # This will fail
                try:
                    self.handle_request_cycle("calculations", "FAILING_OPERATION")
                except ValueError:
                    # Continue with recovery
                    self.handle_request_cycle("file_data", "GET_VALUE", path=["backup"])

                return True

        error_ops = ErrorProneOperations()
        result = error_ops.operation_with_recovery()

        assert result is True
        mock_aggregated_logger.log_operation.assert_called_once()

        # Check operation details
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]
        assert operation_log.operation_name == "ERROR_RECOVERY_TEST"
        assert len(operation_log.sub_operations) == 3
        assert operation_log.status == "success"  # Check sub-operation statuses - 2 successful, 1 failed
        successful_subops = [sub for sub in operation_log.sub_operations if sub.status == "OK"]
        failed_subops = [sub for sub in operation_log.sub_operations if sub.status == "Error"]
        assert len(successful_subops) == 2
        assert len(failed_subops) == 1


class TestPerformanceIntegration:
    """Test performance characteristics of the integrated system."""

    def test_high_volume_operations(self, mock_aggregated_logger):
        """Test system performance with high volume of operations."""
        import time

        class HighVolumeOperations:
            def handle_request_cycle(self, target, operation, **kwargs):
                return {"data": f"response_{operation}"}

            @operation("HIGH_VOLUME_TEST")
            def many_suboperations(self, count=50):
                for i in range(count):
                    self.handle_request_cycle("target", f"OP_{i}", index=i)
                return count

        start_time = time.time()
        high_vol_ops = HighVolumeOperations()
        result = high_vol_ops.many_suboperations(100)
        end_time = time.time()

        execution_time = end_time - start_time

        assert result == 100
        mock_aggregated_logger.log_operation.assert_called_once()

        # Check operation details
        operation_log = mock_aggregated_logger.log_operation.call_args[0][0]
        assert operation_log.operation_name == "HIGH_VOLUME_TEST"
        assert len(operation_log.sub_operations) == 100
        assert operation_log.status == "success"  # Performance check - should complete reasonably quickly
        assert execution_time < 5.0  # Should complete in less than 5 seconds

    def test_memory_usage_stability(self, mock_aggregated_logger):
        """Test that memory usage remains stable with repeated operations."""

        class MemoryTestOperations:
            def handle_request_cycle(self, target, operation, **kwargs):
                # Create some data that should be cleaned up
                large_data = list(range(1000))
                return {"data": len(large_data)}

            @operation("MEMORY_TEST")
            def memory_test_operation(self):
                self.handle_request_cycle("test", "CREATE_DATA")
                return True

        memory_ops = MemoryTestOperations()

        # Run multiple operations
        for i in range(10):
            result = memory_ops.memory_test_operation()
            assert result is True

        # Verify all operations were logged
        assert mock_aggregated_logger.log_operation.call_count == 10

        # Check that each operation was logged correctly
        for call in mock_aggregated_logger.log_operation.call_args_list:
            operation_log = call[0][0]
            assert operation_log.operation_name == "MEMORY_TEST"
            assert len(operation_log.sub_operations) == 1
            assert operation_log.status == "success"
