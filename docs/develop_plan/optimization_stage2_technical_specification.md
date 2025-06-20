# Техническое задание: Этап 2 - Средние изменения для оптимизации производительности MODEL_BASED_CALCULATION

## Общая информация

**Документ:** Этап 2 реализации OPTIMIZATION_PERFORMANCE_ANALYSIS.md  
**Ожидаемые сроки:** 3-4 часа  
**Ожидаемый результат:** Ускорение в 4-8 раз, утилизация CPU 70-85%  
**Сложность:** Средняя  

## Цели и задачи

### Основная цель
Реализовать средний уровень оптимизации производительности MODEL_BASED_CALCULATION путем добавления новых алгоритмов оптимизации с ручной настройкой параметров пользователем.

### Ключевые задачи
1. **Интеграция dual_annealing** как третьего метода оптимизации
2. **Расширение UI** для поддержки новых возможностей
3. **Комплексное тестирование** новой функциональности

## Детальное описание задач

### Задача 1: Интеграция Dual Annealing алгоритма

#### 1.1 Добавление dual_annealing в core/app_settings.py

**Файл:** `src/core/app_settings.py`

**Текущее состояние:**
Проект уже поддерживает:
- `differential_evolution` с `MODEL_BASED_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS`
- `basinhopping` через `calculation.py:108-115` (интеграция уже существует)

**Действия:**
- Добавить "dual_annealing" в список OPTIMIZATION_METHODS
- Создать конфигурацию DUAL_ANNEALING_DEFAULT_KWARGS
- Добавить валидационные диапазоны DUAL_ANNEALING_PARAM_RANGES

**Конкретная реализация:**
```python
# Добавить в OPTIMIZATION_METHODS (если список не существует, создать):
OPTIMIZATION_METHODS = [
    "differential_evolution",
    "basinhopping", 
    "dual_annealing",  # НОВЫЙ МЕТОД
]

# Новые константы после MODEL_BASED_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS:
DUAL_ANNEALING_DEFAULT_KWARGS = {
    "maxiter": 1000,
    "initial_temp": 5230.0,
    "restart_temp_ratio": 2e-05,
    "visit": 2.62,
    "accept": -5.0,
    "maxfun": 1000000,
    "seed": None,
    "no_local_search": False,  # Важно для точности
    "callback": None,
    "x0": None,
}

DUAL_ANNEALING_PARAM_RANGES = {
    "maxiter": (100, 5000),
    "initial_temp": (1000.0, 10000.0),
    "restart_temp_ratio": (1e-06, 1e-03),
    "visit": (2.0, 3.0),
    "accept": (-10.0, 0.0),
    "maxfun": (100000, 10000000),
}
```

**Интеграция с архитектурой:**
- Константы будут использоваться в `CalculationSettingsDialog` для создания UI элементов
- Валидационные диапазоны будут применяться в `validate_parameter()` методах GUI

#### 1.2 Обновление core/calculation.py для поддержки dual_annealing

**Файл:** `src/core/calculation.py`

**Текущее состояние:**
В `run_calculation_scenario()` (строки 95-115) уже есть поддержка:
- `differential_evolution` - вызывает `start_differential_evolution()`
- `basinhopping` - через `scenario_instance.run()` в потоке

**Действия:**
1. Добавить импорт `from scipy.optimize import dual_annealing`
2. Добавить метод `start_dual_annealing()` аналогично `start_differential_evolution()` (строка 101)
3. Расширить условие в `run_calculation_scenario()` для обработки dual_annealing

**Критические моменты архитектуры:**
- dual_annealing должен интегрироваться через существующую `CalculationThread` систему
- Callback должен следовать паттерну `make_de_callback()` для model_based сценариев
- Результат возвращается как OptimizeResult объект (обрабатывается в `_calculation_finished()`)

**Конкретная реализация:**
```python
# Добавить импорт в начало файла:
from scipy.optimize import OptimizeResult, differential_evolution, dual_annealing

# Добавить новый метод после start_differential_evolution():
def start_dual_annealing(self, bounds, target_function, **kwargs):
    self.start_calculation_thread(
        dual_annealing,
        target_function,
        bounds=bounds,
        **kwargs,
    )

# Расширить условие в run_calculation_scenario() после строки 108:
elif optimization_method == "dual_annealing":
    calc_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()
    
    if scenario_key == "model_based_calculation":
        calc_params["callback"] = make_de_callback(target_function, self)
    
    self.start_dual_annealing(bounds=bounds, target_function=target_function, **calc_params)
```

#### 1.3 Обновление ModelBasedScenario для поддержки dual_annealing

**Файл:** `src/core/calculation_scenarios.py`

**Текущее состояние:**
- `ModelBasedScenario.get_optimization_method()` (строка 105) возвращает метод из `calculation_settings`
- Система сценариев уже поддерживает различные оптимизационные методы через базовую архитектуру

**Действия:**
- Убедиться, что `ModelBasedScenario.get_optimization_method()` корректно обрабатывает "dual_annealing"
- Проверить совместимость bounds и target_function с dual_annealing API

**Архитектурная интеграция:**
- Метод уже получает настройки из `self.params.get("calculation_settings", {}).get("method")`
- Target function и bounds уже корректно формируются в базовом классе
- Dual annealing будет использовать ту же `ModelBasedTargetFunction` что и другие методы

