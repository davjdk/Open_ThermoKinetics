# Этап 1: Создание API для явного логирования операций

## Цель этапа
Создать базовую инфраструктуру для явного обозначения границ операций в коде через API методы.

## Компоненты для реализации

### 1.1. OperationLogger - основной API класс
Создать новый класс `OperationLogger` в `src/log_aggregator/operation_logger.py`:

```python
class OperationLogger:
    def start_operation(self, name: str) -> None:
        """Начать новую операцию с указанным именем"""
        
    def end_operation(self) -> None:
        """Завершить текущую операцию"""
        
    def add_metric(self, key: str, value: Any) -> None:
        """Добавить произвольную метрику к текущей операции"""
```

### 1.2. Контекстный менеджер
Создать контекстный менеджер для удобства использования:

```python
@contextmanager
def log_operation(name: str):
    """Контекстный менеджер для операций"""
    operation_logger.start_operation(name)
    try:
        yield
    finally:
        operation_logger.end_operation()
```

### 1.3. Декоратор для операций
Создать декоратор для автоматического оборачивания методов:

```python
def operation(name: str):
    """Декоратор для автоматического логирования операций"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with log_operation(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
```

## Места в коде для интеграции

### Основные операции в MainWindow
Следующие методы должны быть обернуты в операции:

| Метод                                | Название операции          | Тип каскада                      |
| ------------------------------------ | -------------------------- | -------------------------------- |
| `_handle_add_new_series`             | ADD_NEW_SERIES             | Сложный (3 handle_request_cycle) |
| `_handle_model_free_calculation`     | MODEL_FREE_CALCULATION     | Сложный (3 handle_request_cycle) |
| `_handle_model_fit_calculation`      | MODEL_FIT_CALCULATION      | Сложный (3 handle_request_cycle) |
| `_handle_model_based_calculation`    | MODEL_BASED_CALCULATION    | Сложный (несколько вызовов)      |
| `_handle_load_deconvolution_results` | LOAD_DECONVOLUTION_RESULTS | Средний (2 handle_request_cycle) |
| `_handle_select_series`              | SELECT_SERIES              | Средний (2 handle_request_cycle) |
| `_handle_scheme_change`              | SCHEME_CHANGE              | Средний (2 handle_request_cycle) |
| `_handle_deconvolution`              | DECONVOLUTION              | Простой (1 handle_request_cycle) |
| `_handle_add_reaction`               | ADD_REACTION               | Простой (1 handle_request_cycle) |
| `_handle_remove_reaction`            | REMOVE_REACTION            | Простой (1 handle_request_cycle) |
| `_handle_import_reactions`           | IMPORT_REACTIONS           | Простой (1 handle_request_cycle) |
| `_handle_export_reactions`           | EXPORT_REACTIONS           | Простой (1 handle_request_cycle) |

### Пример интеграции
```python
@operation("ADD_NEW_SERIES")
def _handle_add_new_series(self, params):
    # Существующий код без изменений
    df_copies = self.handle_request_cycle("file_data", OperationType.GET_ALL_DATA, file_name="all_files")
    # ... остальной код
```

Или с использованием контекстного менеджера:

```python
def _handle_add_new_series(self, params):
    with log_operation("ADD_NEW_SERIES"):
        # Существующий код без изменений
        df_copies = self.handle_request_cycle("file_data", OperationType.GET_ALL_DATA, file_name="all_files")
        # ... остальной код
```

## Критерии завершения этапа
1. ✅ Создан класс `OperationLogger` с базовым API
2. ✅ Реализован контекстный менеджер `log_operation`
3. ✅ Реализован декоратор `@operation`
4. ✅ Добавлена интеграция в 5-7 основных методов MainWindow
5. ✅ Написаны базовые unit-тесты для API
6. ✅ Проверена совместимость с существующей системой логирования

## Ожидаемый результат
После завершения этапа разработчики смогут явно маркировать границы операций в коде, что создаст основу для дальнейшей агрегации и анализа логов.
