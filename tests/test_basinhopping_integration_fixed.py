"""
Integration tests for basinhopping with full calculation workflow.

This module tests end-to-end basinhopping integration with Calculations class,
ensuring proper interaction between all components.
"""

import numpy as np
import pandas as pd

from src.core.app_settings import OperationType
from src.core.base_signals import BaseSignals
from src.core.calculation import Calculations
from src.core.series_data import SeriesData


class TestBasinhoppingIntegration:
    """Integration tests for basinhopping workflow."""

    def setup_method(self):
        """Setup test fixtures for integration tests."""
        # Create Qt signals
        self.signals = BaseSignals()

        # Create calculations instance
        self.calculations = Calculations(self.signals)

        # Create test series data
        self.series_data = SeriesData(signals=self.signals)

        # Setup test data
        self.setup_test_data()

    def setup_test_data(self):
        """Setup realistic test data for model-based calculations."""
        # Create experimental data
        temperature = np.linspace(300, 600, 100)
        # Simulate experimental data for different heating rates
        exp_data = pd.DataFrame(
            {
                "temperature": temperature - 273.15,  # Celsius
                "3.0": np.exp(-((temperature - 450) ** 2) / 1000) * 0.8 + 0.1,  # 3 K/min
                "5.0": np.exp(-((temperature - 460) ** 2) / 1000) * 0.9 + 0.1,  # 5 K/min
                "10.0": np.exp(-((temperature - 470) ** 2) / 1000) * 1.0 + 0.1,  # 10 K/min
            }
        )

        # Create series with reaction scheme
        series_name = "test_series"
        self.series_data.add_series(exp_data, [1.0, 1.0, 1.0], series_name)

        # Setup simple reaction scheme: A -> B
        reaction_scheme = {
            "components": [{"id": "A"}, {"id": "B"}],
            "reactions": [
                {
                    "from": "A",
                    "to": "B",
                    "reaction_type": "F1",
                    "allowed_models": ["F1", "A2", "R3"],
                    "Ea": 150,
                    "log_A": 10,
                    "contribution": 1.0,
                    "Ea_min": 50.0,
                    "Ea_max": 300.0,
                    "log_A_min": 5.0,
                    "log_A_max": 15.0,
                    "contribution_min": 0.5,
                    "contribution_max": 1.0,
                }
            ],
        }

        # Set reaction scheme
        self.series_data.update_series(series_name, {"reaction_scheme": reaction_scheme})

        # Set calculation settings for basinhopping
        calculation_settings = {
            "method": "basinhopping",
            "method_parameters": {
                "niter": 10,  # Small number for fast tests
                "T": 1.0,
                "stepsize": 0.3,
                "batch_size": 2,
                "minimizer_kwargs": {"method": "L-BFGS-B", "options": {"maxiter": 10}},
            },
        }

        self.series_data.update_series(series_name, {"calculation_settings": calculation_settings})

        self.series_name = series_name

    def test_end_to_end_basinhopping(self):
        """Test complete basinhopping optimization workflow."""
        # Get series data
        series_data = self.series_data.get_series(self.series_name)

        # Prepare calculation parameters
        params = {
            "operation": OperationType.MODEL_BASED_CALCULATION,
            "series_name": self.series_name,
            "experimental_data": series_data["experimental_data"],
            "reaction_scheme": series_data["reaction_scheme"],
            "calculation_settings": series_data["calculation_settings"],
            "calculation_scenario": "model_based_calculation",
        }

        # Mock signal emission to capture results
        results = []

        def capture_result(result_dict):
            results.append(result_dict)

        self.calculations.new_best_result.connect(capture_result)

        # Run calculation
        self.calculations.run_calculation_scenario(params)

        # Wait for calculation to complete
        if self.calculations.thread:
            self.calculations.thread.wait(30000)  # 30 second timeout

        # Verify results
        assert not self.calculations.calculation_active, "Calculation should be finished"
        assert len(results) > 0, "Should have captured some results"

        # Check result structure
        last_result = results[-1]
        assert "best_mse" in last_result
        assert "params" in last_result
        assert isinstance(last_result["best_mse"], (float, int))
        assert isinstance(last_result["params"], list)

    def test_comparison_with_differential_evolution(self):
        """Compare basinhopping vs differential_evolution results."""
        # Get series data
        series_data = self.series_data.get_series(self.series_name)

        # Test differential evolution first
        params_de = {
            "operation": OperationType.MODEL_BASED_CALCULATION,
            "series_name": self.series_name,
            "experimental_data": series_data["experimental_data"],
            "reaction_scheme": series_data["reaction_scheme"],
            "calculation_settings": {
                "method": "differential_evolution",
                "method_parameters": {"maxiter": 10, "popsize": 5},
            },
            "calculation_scenario": "model_based_calculation",
        }

        de_results = []

        def capture_de_result(result_dict):
            de_results.append(result_dict)

        self.calculations.new_best_result.connect(capture_de_result)
        self.calculations.run_calculation_scenario(params_de)

        if self.calculations.thread:
            self.calculations.thread.wait(30000)

        # Reset for basinhopping test
        self.calculations.new_best_result.disconnect()

        # Test basinhopping
        params_bh = params_de.copy()
        params_bh["calculation_settings"] = {
            "method": "basinhopping",
            "method_parameters": {"niter": 10, "T": 1.0, "stepsize": 0.3, "batch_size": 2},
        }

        bh_results = []

        def capture_bh_result(result_dict):
            bh_results.append(result_dict)

        self.calculations.new_best_result.connect(capture_bh_result)
        self.calculations.run_calculation_scenario(params_bh)

        if self.calculations.thread:
            self.calculations.thread.wait(30000)

        # Compare results
        assert len(de_results) > 0, "Differential evolution should produce results"
        assert len(bh_results) > 0, "Basinhopping should produce results"

        de_final_mse = de_results[-1]["best_mse"]
        bh_final_mse = bh_results[-1]["best_mse"]

        # Both should find reasonable solutions (MSE < 1.0 for our synthetic data)
        assert de_final_mse < 1.0, f"DE MSE too high: {de_final_mse}"
        assert bh_final_mse < 1.0, f"BH MSE too high: {bh_final_mse}"

    def test_stop_calculation_functionality(self):
        """Test that stop calculation works for basinhopping."""
        # Get series data
        series_data = self.series_data.get_series(self.series_name)

        # Setup parameters for long-running calculation
        params = {
            "operation": OperationType.MODEL_BASED_CALCULATION,
            "series_name": self.series_name,
            "experimental_data": series_data["experimental_data"],
            "reaction_scheme": series_data["reaction_scheme"],
            "calculation_settings": {
                "method": "basinhopping",
                "method_parameters": {
                    "niter": 1000,  # Long running
                    "T": 1.0,
                    "stepsize": 0.3,
                    "batch_size": 2,
                },
            },
            "calculation_scenario": "model_based_calculation",
        }

        # Start calculation
        self.calculations.run_calculation_scenario(params)

        # Let it run briefly
        import time

        time.sleep(0.5)

        # Stop calculation
        assert self.calculations.calculation_active, "Calculation should be running"
        self.calculations.stop_calculation()

        # Wait for stop
        if self.calculations.thread:
            self.calculations.thread.wait(10000)  # 10 second timeout

        # Verify stop
        assert not self.calculations.calculation_active, "Calculation should be stopped"

    def test_error_handling(self):
        """Test proper error handling in basinhopping workflow."""
        # Get series data
        series_data = self.series_data.get_series(self.series_name)

        # Test with invalid parameters
        params = {
            "operation": OperationType.MODEL_BASED_CALCULATION,
            "series_name": self.series_name,
            "experimental_data": series_data["experimental_data"],
            "reaction_scheme": series_data["reaction_scheme"],
            "calculation_settings": {
                "method": "basinhopping",
                "method_parameters": {
                    "niter": -1,  # Invalid parameter
                    "T": 1.0,
                    "stepsize": 0.3,
                    "batch_size": 2,
                },
            },
            "calculation_scenario": "model_based_calculation",
        }

        # This should handle the error gracefully
        errors = []

        def capture_error(error_msg):
            errors.append(error_msg)

        self.calculations.error_occurred.connect(capture_error)
        self.calculations.run_calculation_scenario(params)

        if self.calculations.thread:
            self.calculations.thread.wait(30000)

        # Should capture error or complete without crashing
        assert not self.calculations.calculation_active, "Calculation should be finished"

    def test_progress_reporting(self):
        """Test that progress signals are emitted during basinhopping."""
        # Get series data
        series_data = self.series_data.get_series(self.series_name)

        # Setup parameters
        params = {
            "operation": OperationType.MODEL_BASED_CALCULATION,
            "series_name": self.series_name,
            "experimental_data": series_data["experimental_data"],
            "reaction_scheme": series_data["reaction_scheme"],
            "calculation_settings": {
                "method": "basinhopping",
                "method_parameters": {"niter": 5, "T": 1.0, "stepsize": 0.3, "batch_size": 2},
            },
            "calculation_scenario": "model_based_calculation",
        }

        progress_values = []

        def capture_progress(progress):
            progress_values.append(progress)

        self.calculations.progress_updated.connect(capture_progress)
        self.calculations.run_calculation_scenario(params)

        if self.calculations.thread:
            self.calculations.thread.wait(30000)

        # Verify progress was reported
        assert len(progress_values) > 0, "Should have reported progress"
        assert any(p > 0 for p in progress_values), "Should have non-zero progress"
        assert any(p <= 100 for p in progress_values), "Progress should not exceed 100%"