**Минимальные изменения (проверить совместимость):**
```python
# В ModelBasedScenario.get_optimization_method() (строка 105):
# Метод уже корректный, изменения не требуются
def get_optimization_method(self) -> str:
    return self.params.get("calculation_settings", {}).get("method", "differential_evolution")
```

**Проверка совместимости bounds:**
- dual_annealing принимает bounds в том же формате что и differential_evolution
- ModelBasedTargetFunction.__call__() универсальна для всех scipy оптимизаторов

### Задача 2: Расширение пользовательского интерфейса

#### 2.1 Обновление CalculationSettingsDialog

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/model_based.py`

**Текущее состояние анализа:**
- `CalculationSettingsDialog.__init__()` (строка 686) имеет ComboBox с методами: `["differential_evolution", "another_method"]`
- `update_method_parameters()` (строка 846) показывает/скрывает DE группу параметров
- `get_data()` (строка 853) обрабатывает параметры для каждого метода
- `validate_parameter()` и `get_tooltip_for_parameter()` содержат валидацию DE параметров

**Действия:**
1. Добавить "dual_annealing" в ComboBox выбора методов
2. Создать группу параметров для dual_annealing
3. Расширить `update_method_parameters()` для показа dual_annealing параметров
4. Добавить валидацию параметров dual_annealing
5. Добавить tooltips для новых параметров

**Конкретная реализация:**

```python
# В CalculationSettingsDialog.__init__() (строка 700):
self.calculation_method_combo.addItems(["differential_evolution", "basinhopping", "dual_annealing"])

# Добавить после создания self.de_group (строка 712):
self.da_group = QGroupBox("Dual Annealing Settings")
self.da_layout = QFormLayout()
self.da_group.setLayout(self.da_layout)
left_layout.addWidget(self.da_group, stretch=0)
self.da_params_edits = {}

# В update_method_parameters() расширить условие:
def update_method_parameters(self):
    selected_method = self.calculation_method_combo.currentText()
    if selected_method == "differential_evolution":
        self.de_group.setVisible(True)
        self.da_group.setVisible(False)
    elif selected_method == "dual_annealing":
        self.de_group.setVisible(False) 
        self.da_group.setVisible(True)
    else:
        self.de_group.setVisible(False)
        self.da_group.setVisible(False)

# В get_data() добавить обработку dual_annealing параметров после DE блока:
elif selected_method == "dual_annealing":
    for key, widget in self.da_params_edits.items():
        # Аналогичная логика как для DE параметров
```

**Интеграция с архитектурой:**
- Использовать `DUAL_ANNEALING_DEFAULT_KWARGS` из `app_settings.py`
- Применить существующие паттерны валидации и UI создания
- Следовать структуре DE группы для консистентности

#### 2.2 Расширение валидации и tooltips для dual_annealing

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/model_based.py`

**Действия в validate_parameter()** (строка 949):
```python
# Добавить новые случаи валидации:
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
    if not isinstance(value, int) or value < 1:
        return False, "Must be an integer >= 1."
elif key == "no_local_search":
    if not isinstance(value, bool):
        return False, "Must be a boolean value."
```

**Действия в get_tooltip_for_parameter()** (строка 993):
```python
# Расширить tooltips словарь:
tooltips = {
    # ...existing tooltips...
    "initial_temp": "Initial temperature. Must be > 0.",
    "restart_temp_ratio": "Temperature restart ratio. Range: 1e-10 to 1e-1.",
    "visit": "Visit parameter. Controls step acceptance. Range: 1.0 to 5.0.",
    "accept": "Accept parameter. Controls acceptance probability. Range: -20.0 to 20.0.",
    "maxfun": "Maximum function evaluations. Must be >= 1.",
    "no_local_search": "Disable local search optimization.",
}
```

**Инициализация dual_annealing параметров в __init__():**
```python
# После создания DA группы, добавить создание полей:
if selected_method == "dual_annealing" or True:  # Всегда создавать для переключения
    from src.core.app_settings import DUAL_ANNEALING_DEFAULT_KWARGS
    for param_name, default_value in DUAL_ANNEALING_DEFAULT_KWARGS.items():
        if param_name in ['callback', 'x0']:  # Пропустить технические параметры
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
```

### Задача 3: Критические архитектурные исправления

#### 3.1 Исправление работы с basinhopping

**Проблема:** 
В `src/core/calculation.py` строка 108 basinhopping обрабатывается некорректно. Метод вызывается через `scenario_instance.run()`, но такого метода нет в `ModelBasedScenario`.

**Файл:** `src/core/calculation.py`

**Действие:** Исправить обработку basinhopping по аналогии с differential_evolution:

```python
# В run_calculation_scenario() заменить строки 108-115:
elif optimization_method == "basinhopping":
    calc_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()
    
    if scenario_key == "model_based_calculation":
        calc_params["callback"] = make_de_callback(target_function, self)
    
    self.start_basinhopping(bounds=bounds, target_function=target_function, **calc_params)

# Добавить новый метод после start_differential_evolution():
def start_basinhopping(self, bounds, target_function, **kwargs):
    from scipy.optimize import basinhopping
    self.start_calculation_thread(
        basinhopping,
        target_function,
        bounds=bounds,
        **kwargs,
    )
```

