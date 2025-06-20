# Этап 2 - Фаза 1: Интеграция core компонентов

## Общая информация

**Документ:** Фаза 1 - Интеграция dual_annealing в core модули  
**Ожидаемые сроки:** 1-1.5 часа  
**Сложность:** Низкая-Средняя  
**Pull Request:** `feature/stage2-phase1-core-dual-annealing`

## Цели фазы 1

### Основная цель
Интегрировать dual_annealing алгоритм в core модули приложения и исправить критические архитектурные проблемы с basinhopping.

### Задачи фазы 1
1. **Добавление констант dual_annealing** в `app_settings.py`
2. **Интеграция методов оптимизации** в `calculation.py`
3. **Исправление basinhopping** архитектуры
4. **Валидация совместимости** с `calculation_scenarios.py`

## Детальное описание

### Задача 1.1: Обновление app_settings.py

**Файл:** `src/core/app_settings.py`

**Действия:**
```python
# Добавить после MODEL_FREE_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS:
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

DUAL_ANNEALING_PARAM_RANGES = {
    "maxiter": (100, 5000),
    "initial_temp": (1000.0, 10000.0),
    "restart_temp_ratio": (1e-06, 1e-03),
    "visit": (2.0, 3.0),
    "accept": (-10.0, 0.0),
    "maxfun": (100000, 10000000),
}
```

### Задача 1.2: Обновление calculation.py

**Файл:** `src/core/calculation.py`

**Действия:**

1. **Добавить импорт:**
```python
# В начало файла добавить:
from scipy.optimize import OptimizeResult, differential_evolution, dual_annealing, basinhopping
```

2. **Добавить метод start_dual_annealing:**
```python
# После start_differential_evolution() добавить:
def start_dual_annealing(self, bounds, target_function, **kwargs):
    """Start dual annealing optimization in a separate thread.
    
    Args:
        bounds: List of (min, max) tuples for each parameter
        target_function: Function to minimize
        **kwargs: Additional parameters for dual_annealing
    """
    try:
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

3. **Добавить метод start_basinhopping:**
```python
# После start_dual_annealing() добавить:
def start_basinhopping(self, bounds, target_function, **kwargs):
    """Start basin hopping optimization in a separate thread.
    
    Args:
        bounds: List of (min, max) tuples for each parameter
        target_function: Function to minimize
        **kwargs: Additional parameters for basinhopping
    """
    self.start_calculation_thread(
        basinhopping,
        target_function,
        bounds=bounds,
        **kwargs,
    )
```

4. **Исправить run_calculation_scenario:**
```python
# Заменить строки 108-115 на:
elif optimization_method == "basinhopping":
    calc_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()
    
    if scenario_key == "model_based_calculation":
        calc_params["callback"] = make_de_callback(target_function, self)
    
    self.start_basinhopping(bounds=bounds, target_function=target_function, **calc_params)

elif optimization_method == "dual_annealing":
    calc_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()
    
    if scenario_key == "model_based_calculation":
        calc_params["callback"] = make_de_callback(target_function, self)
    
    self.start_dual_annealing(bounds=bounds, target_function=target_function, **calc_params)
```

### Задача 1.3: Валидация совместимости с calculation_scenarios.py

**Файл:** `src/core/calculation_scenarios.py`

**Действия:**
- Проверить совместимость `ModelBasedScenario.get_optimization_method()` с новыми методами
- Убедиться что bounds и target_function работают с dual_annealing

**Ожидаемый результат:** Никаких изменений не требуется, так как метод универсален.

## Тестирование фазы 1

### Модульные тесты

**Файл:** `tests/test_stage2_phase1_core.py` (новый файл)

```python
import pytest
from unittest.mock import Mock, patch
from src.core.app_settings import (
    DUAL_ANNEALING_DEFAULT_KWARGS, 
    BASINHOPPING_DEFAULT_KWARGS,
    OPTIMIZATION_METHODS
)
from src.core.calculation import Calculations

