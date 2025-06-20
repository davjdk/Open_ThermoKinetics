# Этап 2 - Фаза 2: Интеграция GUI компонентов

## Общая информация

**Документ:** Фаза 2 - Расширение пользовательского интерфейса для dual_annealing  
**Ожидаемые сроки:** 1.5-2 часа  
**Сложность:** Средняя  
**Pull Request:** `feature/stage2-phase2-gui-dual-annealing`  
**Зависимости:** Фаза 1 должна быть завершена и смержена

## Цели фазы 2

### Основная цель
Расширить пользовательский интерфейс для поддержки всех трех методов оптимизации с полной валидацией параметров и intuitive UX.

### Задачи фазы 2
1. **Расширение CalculationSettingsDialog** для поддержки dual_annealing
2. **Добавление валидации параметров** и tooltips
3. **Создание динамических групп параметров** для каждого метода
4. **Интеграция UX улучшений** и обработки ошибок

## Детальное описание

### Задача 2.1: Расширение CalculationSettingsDialog

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/model_based.py`

**Действия:**

1. **Обновить инициализацию ComboBox:**
```python
# В CalculationSettingsDialog.__init__() (строка ~700):
self.calculation_method_combo.addItems([
    "differential_evolution", 
    "basinhopping", 
    "dual_annealing"
])
```

2. **Создать группы параметров для всех методов:**
```python
# После создания self.de_group добавить:

# Basinhopping группа
self.ba_group = QGroupBox("Basin Hopping Settings")
self.ba_layout = QFormLayout()
self.ba_group.setLayout(self.ba_layout)
left_layout.addWidget(self.ba_group, stretch=0)
self.ba_params_edits = {}

# Dual Annealing группа
self.da_group = QGroupBox("Dual Annealing Settings")
self.da_layout = QFormLayout()
self.da_group.setLayout(self.da_layout)
left_layout.addWidget(self.da_group, stretch=0)
self.da_params_edits = {}

# Изначально скрыть новые группы
self.ba_group.setVisible(False)
self.da_group.setVisible(False)
```

3. **Инициализация параметров для всех методов:**
```python
# В __init__() после создания групп:
def initialize_method_parameters(self):
    """Инициализация параметров для всех методов оптимизации"""
    from src.core.app_settings import (
        BASINHOPPING_DEFAULT_KWARGS,
        DUAL_ANNEALING_DEFAULT_KWARGS
    )
    
    # Инициализация Basinhopping параметров
    for param_name, default_value in BASINHOPPING_DEFAULT_KWARGS.items():
        if param_name in ['callback', 'take_step', 'accept_test']:  # Пропустить технические
            continue
        label = QLabel(param_name)
        label.setToolTip(self.get_tooltip_for_parameter(param_name))
        
        if isinstance(default_value, bool):
            edit_widget = QCheckBox()
            edit_widget.setChecked(default_value)
        elif isinstance(default_value, dict):
            # Для minimizer_kwargs отображаем как строку
            edit_widget = QLineEdit(str(default_value))
        else:
            text_val = str(default_value) if default_value is not None else "None"
            edit_widget = QLineEdit(text_val)
        
        self.ba_params_edits[param_name] = edit_widget
        self.ba_layout.addRow(label, edit_widget)
    
    # Инициализация Dual Annealing параметров
    for param_name, default_value in DUAL_ANNEALING_DEFAULT_KWARGS.items():
        if param_name in ['callback', 'x0']:  # Пропустить технические
            continue
        label = QLabel(param_name)
        label.setToolTip(self.get_tooltip_for_parameter(param_name))
        
        if isinstance(default_value, bool):
            edit_widget = QCheckBox()
            edit_widget.setChecked(default_value)
        else:
            text_val = str(default_value) if default_value is not None else "None"
            edit_widget = QLineEdit(text_val)
        
        self.da_params_edits[param_name] = edit_widget
        self.da_layout.addRow(label, edit_widget)

# Вызвать в конце __init__()
self.initialize_method_parameters()
```

### Задача 2.2: Обновление логики переключения методов

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/model_based.py`

**Действия:**

1. **Расширить update_method_parameters():**
```python
def update_method_parameters(self):
    """Показать/скрыть группы параметров в зависимости от выбранного метода"""
    selected_method = self.calculation_method_combo.currentText()
    
    # Скрыть все группы сначала
    self.de_group.setVisible(False)
    self.ba_group.setVisible(False)
    self.da_group.setVisible(False)
    
    # Показать нужную группу
    if selected_method == "differential_evolution":
        self.de_group.setVisible(True)
    elif selected_method == "basinhopping":
        self.ba_group.setVisible(True)
    elif selected_method == "dual_annealing":
        self.da_group.setVisible(True)
```

