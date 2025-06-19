# Этап 1: Реализация BatchTakeStep ядра

## Описание этапа

Первый этап фокусируется на создании базового функционала **BatchTakeStep** класса - ключевого компонента для реализации мультипроцессного распараллеливания в basinhopping. Этот этап закладывает фундамент для всей системы и может быть разработан и протестирован независимо от UI и интеграции с ModelBased системой.

## Цели этапа

- **Создать BatchTakeStep класс** с поддержкой concurrent.futures для мультипроцессного распараллеливания
- **Реализовать генерацию batch предложений** координат с настраиваемым stepsize
- **Внедрить параллельную оценку** предложений через ProcessPoolExecutor
- **Обеспечить корректное управление ресурсами** с автоматической очисткой пулов процессов
- **Создать comprehensive тесты** для всех компонентов BatchTakeStep

## Архитектура решения

### BatchTakeStep класс

**Файл**: `src/core/batch_take_step.py`

```python
import numpy as np
import concurrent.futures
from typing import Callable, Optional
import os
import logging
from threading import Event

class BatchTakeStep:
    """
    Batch-Stepper реализация для basinhopping с мультипроцессным распараллеливанием
    
    Генерирует batch_size случайных предложений координат и оценивает их параллельно,
    возвращая лучшее предложение в basinhopping алгоритм.
    """
    
    def __init__(
        self, 
        batch_size: int, 
        target_func: Callable, 
        stepsize: float = 0.5, 
        max_workers: Optional[int] = None,
        stop_event: Optional[Event] = None
    ):
        """
        Инициализация BatchTakeStep
        
        Args:
            batch_size: Количество параллельных предложений координат
            target_func: Целевая функция для оптимизации (ModelBasedTargetFunction)
            stepsize: Размер шага для генерации предложений (0.01-2.0)
            max_workers: Максимальное количество процессов (по умолчанию min(batch_size, cpu_count))
            stop_event: Event для прерывания вычислений
        """
        
    def __call__(self, x_current: np.ndarray) -> np.ndarray:
        """
        Главный метод, вызываемый basinhopping для генерации нового предложения
        
        Args:
            x_current: Текущие координаты в пространстве параметров
            
        Returns:
            Лучшие координаты из batch предложений
        """
        
    def _generate_batch_proposals(self, x_current: np.ndarray) -> list[np.ndarray]:
        """Генерация batch_size случайных предложений координат"""
        
    def _evaluate_concurrent_futures(self, proposals: list[np.ndarray]) -> list[float]:
        """Параллельная оценка через concurrent.futures"""
        
    def shutdown(self):
        """Освобождение ресурсов executor"""
        
    def __del__(self):
        """Автоматическое освобождение ресурсов"""
```

### Параметры конфигурации

**Файл**: `src/core/app_settings.py` (расширение)

```python
# BatchTakeStep configuration
DEFAULT_BATCH_SIZE = 4
MIN_BATCH_SIZE = 2
MAX_BATCH_SIZE = 16
DEFAULT_STEPSIZE = 0.5
MIN_STEPSIZE = 0.01
MAX_STEPSIZE = 2.0

# Basinhopping optimization parameters (полная конфигурация)
DEFAULT_BASINHOPPING_PARAMS = {
    'optimization_method': 'differential_evolution',  # Backward compatibility
    'T': 1.0,                                        # Температура Метрополиса
    'niter': 100,                                    # Количество итераций
    'stepsize': 0.5,                                 # Размер шага BatchTakeStep
    'batch_size': 4,                                 # Размер batch (будет адаптирован к CPU)
    'minimizer_method': 'L-BFGS-B'                   # Локальный оптимизатор
}

# Validation ranges для UI (будет использоваться в Этапе 3)
BASINHOPPING_PARAM_RANGES = {
    'T': (0.1, 10.0),
    'niter': (10, 1000),
    'stepsize': (0.01, 2.0),
    'batch_size': (2, 16),
}

# Supported local minimizers for basinhopping
BASINHOPPING_MINIMIZERS = [
    'L-BFGS-B',    # Bounded optimization (recommended)
    'SLSQP',       # Sequential Least Squares Programming
    'TNC',         # Truncated Newton
    'trust-constr' # Trust region with constraints
]
```

## Технические требования

### Генерация batch предложений

- **Алгоритм**: Случайные возмущения в пределах `stepsize`, аналогично стандартному basinhopping
- **Формула**: `x_new = x_current + uniform(-stepsize, stepsize, x_current.shape)`
- **Валидация**: Проверка границ параметров, если они предоставлены
- **Reproducibility**: Использование `numpy.random.default_rng()` с опциональным seed

### Параллельная оценка

**concurrent.futures**:
- ✅ **Стандартная библиотека Python** - не требует дополнительных зависимостей
- ✅ **Совместимость с Windows** - отлично работает с spawn multiprocessing
- ✅ **Интеграция с существующей архитектурой** - использует те же принципы multiprocessing.Manager для разделяемых объектов
- ✅ **Гибкое управление ресурсами** - точный контроль над жизненным циклом пула процессов
- ✅ **Exception handling** - прозрачная передача исключений из worker процессов
- ⚠️ **Сериализация overhead** - требует передачи данных через pickle

