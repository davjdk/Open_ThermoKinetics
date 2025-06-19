"""
Integration tests for UI-backend parameter flow.
Tests that parameters correctly flow from UI to backend.
"""

from unittest.mock import patch

import pytest

from src.gui.main_tab.sub_sidebar.model_based.calculation_settings_dialogs import CalculationSettingsDialog
from src.gui.main_tab.sub_sidebar.model_based.model_based_panel import ModelBasedTab


class TestUIBackendIntegration:
    """Test integration between UI and backend for basinhopping."""

    @pytest.fixture(autouse=True)
    def setup_ui(self, qtbot):
        """Setup ModelBasedTab widget for testing."""
        self.widget = ModelBasedTab()
        qtbot.addWidget(self.widget)
        return self.widget

    def test_parameter_flow_differential_evolution(self, qtbot):
        """Test parameter flow for differential_evolution (existing functionality)."""
        # Test that default method works
        params = self.widget.get_method_params()
        assert params["optimization_method"] == "differential_evolution"

        # Should not contain basinhopping params
        basinhopping_keys = ["T", "niter", "stepsize", "batch_size", "minimizer_method"]
        for key in basinhopping_keys:
            assert key not in params

    def test_parameter_flow_basinhopping(self, qtbot):
        """Test parameter flow for basinhopping."""
        # Switch to basinhopping
        self.widget.method_combo.setCurrentText("basinhopping")

        # Set test values
        test_values = {"T": 2.0, "niter": 200, "stepsize": 0.8, "batch_size": 8, "minimizer_method": "SLSQP"}

        self.widget.temperature_spin.setValue(test_values["T"])
        self.widget.niter_spin.setValue(test_values["niter"])
        self.widget.stepsize_spin.setValue(test_values["stepsize"])
        self.widget.batch_size_spin.setValue(test_values["batch_size"])
        self.widget.minimizer_combo.setCurrentText(test_values["minimizer_method"])

        # Get parameters
        params = self.widget.get_method_params()

        # Verify all parameters are correctly passed
        assert params["optimization_method"] == "basinhopping"
        for key, expected_value in test_values.items():
            assert params[key] == expected_value

    def test_parameter_validation_backend(self, qtbot):
        """Test that backend receives validated parameters."""
        # Create dialog with mock data
        mock_reactions = [{"from": "A", "to": "B", "Ea": 120, "log_A": 8, "contribution": 0.5}]
        mock_calc_method = "basinhopping"
        mock_params = {"T": 1.0, "niter": 100, "stepsize": 0.5, "batch_size": 4, "minimizer_method": "L-BFGS-B"}

        dialog = CalculationSettingsDialog(mock_reactions, mock_calc_method, mock_params, parent=self.widget)

        # Verify dialog has basinhopping parameters setup
        assert hasattr(dialog, "basinhopping_params_edits")
        assert len(dialog.basinhopping_params_edits) == 5  # T, niter, stepsize, batch_size, minimizer_method

    def test_error_handling(self, qtbot):
        """Test error handling for invalid parameters."""
        # Create dialog for testing validation
        dialog = CalculationSettingsDialog([], "basinhopping", {}, parent=self.widget)

        # Test invalid temperature
        is_valid, error_msg = dialog.validate_basinhopping_parameter("T", -1.0)
        assert not is_valid
        assert "positive" in error_msg.lower()

        # Test invalid iterations
        is_valid, error_msg = dialog.validate_basinhopping_parameter("niter", 0)
        assert not is_valid
        assert "positive" in error_msg.lower()

        # Test invalid stepsize
        is_valid, error_msg = dialog.validate_basinhopping_parameter("stepsize", 0.0)
        assert not is_valid
        assert "positive" in error_msg.lower()

        # Test invalid batch size
        is_valid, error_msg = dialog.validate_basinhopping_parameter("batch_size", 1)
        assert not is_valid
        assert ">= 2" in error_msg

        # Test invalid minimizer
        is_valid, error_msg = dialog.validate_basinhopping_parameter("minimizer_method", "INVALID")
        assert not is_valid
        assert "Must be one of" in error_msg

    def test_dialog_method_switching(self, qtbot):
        """Test method switching in settings dialog."""
        dialog = CalculationSettingsDialog([], "differential_evolution", {}, parent=self.widget)
        qtbot.addWidget(dialog)

        # Initially differential_evolution should be visible
        assert dialog.de_group.isVisible()
        assert not dialog.basinhopping_group.isVisible()

        # Switch to basinhopping
        dialog.calculation_method_combo.setCurrentText("basinhopping")
        dialog.update_method_parameters()

        assert not dialog.de_group.isVisible()
        assert dialog.basinhopping_group.isVisible()

        # Switch back
        dialog.calculation_method_combo.setCurrentText("differential_evolution")
        dialog.update_method_parameters()

        assert dialog.de_group.isVisible()
        assert not dialog.basinhopping_group.isVisible() @ patch("src.core.app_settings.BASINHOPPING_PARAM_RANGES")

    def test_parameter_ranges_validation(self, mock_ranges, qtbot):
        """Test that parameter ranges are correctly validated."""
        dialog = CalculationSettingsDialog([], "basinhopping", {}, parent=self.widget)

        # Test boundary values
        assert dialog.validate_basinhopping_parameter("T", 0.1)[0]  # Min valid
        assert dialog.validate_basinhopping_parameter("T", 5.0)[0]  # Max valid
        assert not dialog.validate_basinhopping_parameter("T", 0.05)[0]  # Below min
        assert not dialog.validate_basinhopping_parameter("T", 6.0)[0]  # Above max

    def test_backend_compatibility(self, qtbot):
        """Test backward compatibility with existing backend."""
        # Test that differential_evolution still works without basinhopping params
        params_de = self.widget.get_method_params()
        assert params_de["optimization_method"] == "differential_evolution"

        # Switch to basinhopping and verify it adds new params without breaking old ones
        self.widget.method_combo.setCurrentText("basinhopping")
        params_bh = self.widget.get_method_params()

        assert params_bh["optimization_method"] == "basinhopping"
        assert "T" in params_bh
        assert "niter" in params_bh
        assert "stepsize" in params_bh
        assert "batch_size" in params_bh
        assert "minimizer_method" in params_bh


if __name__ == "__main__":
    pytest.main([__file__])
    pytest.main([__file__])
