import json
import os
from collections import defaultdict

import numpy as np
from core.basic_signals import BasicSignals
from core.logger_config import logger
from core.logger_console import LoggerConsole as console
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class FileTransferButtons(QWidget, BasicSignals):
    request_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        # После добавления сигналов при первом выборе вкладки деконволюции происходит
        # непрусмотренное выскакивание окна на долю секунды
        BasicSignals.__init__(self, actor_name="file_tansfer_buttons")
        self.layout = QVBoxLayout(self)

        self.load_reactions_button = QPushButton("Импорт")
        self.export_reactions_button = QPushButton("Экспорт")
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.load_reactions_button)
        self.buttons_layout.addWidget(self.export_reactions_button)
        self.layout.addLayout(self.buttons_layout)

        self.load_reactions_button.clicked.connect(self.load_reactions)
        self.export_reactions_button.clicked.connect(self.export_reactions)

    @pyqtSlot(dict)
    def response_slot(self, params: dict):
        super().response_slot(params)

    def load_reactions(self):
        pass

    def _generate_suggested_file_name(self, file_name: str, data: dict):
        n_reactions = len(data)
        reaction_types = []
        for reaction_key, reaction_data in data.items():
            function = reaction_data.get("function", "")
            if function == "gauss":
                reaction_types.append("gs")
            elif function == "fraser":
                reaction_types.append("fr")
            elif function == "ads":
                reaction_types.append("ads")

        reaction_codes = "_".join(reaction_types)
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        suggested_file_name = f"{base_name}_{n_reactions}_rcts_{reaction_codes}.json"
        return suggested_file_name

    def export_reactions(self):
        request_id = self.create_and_emit_request("main_tab", "get_file_name")
        file_name = self.handle_response_data(request_id)
        logger.debug(f"file_name: {file_name}")

        request_id = self.create_and_emit_request("calculations_data", "get_value", path_keys=[file_name])
        data = self.handle_response_data(request_id)
        logger.debug(f"data: {data}")

        suggested_file_name = self._generate_suggested_file_name(file_name, data)

        save_file_name, _ = QFileDialog.getSaveFileName(
            self, "Выберите место для сохранения JSON файла", suggested_file_name, "JSON Files (*.json)"
        )

        if save_file_name:
            with open(save_file_name, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4, cls=NumpyArrayEncoder)
                console.log(f"Данные успешно экспортированы в файл:\n\n{save_file_name}")
                logger.info(f"Данные успешно экспортированы в файл:{save_file_name}")


class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyArrayEncoder, self).default(obj)


