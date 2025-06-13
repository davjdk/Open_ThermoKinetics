"""
Integration tests for OperationLogger with MainWindow.

Tests the integration of operation logging with actual MainWindow methods
and real-world usage scenarios.
"""

import pytest

from src.log_aggregator.operation_logger import log_operation, operation


class MockMainWindow:
    """Mock MainWindow class for integration testing."""

    def __init__(self):
        # Use the global operation_logger instance for consistency with MainWindow
        from src.log_aggregator.operation_logger import operation_logger

        self.operation_logger = operation_logger
        self.request_cycle_calls = []

    def handle_request_cycle(self, target, operation_type, **kwargs):
        """Mock handle_request_cycle method."""
        self.request_cycle_calls.append({"target": target, "operation_type": operation_type, "kwargs": kwargs})
        return {"success": True, "data": f"mock_data_for_{operation_type}"}

    @operation("ADD_NEW_SERIES")
    def _handle_add_new_series(self, operation_info):
        """Mock method with decorator integration."""
        # Add operation metrics
        self.operation_logger.add_metric("files_count", len(operation_info.get("files", [])))
        self.operation_logger.add_metric("heating_rates", operation_info.get("heating_rates", []))

        # Simulate multiple handle_request_cycle calls
        self.handle_request_cycle("file_data", "GET_ALL_DATA")
        self.handle_request_cycle("series_data", "ADD_NEW_SERIES", **operation_info)
        self.handle_request_cycle("series_data", "GET_SERIES", series_name="new_series")

        # Add result metrics
        self.operation_logger.add_metric("series_created", True)
        self.operation_logger.add_metric("data_points", 1000)

        return {"success": True, "series_id": "test_series"}

    def _handle_deconvolution_with_context(self, operation_info):
        """Mock method using context manager."""
        with log_operation("DECONVOLUTION"):
            self.operation_logger.add_metric("reactions_to_fit", len(operation_info.get("reactions", [])))
            self.operation_logger.add_metric("optimization_method", operation_info.get("method", "default"))

            result = self.handle_request_cycle("calculations", "DECONVOLUTION", **operation_info)

            if result.get("success"):
                self.operation_logger.add_metric("final_mse", 0.001)
                self.operation_logger.add_metric("reactions_found", 3)

            return result

    def _handle_model_free_calculation_mixed(self, operation_info):
        """Mock method mixing decorator and context manager."""
        with log_operation("MODEL_FREE_CALCULATION"):
            self.operation_logger.add_metric("calculation_method", operation_info.get("method", "Friedman"))

            # Call decorated helper method
            data = self._prepare_model_free_data(operation_info)

            result = self.handle_request_cycle("calculations", "MODEL_FREE_CALCULATION", **operation_info)
            self.handle_request_cycle("series_data", "UPDATE_SERIES", **operation_info)

            self.operation_logger.add_metric("reactions_analyzed", len(data.get("reactions", [])))

            return result

    @operation("PREPARE_MODEL_FREE_DATA")
    def _prepare_model_free_data(self, operation_info):
        """Mock helper method with decorator."""
        self.operation_logger.add_metric("data_validation", True)

        self.handle_request_cycle("series_data", "GET_SERIES", **operation_info)

        self.operation_logger.add_metric("series_loaded", True)

        return {"reactions": ["reaction_0", "reaction_1", "reaction_2"]}