#### 3.2 Обновление константы OPTIMIZATION_METHODS

**Проблема:** 
В `app_settings.py` нет централизованного списка методов оптимизации.

**Файл:** `src/core/app_settings.py`

**Действие:** Добавить после существующих MODEL_*_DEFAULT_KWARGS:

```python
# После MODEL_FREE_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS:
OPTIMIZATION_METHODS = [
    "differential_evolution",
    "basinhopping", 
    "dual_annealing",  # НОВЫЙ МЕТОД
]

# Новые константы для basinhopping (добавить для полноты):
BASINHOPPING_DEFAULT_KWARGS = {
    "niter": 100,
    "T": 1.0,
    "stepsize": 0.5,
    "minimizer_kwargs": {"method": "L-BFGS-B"},
    "take_step": None,
    "accept_test": None,
    "callback": None,
    "interval": 50,
    "disp": False,
    "niter_success": None,
    "seed": None,
}

DUAL_ANNEALING_DEFAULT_KWARGS = {
    "maxiter": 1000,
    "initial_temp": 5230.0,
    "restart_temp_ratio": 2e-05,
    "visit": 2.62,
    "accept": -5.0,
    "maxfun": 1000000,
    "seed": None,
    "no_local_search": False,  # Важно для точности
    "callback": None,
    "x0": None,
}
```

#### 3.3 Исправление интеграции с GUI

**Проблема:** 
В существующем CalculationSettingsDialog нет полной поддержки всех методов.

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/model_based.py`

**Действие:** Обновить логику CalculationSettingsDialog для поддержки всех трех методов:

```python
# В CalculationSettingsDialog.__init__() обновить строку 700:
self.calculation_method_combo.addItems(["differential_evolution", "basinhopping", "dual_annealing"])

# В update_method_parameters() расширить логику:
def update_method_parameters(self):
    selected_method = self.calculation_method_combo.currentText()
    # Скрыть все группы сначала
    self.de_group.setVisible(False)
    if hasattr(self, 'ba_group'):
        self.ba_group.setVisible(False)
    if hasattr(self, 'da_group'):
        self.da_group.setVisible(False)
    
    # Показать нужную группу
    if selected_method == "differential_evolution":
        self.de_group.setVisible(True)
    elif selected_method == "basinhopping":
        self.ba_group.setVisible(True)
    elif selected_method == "dual_annealing":
        self.da_group.setVisible(True)
```

### Задача 4: Комплексное тестирование

#### 4.1 Модульные тесты

**Файл:** `tests/test_optimization_stage2.py` (новый файл)

**Цель:** Проверка корректности работы новых компонентов и исправленных архитектурных элементов.

```python
import pytest
import numpy as np
from unittest.mock import Mock, patch
from src.core.app_settings import DUAL_ANNEALING_DEFAULT_KWARGS, BASINHOPPING_DEFAULT_KWARGS
from src.core.calculation import Calculations
from src.core.calculation_scenarios import ModelBasedScenario

class TestDualAnnealingIntegration:
    """Тесты интеграции dual_annealing"""
    
    def test_dual_annealing_default_parameters(self):
        """Тест корректности дефолтных параметров dual_annealing"""
        assert "maxiter" in DUAL_ANNEALING_DEFAULT_KWARGS
        assert "initial_temp" in DUAL_ANNEALING_DEFAULT_KWARGS
        assert DUAL_ANNEALING_DEFAULT_KWARGS["initial_temp"] > 0
        assert 1e-10 <= DUAL_ANNEALING_DEFAULT_KWARGS["restart_temp_ratio"] <= 1e-1
        
    def test_dual_annealing_bounds_compatibility(self):
        """Тест совместимости bounds с dual_annealing"""
        bounds = [(0, 10), (1, 5), (-1, 1)]
        scenario = ModelBasedScenario()
        # Проверить, что bounds корректно обрабатываются
        assert scenario.validate_bounds_for_method("dual_annealing", bounds) == True
        
    def test_dual_annealing_callback_integration(self):
        """Тест интеграции callback функции"""
        calc = Calculations()
        with patch('src.core.calculation.make_de_callback') as mock_callback:
            mock_callback.return_value = Mock()
            calc.start_dual_annealing(
                bounds=[(0, 1)], 
                target_function=lambda x: x[0]**2,
                maxiter=10
            )
            mock_callback.assert_called_once()

class TestBasinhoppingCorrection:
    """Тесты исправления basinhopping архитектуры"""
    
    def test_basinhopping_method_available(self):
        """Тест доступности метода basinhopping"""
        from src.core.app_settings import OPTIMIZATION_METHODS
        assert "basinhopping" in OPTIMIZATION_METHODS
        
    def test_basinhopping_execution_flow(self):
        """Тест корректности потока выполнения basinhopping"""
        calc = Calculations()
        with patch('src.core.calculation.basinhopping') as mock_bh:
            calc.start_basinhopping(
                bounds=[(0, 1)], 
                target_function=lambda x: x[0]**2,
                niter=5
            )
            mock_bh.assert_called_once()