2. **Обновить get_data() для всех методов:**
```python
def get_data(self):
    """Получить настройки расчета для выбранного метода"""
    selected_method = self.calculation_method_combo.currentText()
    settings = {"method": selected_method, "method_parameters": {}}
    
    try:
        if selected_method == "differential_evolution":
            # Существующая логика для DE
            for key, widget in self.de_params_edits.items():
                # ... существующий код ...
                
        elif selected_method == "basinhopping":
            for key, widget in self.ba_params_edits.items():
                if isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                else:
                    text_value = widget.text().strip()
                    if key == "minimizer_kwargs":
                        # Парсинг словаря из строки
                        try:
                            import ast
                            value = ast.literal_eval(text_value)
                        except:
                            value = {"method": "L-BFGS-B"}  # Дефолт
                    elif key in ["niter", "interval", "niter_success"]:
                        value = int(text_value) if text_value != "None" else None
                    elif key in ["T", "stepsize"]:
                        value = float(text_value)
                    else:
                        value = text_value if text_value != "None" else None
                
                # Валидация параметра
                is_valid, error_msg = self.validate_parameter(key, value)
                if not is_valid:
                    raise ValueError(f"Параметр '{key}': {error_msg}")
                
                settings["method_parameters"][key] = value
                
        elif selected_method == "dual_annealing":
            for key, widget in self.da_params_edits.items():
                if isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                else:
                    text_value = widget.text().strip()
                    if key in ["initial_temp", "restart_temp_ratio", "visit", "accept"]:
                        value = float(text_value)
                    elif key in ["maxiter", "maxfun"]:
                        value = int(text_value) if text_value != "None" else None
                    else:
                        value = text_value if text_value != "None" else None
                
                # Валидация параметра
                is_valid, error_msg = self.validate_parameter(key, value)
                if not is_valid:
                    raise ValueError(f"Параметр '{key}': {error_msg}")
                
                settings["method_parameters"][key] = value
                
        return settings
        
    except ValueError as e:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Ошибка валидации", str(e))
        return None
    except Exception as e:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Критическая ошибка", f"Неожиданная ошибка: {str(e)}")
        return None
```

### Задача 2.3: Расширение валидации параметров

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/model_based.py`

**Действия:**

1. **Расширить validate_parameter():**
```python
def validate_parameter(self, key: str, value) -> tuple[bool, str]:
    """Валидация параметров всех методов оптимизации"""
    
    # Существующая валидация DE параметров...
    
    # Валидация Basinhopping параметров
    elif key == "niter":
        if not isinstance(value, int) or value < 1:
            return False, "Must be an integer >= 1."
    elif key == "T":
        if not isinstance(value, (int, float)) or value <= 0:
            return False, "Must be a positive number."
    elif key == "stepsize":
        if not isinstance(value, (int, float)) or value <= 0:
            return False, "Must be a positive number."
    elif key == "minimizer_kwargs":
        if not isinstance(value, dict):
            return False, "Must be a valid dictionary."
    elif key == "interval":
        if value is not None and (not isinstance(value, int) or value < 1):
            return False, "Must be an integer >= 1 or None."
    elif key == "niter_success":
        if value is not None and (not isinstance(value, int) or value < 1):
            return False, "Must be an integer >= 1 or None."
    elif key == "disp":
        if not isinstance(value, bool):
            return False, "Must be a boolean value."
    
    # Валидация Dual Annealing параметров
    elif key == "initial_temp":
        if not isinstance(value, (int, float)) or value <= 0:
            return False, "Must be a positive number."
    elif key == "restart_temp_ratio":
        if not isinstance(value, (int, float)) or not 1e-10 <= value <= 1e-1:
            return False, "Must be between 1e-10 and 1e-1."
    elif key == "visit":
        if not isinstance(value, (int, float)) or not 1.0 <= value <= 5.0:
            return False, "Must be between 1.0 and 5.0."
    elif key == "accept":
        if not isinstance(value, (int, float)) or not -20.0 <= value <= 20.0:
            return False, "Must be between -20.0 and 20.0."
    elif key == "maxfun":
        if value is not None and (not isinstance(value, int) or value < 1):
            return False, "Must be an integer >= 1 or None."
    elif key == "no_local_search":
        if not isinstance(value, bool):
            return False, "Must be a boolean value."
    elif key == "seed":
        if value is not None and not isinstance(value, int):
            return False, "Must be an integer or None."
    
    return True, ""