class ReactionTable(QWidget):
    reaction_added = pyqtSignal(dict)
    reaction_removed = pyqtSignal(dict)
    reaction_chosed = pyqtSignal(dict)
    reaction_function_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.add_reaction_button = QPushButton("Добавить")
        self.del_reaction_button = QPushButton("Удалить")
        self.top_buttons_layout = QHBoxLayout()
        self.top_buttons_layout.addWidget(self.add_reaction_button)
        self.top_buttons_layout.addWidget(self.del_reaction_button)
        self.layout.addLayout(self.top_buttons_layout)

        self.reactions_tables = {}
        self.reactions_counters = defaultdict(int)
        self.active_file = None
        self.active_reaction = ""
        self.calculation_settings = defaultdict(dict)

        self.settings_button = QPushButton("Настрйоки расчета")
        self.layout.addWidget(self.settings_button)

        self.add_reaction_button.clicked.connect(self.add_reaction)
        self.del_reaction_button.clicked.connect(self.del_reaction)
        self.settings_button.clicked.connect(self.open_settings)

    def switch_file(self, file_name):
        if file_name not in self.reactions_tables:
            self.reactions_tables[file_name] = QTableWidget()
            self.reactions_tables[file_name].setColumnCount(2)
            self.reactions_tables[file_name].setHorizontalHeaderLabels(["Имя", "Функция"])
            self.reactions_tables[file_name].horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.reactions_tables[file_name].itemClicked.connect(self.selected_reaction)
            self.layout.addWidget(self.reactions_tables[file_name])

        if self.active_file:
            self.reactions_tables[self.active_file].setVisible(False)

        self.reactions_tables[file_name].setVisible(True)
        self.active_file = file_name

    def function_changed(self, reaction_name, combo):
        function = combo.currentText()
        data_change = {
            "path_keys": [reaction_name, "function"],
            "operation": "update_value",
            "value": function,
        }
        self.reaction_function_changed.emit(data_change)
        logger.debug(f"Изменена реакция для {reaction_name}: {function}")

    def add_reaction(self):
        if not self.active_file:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран.")
            return

        table = self.reactions_tables[self.active_file]
        row_count = table.rowCount()
        table.insertRow(row_count)

        reaction_name = f"reaction_{self.reactions_counters[self.active_file]}"
        combo = QComboBox()
        combo.addItems(["gauss", "fraser", "ads"])
        combo.setCurrentText("gauss")
        combo.currentIndexChanged.connect(lambda: self.function_changed(reaction_name, combo))

        table.setItem(row_count, 0, QTableWidgetItem(reaction_name))
        table.setCellWidget(row_count, 1, combo)

        reaction_data = {"path_keys": [reaction_name], "operation": "add_reaction"}
        self.reaction_added.emit(reaction_data)
        self.reactions_counters[self.active_file] += 1

    def on_fail_add_reaction(self):
        if not self.active_file:
            logger.debug("Файл не выбран. Откат операции добавления невозможен.")
            return

        table = self.reactions_tables[self.active_file]
        if table.rowCount() > 0:
            last_row = table.rowCount() - 1
            table.removeRow(last_row)
            self.reactions_counters[self.active_file] -= 1
            logger.debug("Неудачное добавление реакции. Удалена последняя строка.")

    def del_reaction(self):
        if not self.active_file:
            QMessageBox.warning(self, "Удаление Реакции", "Файл не выбран.")
            return

        table = self.reactions_tables[self.active_file]
        if table.rowCount() > 0:
            last_row = table.rowCount() - 1
            item = table.item(last_row, 0)
            if item is not None:
                reaction_name = item.text()
                table.removeRow(last_row)
                self.reactions_counters[self.active_file] -= 1

                reaction_data = {
                    "path_keys": [reaction_name],
                    "operation": "remove_reaction",
                }
                self.reaction_removed.emit(reaction_data)
            else:
                logger.debug("Попытка удалить пустую ячейку.")
        else:
            QMessageBox.warning(self, "Удаление Реакции", "В списке нет реакций для удаления.")

    def selected_reaction(self, item):
        row = item.row()
        reaction_name = self.reactions_tables[self.active_file].item(row, 0).text()
        self.active_reaction = reaction_name
        logger.debug(f"Активная реакция: {reaction_name}")
        self.reaction_chosed.emit({"path_keys": [reaction_name], "operation": "highlight_reaction"})

    def open_settings(self):
        if self.active_file:
            table = self.reactions_tables[self.active_file]
            reactions = {}
            for row in range(table.rowCount()):
                reaction_name = table.item(row, 0).text()
                combo = table.cellWidget(row, 1)
                reactions[reaction_name] = combo

            initial_settings = self.calculation_settings[self.active_file]
            dialog = CalculationSettingsDialog(reactions, initial_settings, self)
            if dialog.exec():
                selected_functions = dialog.get_selected_functions()

                empty_keys = [key for key, value in selected_functions.items() if not value]
                if empty_keys:
                    QMessageBox.warning(
                        self,
                        "Ошибка настроек",
                        f"{', '.join(empty_keys)} должна описываться хотя бы одной функцией.",
                    )
                    self.open_settings()
                    return

                self.calculation_settings[self.active_file] = selected_functions
                logger.debug(f"Выбранные функции: {selected_functions}")

                formatted_functions = "\n".join([f"{key}: {value}" for key, value in selected_functions.items()])
                message = f"    {self.active_file}\n{formatted_functions}"

                QMessageBox.information(self, "Фуннкции на расчет", f"Настройки обновлены для:\n{message}")
        else:
            QMessageBox.warning(self, "Фуннкции на расчет", "Файл не выбран.")