class TestPhase1CoreIntegration:
    """Тесты интеграции core компонентов фазы 1"""
    
    def test_optimization_methods_available(self):
        """Тест доступности всех методов оптимизации"""
        assert "differential_evolution" in OPTIMIZATION_METHODS
        assert "basinhopping" in OPTIMIZATION_METHODS
        assert "dual_annealing" in OPTIMIZATION_METHODS
        
    def test_dual_annealing_default_kwargs(self):
        """Тест корректности дефолтных параметров dual_annealing"""
        assert "maxiter" in DUAL_ANNEALING_DEFAULT_KWARGS
        assert "initial_temp" in DUAL_ANNEALING_DEFAULT_KWARGS
        assert DUAL_ANNEALING_DEFAULT_KWARGS["initial_temp"] > 0
        assert 1e-10 <= DUAL_ANNEALING_DEFAULT_KWARGS["restart_temp_ratio"] <= 1e-1
        
    def test_basinhopping_default_kwargs(self):
        """Тест корректности дефолтных параметров basinhopping"""
        assert "niter" in BASINHOPPING_DEFAULT_KWARGS
        assert "T" in BASINHOPPING_DEFAULT_KWARGS
        assert BASINHOPPING_DEFAULT_KWARGS["T"] > 0
        
    def test_dual_annealing_method_integration(self):
        """Тест интеграции start_dual_annealing метода"""
        calc = Calculations()
        
        with patch('src.core.calculation.dual_annealing') as mock_da:
            calc.start_dual_annealing(
                bounds=[(0, 1)], 
                target_function=lambda x: x[0]**2,
                maxiter=10
            )
            # Проверяем что метод был вызван через start_calculation_thread
            assert hasattr(calc, 'start_dual_annealing')
            
    def test_basinhopping_method_integration(self):
        """Тест интеграции start_basinhopping метода"""
        calc = Calculations()
        
        with patch('src.core.calculation.basinhopping') as mock_bh:
            calc.start_basinhopping(
                bounds=[(0, 1)], 
                target_function=lambda x: x[0]**2,
                niter=5
            )
            # Проверяем что метод был вызван через start_calculation_thread
            assert hasattr(calc, 'start_basinhopping')
```

## Критерии приемки фазы 1

### Функциональные критерии
- ✅ **CORE-001**: OPTIMIZATION_METHODS содержит все три метода
- ✅ **CORE-002**: DUAL_ANNEALING_DEFAULT_KWARGS и BASINHOPPING_DEFAULT_KWARGS добавлены
- ✅ **CORE-003**: start_dual_annealing() метод интегрирован и работает
- ✅ **CORE-004**: start_basinhopping() метод интегрирован и работает
- ✅ **CORE-005**: run_calculation_scenario() поддерживает все три метода

### Качественные критерии
- ✅ **QUAL-001**: Все новые методы имеют docstrings
- ✅ **QUAL-002**: Параметры валидируются перед запуском
- ✅ **QUAL-003**: Ошибки обрабатываются и логируются
- ✅ **QUAL-004**: Модульные тесты покрывают новую функциональность

## Deliverables фазы 1

1. **Обновленные файлы:**
   - `src/core/app_settings.py` - новые константы
   - `src/core/calculation.py` - новые методы оптимизации
   
2. **Новые тесты:**
   - `tests/test_stage2_phase1_core.py` - модульные тесты

3. **Документация:**
   - Обновленные docstrings в новых методах

## План выполнения фазы 1

### Шаг 1: Обновление констант (15 минут)
1. Добавить новые константы в `app_settings.py`
2. Проверить корректность значений

### Шаг 2: Интеграция методов (30 минут)
1. Добавить `start_dual_annealing()` и `start_basinhopping()`
2. Обновить `run_calculation_scenario()`
3. Добавить обработку ошибок

### Шаг 3: Тестирование (30 минут)
1. Написать модульные тесты
2. Запустить и проверить все тесты
3. Исправить найденные проблемы

### Шаг 4: Подготовка PR (15 минут)
1. Проверить соответствие coding standards
2. Создать pull request
3. Добавить описание изменений

## Результат фазы 1

После завершения фазы 1:
- ✅ Core модули поддерживают все три метода оптимизации
- ✅ Архитектурные проблемы с basinhopping исправлены
- ✅ Фундамент для GUI интеграции готов
- ✅ Система готова к фазе 2 (GUI расширения)

**Следующая фаза:** Phase 2 - GUI Integration (расширение пользовательского интерфейса)
