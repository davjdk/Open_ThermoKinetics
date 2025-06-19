# Этап 3: Интеграция с классом Calculations

## Описание этапа

Интеграция созданного прокси-менеджера с существующим классом `Calculations`. На этом этапе модифицируется логика запуска и остановки `model_based_calculation` для использования отдельного процесса вместо QThread.

## Задачи этапа

### 1. Модификация класса Calculations

**Файл:** `src/core/calculation.py`

Добавить поддержку прокси-менеджера:

```python
from .model_calc_proxy import ModelCalcProxy

class Calculations(BaseSlots):
    def __init__(self):
        # ...existing code...
        self.model_calc_proxy = ModelCalcProxy(self)
        
    def run_calculation_scenario(self, params: dict):
        """Модифицированный метод для поддержки subprocess."""
        scenario_key = params.get("scenario_key")
        
        if scenario_key == "model_based_calculation":
            # Новый путь через процесс-работник
            self._run_model_based_subprocess(params)
        else:
            # Существующий путь через QThread
            self._run_thread_calculation(params)
            
    def _run_model_based_subprocess(self, params: dict):
        """
        Запуск model-based расчета в отдельном процессе.
        
        Args:
            params: Параметры расчета с настройками сценария
        """
        # Получение сценария и подготовка данных
        scenario_instance = self._get_scenario_instance(params)
        
        # Подготовка параметров для процесса
        bounds = scenario_instance.get_bounds()
        constraints = scenario_instance.get_constraints()
        target_function = scenario_instance.get_target_function(calculations_instance=self)
        
        # Формирование параметров алгоритма
        method_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()
        if constraints:
            method_params["constraints"] = constraints
            
        # Установка стратегии результатов
        strategy_type = scenario_instance.get_result_strategy_type()
        self.set_result_strategy(strategy_type)
        
        # Запуск через прокси
        self.model_calc_proxy.start_process(target_function, bounds, method_params)
        
    def _run_thread_calculation(self, params: dict):
        """Существующая логика для других типов расчетов."""
        # ...existing thread-based logic...
        
    def stop_calculation(self):
        """Модифицированный метод остановки расчетов."""
        # Проверка активного subprocess
        if (self.model_calc_proxy.process and 
            self.model_calc_proxy.process.is_alive()):
            logger.info("Stopping current calculation (subprocess).")
            self.model_calc_proxy.stop_process()
            self.calculation_active = False
            self.result_strategy = None
            console.log("\\nCalculation process has been requested to stop.")
            return True
            
        # Существующая логика для QThread
        if self.thread and self.thread.isRunning():
            self.stop_event.set()
            self.calculation_active = False
            self.result_strategy = None
            self.thread.requestInterruption()
            console.log("Calculation thread has been requested to stop...")
            return True
            
        logger.info("No active calculation to stop.")
        console.log("No active calculation to stop.")
        return False
```

### 2. Обработка различий в инициализации

Адаптировать создание целевой функции для subprocess:

```python
def _prepare_target_function_for_subprocess(self, scenario_instance):
    """
    Подготовка целевой функции для использования в subprocess.
    
    Обеспечивает сериализуемость и совместимость с multiprocessing.
    """
    target_function = scenario_instance.get_target_function(calculations_instance=self)
    
    # Проверка сериализуемости
    try:
        import pickle
        pickle.dumps(target_function)
    except Exception as e:
        logger.error(f"Target function is not serializable: {e}")
        raise ValueError("Target function cannot be used in subprocess")
        
    return target_function
```

### 3. Адаптация системы ограничений

Обеспечить передачу ограничений в subprocess:

```python
def _prepare_constraints_for_subprocess(self, scenario_instance):
    """
    Подготовка ограничений для subprocess.
    
    Если ограничения не сериализуются, передаем данные для их воссоздания.
    """
    constraints = scenario_instance.get_constraints()
    
    if not constraints:
        return None
        
    try:
        import pickle
        pickle.dumps(constraints)
        return constraints
    except:
        # Ограничения не сериализуются, передаем данные схемы
        reaction_scheme = scenario_instance.get_reaction_scheme_data()
        return {"recreate_from_scheme": reaction_scheme}
```