**concurrent.futures реализация**:
- **ProcessPoolExecutor** с настраиваемым `max_workers`
- **Exception handling**: Корректная обработка ошибок в worker процессах
- **Timeout поддержка**: Опциональный timeout для долгих вычислений
- **Resource cleanup**: Автоматическое закрытие пула при завершении

### Управление ресурсами

- **Context manager поддержка**: Использование `with` statements для automatic cleanup
- **Stop event интеграция**: Прерывание вычислений через threading.Event
- **Memory efficiency**: Minimal overhead при передаче данных между процессами
- **Error recovery**: Graceful handling исключений в worker процессах

## Критерии приемки

### Функциональные тесты

1. **Базовая функциональность**:
   - ✅ Генерация корректного количества batch предложений
   - ✅ Параллельная оценка всех предложений
   - ✅ Возврат лучшего (минимального) результата
   - ✅ Работа с различными размерностями координат

2. **Конфигурация**:
   - ✅ Корректная обработка различных batch_size (2-16)
   - ✅ Адаптация stepsize для генерации предложений
   - ✅ Автоматическое определение max_workers

3. **Управление ресурсами**:
   - ✅ Автоматическое закрытие пулов процессов
   - ✅ Корректная обработка исключений
   - ✅ Прерывание через stop_event
   - ✅ Memory cleanup после завершения

### Производительные тесты

1. **Масштабируемость**:
   - ✅ Ускорение при увеличении batch_size до количества CPU
   - ✅ Минимальный overhead по сравнению с последовательной оценкой
   - ✅ Эффективное использование доступных ядер CPU

2. **Стабильность**:
   - ✅ Отсутствие утечек памяти при длительных вычислениях
   - ✅ Корректное завершение всех процессов
   - ✅ Воспроизводимость результатов с одинаковыми параметрами

## Тестовые сценарии

### Модульные тесты

**Файл**: `tests/test_batch_take_step.py`

```python
import pytest
import numpy as np
from threading import Event
from src.core.batch_take_step import BatchTakeStep

class TestBatchTakeStep:
    """Тестирование BatchTakeStep класса"""
    
    def test_basic_functionality(self):
        """Тест базовой функциональности"""
        
    def test_batch_size_validation(self):
        """Тест валидации batch_size"""
        
    def test_stepsize_effect(self):
        """Тест влияния stepsize на генерацию предложений"""
        
    def test_concurrent_futures_executor(self):
        """Тест работы concurrent.futures executor"""
        
    def test_stop_event_interruption(self):
        """Тест прерывания через stop_event"""
        
    def test_resource_cleanup(self):
        """Тест корректной очистки ресурсов"""
        
    def test_error_handling(self):
        """Тест обработки ошибок в worker процессах"""
```

### Интеграционные тесты

**Файл**: `tests/test_batch_integration.py`

```python
def test_scipy_basinhopping_integration():
    """Тест интеграции с scipy.optimize.basinhopping"""
    
def test_performance_comparison():
    """Сравнение производительности с стандартным basinhopping"""
    
def test_multiprocessing_compatibility():
    """Тест совместимости с multiprocessing на Windows/Linux"""
```

## Результаты этапа

### Deliverables

1. **BatchTakeStep класс** (`src/core/batch_take_step.py`) - полная реализация
2. **Константы конфигурации** (расширение `src/core/app_settings.py`)
3. **Модульные тесты** (`tests/test_batch_take_step.py`) - 95%+ покрытие
4. **Интеграционные тесты** (`tests/test_batch_integration.py`) 
5. **Документация** (docstrings + примеры использования)

### Метрики качества

- **Test Coverage**: ≥95% для BatchTakeStep класса
- **Performance**: Ускорение ≥2x при batch_size=4 на 4+ ядрах
- **Memory**: Отсутствие утечек памяти в длительных тестах
- **Compatibility**: Работа на Windows 10/11 и Ubuntu 20.04/22.04

## Dependencies

**Этап 1 не зависит от других этапов** и может быть реализован параллельно с разработкой UI компонентов.

### Внешние зависимости

- **Python ≥3.8**: concurrent.futures, threading
- **NumPy**: Для работы с массивами координат
- **SciPy**: Для интеграционного тестирования с basinhopping
- **Pytest**: Для модульного и интеграционного тестирования

## Pull Request критерии

### Обязательные проверки

1. ✅ **Все тесты проходят** (модульные + интеграционные)
2. ✅ **Code coverage ≥95%** для новых компонентов  
3. ✅ **Линтеры чистые** (flake8, mypy, black)
4. ✅ **Документация complete** (docstrings + README update)
5. ✅ **Performance benchmarks** (ускорение vs sequential)

### Дополнительные проверки

- ✅ **Cross-platform тестирование** (Windows + Linux CI)
- ✅ **Memory профилирование** (отсутствие leaks)
- ✅ **Exception handling** (graceful error recovery)
- ✅ **Resource cleanup** (все процессы завершены)

## Следующий этап

После завершения **Этапа 1**, BatchTakeStep будет готов к интеграции с ModelBasedScenario в **Этапе 2: Backend интеграция basinhopping**.