class CalculationSettingsDialog(QDialog):
    def __init__(self, reactions, initial_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Фуннкции на расчет")
        self.reactions = reactions
        self.initial_settings = initial_settings
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.form_layout = QFormLayout()
        self.checkboxes = {}
        for reaction_name, combo in self.reactions.items():
            functions = [combo.itemText(i) for i in range(combo.count())]
            checkbox_layout = QVBoxLayout()
            self.checkboxes[reaction_name] = []
            for function in functions:
                checkbox = QCheckBox(function)
                checkbox.setChecked(function in self.initial_settings.get(reaction_name, []))
                self.checkboxes[reaction_name].append(checkbox)
                checkbox_layout.addWidget(checkbox)
            self.form_layout.addRow(reaction_name, checkbox_layout)

        layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_selected_functions(self):
        selected_functions = {}
        for reaction_name, checkboxes in self.checkboxes.items():
            selected_functions[reaction_name] = [cb.text() for cb in checkboxes if cb.isChecked()]
        return selected_functions


class CoeffsTable(QTableWidget):
    update_value = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(5, 2, parent)
        self.header_labels = ["от", "до"]
        self.row_labels_dict = {
            "gauss": ["h", "z", "w"],
            "fraser": ["h", "z", "w", "fr"],
            "ads": ["h", "z", "w", "ads1", "ads2"],
        }
        self.default_row_labels = ["h", "z", "w", "_", "_"]
        self.setHorizontalHeaderLabels(self.header_labels)
        self.setVerticalHeaderLabels(self.default_row_labels)
        self.mock_table()
        self.calculate_fixed_height()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cellChanged.connect(self.update_reaction_params)
        self._is_table_filling = False

    def calculate_fixed_height(self):
        row_height = self.rowHeight(0)
        borders_height = len(self.default_row_labels) * 2
        header_height = self.horizontalHeader().height()
        total_height = (row_height * len(self.default_row_labels)) + header_height + borders_height
        self.setFixedHeight(total_height)

    def mock_table(self):
        for i in range(len(self.default_row_labels)):
            for j in range(len(self.header_labels)):
                self.setItem(i, j, QTableWidgetItem("NaN"))

    def fill_table(self, reaction_params: dict):
        logger.debug(f"Приняты параметры реакции для таблицы {reaction_params}")
        param_keys = ["lower_bound_coeffs", "upper_bound_coeffs"]
        function_type = reaction_params[param_keys[0]][1]
        if function_type not in self.row_labels_dict:
            logger.error(f"Неизвестный тип функции: {function_type}")
            return

        self._is_table_filling = True
        row_labels = self.row_labels_dict[function_type]
        self.setRowCount(len(row_labels))
        self.setVerticalHeaderLabels(row_labels)

        for j, key in enumerate(param_keys):
            try:
                data = reaction_params[key][2]  # структура ключей: x_range, function_type, params
                for i in range(min(len(row_labels), len(data))):
                    value = f"{data[i]:.2f}"
                    self.setItem(i, j, QTableWidgetItem(value))
            except IndexError as e:
                logger.error(f"Ошибка индекса при обработке данных '{key}': {e}")

        self.mock_remaining_cells(len(row_labels))
        self._is_table_filling = False

    def mock_remaining_cells(self, num_rows):
        for i in range(num_rows, len(self.default_row_labels)):
            for j in range(len(self.header_labels)):
                self.setItem(i, j, QTableWidgetItem("NaN"))

    def update_reaction_params(self, row, column):
        if not self._is_table_filling:
            try:
                item = self.item(row, column)
                value = float(item.text())
                row_label = self.verticalHeaderItem(row).text()
                column_label = self.horizontalHeaderItem(column).text()

                path_keys = [self.column_to_bound(column_label), row_label]
                data_change = {
                    "path_keys": path_keys,
                    "operation": "update_value",
                    "value": value,
                }
                self.update_value.emit(data_change)
            except ValueError as e:
                console.log(f"Неверные данные для преобразования в число: ряд {row+1}, колонка {column+1}")
                logger.error(f"Неверные данные для преобразования в число: ряд {row}, колонка {column}: {e}")

    def column_to_bound(self, column_label):
        return {"от": "lower_bound_coeffs", "до": "upper_bound_coeffs"}.get(column_label, "")


class CalcButtons(QWidget):
    calculation_started = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.start_button = QPushButton("Начать расчет")
        self.stop_button = QPushButton("Остановить расчет")
        self.layout.addWidget(self.start_button)

        self.start_button.clicked.connect(self.check_and_start_calculation)
        self.stop_button.clicked.connect(self.stop_calculation)
        self.is_calculating = False
        self.parent = parent

    def check_and_start_calculation(self):
        if not self.parent.reactions_table.active_file:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран.")
            return

        settings = self.parent.reactions_table.calculation_settings.get(self.parent.reactions_table.active_file, {})
        if not settings:
            QMessageBox.information(self, "Настройки обязательны.", "Настройки расчета не установлены.")
            self.parent.open_settings_dialog()
        else:
            data = {
                "path_keys": [],
                "operation": "deconvolution",
                "chosen_functions": settings,
            }
            self.calculation_started.emit(data)
            self.start_calculation()

    def start_calculation(self):
        self.is_calculating = True
        self.layout.replaceWidget(self.start_button, self.stop_button)
        self.start_button.hide()
        self.stop_button.show()

    def stop_calculation(self):
        self.is_calculating = False
        self.layout.replaceWidget(self.stop_button, self.start_button)
        self.stop_button.hide()
        self.start_button.show()


class DeconvolutionSubBar(QWidget, BasicSignals):
    update_value = pyqtSignal(dict)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        BasicSignals.__init__(self, actor_name="deconvolution_sub_bar")
        layout = QVBoxLayout(self)

        self.reactions_table = ReactionTable(self)
        self.coeffs_table = CoeffsTable(self)
        self.file_transfer_buttons = FileTransferButtons(self)
        self.calc_buttons = CalcButtons(self)

        layout.addWidget(self.reactions_table)
        layout.addWidget(self.coeffs_table)
        layout.addWidget(self.file_transfer_buttons)
        layout.addWidget(self.calc_buttons)

        self.coeffs_table.update_value.connect(self.handle_update_value)
        self.reactions_table.reaction_function_changed.connect(self.handle_update_function_value)

    def handle_update_value(self, data: dict):
        if self.reactions_table.active_reaction:
            data["path_keys"].insert(0, self.reactions_table.active_reaction)
            self.update_value.emit(data)
        else:
            console.log("Для изменения значения выберите реакцию.")

    def handle_update_function_value(self, data: dict):
        if self.reactions_table.active_reaction is not None:
            self.update_value.emit(data)

    def open_settings_dialog(self):
        self.reactions_table.open_settings()

    def get_reactions_for_file(self, file_name):
        table = self.reactions_table.reactions_tables[file_name]
        reactions = {}
        for row in range(table.rowCount()):
            reaction_name = table.item(row, 0).text()
            combo = table.cellWidget(row, 1)
            reactions[reaction_name] = combo
        return reactions