class TestCalculationScenarioCorrections:
    """Тесты исправлений в run_calculation_scenario"""
    
    def test_all_methods_supported(self):
        """Тест поддержки всех методов оптимизации"""
        calc = Calculations()
        methods = ["differential_evolution", "basinhopping", "dual_annealing"]
        
        for method in methods:
            params = {
                "calculation_settings": {
                    "method": method,
                    "method_parameters": {"maxiter": 10}
                }
            }
            # Проверить, что метод распознается
            assert calc.validate_optimization_method(method) == True
```

#### 4.2 Интеграционные тесты GUI

**Файл:** `tests/test_gui_integration_stage2.py` (новый файл)

**Цель:** Проверка корректности интеграции GUI компонентов с новыми методами оптимизации.

```python
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.gui.main_tab.sub_sidebar.model_based.model_based import CalculationSettingsDialog

class TestCalculationSettingsDialogExtensions:
    """Тесты расширенного CalculationSettingsDialog"""
    
    @pytest.fixture
    def app(self):
        """Создание QApplication для тестов"""
        return QApplication.instance() or QApplication([])
    
    @pytest.fixture
    def dialog(self, app):
        """Создание диалога для тестирования"""
        return CalculationSettingsDialog()
    
    def test_all_methods_available(self, dialog):
        """Тест доступности всех методов в ComboBox"""
        methods = []
        for i in range(dialog.calculation_method_combo.count()):
            methods.append(dialog.calculation_method_combo.itemText(i))
        
        assert "differential_evolution" in methods
        assert "basinhopping" in methods
        assert "dual_annealing" in methods
    
    def test_dual_annealing_parameters_groups(self, dialog):
        """Тест создания группы параметров для dual_annealing"""
        dialog.calculation_method_combo.setCurrentText("dual_annealing")
        dialog.update_method_parameters()
        
        assert hasattr(dialog, 'da_group')
        assert dialog.da_group.isVisible()
        assert hasattr(dialog, 'da_params_edits')
        assert len(dialog.da_params_edits) > 0
    
    def test_parameter_validation(self, dialog):
        """Тест валидации параметров dual_annealing"""
        # Тест корректных значений
        assert dialog.validate_parameter("initial_temp", 100.0) == (True, "")
        assert dialog.validate_parameter("visit", 2.5) == (True, "")
        
        # Тест некорректных значений
        is_valid, msg = dialog.validate_parameter("initial_temp", -1.0)
        assert not is_valid
        assert "positive" in msg.lower()
        
    def test_tooltips_availability(self, dialog):
        """Тест доступности tooltips для новых параметров"""
        tooltip = dialog.get_tooltip_for_parameter("initial_temp")
        assert tooltip is not None and len(tooltip) > 0
        
        tooltip = dialog.get_tooltip_for_parameter("restart_temp_ratio")
        assert tooltip is not None and len(tooltip) > 0
```

#### 4.3 Интеграционные тесты полного рабочего процесса

**Файл:** `tests/test_model_based_integration_stage2.py` (новый файл)

**Цель:** Проверка полного цикла оптимизации с новыми методами через архитектуру сигналов.

```python
import pytest
import numpy as np
from unittest.mock import Mock, patch
from src.core.base_signals import BaseSignals
from src.core.calculation_data import CalculationsData
from src.core.series_data import SeriesData
from src.core.app_settings import OperationType

class TestModelBasedWorkflow:
    """Тесты полного рабочего процесса model-based анализа"""
    
    @pytest.fixture
    def signals(self):
        """Создание системы сигналов для тестирования"""
        return BaseSignals()
    
    @pytest.fixture
    def test_data(self):
        """Создание тестовых данных для анализа"""
        return {
            "test_series": {
                "experimental_data": np.random.random((100, 4)),
                "experimental_masses": [1, 1, 1],
                "reaction_scheme": {
                    "components": [{"id": "A"}, {"id": "B"}],
                    "reactions": [{
                        "from": "A", "to": "B",
                        "reaction_type": "F2",
                        "Ea": 120, "log_A": 8, "contribution": 0.5
                    }]
                },
                "calculation_settings": {
                    "method": "dual_annealing",
                    "method_parameters": {
                        "maxiter": 50,
                        "initial_temp": 5230.0
                    }
                }
            }
        }
    
    def test_dual_annealing_full_workflow(self, signals, test_data):
        """Тест полного цикла оптимизации с dual_annealing"""
        with patch('src.core.calculations.ModelBasedScenario') as mock_scenario:
            mock_scenario.return_value.run.return_value = {
                "optimized_params": {"Ea": 125, "log_A": 8.5},
                "mse": 0.001,
                "success": True
            }
            
            series_data = SeriesData(signals)
            series_data.data = test_data
            
            # Симуляция запроса MODEL_BASED_CALCULATION
            response = series_data.process_request(
                operation_type=OperationType.MODEL_BASED_CALCULATION,
                series_name="test_series"
            )
            
            assert response is not None
            assert "optimized_params" in response
    
    def test_method_switching_compatibility(self, signals, test_data):
        """Тест совместимости переключения между методами"""
        series_data = SeriesData(signals)
        series_data.data = test_data
        
        methods = ["differential_evolution", "basinhopping", "dual_annealing"]
        
        for method in methods:
            # Обновить метод в настройках
            series_data.update_value(
                ["test_series", "calculation_settings", "method"], 
                method
            )
            
            # Проверить, что метод корректно сохранился
            saved_method = series_data.get_value(
                ["test_series", "calculation_settings", "method"]
            )
            assert saved_method == method