```

2. **Расширить get_tooltip_for_parameter():**
```python
def get_tooltip_for_parameter(self, param_name: str) -> str:
    """Получить tooltip для параметра"""
    tooltips = {
        # Существующие DE tooltips...
        
        # Basinhopping tooltips
        "niter": "Number of basin hopping iterations. Must be >= 1.",
        "T": "Temperature parameter for acceptance test. Must be > 0.",
        "stepsize": "Maximum step size for use in random displacement. Must be > 0.",
        "minimizer_kwargs": "Extra keyword arguments for the minimizer.",
        "interval": "Interval for how often to update the stepsize. Can be None.",
        "disp": "Print status messages during optimization.",
        "niter_success": "Stop after this many consecutive successful moves. Can be None.",
        
        # Dual Annealing tooltips
        "initial_temp": "Initial temperature. Must be > 0. Default: 5230.0",
        "restart_temp_ratio": "Temperature restart ratio. Range: 1e-10 to 1e-1. Default: 2e-05",
        "visit": "Visit parameter. Controls step acceptance. Range: 1.0 to 5.0. Default: 2.62",
        "accept": "Accept parameter. Controls acceptance probability. Range: -20.0 to 20.0. Default: -5.0",
        "maxfun": "Maximum function evaluations. Must be >= 1 or None. Default: 1000000",
        "no_local_search": "Disable local search optimization. Default: False",
        "seed": "Random seed for reproducible results. Can be None.",
    }
    return tooltips.get(param_name, "")
```

## Тестирование фазы 2

### GUI интеграционные тесты

**Файл:** `tests/test_stage2_phase2_gui.py` (новый файл)

```python
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.gui.main_tab.sub_sidebar.model_based.model_based import CalculationSettingsDialog

class TestPhase2GuiIntegration:
    """Тесты GUI интеграции фазы 2"""
    
    @pytest.fixture
    def app(self):
        """Создание QApplication для тестов"""
        return QApplication.instance() or QApplication([])
    
    @pytest.fixture
    def dialog(self, app):
        """Создание диалога для тестирования"""
        return CalculationSettingsDialog()
    
    def test_all_methods_available_in_combo(self, dialog):
        """Тест доступности всех методов в ComboBox"""
        methods = []
        for i in range(dialog.calculation_method_combo.count()):
            methods.append(dialog.calculation_method_combo.itemText(i))
        
        assert "differential_evolution" in methods
        assert "basinhopping" in methods
        assert "dual_annealing" in methods
        assert len(methods) == 3
    
    def test_parameter_groups_creation(self, dialog):
        """Тест создания групп параметров для всех методов"""
        # Проверить наличие всех групп
        assert hasattr(dialog, 'de_group')
        assert hasattr(dialog, 'ba_group') 
        assert hasattr(dialog, 'da_group')
        
        # Проверить наличие словарей параметров
        assert hasattr(dialog, 'de_params_edits')
        assert hasattr(dialog, 'ba_params_edits')
        assert hasattr(dialog, 'da_params_edits')
    
    def test_method_switching_visibility(self, dialog):
        """Тест переключения видимости групп параметров"""
        # Тест переключения на dual_annealing
        dialog.calculation_method_combo.setCurrentText("dual_annealing")
        dialog.update_method_parameters()
        
        assert not dialog.de_group.isVisible()
        assert not dialog.ba_group.isVisible()
        assert dialog.da_group.isVisible()
        
        # Тест переключения на basinhopping
        dialog.calculation_method_combo.setCurrentText("basinhopping")
        dialog.update_method_parameters()
        
        assert not dialog.de_group.isVisible()
        assert dialog.ba_group.isVisible()
        assert not dialog.da_group.isVisible()
        
        # Тест переключения на differential_evolution
        dialog.calculation_method_combo.setCurrentText("differential_evolution")
        dialog.update_method_parameters()
        
        assert dialog.de_group.isVisible()
        assert not dialog.ba_group.isVisible()
        assert not dialog.da_group.isVisible()
    
    def test_dual_annealing_parameter_validation(self, dialog):
        """Тест валидации параметров dual_annealing"""
        # Тест корректных значений
        assert dialog.validate_parameter("initial_temp", 100.0) == (True, "")
        assert dialog.validate_parameter("visit", 2.5) == (True, "")
        assert dialog.validate_parameter("no_local_search", False) == (True, "")
        
        # Тест некорректных значений
        is_valid, msg = dialog.validate_parameter("initial_temp", -1.0)
        assert not is_valid
        assert "positive" in msg.lower()
        
        is_valid, msg = dialog.validate_parameter("restart_temp_ratio", 1.0)  # Вне диапазона
        assert not is_valid
        assert "between" in msg.lower()
    
    def test_basinhopping_parameter_validation(self, dialog):
        """Тест валидации параметров basinhopping"""
        # Тест корректных значений
        assert dialog.validate_parameter("niter", 100) == (True, "")
        assert dialog.validate_parameter("T", 1.0) == (True, "")
        assert dialog.validate_parameter("minimizer_kwargs", {"method": "L-BFGS-B"}) == (True, "")
        
        # Тест некорректных значений
        is_valid, msg = dialog.validate_parameter("niter", 0)
        assert not is_valid
        assert "integer >= 1" in msg
        
        is_valid, msg = dialog.validate_parameter("T", -1.0)
        assert not is_valid
        assert "positive" in msg.lower()
    
    def test_tooltips_availability(self, dialog):
        """Тест доступности tooltips для всех параметров"""
        # Dual annealing tooltips
        tooltip = dialog.get_tooltip_for_parameter("initial_temp")
        assert tooltip is not None and len(tooltip) > 0
        assert "temperature" in tooltip.lower()
        
        tooltip = dialog.get_tooltip_for_parameter("restart_temp_ratio")
        assert tooltip is not None and len(tooltip) > 0
        
        # Basinhopping tooltips
        tooltip = dialog.get_tooltip_for_parameter("niter")
        assert tooltip is not None and len(tooltip) > 0
        assert "iteration" in tooltip.lower()
        
        tooltip = dialog.get_tooltip_for_parameter("T")
        assert tooltip is not None and len(tooltip) > 0
    
    def test_get_data_for_all_methods(self, dialog):
        """Тест получения данных для всех методов"""
        methods = ["differential_evolution", "basinhopping", "dual_annealing"]
        
        for method in methods:
            dialog.calculation_method_combo.setCurrentText(method)
            dialog.update_method_parameters()
            
            # Получить настройки
            settings = dialog.get_data()
            
            # Базовые проверки
            assert settings is not None
            assert settings["method"] == method
            assert "method_parameters" in settings
            assert isinstance(settings["method_parameters"], dict)
