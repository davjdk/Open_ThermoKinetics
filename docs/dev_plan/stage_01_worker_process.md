# Этап 1: Создание процесса-работника для MODEL_BASED_CALCULATION

## Описание этапа

Создание базовой инфраструктуры для выполнения `model_based_calculation` в отдельном процессе. На этом этапе реализуется процесс-работник и основная логика взаимодействия через межпроцессную очередь.

## Задачи этапа

### 1. Создание модуля процесса-работника

**Файл:** `src/core/model_calc_worker.py`

Реализовать функцию-работник, которая:
- Принимает целевую функцию, границы параметров и настройки алгоритма
- Выполняет оптимизацию через `scipy.optimize.differential_evolution`
- Отправляет промежуточные результаты через очередь
- Обрабатывает сигналы остановки через `stop_event`

```python
from scipy.optimize import differential_evolution
import multiprocessing

def run_model_calc(target_func, bounds, method_params, stop_event, result_queue):
    """
    Функция-работник для выполнения model-based расчета в отдельном процессе.
    
    Args:
        target_func: Объект ModelBasedTargetFunction
        bounds: Границы параметров для оптимизации
        method_params: Параметры алгоритма дифференциальной эволюции
        stop_event: Событие для координации остановки
        result_queue: Очередь для отправки результатов
    """
    
    def de_callback(xk, convergence):
        """Callback для отправки промежуточных результатов."""
        if stop_event.is_set():
            return True  # Прерывание оптимизации
        
        # Отправка лучшего результата в главный процесс
        best_mse = target_func.best_mse.value
        best_params = list(target_func.best_params)
        result_queue.put({
            "best_mse": best_mse, 
            "params": best_params
        })
        return False
    
    # Установка callback в параметры
    method_params = method_params.copy()
    method_params["callback"] = de_callback
    
    try:
        # Запуск оптимизации с включенным параллелизмом
        if "workers" not in method_params or method_params["workers"] == 1:
            method_params["workers"] = -1  # Использовать все ядра
            
        result = differential_evolution(target_func, bounds, **method_params)
        
        # Отправка финального результата
        result_queue.put({"final_result": result})
        
    except Exception as e:
        # Отправка информации об ошибке
        result_queue.put({"error": str(e)})
```

### 2. Обработка ограничений (NonlinearConstraint)

Добавить поддержку ограничений, которые могут не сериализоваться:

```python
def recreate_constraints(reaction_scheme_data):
    """
    Воссоздание ограничений внутри процесса-работника.
    
    Args:
        reaction_scheme_data: Данные схемы реакций для создания ограничений
        
    Returns:
        List[NonlinearConstraint]: Список ограничений
    """
    # Воссоздание логики из ModelBasedScenario.get_constraints()
    # без передачи несериализуемых объектов
    pass
```

### 3. Тестирование базовой функциональности

Создать тесты для проверки:
- Корректного запуска процесса-работника
- Передачи данных через очередь
- Обработки сигналов остановки
- Работы с вложенными процессами SciPy

**Файл:** `tests/test_model_calc_worker.py`

```python
import unittest
import multiprocessing
from src.core.model_calc_worker import run_model_calc

class TestModelCalcWorker(unittest.TestCase):
    
    def test_worker_process_creation(self):
        """Тест создания и запуска процесса-работника."""
        pass
    
    def test_result_queue_communication(self):
        """Тест передачи результатов через очередь."""
        pass
    
    def test_stop_event_handling(self):
        """Тест обработки сигналов остановки."""
        pass
    
    def test_scipy_parallel_execution(self):
        """Тест работы SciPy с workers > 1 внутри процесса."""
        pass
```

## Критерии приемки

1. ✅ Создан модуль `model_calc_worker.py` с функцией `run_model_calc`
2. ✅ Функция корректно обрабатывает параметры и запускает SciPy оптимизацию
3. ✅ Реализована отправка промежуточных результатов через очередь
4. ✅ Обработка сигналов остановки работает корректно
5. ✅ SciPy использует `workers > 1` без конфликтов
6. ✅ Написаны базовые unit-тесты
7. ✅ Функция обрабатывает исключения и отправляет ошибки

## Результат этапа

- Готовый модуль процесса-работника
- Базовые тесты функциональности
- Документация API функции-работника
- Подтверждение работы вложенных процессов SciPy

## Pull Request

**Название:** `feat: add worker process for model-based calculations`

**Описание:**
```
Добавлен процесс-работник для выполнения model-based расчетов:

- Создан модуль model_calc_worker.py с функцией run_model_calc
- Реализована отправка промежуточных результатов через multiprocessing.Queue
- Добавлена обработка сигналов остановки через multiprocessing.Event
- Включен параллелизм SciPy (workers > 1) внутри процесса
- Написаны unit-тесты для базовой функциональности

Этот этап создает основу для вынесения тяжелых вычислений из GUI потока.
```

**Связанные файлы:**
- `src/core/model_calc_worker.py` (новый)
- `tests/test_model_calc_worker.py` (новый)
- `docs/dev_plan/stage_01_worker_process.md` (новый)