#### 4.4 Тесты производительности и бенчмарки

**Файл:** `tests/test_performance_benchmarks.py` (новый файл)

**Цель:** Измерение и валидация улучшений производительности.

```python
import pytest
import time
import psutil
import numpy as np
from src.core.calculation_scenarios import ModelBasedScenario

class TestPerformanceBenchmarks:
    """Бенчмарки производительности для этапа 2"""
    
    @pytest.fixture
    def benchmark_data(self):
        """Стандартные данные для бенчмарков"""
        return {
            "experimental_data": np.random.random((1000, 4)),
            "reaction_scheme": {
                "components": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
                "reactions": [
                    {"from": "A", "to": "B", "Ea": 120, "log_A": 8},
                    {"from": "B", "to": "C", "Ea": 150, "log_A": 9}
                ]
            }
        }
    
    def test_dual_annealing_performance(self, benchmark_data):
        """Бенчмарк производительности dual_annealing"""
        scenario = ModelBasedScenario()
        
        start_time = time.time()
        cpu_before = psutil.cpu_percent(interval=None)
        
        # Запуск оптимизации
        result = scenario.run_optimization(
            method="dual_annealing",
            data=benchmark_data,
            maxiter=100
        )
        
        end_time = time.time()
        cpu_after = psutil.cpu_percent(interval=1)
        
        execution_time = end_time - start_time
        cpu_utilization = cpu_after - cpu_before
        
        # Валидация производительности
        assert execution_time < 60  # Не более 1 минуты для тестовых данных
        assert cpu_utilization > 50  # Хорошая утилизация CPU
        assert result["success"] == True
    
    def test_methods_comparison(self, benchmark_data):
        """Сравнительный бенчмарк всех методов"""
        scenario = ModelBasedScenario()
        methods = ["differential_evolution", "basinhopping", "dual_annealing"]
        results = {}
        
        for method in methods:
            start_time = time.time()
            
            result = scenario.run_optimization(
                method=method,
                data=benchmark_data,
                maxiter=50  # Уменьшено для быстрого тестирования
            )
            
            execution_time = time.time() - start_time
            results[method] = {
                "time": execution_time,
                "mse": result.get("mse", float('inf')),
                "success": result.get("success", False)
            }
        
        # Валидация: все методы должны работать
        for method, result in results.items():
            assert result["success"], f"Method {method} failed"
            assert result["time"] < 120, f"Method {method} too slow"
    
    def test_cpu_utilization_improvement(self, benchmark_data):
        """Тест улучшения утилизации CPU"""
        scenario = ModelBasedScenario()
        
        # Измерение утилизации для dual_annealing
        cpu_samples = []
        def cpu_monitor():
            for _ in range(10):
                cpu_samples.append(psutil.cpu_percent(interval=0.5))
        
        import threading
        monitor_thread = threading.Thread(target=cpu_monitor)
        monitor_thread.start()
        
        result = scenario.run_optimization(
            method="dual_annealing",
            data=benchmark_data,
            maxiter=100
        )
        
        monitor_thread.join()
        avg_cpu = np.mean(cpu_samples)
        
        # Валидация целевой утилизации 70-85%
        assert 60 <= avg_cpu <= 90, f"CPU utilization {avg_cpu}% outside target range"
        assert result["success"] == True
```

### Задача 5: Архитектурные улучшения и UX

#### 5.1 Улучшение обработки ошибок и пользовательского интерфейса

**Цель:** Обеспечить надежную работу с новыми методами оптимизации и информативную обратную связь пользователю.

**Файл:** `src/core/calculation.py`

**Действие:** Добавить обработку специфичных ошибок dual_annealing:

```python
# В start_dual_annealing() добавить try-catch:
def start_dual_annealing(self, bounds, target_function, **kwargs):
    try:
        from scipy.optimize import dual_annealing
        
        # Валидация параметров перед запуском
        if kwargs.get("initial_temp", 0) <= 0:
            raise ValueError("initial_temp must be positive")
            
        if not (1e-10 <= kwargs.get("restart_temp_ratio", 1e-5) <= 1e-1):
            raise ValueError("restart_temp_ratio must be between 1e-10 and 1e-1")
        
        self.start_calculation_thread(
            dual_annealing,
            target_function,
            bounds=bounds,
            **kwargs,
        )
        
    except ImportError:
        self.calculation_error.emit("dual_annealing не доступен в текущей версии SciPy")
    except ValueError as e:
        self.calculation_error.emit(f"Некорректные параметры dual_annealing: {str(e)}")
    except Exception as e:
        self.calculation_error.emit(f"Ошибка при запуске dual_annealing: {str(e)}")
```

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/model_based.py`

**Действие:** Улучшить валидацию и сообщения об ошибках в CalculationSettingsDialog:

```python
# В collect_calculation_settings() добавить расширенную валидацию:
def collect_calculation_settings(self):
    method = self.calculation_method_combo.currentText()
    settings = {"method": method, "method_parameters": {}}
    
    try:
        if method == "dual_annealing":
            # Валидация dual_annealing параметров
            for param, widget in self.da_params_edits.items():
                if isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                else:
                    text_value = widget.text().strip()
                    if param in ["initial_temp", "restart_temp_ratio", "visit", "accept"]:
                        value = float(text_value)
                    elif param in ["maxiter", "maxfun"]:
                        value = int(text_value)
                    else:
                        value = text_value if text_value != "None" else None
                
                # Валидация каждого параметра
                is_valid, error_msg = self.validate_parameter(param, value)
                if not is_valid:
                    raise ValueError(f"Параметр '{param}': {error_msg}")
                
                settings["method_parameters"][param] = value
                
        # Аналогичная валидация для basinhopping...
        elif method == "basinhopping":
            for param, widget in self.ba_params_edits.items():
                # Валидация basinhopping параметров
                pass
                
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

