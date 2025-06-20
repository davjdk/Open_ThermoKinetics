"""
Series management and calculation settings dialogs.
Contains dialogs for configuring calculation parameters and model selection.
"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_settings import BASINHOPPING_MINIMIZERS, BASINHOPPING_PARAM_RANGES, NUC_MODELS_LIST


class CalculationSettingsDialog(QDialog):
    """Dialog for configuring calculation settings and reaction parameters."""

    def __init__(
        self, reactions_data: list[dict], calculation_method: str, calculation_method_params: dict, parent=None
    ):
        """Initialize calculation settings dialog.

        Args:
            reactions_data: List of reaction configurations
            calculation_method: Current calculation method
            calculation_method_params: Method-specific parameters            parent: Parent widget
        """
        super().__init__(parent)
        self.calculation_method = calculation_method
        self.calculation_method_params = calculation_method_params
        self.setWindowTitle("Calculation Settings")

        self.reactions_data = reactions_data or []
        self.de_params_edits = {}
        self._last_method = None  # Track method changes for parameter switching

        self._setup_ui()
        self.update_method_parameters()

    def _setup_ui(self):
        """Setup the dialog user interface."""
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        # Left panel - method settings
        left_widget = self._create_left_panel()
        main_layout.addWidget(left_widget)

        # Right panel - reaction settings
        right_widget = self._create_right_panel()
        main_layout.addWidget(right_widget, stretch=1)

    def _create_left_panel(self):
        """Create left panel with method configuration."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)  # Method selection
        method_label = QLabel("Calculation method:")
        self.calculation_method_combo = QComboBox()
        self.calculation_method_combo.addItems(["differential_evolution", "basinhopping"])
        self.calculation_method_combo.setCurrentText(self.calculation_method)
        self.calculation_method_combo.currentTextChanged.connect(self.update_method_parameters)

        left_layout.addWidget(method_label)
        left_layout.addWidget(self.calculation_method_combo)  # Differential evolution settings
        self.de_group = QGroupBox("Differential Evolution Settings")
        self.de_layout = QFormLayout()
        self.de_group.setLayout(self.de_layout)
        left_layout.addWidget(self.de_group, stretch=0)

        self._setup_de_parameters()

        # Basin-hopping settings
        self.basinhopping_group = QGroupBox("Basin-Hopping Parameters")
        self.basinhopping_layout = QFormLayout()
        self.basinhopping_group.setLayout(self.basinhopping_layout)
        left_layout.addWidget(self.basinhopping_group, stretch=0)

        self._setup_basinhopping_parameters()
        left_layout.addStretch(1)

        return left_widget

    def _setup_de_parameters(self):
        """Setup differential evolution parameter inputs."""
        for param_name, default_value in self.calculation_method_params.items():
            label = QLabel(param_name)
            label.setToolTip(self.get_tooltip_for_parameter(param_name))

            if isinstance(default_value, bool):
                edit_widget = QCheckBox()
                edit_widget.setChecked(default_value)
            elif param_name in ["strategy", "init", "updating"]:
                edit_widget = QComboBox()
                edit_widget.addItems(self.get_options_for_parameter(param_name))
                edit_widget.setCurrentText(str(default_value))
            elif isinstance(default_value, tuple):
                # Handle tuple parameters - display as string but preserve type info
                text_val = str(default_value) if default_value else "()"
                edit_widget = QLineEdit(text_val)
            else:
                text_val = str(default_value) if default_value is not None else "None"
                edit_widget = QLineEdit(text_val)

            self.de_params_edits[param_name] = edit_widget
            self.de_layout.addRow(label, edit_widget)

    def _create_right_panel(self):
        """Create right panel with reaction configurations."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Scroll area for reactions
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        right_layout.addWidget(scroll_area)

        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)

        self.reactions_grid = QGridLayout(scroll_content)
        scroll_content.setLayout(self.reactions_grid)

        self.reaction_boxes = []
        self._setup_reaction_boxes()

        # Dialog buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        right_layout.addWidget(btn_box)

        return right_widget

    def _setup_reaction_boxes(self):
        """Setup individual reaction configuration boxes."""
        for i, reaction in enumerate(self.reactions_data):
            row = i % 2
            col = i // 2

            box_widget = self._create_reaction_box(reaction)
            self.reactions_grid.addWidget(box_widget, row, col)

    def _create_reaction_box(self, reaction):
        """Create configuration box for a single reaction."""
        box_widget = QWidget()
        box_layout = QVBoxLayout(box_widget)

        # Reaction header
        top_line_widget = QWidget()
        top_line_layout = QHBoxLayout(top_line_widget)

        reaction_label = QLabel(f"{reaction.get('from', '?')} -> {reaction.get('to', '?')}")
        top_line_layout.addWidget(reaction_label)

        combo_type = QComboBox()
        combo_type.addItems(NUC_MODELS_LIST)
        current_type = reaction.get("reaction_type", "F2")
        if current_type in NUC_MODELS_LIST:
            combo_type.setCurrentText(current_type)
        top_line_layout.addWidget(combo_type)

        box_layout.addWidget(top_line_widget)

        # Model selection
        models_selection_widget = self._create_models_selection(reaction)
        box_layout.addWidget(models_selection_widget)

        # Parameter table
        table = self._create_parameter_table(reaction)
        box_layout.addWidget(table)

        # Store components for later retrieval
        many_models_checkbox = models_selection_widget.findChild(QCheckBox)
        add_models_button = models_selection_widget.findChild(QPushButton)

        self.reaction_boxes.append((combo_type, many_models_checkbox, add_models_button, table, reaction_label))

        return box_widget

    def _create_models_selection(self, reaction):
        """Create model selection widgets."""
        models_selection_widget = QWidget()
        models_selection_layout = QHBoxLayout(models_selection_widget)

        many_models_checkbox = QCheckBox("Many models")
        add_models_button = QPushButton("Add models")
        add_models_button.setEnabled(False)
        add_models_button.selected_models = []

        models_selection_layout.addWidget(many_models_checkbox)
        models_selection_layout.addWidget(add_models_button)

        # Connect signals
        many_models_checkbox.stateChanged.connect(
            lambda state, btn=add_models_button: btn.setEnabled(state == Qt.CheckState.Checked.value)
        )

        def open_models_dialog(checked, btn=add_models_button):
            dialog = ModelsSelectionDialog(NUC_MODELS_LIST, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected = dialog.get_selected_models()
                btn.selected_models = selected
                btn.setText(f"Add models ({len(selected)})")

        add_models_button.clicked.connect(open_models_dialog)

        return models_selection_widget

    def _create_parameter_table(self, reaction):
        """Create parameter range table for a reaction."""
        table = QTableWidget(3, 2, self)
        table.setHorizontalHeaderLabels(["Min", "Max"])
        table.setVerticalHeaderLabels(["Ea", "log(A)", "contribution"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        table.verticalHeader().setVisible(True)
        table.horizontalHeader().setVisible(True)

        table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: lightgray;
                color: black;
            }
            QTableWidget::item:focus {
                background-color: lightgray;
                color: black;
            }
        """)

        # Fill with reaction data
        ea_min = str(reaction.get("Ea_min", 1))
        ea_max = str(reaction.get("Ea_max", 2000))
        table.setItem(0, 0, QTableWidgetItem(ea_min))
        table.setItem(0, 1, QTableWidgetItem(ea_max))

        log_a_min = str(reaction.get("log_A_min", 0.1))
        log_a_max = str(reaction.get("log_A_max", 100))
        table.setItem(1, 0, QTableWidgetItem(log_a_min))
        table.setItem(1, 1, QTableWidgetItem(log_a_max))

        contrib_min = str(reaction.get("contribution_min", 0.01))
        contrib_max = str(reaction.get("contribution_max", 1.0))
        table.setItem(2, 0, QTableWidgetItem(contrib_min))
        table.setItem(2, 1, QTableWidgetItem(contrib_max))

        return table

    def update_method_parameters(self):
        """Update parameter visibility and load default parameters based on selected method."""
        selected_method = self.calculation_method_combo.currentText()

        # Show only the relevant parameter group
        if selected_method == "differential_evolution":
            self.de_group.setVisible(True)
            self.basinhopping_group.setVisible(False)
            # Load default DE parameters if switching from basinhopping
            if hasattr(self, "_last_method") and self._last_method == "basinhopping":
                self._load_default_de_parameters()
        elif selected_method == "basinhopping":
            self.de_group.setVisible(False)
            self.basinhopping_group.setVisible(True)
            # Load default basinhopping parameters if switching from DE
            if hasattr(self, "_last_method") and self._last_method == "differential_evolution":
                self._load_default_basinhopping_parameters()
        else:
            # Default to DE if unknown method
            self.de_group.setVisible(True)
            self.basinhopping_group.setVisible(False)
            if hasattr(self, "_last_method") and self._last_method == "basinhopping":
                self._load_default_de_parameters()

        # Remember current method for next switch
        self._last_method = selected_method

    def get_data(self):  # noqa: C901
        """Get dialog data - calculation settings and updated reactions."""
        selected_method = self.calculation_method_combo.currentText()
        errors = []
        method_params = {}

        # Validate and collect method parameters
        if selected_method == "differential_evolution":
            for key, widget in self.de_params_edits.items():
                if isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                else:
                    text = widget.text().strip()
                    default_value = self.calculation_method_params[key]
                    value = self.convert_to_type(text, default_value)

                is_valid, error_msg = self.validate_parameter(key, value)
                if not is_valid:
                    errors.append(f"Parameter '{key}': {error_msg}")
                method_params[key] = value
        elif selected_method == "basinhopping":
            for key, widget in self.basinhopping_params_edits.items():
                if isinstance(widget, QComboBox):
                    value = widget.currentText()
                elif isinstance(widget, QDoubleSpinBox):
                    value = widget.value()
                elif isinstance(widget, QSpinBox):
                    value = widget.value()
                else:
                    value = widget.value()

                is_valid, error_msg = self.validate_basinhopping_parameter(key, value)
                if not is_valid:
                    errors.append(f"Basinhopping parameter '{key}': {error_msg}")
                method_params[key] = value
        else:
            method_params = {"info": "No additional params set for unknown method"}

        if errors:
            QMessageBox.warning(self, "Invalid parameters", "\n".join(errors))
            return None, None

        # Collect updated reaction data
        updated_reactions = self._collect_reaction_data()

        return {"method": selected_method, "method_parameters": method_params}, updated_reactions

    def _collect_reaction_data(self):
        """Collect reaction configuration data from UI."""
        updated_reactions = []

        for (combo_type, many_models_checkbox, add_models_button, table, label_reaction), old_reaction in zip(
            self.reaction_boxes, self.reactions_data
        ):
            # Get table values
            ea_min_str = table.item(0, 0).text().strip()
            ea_max_str = table.item(0, 1).text().strip()
            loga_min_str = table.item(1, 0).text().strip()
            loga_max_str = table.item(1, 1).text().strip()
            contrib_min_str = table.item(2, 0).text().strip()
            contrib_max_str = table.item(2, 1).text().strip()

            # Create updated reaction
            updated_reaction = old_reaction.copy()
            updated_reaction["reaction_type"] = combo_type.currentText()

            # Update range values with validation
            try:
                updated_reaction["Ea_min"] = float(ea_min_str)
                updated_reaction["Ea_max"] = float(ea_max_str)
                updated_reaction["log_A_min"] = float(loga_min_str)
                updated_reaction["log_A_max"] = float(loga_max_str)
                updated_reaction["contribution_min"] = float(contrib_min_str)
                updated_reaction["contribution_max"] = float(contrib_max_str)
            except ValueError:
                # Keep original values if conversion fails
                pass

            # Handle multiple models if selected
            if many_models_checkbox.isChecked():
                selected_models = getattr(add_models_button, "selected_models", [])
                if selected_models:
                    updated_reaction["allowed_models"] = selected_models

            updated_reactions.append(updated_reaction)

        return updated_reactions

    # Helper methods for parameter validation and tooltips
    def get_tooltip_for_parameter(self, param_name):
        """Get tooltip text for a parameter."""
        tooltips = {
            "strategy": "Differential evolution strategy to use",
            "maxiter": "Maximum number of iterations",
            "popsize": "Population size multiplier",
            "workers": "Number of parallel workers",
            "polish": "Whether to polish final result",
        }
        return tooltips.get(param_name, f"Parameter: {param_name}")

    def get_options_for_parameter(self, param_name):
        """Get valid options for choice parameters."""
        options = {
            "strategy": ["best1bin", "best1exp", "rand1exp", "randtobest1exp", "currenttobest1exp"],
            "init": ["latinhypercube", "random"],
            "updating": ["immediate", "deferred"],
        }
        return options.get(param_name, ["default"])

    def convert_to_type(self, text, default_value):
        """Convert text input to appropriate type."""
        if default_value is None:
            return text if text != "None" else None

        if isinstance(default_value, int):
            return int(text)
        elif isinstance(default_value, float):
            return float(text)
        elif isinstance(default_value, bool):
            return text.lower() in ("true", "1", "yes")
        elif isinstance(default_value, tuple):
            if text.strip() == "()":
                return ()
            try:
                # Use eval for safe tuple parsing (only for tuples)
                if text.startswith("(") and text.endswith(")"):
                    return eval(text)
                else:
                    # Try to convert to tuple of floats
                    parts = text.split(",")
                    if len(parts) == 2:
                        return (float(parts[0].strip()), float(parts[1].strip()))
            except (ValueError, SyntaxError):
                return default_value
            return default_value
        else:
            return text

    def validate_parameter(self, param_name, value):
        """Validate parameter value."""
        if param_name == "maxiter" and (not isinstance(value, int) or value <= 0):
            return False, "Must be a positive integer"
        if param_name == "popsize" and (not isinstance(value, int) or value <= 0):
            return False, "Must be a positive integer"
        if param_name == "workers" and (not isinstance(value, int) or value < 1):
            return False, "Must be an integer >= 1"
        return True, ""

    def _setup_basinhopping_parameters(self):
        """Setup basin-hopping parameter inputs."""
        # Use existing parameters if method is basinhopping, otherwise use defaults
        if self.calculation_method == "basinhopping" and self.calculation_method_params:
            current_params = self.calculation_method_params.copy()
        else:
            current_params = {
                "T": 1.0,
                "niter": 100,
                "stepsize": 0.5,
                "batch_size": min(4, os.cpu_count() or 4),
                "minimizer_method": "L-BFGS-B",
            }

        self.basinhopping_params_edits = {}

        # Temperature parameter (T)
        self.temperature_spin = QDoubleSpinBox()
        t_range = BASINHOPPING_PARAM_RANGES["T"]
        self.temperature_spin.setRange(t_range[0], t_range[1])
        self.temperature_spin.setValue(current_params.get("T", 1.0))
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(2)
        self.temperature_spin.setToolTip("Temperature parameter for acceptance probability")
        self.basinhopping_params_edits["T"] = self.temperature_spin
        self.basinhopping_layout.addRow("Temperature (T):", self.temperature_spin)

        # Number of iterations (niter)
        self.niter_spin = QSpinBox()
        niter_range = BASINHOPPING_PARAM_RANGES["niter"]
        self.niter_spin.setRange(niter_range[0], niter_range[1])
        self.niter_spin.setValue(current_params.get("niter", 100))
        self.niter_spin.setToolTip("Number of basin-hopping iterations")
        self.basinhopping_params_edits["niter"] = self.niter_spin
        self.basinhopping_layout.addRow("Iterations (niter):", self.niter_spin)

        # Step size (stepsize)
        self.stepsize_spin = QDoubleSpinBox()
        stepsize_range = BASINHOPPING_PARAM_RANGES["stepsize"]
        self.stepsize_spin.setRange(stepsize_range[0], stepsize_range[1])
        self.stepsize_spin.setValue(current_params.get("stepsize", 0.5))
        self.stepsize_spin.setSingleStep(0.01)
        self.stepsize_spin.setDecimals(3)
        self.stepsize_spin.setToolTip("Step size for random displacement")
        self.basinhopping_params_edits["stepsize"] = self.stepsize_spin
        self.basinhopping_layout.addRow("Step Size:", self.stepsize_spin)

        # Batch size for Batch-Stepper (batch_size)
        self.batch_size_spin = QSpinBox()
        batch_range = BASINHOPPING_PARAM_RANGES["batch_size"]
        self.batch_size_spin.setRange(batch_range[0], min(batch_range[1], os.cpu_count() or 4))
        self.batch_size_spin.setValue(current_params.get("batch_size", min(4, os.cpu_count() or 4)))
        self.batch_size_spin.setToolTip("Batch size for parallel step evaluation")
        self.basinhopping_params_edits["batch_size"] = self.batch_size_spin
        self.basinhopping_layout.addRow("Batch Size:", self.batch_size_spin)

        # Local minimizer method (minimizer_method)
        self.minimizer_combo = QComboBox()
        self.minimizer_combo.addItems(BASINHOPPING_MINIMIZERS)
        self.minimizer_combo.setCurrentText(current_params.get("minimizer_method", "L-BFGS-B"))
        self.minimizer_combo.setToolTip("Local minimizer method for each basin")
        self.basinhopping_params_edits["minimizer_method"] = self.minimizer_combo
        self.basinhopping_layout.addRow("Local Minimizer:", self.minimizer_combo)

    def validate_basinhopping_parameter(self, param_name, value):  # noqa: C901
        """Validate basinhopping parameter value."""
        if param_name == "T":
            t_range = BASINHOPPING_PARAM_RANGES["T"]
            if not (t_range[0] <= value <= t_range[1]):
                return False, f"Must be between {t_range[0]} and {t_range[1]}"
        elif param_name == "niter":
            niter_range = BASINHOPPING_PARAM_RANGES["niter"]
            if not (niter_range[0] <= value <= niter_range[1]):
                return False, f"Must be between {niter_range[0]} and {niter_range[1]}"
        elif param_name == "stepsize":
            stepsize_range = BASINHOPPING_PARAM_RANGES["stepsize"]
            if not (stepsize_range[0] <= value <= stepsize_range[1]):
                return False, f"Must be between {stepsize_range[0]} and {stepsize_range[1]}"
        elif param_name == "batch_size":
            batch_range = BASINHOPPING_PARAM_RANGES["batch_size"]
            max_cpus = os.cpu_count() or 4
            if not (batch_range[0] <= value <= min(batch_range[1], max_cpus)):
                return False, f"Must be between {batch_range[0]} and {min(batch_range[1], max_cpus)}"
        elif param_name == "minimizer_method":
            if value not in BASINHOPPING_MINIMIZERS:
                return False, f"Must be one of {BASINHOPPING_MINIMIZERS}"
        return True, ""

    def _load_default_de_parameters(self):
        """Load default differential evolution parameters into UI."""
        from src.core.app_settings import MODEL_BASED_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS

        default_params = MODEL_BASED_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS.copy()

        # Clear existing widgets and recreate with default parameters
        self._clear_de_parameters()
        self.calculation_method_params = default_params
        self._setup_de_parameters()

    def _clear_de_parameters(self):
        """Clear all differential evolution parameter widgets."""
        # Remove all widgets from the layout
        while self.de_layout.count():
            child = self.de_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Clear the edits dictionary
        self.de_params_edits.clear()

    def _clear_basinhopping_parameters(self):
        """Clear all basinhopping parameter widgets."""
        # Remove all widgets from the layout
        while self.basinhopping_layout.count():
            child = self.basinhopping_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Clear the edits dictionary
        if hasattr(self, "basinhopping_params_edits"):
            self.basinhopping_params_edits.clear()

    def _load_default_basinhopping_parameters(self):
        """Load default basinhopping parameters into UI."""
        from src.core.app_settings import DEFAULT_BASINHOPPING_PARAMS

        default_params = DEFAULT_BASINHOPPING_PARAMS.copy()
        # Clear existing widgets and recreate with default parameters
        self._clear_basinhopping_parameters()
        self.calculation_method_params = {
            "T": default_params.get("T", 1.0),
            "niter": default_params.get("niter", 100),
            "stepsize": default_params.get("stepsize", 0.5),
            "batch_size": default_params.get("batch_size") or min(4, os.cpu_count() or 4),
            "minimizer_method": default_params.get("minimizer_kwargs", {}).get("method", "L-BFGS-B"),
        }
        self._setup_basinhopping_parameters()


class ModelsSelectionDialog(QDialog):
    """Dialog for selecting multiple models from a list."""

    def __init__(self, models_list, parent=None):
        """Initialize models selection dialog.

        Args:
            models_list: List of available model names
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Select Models")
        self.models_list = models_list
        self.selected_models = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog user interface."""
        layout = QVBoxLayout(self)

        # Create grid of checkboxes
        grid = QGridLayout()
        layout.addLayout(grid)

        self.checkboxes = []
        col_count = 6

        for index, model in enumerate(self.models_list):
            checkbox = QCheckBox(model)
            self.checkboxes.append(checkbox)
            row = index // col_count
            col = index % col_count
            grid.addWidget(checkbox, row, col)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_models(self):
        """Get list of selected model names."""
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]
