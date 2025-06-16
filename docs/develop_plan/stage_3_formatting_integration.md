# Этап 3: Интеграция с форматированием

**Проект:** Open ThermoKinetics - Анализ кинетики твердофазных реакций  
**Модуль:** `src/core/log_aggregator`  
**Этап:** 3 из 4  
**Продолжительность:** 2-3 дня  
**Приоритет:** Высокий  

## Цель этапа

Интегрировать систему расширенной обработки ошибок с форматированием логов для вывода детальной информации об ошибках подопераций.

## Задачи этапа

### 3.1 Обновление OperationTableFormatter

**Целевой файл:** `src/core/log_aggregator/table_formatter.py`

**Добавить новые методы для форматирования ошибок:**

1. **Метод `_format_error_details_block()`:**
```python
def _format_error_details_block(self, operation_log: OperationLog) -> str:
    """
    Format detailed error information for sub-operations with errors.
    
    Args:
        operation_log: The operation log data
        
    Returns:
        str: Formatted error details block
    """
    error_sub_operations = [
        sub_op for sub_op in operation_log.sub_operations 
        if sub_op.status == "Error" and sub_op.has_detailed_error()
    ]
    
    if not error_sub_operations:
        return ""
    
    lines = ["ERROR DETAILS:"]
    lines.append("─" * 77)  # Separator line
    
    for sub_op in error_sub_operations:
        error_block = self._format_single_error_details(sub_op)
        lines.append(error_block)
        lines.append("")  # Empty line between errors
    
    lines.append("─" * 77)  # Bottom separator
    
    return "\n".join(lines)

def _format_single_error_details(self, sub_operation: SubOperationLog) -> str:
    """
    Format detailed information for a single sub-operation error.
    
    Args:
        sub_operation: SubOperationLog with error details
        
    Returns:
        str: Formatted error information
    """
    if not sub_operation.has_detailed_error():
        return f"Step {sub_operation.step_number}: {sub_operation.clean_operation_name} → {sub_operation.target}\n  Error: {sub_operation.get_error_summary()}"
    
    error_details = sub_operation.error_details
    lines = []
    
    # Header line
    lines.append(f"Step {sub_operation.step_number}: {sub_operation.clean_operation_name} → {sub_operation.target}")
    
    # Error type and severity
    lines.append(f"  Error Type: {error_details.error_type.value.upper()}")
    lines.append(f"  Severity: {error_details.severity.value.upper()}")
    
    # Error message
    lines.append(f"  Message: {error_details.error_message}")
    
    # Context information
    if error_details.error_context:
        lines.append("  Context:")
        for key, value in error_details.error_context.items():
            lines.append(f"    - {key}: {value}")
    
    # Technical details
    if error_details.technical_details:
        lines.append(f"  Technical Details: {error_details.technical_details}")
    
    # Suggested action
    if error_details.suggested_action:
        lines.append(f"  Suggested Action: {error_details.suggested_action}")
    
    return "\n".join(lines)
```

2. **Добавить конфигурационные параметры:**
```python
class OperationTableFormatter:
    """Formatter for creating human-readable tables from operation logs."""

    def __init__(self, 
                 table_format: str = "grid", 
                 max_cell_width: int = 50,
                 include_error_details: bool = True,
                 max_error_context_items: int = 5):
        """
        Initialize the table formatter.

        Args:
            table_format: Tabulate table format (grid, plain, simple, etc.)
            max_cell_width: Maximum width for table cells
            include_error_details: Whether to include detailed error blocks
            max_error_context_items: Maximum number of context items to display
        """
        self.table_format = table_format
        self.max_cell_width = max_cell_width
        self.include_error_details = include_error_details
        self.max_error_context_items = max_error_context_items
        self._operation_counter = 0
```

3. **Модифицировать метод `format_operation_log()`:**
```python
def format_operation_log(self, operation_log: OperationLog) -> str:
    """
    Format a complete operation log into a readable table format.
    
    Args:
        operation_log: The OperationLog instance to format
        
    Returns:
        str: Complete formatted operation log
    """
    self._operation_counter += 1
    operation_id = self._operation_counter
    
    parts = []
    
    # 1. Header separator
    parts.append("=" * 80)
    
    # 2. Operation header
    header = self._format_operation_header(operation_log, operation_id)
    parts.append(header)
    parts.append("")  # Empty line
    
    # 3. Sub-operations table
    table = self._format_sub_operations_table(operation_log.sub_operations)
    parts.append(table)
    parts.append("")  # Empty line
    
    # 4. Error details block (NEW)
    if self.include_error_details:
        error_block = self._format_error_details_block(operation_log)
        if error_block:
            parts.append(error_block)
            parts.append("")  # Empty line
    
    # 5. Operation summary
    summary = self._format_operation_summary(operation_log, operation_id)
    parts.append(summary)
    
    # 6. Footer separator
    parts.append("=" * 80)
    
    return "\n".join(parts) + "\n"
```