#### 5.2 Улучшение миграции и обратной совместимости

**Файл:** `src/core/series_data.py`

**Действие:** Добавить автоматическую миграцию старых конфигураций:

```python
# В SeriesData.load_data() добавить миграцию:
def migrate_calculation_settings(self, series_data):
    """Миграция старых настроек расчета к новому формату"""
    for series_name, series_info in series_data.items():
        if "calculation_settings" in series_info:
            settings = series_info["calculation_settings"]
            
            # Миграция старого формата method в новый
            if "method" not in settings and "optimization_method" in settings:
                settings["method"] = settings.pop("optimization_method")
            
            # Установка дефолтных параметров для новых методов
            if settings.get("method") == "dual_annealing":
                if "method_parameters" not in settings:
                    from src.core.app_settings import DUAL_ANNEALING_DEFAULT_KWARGS
                    settings["method_parameters"] = DUAL_ANNEALING_DEFAULT_KWARGS.copy()
            
            # Валидация и исправление некорректных методов
            valid_methods = ["differential_evolution", "basinhopping", "dual_annealing"]
            if settings.get("method") not in valid_methods:
                print(f"Warning: неизвестный метод {settings.get('method')}, "
                      f"заменен на differential_evolution")
                settings["method"] = "differential_evolution"
    
    return series_data
```

#### 5.3 Расширение логирования и диагностики

**Файл:** `src/core/calculation.py`

**Действие:** Добавить детальное логирование для новых методов:

```python
# В run_calculation_scenario() добавить логирование:
def run_calculation_scenario(self, scenario_key, params):
    optimization_method = params.get("calculation_settings", {}).get("method", "differential_evolution")
    method_params = params.get("calculation_settings", {}).get("method_parameters", {})
    
    # Логирование запуска оптимизации
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting optimization with method: {optimization_method}")
    logger.debug(f"Method parameters: {method_params}")
    
    try:
        # Существующая логика...
        
    except Exception as e:
        logger.error(f"Optimization failed with method {optimization_method}: {str(e)}")
        logger.debug(f"Full error details", exc_info=True)
        raise
```

### Задача 6: Документация и пользовательские материалы

#### 6.1 Обновление пользовательской документации

**Файл:** `src/gui/user_guide_tab/guide_content.py`

**Действие:** Добавить раздел о новом методе dual_annealing:

```python
# Добавить в content_structure:
"model_based_analysis": {
    "dual_annealing_method": {
        "ru": {
            "title": "Метод Dual Annealing",
            "content": [
                "Dual Annealing - это современный глобальный метод оптимизации...",
                "Преимущества метода:",
                "• Эффективный поиск глобального минимума",
                "• Хорошая производительность на сложных функциях",
                "• Автоматическая настройка температуры",
                "",
                "Ключевые параметры:",
                "• initial_temp - начальная температура (по умолчанию 5230)",
                "• restart_temp_ratio - коэффициент перезапуска (2e-05)",
                "• visit - параметр посещения (2.62)",
                "• accept - параметр принятия (-5.0)",
            ]
        },
        "en": {
            "title": "Dual Annealing Method",
            "content": [
                "Dual Annealing is a modern global optimization method...",
                # English translation
            ]
        }
    }
}
```

#### 6.2 Создание технической документации

**Файл:** `docs/develop_plan/optimization_stage2_api_documentation.md` (новый файл)

**Содержание:**
- API документация для новых методов
- Примеры использования dual_annealing
- Рекомендации по выбору параметров
- Сравнительная таблица методов оптимизации

#### 6.3 Обновление README.md

**Действие:** Добавить информацию о новых возможностях:

```markdown
## Методы оптимизации

Приложение поддерживает три метода глобальной оптимизации:

1. **Differential Evolution** - надежный эволюционный алгоритм
2. **Basin Hopping** - метод с локальным поиском
3. **Dual Annealing** (новый) - современный метод симулированного отжига

### Рекомендации по выбору метода:

- **Differential Evolution**: универсальный выбор для большинства задач
- **Basin Hopping**: для задач с множественными локальными минимумами
- **Dual Annealing**: для сложных многомерных задач, требующих точного решения
```

## Технические требования

