"""
UI tests for ModelBasedPanel basinhopping components.
Tests the UI components and parameter validation for basinhopping.
"""

import os

import pytest
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.core.app_settings import BASINHOPPING_MINIMIZERS, BASINHOPPING_PARAM_RANGES
from src.gui.main_tab.sub_sidebar.model_based.model_based_panel import ModelBasedTab


class TestModelBasedPanelUI:
    """Test UI components for basinhopping in ModelBasedPanel."""

    @pytest.fixture(autouse=True)
    def setup_ui(self, qtbot):
        """Setup ModelBasedTab widget for testing."""
        self.widget = ModelBasedTab()
        qtbot.addWidget(self.widget)
        return self.widget

    def test_method_switching(self, qtbot):
        """Test switching between optimization methods."""
        # Initially differential_evolution should be selected
        assert self.widget.method_combo.currentText() == "differential_evolution"
        assert not self.widget.basinhopping_group.isVisible()

        # Switch to basinhopping
        self.widget.method_combo.setCurrentText("basinhopping")
        QTest.qWait(100)  # Allow UI to update

        assert self.widget.method_combo.currentText() == "basinhopping"
        assert self.widget.basinhopping_group.isVisible()

        # Switch back to differential_evolution
        self.widget.method_combo.setCurrentText("differential_evolution")
        QTest.qWait(100)

        assert self.widget.method_combo.currentText() == "differential_evolution"
        assert not self.widget.basinhopping_group.isVisible()

    def test_parameter_validation(self, qtbot):
        """Test validation of parameter ranges and types."""
        # Switch to basinhopping to access parameters
        self.widget.method_combo.setCurrentText("basinhopping")
        QTest.qWait(100)

        # Test temperature validation
        t_range = BASINHOPPING_PARAM_RANGES["T"]
        self.widget.temperature_spin.setValue(t_range[0])
        assert self.widget.temperature_spin.value() == t_range[0]

        self.widget.temperature_spin.setValue(t_range[1])
        assert self.widget.temperature_spin.value() == t_range[1]

        # Test iterations validation
        niter_range = BASINHOPPING_PARAM_RANGES["niter"]
        self.widget.niter_spin.setValue(niter_range[0])
        assert self.widget.niter_spin.value() == niter_range[0]

        self.widget.niter_spin.setValue(niter_range[1])
        assert self.widget.niter_spin.value() == niter_range[1]

        # Test stepsize validation
        stepsize_range = BASINHOPPING_PARAM_RANGES["stepsize"]
        self.widget.stepsize_spin.setValue(stepsize_range[0])
        assert self.widget.stepsize_spin.value() == stepsize_range[0]

        self.widget.stepsize_spin.setValue(stepsize_range[1])
        assert self.widget.stepsize_spin.value() == stepsize_range[1]

        # Test batch size validation
        batch_range = BASINHOPPING_PARAM_RANGES["batch_size"]
        self.widget.batch_size_spin.setValue(batch_range[0])
        assert self.widget.batch_size_spin.value() == batch_range[0]

        self.widget.batch_size_spin.setValue(batch_range[1])
        assert self.widget.batch_size_spin.value() == batch_range[1]

        # Test minimizer combo
        for minimizer in BASINHOPPING_MINIMIZERS:
            self.widget.minimizer_combo.setCurrentText(minimizer)
            assert self.widget.minimizer_combo.currentText() == minimizer

    def test_parameter_passing(self, qtbot):
        """Test correct parameter passing to backend."""
        # Test differential_evolution parameters
        de_params = self.widget.get_method_params()
        assert de_params["optimization_method"] == "differential_evolution"
        assert "T" not in de_params  # basinhopping params should not be present

        # Switch to basinhopping and test parameters
        self.widget.method_combo.setCurrentText("basinhopping")
        QTest.qWait(100)

        # Set specific values
        test_T = 1.5
        test_niter = 150
        test_stepsize = 0.7
        test_batch_size = 6
        test_minimizer = "SLSQP"

        self.widget.temperature_spin.setValue(test_T)
        self.widget.niter_spin.setValue(test_niter)
        self.widget.stepsize_spin.setValue(test_stepsize)
        self.widget.batch_size_spin.setValue(test_batch_size)
        self.widget.minimizer_combo.setCurrentText(test_minimizer)

        # Get parameters and verify
        basinhopping_params = self.widget.get_method_params()

        assert basinhopping_params["optimization_method"] == "basinhopping"
        assert basinhopping_params["T"] == test_T
        assert basinhopping_params["niter"] == test_niter
        assert basinhopping_params["stepsize"] == test_stepsize
        assert basinhopping_params["batch_size"] == test_batch_size
        assert basinhopping_params["minimizer_method"] == test_minimizer

    def test_dynamic_visibility(self, qtbot):
        """Test dynamic visibility of basinhopping parameters."""
        # Initially should be hidden
        assert not self.widget.basinhopping_group.isVisible()

        # Show basinhopping parameters
        self.widget._on_method_changed("basinhopping")
        assert self.widget.basinhopping_group.isVisible()

        # Hide basinhopping parameters
        self.widget._on_method_changed("differential_evolution")
        assert not self.widget.basinhopping_group.isVisible()

    def test_default_values(self, qtbot):
        """Test default values for all parameters."""
        self.widget.method_combo.setCurrentText("basinhopping")
        QTest.qWait(100)

        # Test default values match expected ranges
        assert 1.0 == self.widget.temperature_spin.value()
        assert 100 == self.widget.niter_spin.value()
        assert 0.5 == self.widget.stepsize_spin.value()
        assert self.widget.batch_size_spin.value() == min(4, os.cpu_count())
        assert self.widget.minimizer_combo.currentText() in BASINHOPPING_MINIMIZERS

    def test_ui_layout_adaptation(self, qtbot):
        """Test UI layout adaptation when switching methods."""
        # Get initial size
        initial_size = self.widget.size()  # Switch to basinhopping - should expand
        self.widget.method_combo.setCurrentText("basinhopping")
        QTest.qWait(100)

        # Switch back to differential_evolution - should contract
        self.widget.method_combo.setCurrentText("differential_evolution")
        QTest.qWait(100)
        final_size = self.widget.size()

        # The widget should adapt its size (we can't predict exact values due to layout managers)
        assert not self.widget.basinhopping_group.isVisible()
        assert final_size == initial_size or abs(final_size.height() - initial_size.height()) < 50


if __name__ == "__main__":
    app = QApplication([])
    pytest.main([__file__])