### 3.2 Обновление AggregatedOperationLogger

**Целевой файл:** `src/core/log_aggregator/aggregated_operation_logger.py`

**Добавить конфигурируемость форматирования:**

```python
class AggregatedOperationLogger:
    """Singleton logger for aggregated operation logs."""
    
    _instance = None
    _logger = None
    _formatter = None
    
    def __init__(self, include_error_details: bool = True):
        """
        Initialize the aggregated operation logger.
        
        Args:
            include_error_details: Whether to include detailed error information
        """
        if AggregatedOperationLogger._logger is None:
            self._setup_logger()
            
        if AggregatedOperationLogger._formatter is None:
            from .table_formatter import OperationTableFormatter
            AggregatedOperationLogger._formatter = OperationTableFormatter(
                include_error_details=include_error_details
            )
    
    def set_error_details_enabled(self, enabled: bool):
        """Enable or disable detailed error logging."""
        if self._formatter:
            self._formatter.include_error_details = enabled
```

### 3.3 Интеграция с операционным логгером

**Целевой файл:** `src/core/log_aggregator/operation_logger.py`

**Обновить HandleRequestCycleProxy для сохранения данных ошибок:**

```python
class HandleRequestCycleProxy:
    """Proxy for intercepting handle_request_cycle calls."""
    
    def __call__(self, target: str, operation: str, **kwargs) -> Any:
        """Proxy call that captures sub-operation data."""
        operation_logger = get_current_operation_logger()
        if operation_logger is None:
            return self.original_method(target, operation, **kwargs)
        
        step_number = len(operation_logger.operation_log.sub_operations) + 1
        start_time = time.time()
        
        # Create sub-operation log
        sub_operation = SubOperationLog(
            step_number=step_number,
            operation_name=operation,
            target=target,
            start_time=start_time,
            request_kwargs=kwargs.copy()  # Store request parameters
        )
        
        try:
            # Execute original method
            response_data = self.original_method(target, operation, **kwargs)
            
            # Complete sub-operation with success
            sub_operation.complete_operation(response_data)
            
            return response_data
            
        except Exception as e:
            # Complete sub-operation with error
            sub_operation.complete_operation(
                response_data=None,
                exception_occurred=True
            )
            sub_operation.exception_traceback = str(e)
            
            # Re-raise the exception
            raise
            
        finally:
            # Add sub-operation to main operation log
            operation_logger.operation_log.sub_operations.append(sub_operation)
```

### 3.4 Обновление экспорта модуля

**Целевой файл:** `src/core/log_aggregator/__init__.py`

```python
"""
Log aggregator module for operation tracking and analysis.

This module provides comprehensive logging and analysis capabilities
for tracking operations and sub-operations within the application.
"""

from .operation_logger import operation, OperationLogger
from .operation_log import OperationLog
from .sub_operation_log import SubOperationLog
from .table_formatter import OperationTableFormatter
from .aggregated_operation_logger import AggregatedOperationLogger, get_aggregated_logger
from .error_handler import (
    ErrorAnalysis, 
    ErrorCategory, 
    ErrorSeverity, 
    SubOperationErrorHandler
)

__all__ = [
    "operation",
    "OperationLogger",
    "OperationLog", 
    "SubOperationLog",
    "OperationTableFormatter",
    "AggregatedOperationLogger",
    "get_aggregated_logger",
    "ErrorAnalysis",
    "ErrorCategory", 
    "ErrorSeverity",
    "SubOperationErrorHandler"
]
```

## Ожидаемый результат

### Новый формат вывода с детальными ошибками:

```
================================================================================
Operation "MODEL_FIT_CALCULATION" – STARTED (id=28, 2025-06-16 13:42:31)

+--------+----------------------+-----------------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target          | Result data type   |  Status  |   Time, s |
+========+======================+=================+====================+==========+===========+
|      1 | GET_SERIES_VALUE     | series_data     | dict               |  Error   |     0.033 |
|      2 | MODEL_FIT_CALC       | model_fit_ca... | dict               |  Error   |     0.498 |
|      3 | UPDATE_SERIES        | series_data     | bool               |    OK    |     0.026 |
+--------+----------------------+-----------------+--------------------+----------+-----------+

ERROR DETAILS:
─────────────────────────────────────────────────────────────────────────────────
Step 1: GET_SERIES_VALUE → series_data
  Error Type: DATA_VALIDATION_ERROR
  Severity: HIGH
  Message: Series data not found or invalid format
  Context: 
    - Target series: "test_series"
    - Expected path: ["test_series", "experimental_data"]
    - Actual data type: None
  Technical Details: KeyError in series_data.get_value() - missing experimental_data key
  
Step 2: MODEL_FIT_CALC → model_fit_calculation
  Error Type: CALCULATION_ERROR  
  Severity: CRITICAL
  Message: Insufficient data for model fitting calculation
  Context:
    - Required parameters: experimental_data, reaction_scheme
    - Missing parameters: experimental_data
    - Available data: deconvolution_results only
  Technical Details: ValueError: Cannot perform model fitting without experimental data
─────────────────────────────────────────────────────────────────────────────────

SUMMARY: steps 3, successful 1, with errors 2, total time 0.562 s.
Operation "MODEL_FIT_CALCULATION" – COMPLETED (status: successful)
================================================================================
```

## Тестирование

### 3.5 Комплексные тесты интеграции

**Обновить тестовый файл:** `tests/test_log_aggregator/test_table_formatter.py`

**Тест-кейсы:**

1. **Тестирование форматирования с ошибками:**
```python
def test_format_operation_log_with_error_details():
    """Test complete operation log formatting with error details."""
    
def test_format_error_details_block():
    """Test error details block formatting."""
    
def test_format_single_error_details():
    """Test single error details formatting."""
    
def test_configurable_error_details():
    """Test configurable error details inclusion."""
```

2. **Тестирование интеграции:**
```python
def test_end_to_end_error_logging():
    """Test complete end-to-end error logging flow."""
    
def test_error_details_disabled():
    """Test operation when error details are disabled."""
```

### 3.6 Тестирование производительности

**Создать файл:** `tests/test_log_aggregator/test_performance.py`

```python
def test_error_analysis_performance():
    """Test that error analysis doesn't significantly impact performance."""
    
def test_large_operation_log_formatting():
    """Test formatting performance with large operation logs."""
```

## Критерии завершения этапа

- ✅ `OperationTableFormatter` обновлен с методами форматирования ошибок
- ✅ Конфигурационные параметры для управления выводом ошибок добавлены
- ✅ `AggregatedOperationLogger` поддерживает настройку детализации ошибок
- ✅ `operation_logger.py` обновлен для сохранения данных ошибок
- ✅ Экспорт модуля `__init__.py` обновлен
- ✅ Все тесты интеграции проходят успешно
- ✅ Производительность форматирования приемлемая
- ✅ Ручное тестирование на реальных логах завершено
- ✅ Code review пройден

## Файлы для изменения

1. `src/core/log_aggregator/table_formatter.py` - методы форматирования ошибок
2. `src/core/log_aggregator/aggregated_operation_logger.py` - конфигурируемость
3. `src/core/log_aggregator/operation_logger.py` - сохранение данных ошибок
4. `src/core/log_aggregator/__init__.py` - обновление экспорта
5. `tests/test_log_aggregator/test_table_formatter.py` - обновление тестов
6. `tests/test_log_aggregator/test_performance.py` - тесты производительности

## Зависимости

- **Завершен Этап 1:** Улучшение отображения операций
- **Завершен Этап 2:** Создание системы обработки ошибок
- **Внешние библиотеки:** Использует существующие зависимости
- **Совместимость:** Полная обратная совместимость

## Конфигурационные возможности

После завершения этапа будут доступны следующие настройки:

```python
# Включение/отключение детальных ошибок
formatter = OperationTableFormatter(include_error_details=True)

# Настройка максимального количества контекстных элементов
formatter = OperationTableFormatter(max_error_context_items=3)

# Отключение детальных ошибок для production
aggregated_logger = AggregatedOperationLogger(include_error_details=False)
```

## Следующий этап

После завершения Этапа 3 переходить к **Этапу 4: Документация и финализация**.