### Требования к производительности
- **Утилизация CPU:** 70-85% при использовании всех доступных ядер
- **Ускорение:** В 4-8 раз по сравнению с первоначальной реализацией
- **Память:** Не более 2 GB дополнительного использования памяти
- **Отзывчивость UI:** GUI должен оставаться отзывчивым во время оптимизации

### Требования к совместимости
- **Python версии:** 3.8+
- **Зависимости:** Все новые зависимости должны быть добавлены в pyproject.toml
- **ОС:** Windows, Linux, macOS
- **Обратная совместимость:** Существующие конфигурации должны продолжать работать

### Требования к качеству кода
- **Покрытие тестами:** Минимум 85% для новых модулей
- **Документация:** Полное покрытие docstrings в стиле Google
- **Типизация:** Использование type hints для всех публичных API
- **Линтинг:** Соответствие правилам black, isort, flake8

### Требования к архитектурной совместимости
- **Сигнально-слотовая архитектура:** Все новые компоненты должны использовать BaseSignals/BaseSlots
- **Path-keys система:** Доступ к данным через иерархическую адресацию
- **Модульность:** Новые компоненты должны быть изолированы и расширяемы
- **Событийно-управляемая коммуникация:** Qt сигналы для неблокирующих операций

## Структура файлов

### Новые файлы
```
tests/
  test_optimization_stage2.py         # Модульные тесты
  test_model_based_integration_stage2.py  # Интеграционные тесты
  test_performance_benchmarks.py      # Бенчмарки производительности

docs/
  develop_plan/
    optimization_stage2_results.md    # Отчет о результатах
```

### Модифицируемые файлы
```
src/
  core/
    app_settings.py                   # Новые константы и конфигурации
    calculation_scenarios.py          # Интеграция новых возможностей  gui/
    main_tab/sub_sidebar/model_based/
      model_based_panel.py           # Поддержка dual_annealing
      calculation_controls.py        # Поддержка нового метода
      calculation_settings_dialogs.py # Новый диалог dual_annealing
```

## План выполнения

### Этап 2.1: Подготовка инфраструктуры (1 час)
1. Обновление `app_settings.py` с новыми константами
2. Настройка базовой структуры тестов

### Этап 2.2: Реализация основного функционала (1-2 часа)
1. Интеграция dual_annealing в ModelBasedScenario

### Этап 2.3: Интеграция с UI (1 час)
1. Обновление ModelBasedPanel
2. Создание DualAnnealingSettingsDialog
3. Обновление CalculationControls

### Этап 2.4: Тестирование и отладка (1 час)
1. Написание и запуск модульных тестов
2. Интеграционное тестирование
3. Бенчмарки производительности
4. Исправление найденных проблем

### Этап 2.5: Документация и финализация (30 минут)
1. Обновление документации API
2. Создание отчета о результатах
3. Подготовка к следующему этапу

## Критерии успеха

### Функциональные критерии
- ✅ dual_annealing успешно интегрирован и работает
- ✅ GUI поддерживает новый метод оптимизации
- ✅ Все тесты проходят успешно

### Критерии производительности
- ✅ Утилизация CPU 70-85% (по сравнению с 20-30% до оптимизации)
- ✅ Ускорение в 4-8 раз по времени выполнения

### Критерии качества
- ✅ Покрытие тестами >= 85%
- ✅ Все новые модули имеют полную документацию
- ✅ Код соответствует стандартам проекта
- ✅ Обратная совместимость сохранена

## Поставляемые результаты (Deliverables)

### Готовые к производству компоненты
1. **Обновленные core модули:**
   - `src/core/app_settings.py` - с константами для всех трех методов оптимизации
   - `src/core/calculation.py` - с полной поддержкой dual_annealing и исправленным basinhopping
   - `src/core/calculation_scenarios.py` - с корректной интеграцией новых методов

2. **Расширенные GUI компоненты:**
   - `src/gui/main_tab/sub_sidebar/model_based/model_based.py` - обновленный CalculationSettingsDialog
   - Полная поддержка трех методов оптимизации в пользовательском интерфейсе
   - Валидация параметров и tooltips для всех методов

3. **Комплексная система тестирования:**
   - `tests/test_optimization_stage2.py` - модульные тесты для новых компонентов
   - `tests/test_gui_integration_stage2.py` - интеграционные тесты GUI
   - `tests/test_model_based_integration_stage2.py` - полные workflow тесты
   - `tests/test_performance_benchmarks.py` - бенчмарки производительности

### Документация
4. **Обновленная техническая документация:**
   - `docs/develop_plan/optimization_stage2_api_documentation.md` - API документация
   - Обновленный раздел в `src/gui/user_guide_tab/guide_content.py`
   - Обновленный `README.md` с информацией о новых методах

5. **Отчет о результатах:**
   - `docs/develop_plan/optimization_stage2_results.md` - детальный отчет о достигнутых результатах
   - Бенчмарки производительности и сравнительный анализ

## Критерии приемки (Acceptance Criteria)

### Критерии функциональности
- ✅ **DA-001**: dual_annealing интегрирован и доступен через GUI
- ✅ **DA-002**: Все три метода (DE, BH, DA) работают корректно через единый интерфейс
- ✅ **DA-003**: Параметры методов валидируются и имеют tooltips
- ✅ **DA-004**: Обратная совместимость с существующими конфигурациями сохранена
- ✅ **DA-005**: Миграция старых настроек работает автоматически