```

## Критерии приемки фазы 2

### Функциональные критерии
- ✅ **GUI-001**: CalculationSettingsDialog поддерживает все три метода
- ✅ **GUI-002**: Группы параметров создаются для каждого метода
- ✅ **GUI-003**: Переключение между методами работает корректно
- ✅ **GUI-004**: Валидация параметров работает для всех методов
- ✅ **GUI-005**: Tooltips доступны для всех параметров

### UX критерии
- ✅ **UX-001**: Интерфейс интуитивно понятен
- ✅ **UX-002**: Валидация предоставляет информативные сообщения
- ✅ **UX-003**: Переключение методов происходит плавно
- ✅ **UX-004**: Параметры имеют разумные значения по умолчанию

### Качественные критерии
- ✅ **QUAL-001**: GUI тесты покрывают новую функциональность
- ✅ **QUAL-002**: Обработка ошибок работает корректно
- ✅ **QUAL-003**: Код соответствует стандартам проекта

## Deliverables фазы 2

1. **Обновленные файлы:**
   - `src/gui/main_tab/sub_sidebar/model_based/model_based.py` - расширенный CalculationSettingsDialog
   
2. **Новые тесты:**
   - `tests/test_stage2_phase2_gui.py` - GUI интеграционные тесты

3. **UX улучшения:**
   - Полная валидация параметров с informative messages
   - Tooltips для всех параметров оптимизации

## План выполнения фазы 2

### Шаг 1: Расширение ComboBox и групп (30 минут)
1. Добавить новые методы в ComboBox
2. Создать группы параметров для basinhopping и dual_annealing
3. Инициализировать параметры из app_settings

### Шаг 2: Логика переключения (30 минут)
1. Обновить `update_method_parameters()`
2. Расширить `get_data()` для всех методов
3. Добавить обработку ошибок

### Шаг 3: Валидация и tooltips (45 минут)
1. Расширить `validate_parameter()` для новых методов
2. Добавить tooltips для всех параметров
3. Тестировать валидацию

### Шаг 4: Тестирование и отладка (45 минут)
1. Написать GUI интеграционные тесты
2. Запустить и проверить все тесты
3. Исправить найденные проблемы
4. Проверить UX на различных сценариях

## Результат фазы 2

После завершения фазы 2:
- ✅ GUI полностью поддерживает все три метода оптимизации
- ✅ Пользователь может легко переключаться между методами
- ✅ Все параметры валидируются с понятными сообщениями
- ✅ Система готова к фазе 3 (полное интеграционное тестирование)

**Следующая фаза:** Phase 3 - Full Integration Testing (комплексное тестирование всего workflow)