### 4. Обеспечение обратной совместимости

Сохранить полную совместимость с существующим API:

```python
def start_differential_evolution(self, **kwargs):
    """
    Обратно совместимый метод запуска дифференциальной эволюции.
    
    Автоматически определяет, использовать subprocess или thread.
    """
    if "scenario_key" in kwargs and kwargs["scenario_key"] == "model_based_calculation":
        # Новый путь
        params = {"scenario_key": "model_based_calculation", **kwargs}
        self._run_model_based_subprocess(params)
    else:
        # Существующий путь
        self._start_differential_evolution_thread(**kwargs)
```

### 5. Тестирование интеграции

**Файл:** `tests/test_calculations_integration.py`

```python
import unittest
from unittest.mock import Mock, patch
from src.core.calculation import Calculations

class TestCalculationsIntegration(unittest.TestCase):
    
    def setUp(self):
        self.calculations = Calculations()
        
    def test_model_based_subprocess_path(self):
        """Тест выбора subprocess для model_based_calculation."""
        pass
        
    def test_other_scenarios_thread_path(self):
        """Тест сохранения thread для других сценариев."""
        pass
        
    def test_stop_calculation_subprocess(self):
        """Тест остановки subprocess расчета."""
        pass
        
    def test_stop_calculation_thread(self):
        """Тест остановки thread расчета (обратная совместимость)."""
        pass
        
    def test_backward_compatibility(self):
        """Тест обратной совместимости API."""
        pass
        
    def test_signal_propagation(self):
        """Тест корректности передачи сигналов."""
        pass
```

### 6. Интеграционные тесты с GUI

**Файл:** `tests/test_gui_integration.py`

```python
import unittest
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

class TestGUIIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])
        
    def setUp(self):
        self.main_window = MainWindow()
        
    def test_model_based_calculation_launch(self):
        """Тест запуска model-based расчета через GUI."""
        pass
        
    def test_progress_updates(self):
        """Тест обновления прогресса в GUI."""
        pass
        
    def test_stop_button_functionality(self):
        """Тест кнопки остановки."""
        pass
        
    def test_ui_responsiveness(self):
        """Тест отзывчивости UI во время расчета."""
        pass
```

## Критерии приемки

1. ✅ Класс `Calculations` успешно интегрирован с `ModelCalcProxy`
2. ✅ Model-based расчеты выполняются в subprocess
3. ✅ Другие типы расчетов продолжают работать через QThread
4. ✅ Сохранена полная обратная совместимость API
5. ✅ Сигналы Qt работают корректно в обоих режимах
6. ✅ Остановка расчетов работает для обоих путей
7. ✅ GUI остается отзывчивым во время subprocess расчетов
8. ✅ Написаны интеграционные тесты
9. ✅ Нет регрессий в существующей функциональности

## Результат этапа

- Полная интеграция subprocess в класс Calculations
- Сохранение обратной совместимости
- Отзывчивый GUI во время тяжелых вычислений
- Comprehensive тест-покрытие интеграции
- Готовность к production использованию

## Pull Request

**Название:** `feat: integrate subprocess model-based calculations`

**Описание:**
```
Интеграция subprocess для model-based расчетов в класс Calculations:

- Модифицирован Calculations для поддержки двух путей: subprocess и thread
- Model-based расчеты теперь выполняются в отдельном процессе
- Сохранена полная обратная совместимость API
- Другие типы расчетов продолжают использовать QThread
- Обновлена логика остановки для обоих путей
- Написаны интеграционные тесты с GUI
- Подтверждена отзывчивость UI во время тяжелых вычислений

Теперь SciPy может использовать workers > 1 без блокировки GUI.
```

**Связанные файлы:**
- `src/core/calculation.py` (изменен)
- `tests/test_calculations_integration.py` (новый)
- `tests/test_gui_integration.py` (новый)
- `docs/dev_plan/stage_03_calculations_integration.md` (новый)