### Критерии производительности
- ✅ **PERF-001**: Утилизация CPU составляет 70-85% во время оптимизации
- ✅ **PERF-002**: Время выполнения сокращено в 4-8 раз по сравнению с базовой реализацией
- ✅ **PERF-003**: GUI остается отзывчивым во время фоновых вычислений
- ✅ **PERF-004**: Потребление памяти не превышает +2GB от базового уровня

### Критерии качества
- ✅ **QUAL-001**: Покрытие тестами новых модулей >= 85%
- ✅ **QUAL-002**: Все модульные тесты проходят успешно
- ✅ **QUAL-003**: Интеграционные тесты демонстрируют работоспособность full workflow
- ✅ **QUAL-004**: Бенчмарки подтверждают заявленные улучшения производительности
- ✅ **QUAL-005**: Код соответствует стандартам проекта (black, isort, flake8)

### Критерии пользовательского опыта
- ✅ **UX-001**: Переключение между методами оптимизации интуитивно понятно
- ✅ **UX-002**: Валидация параметров предоставляет информативные сообщения об ошибках
- ✅ **UX-003**: Tooltips содержат полезную информацию о параметрах
- ✅ **UX-004**: Диалоги настроек адаптируются под выбранный метод
- ✅ **UX-005**: Процесс оптимизации предоставляет обратную связь о прогрессе

### Критерии архитектурной совместимости
- ✅ **ARCH-001**: Новые компоненты следуют паттернам BaseSignals/BaseSlots
- ✅ **ARCH-002**: Path-keys система используется для доступа к данным
- ✅ **ARCH-003**: Модульная структура сохранена и расширена
- ✅ **ARCH-004**: Сигнально-слотовая коммуникация используется корректно
- ✅ **ARCH-005**: Новые методы интегрированы в существующую архитектуру без breaking changes

## Тестирование и валидация

### План тестирования
1. **Модульное тестирование (Unit Testing):**
   - Тестирование новых методов оптимизации изолированно
   - Валидация параметров и их обработки
   - Проверка корректности интеграции с существующими компонентами

2. **Интеграционное тестирование (Integration Testing):**
   - Полный цикл: GUI → Core → Calculations → Results
   - Переключение между методами оптимизации
   - Совместимость с существующими данными и конфигурациями

3. **Тестирование производительности (Performance Testing):**
   - Бенчмарки времени выполнения для каждого метода
   - Измерение утилизации CPU и памяти
   - Сравнительный анализ до и после оптимизации

4. **Пользовательское тестирование (User Testing):**
   - Тестирование UI/UX на различных сценариях
   - Валидация обработки ошибок и edge cases
   - Проверка интуитивности интерфейса

### Критерии завершения
Этап 2 считается завершенным при выполнении всех критериев приемки и успешном прохождении полного набора тестов. Все deliverables должны быть готовы к production deployment.

## Риски и их митигация

### Риск 1: Производительность dual_annealing ниже ожидаемой
**Митигация:** Тщательная настройка параметров и сравнительное тестирование с DE и basinhopping

### Риск 2: Проблемы интеграции с существующим UI
**Митигация:** Тщательное планирование изменений, поэтапная интеграция, тестирование на каждом шаге

## Заключение

Этап 2 представляет собой сбалансированное расширение функциональности, которое обеспечивает существенное ускорение производительности при умеренной сложности реализации. 

### Ключевые достижения этапа 2:

1. **Расширение методов оптимизации:**
   - Интеграция современного алгоритма dual_annealing
   - Исправление архитектурных проблем с basinhopping
   - Создание единой системы поддержки трех методов оптимизации

2. **Улучшение пользовательского интерфейса:**
   - Единый CalculationSettingsDialog для всех методов
   - Полная валидация параметров с информативными сообщениями
   - Контекстные tooltips для всех параметров оптимизации

3. **Архитектурные улучшения:**
   - Централизованная система констант OPTIMIZATION_METHODS
   - Улучшенная обработка ошибок и логирование
   - Автоматическая миграция старых конфигураций

4. **Повышение производительности:**
   - Целевая утилизация CPU 70-85%
   - Ускорение в 4-8 раз по сравнению с базовой реализацией
   - Сохранение отзывчивости GUI

### Архитектурная ценность:

Реализация этапа 2 полностью соответствует архитектурным принципам проекта:
- **Слабое связывание** через BaseSignals/BaseSlots
- **Модульность** с изолированными компонентами
- **Расширяемость** через единообразные паттерны интеграции
- **Path-keys система** для консистентного доступа к данным

### Подготовка к следующим этапам:

После успешной реализации этапа 2 система будет готова к более глубоким оптимизациям:

**Этап 3: Advanced Optimizations**
- Параллелизация целевой функции на уровне реакций
- Numba JIT компиляция для ускорения вычислений
- Кэширование промежуточных результатов

**Этап 4: Memory & I/O Optimizations**
- Оптимизация работы с большими наборами данных
- Эффективное кэширование результатов оптимизации
- Асинхронная обработка файловых операций

Текущий этап обеспечивает фундамент для дальнейших оптимизаций, сохраняя при этом стабильность и удобство использования системы.