class TestOperationLoggerIntegration:
    """Test OperationLogger integration with MainWindow-like methods."""

    def setup_method(self):
        """Set up test environment."""
        self.main_window = MockMainWindow()

    def test_decorator_integration(self):
        """Test decorator integration with MainWindow method."""
        import io
        import logging

        # Capture logs to verify operation logging
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)

        operation_logger = self.main_window.operation_logger
        operation_logger.logger.addHandler(handler)
        operation_logger.logger.setLevel(logging.INFO)

        operation_info = {
            "files": ["file1.csv", "file2.csv", "file3.csv"],
            "heating_rates": [3, 5, 10],
            "experimental_masses": [1.0, 1.0, 1.0],
        }

        result = self.main_window._handle_add_new_series(operation_info)

        # Check operation was successful
        assert result["success"] is True
        assert result["series_id"] == "test_series"

        # Check handle_request_cycle was called correctly
        assert len(self.main_window.request_cycle_calls) == 3
        assert self.main_window.request_cycle_calls[0]["operation_type"] == "GET_ALL_DATA"
        assert self.main_window.request_cycle_calls[1]["operation_type"] == "ADD_NEW_SERIES"
        assert self.main_window.request_cycle_calls[2]["operation_type"] == "GET_SERIES"

        # Get log output and verify content
        log_output = log_capture.getvalue()

        # Check operation start
        assert "OPERATION_START: ADD_NEW_SERIES" in log_output

        # Check metrics
        assert "Метрика: files_count = 3" in log_output
        assert "Метрика: heating_rates = [3, 5, 10]" in log_output
        assert "Метрика: series_created = True" in log_output
        assert "Метрика: data_points = 1000" in log_output

        # Check operation end
        assert "OPERATION_END: ADD_NEW_SERIES" in log_output
        assert "Статус: SUCCESS" in log_output
        # Clean up
        operation_logger.logger.removeHandler(handler)

    def test_context_manager_integration(self):
        """Test context manager integration."""
        import io
        import logging

        # Capture logs to verify operation logging
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)

        operation_logger = self.main_window.operation_logger
        operation_logger.logger.addHandler(handler)
        operation_logger.logger.setLevel(logging.INFO)

        operation_info = {"reactions": ["reaction_0", "reaction_1"], "method": "differential_evolution"}

        result = self.main_window._handle_deconvolution_with_context(operation_info)

        # Check operation was successful
        assert result["success"] is True

        # Check handle_request_cycle was called
        assert len(self.main_window.request_cycle_calls) == 1
        assert self.main_window.request_cycle_calls[0]["operation_type"] == "DECONVOLUTION"

        # Get log output and verify content
        log_output = log_capture.getvalue()

        # Check operation start
        assert "OPERATION_START: DECONVOLUTION" in log_output

        # Check metrics
        assert "Метрика: reactions_to_fit = 2" in log_output
        assert "Метрика: optimization_method = differential_evolution" in log_output
        assert "Метрика: final_mse = 0.001" in log_output

        # Check operation end
        assert "OPERATION_END: DECONVOLUTION" in log_output
        assert "Статус: SUCCESS" in log_output
        # Clean up
        operation_logger.logger.removeHandler(handler)

    def test_nested_operations_integration(self):
        """Test nested operations with mixed API usage."""
        import io
        import logging

        # Capture logs to verify operation logging
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)

        operation_logger = self.main_window.operation_logger
        operation_logger.logger.addHandler(handler)
        operation_logger.logger.setLevel(logging.INFO)

        operation_info = {"method": "Friedman", "series_name": "test_series"}

        result = self.main_window._handle_model_free_calculation_mixed(operation_info)

        # Check operations were successful
        assert result["success"] is True

        # Check multiple handle_request_cycle calls
        assert len(self.main_window.request_cycle_calls) == 3  # GET_SERIES + MODEL_FREE + UPDATE_SERIES

        # Get log output and verify content
        log_output = log_capture.getvalue()

        # Should have start/end for both operations
        assert "OPERATION_START: MODEL_FREE_CALCULATION" in log_output
        assert "OPERATION_START: PREPARE_MODEL_FREE_DATA" in log_output
        assert "OPERATION_END: MODEL_FREE_CALCULATION" in log_output
        assert "OPERATION_END: PREPARE_MODEL_FREE_DATA" in log_output

        # Check nested operation structure (child operations should have indicator)
        assert "│ 🔄 OPERATION_START: PREPARE_MODEL_FREE_DATA" in log_output
        # Clean up
        operation_logger.logger.removeHandler(handler)

    def test_error_handling_integration(self):
        """Test error handling in integrated operations."""
        import io
        import logging

        # Capture logs to verify operation logging
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)

        operation_logger = self.main_window.operation_logger
        operation_logger.logger.addHandler(handler)
        operation_logger.logger.setLevel(logging.INFO)

        # Make handle_request_cycle raise an exception
        def error_request_cycle(target, operation_type, **kwargs):
            if operation_type == "DECONVOLUTION":
                raise RuntimeError("Calculation failed")
            return {"success": True, "data": "mock_data"}

        self.main_window.handle_request_cycle = error_request_cycle

        operation_info = {"reactions": ["reaction_0"], "method": "test_method"}

        # Operation should handle the exception
        with pytest.raises(RuntimeError):
            self.main_window._handle_deconvolution_with_context(operation_info)

        # Get log output and verify error handling
        log_output = log_capture.getvalue()

        # Check error was logged
        assert "Метрика: error_type = RuntimeError" in log_output
        assert "Метрика: error_message = Calculation failed" in log_output

        # Check operation was still ended with ERROR status
        assert "OPERATION_END: DECONVOLUTION" in log_output
        assert "Статус: ERROR" in log_output
        # Clean up
        operation_logger.logger.removeHandler(handler)

    def test_metric_collection_integration(self):
        """Test comprehensive metric collection in real scenarios."""
        import io
        import logging

        # Capture logs to verify operation logging
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)

        operation_logger = self.main_window.operation_logger
        operation_logger.logger.addHandler(handler)
        operation_logger.logger.setLevel(logging.INFO)
        operation_info = {
            "files": ["file1.csv", "file2.csv"],
            "heating_rates": [5, 10],
            "experimental_masses": [1.2, 1.3],
        }

        self.main_window._handle_add_new_series(operation_info)

        # Get log output and verify content
        log_output = log_capture.getvalue()

        # Check specific metrics were logged
        assert "Метрика: files_count = 2" in log_output
        assert "Метрика: heating_rates = [5, 10]" in log_output
        assert "Метрика: series_created = True" in log_output
        assert "Метрика: data_points = 1000" in log_output

        # Clean up
        operation_logger.logger.removeHandler(handler)

    def test_thread_safety_integration(self):
        """Test thread safety of operation logging in MainWindow context."""
        results = {}
        errors = {}

        def worker_thread(thread_id):
            try:
                # Each thread gets its own MainWindow instance
                main_window = MockMainWindow()

                operation_info = {
                    "files": [f"file_{thread_id}.csv"],
                    "heating_rates": [thread_id],
                    "experimental_masses": [1.0],
                }

                result = main_window._handle_add_new_series(operation_info)
                results[thread_id] = result

                # Check that operations are isolated
                assert main_window.operation_logger.current_operation is None

            except Exception as e:
                errors[thread_id] = str(e)

        # Run multiple threads
        import threading

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Check all threads completed successfully
        assert len(errors) == 0
        assert len(results) == 5
        for i in range(5):
            assert results[i]["success"] is True


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.main_window = MockMainWindow()

    def test_complex_workflow_scenario(self):
        """Test complex workflow with multiple operations."""
        import io
        import logging

        # Capture logs to verify operation logging
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)

        operation_logger = self.main_window.operation_logger
        operation_logger.logger.addHandler(handler)
        operation_logger.logger.setLevel(logging.INFO)

        # Simulate a complex user workflow
        # 1. Add new series
        series_info = {
            "files": ["exp1.csv", "exp2.csv", "exp3.csv"],
            "heating_rates": [3, 5, 10],
            "experimental_masses": [1.0, 1.1, 1.2],
        }
        series_result = self.main_window._handle_add_new_series(series_info)

        # 2. Perform deconvolution
        deconv_info = {"reactions": ["r0", "r1"], "method": "differential_evolution"}
        deconv_result = self.main_window._handle_deconvolution_with_context(deconv_info)

        # 3. Run model-free calculation
        model_free_info = {"method": "Friedman", "series_name": "test_series"}
        model_free_result = self.main_window._handle_model_free_calculation_mixed(model_free_info)

        # Check all operations were successful
        assert series_result["success"] is True
        assert deconv_result["success"] is True
        assert model_free_result["success"] is True

        # Get log output and verify content
        log_output = log_capture.getvalue()

        # Check operation names appear
        operation_names = ["ADD_NEW_SERIES", "DECONVOLUTION", "MODEL_FREE_CALCULATION", "PREPARE_MODEL_FREE_DATA"]
        for op_name in operation_names:
            assert f"OPERATION_START: {op_name}" in log_output, f"Operation {op_name} should appear in logs"
            assert f"OPERATION_END: {op_name}" in log_output, f"Operation {op_name} should end in logs"
            # Clean up
        operation_logger.logger.removeHandler(handler)

    def test_performance_impact(self):
        """Test that operation logging has minimal performance impact."""
        import time

        # Measure time with operation logging
        start_time = time.time()

        for i in range(10):
            operation_info = {"files": [f"file_{i}.csv"], "heating_rates": [i], "experimental_masses": [1.0]}
            self.main_window._handle_add_new_series(operation_info)

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete quickly (allow for test environment variability)
        assert total_time < 5.0, f"10 operations took {total_time}s, should be much faster"
