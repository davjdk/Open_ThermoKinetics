# Этап 3: Упрощение таблиц

**Время выполнения**: 1-2 часа  
**Приоритет**: Высокий  
**Статус**: К разработке  
**Зависимости**: Этап 2 (Форматирование заголовков)

## Задачи

### Задача 3.1: Изменить table_format с "grid" на "simple"

**Файл**: `src/core/log_aggregator/table_formatter.py`

**Текущее состояние** (grid формат):
```
+--------+----------------------+-----------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target    | Result data type   |  Status  |   Time, s |
+========+======================+===========+====================+==========+===========+
|      1 | CHECK_EXPERIMENT_... | file_data | bool               |    OK    |     0.001 |
+--------+----------------------+-----------+--------------------+----------+-----------+
```

**Целевое состояние** (simple формат):
```
   | Step | Sub-operation        | Target    | Result data type | Status | Time, s |
   | ---- | -------------------- | --------- | ---------------- | ------ | ------- |
   | 1    | CHECK_EXPERIMENT_... | file_data | bool             | OK     | 0.001   |
   | 2    | GET_DF_DATA          | file_data | DataFrame        | OK     | 0.003   |
```

**Модификация метода**:
```python
def _format_sub_operations_table(self, sub_operations: List[SubOperationLog]) -> str:
    """Форматирование таблицы подопераций."""
    if not sub_operations:
        return "No sub-operations recorded."
    
    # Подготовка данных для таблицы
    headers = ["Step", "Sub-operation", "Target", "Result data type", "Status", "Time, s"]
    rows = []
    
    for i, sub_op in enumerate(sub_operations, 1):
        execution_time = f"{sub_op.execution_time:.3f}" if sub_op.execution_time else "N/A"
        operation_name = self._truncate_operation_name(sub_op.operation_name)
        
        row = [
            str(i),
            operation_name,
            sub_op.target,
            sub_op.response_data_type,
            sub_op.status,
            execution_time
        ]
        rows.append(row)
    
    # Выбор формата таблицы на основе конфигурации
    table_format = self._get_table_format()
    
    return tabulate(rows, headers=headers, tablefmt=table_format, numalign="right")

def _get_table_format(self) -> str:
    """Определение формата таблицы на основе конфигурации."""
    if self._config.get("mode") == "minimalist":
        return "simple"  # Минималистичный формат
    else:
        return self._config.get("table_format", "grid")  # Стандартный формат
```

### Задача 3.2: Удалить декоративные элементы

**Файл**: `src/core/log_aggregator/table_formatter.py`

**Удаление декоративных рамок**:
```python
def format_operation_log(self, operation_log: OperationLog) -> str:
    """Основной метод форматирования лога операции."""
    parts = []
    
    # Декоративная рамка только в стандартном режиме
    show_borders = self._config.get("show_decorative_borders", True)
    if show_borders:
        parts.append("=" * 80)
    
    # Заголовок операции
    header = self._format_operation_header(operation_log)
    parts.append(header)
    
    # Пустая строка после заголовка только в стандартном режиме
    if show_borders:
        parts.append("")
    
    # Проверка на наличие мета-операций
    if hasattr(operation_log, 'meta_operations') and operation_log.meta_operations:
        meta_summary = self._format_meta_operations_summary(operation_log.meta_operations)
        parts.append(meta_summary)
        parts.append("")
        
        detailed_table = self._format_detailed_breakdown_with_meta(operation_log)
        parts.append(detailed_table)
    else:
        # Обычная таблица подопераций
        sub_ops_table = self._format_sub_operations_table(operation_log.sub_operations)
        parts.append(sub_ops_table)
    
    # Summary блок (всегда присутствует)
    summary = self._format_summary(operation_log)
    parts.append("")
    parts.append(summary)
    
    # Footer только в стандартном режиме
    show_footer = self._config.get("show_completion_footer", True)
    if show_footer:
        footer = self._format_operation_footer(operation_log)
        parts.append(footer)
        parts.append("=" * 80)
    
    return "\n".join(parts)
```

### Задача 3.3: Настроить разделители между таблицами

**Файл**: `src/core/log_aggregator/aggregated_operation_logger.py`

**Модификация метода log_operation**:
```python
def log_operation(self, operation_log: OperationLog) -> None:
    """Запись агрегированного лога операции."""
    try:
        # Применение мета-операций (если включено)
        if self._meta_detector is not None:
            try:
                self._meta_detector.detect_meta_operations(operation_log)
            except Exception as e:
                self._main_logger.debug(f"Meta-operation detection failed: {e}")
        
        # Форматирование операции
        formatted_log = self._formatter.format_operation_log(operation_log)
        
        # Добавление разделителя между операциями
        separator = self._config.get("table_separator", "\n\n")
        
        # Запись в лог
        self._logger.info(formatted_log)
        
        # Добавление разделителя после каждой операции (кроме первой)
        if hasattr(self, '_first_operation'):
            self._logger.info(separator)
        else:
            self._first_operation = False
            
    except Exception as e:
        self._main_logger.warning(f"Failed to log aggregated operation: {e}")
```

**Alternative approach - разделитель в конце форматирования**:
```python
def format_operation_log(self, operation_log: OperationLog) -> str:
    """Основной метод форматирования с автоматическим разделителем."""
    # ...existing formatting logic...
    
    # Добавление разделителя в минималистичном режиме
    separator = self._config.get("table_separator", "")
    if separator and self._config.get("mode") == "minimalist":
        parts.append(separator)
    
    return "\n".join(parts)
```

### Задача 3.4: Тестирование табличного форматирования

**Файл**: `tests/test_log_aggregator/test_table_simplification.py`

```python
import pytest
from src.core.log_aggregator.operation_log import OperationLog, SubOperationLog
from src.core.log_aggregator.table_formatter import OperationTableFormatter

class TestTableSimplification:
    
    def test_simple_table_format(self):
        """Тест простого формата таблицы."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.sub_operations = [
            SubOperationLog(1, "GET_DATA", "file_data", 1640995200.0, 1640995200.1, 0.1, "DataFrame", "OK"),
            SubOperationLog(2, "SET_VALUE", "calc_data", 1640995200.1, 1640995200.2, 0.1, "dict", "OK")
        ]
        
        formatter = OperationTableFormatter()
        formatter._config = {"mode": "minimalist", "table_format": "simple"}
        
        table = formatter._format_sub_operations_table(operation_log.sub_operations)
        
        # Проверяем отсутствие grid-символов
        assert "+" not in table
        assert "=" not in table
        
        # Проверяем наличие simple-символов
        assert "|" in table
        assert "-" in table
        
        # Проверяем структуру
        lines = table.split('\n')
        assert len(lines) >= 3  # Header + separator + data rows
    
    def test_no_decorative_borders_in_minimalist_mode(self):
        """Тест отсутствия декоративных рамок в минималистичном режиме."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        operation_log.end_time = 1640995201.0
        operation_log.status = "success"
        
        formatter = OperationTableFormatter()
        formatter._config = {
            "mode": "minimalist",
            "show_decorative_borders": False,
            "show_completion_footer": False
        }
        
        result = formatter.format_operation_log(operation_log)
        
        # Не должно быть декоративных элементов
        assert "=" * 80 not in result
        assert "COMPLETED" not in result
        
        # Должен содержать основные элементы
        assert "TEST_OPERATION" in result
        assert "SUMMARY:" in result
    
    def test_table_separator_between_operations(self):
        """Тест разделителя между таблицами."""
        formatter = OperationTableFormatter()
        formatter._config = {
            "mode": "minimalist",
            "table_separator": "\n\n"
        }
        
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        
        result = formatter.format_operation_log(operation_log)
        
        # В минималистичном режиме должен заканчиваться разделителем
        assert result.endswith("\n\n")
    
    def test_standard_mode_preserves_grid_format(self):
        """Тест сохранения grid формата в стандартном режиме."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.sub_operations = [
            SubOperationLog(1, "GET_DATA", "file_data", 1640995200.0, 1640995200.1, 0.1, "DataFrame", "OK")
        ]
        
        formatter = OperationTableFormatter()
        formatter._config = {"mode": "standard", "table_format": "grid"}
        
        table = formatter._format_sub_operations_table(operation_log.sub_operations)
        
        # Должны присутствовать grid-символы
        assert "+" in table
        assert "=" in table
        assert "|" in table
```

### Задача 3.5: Оптимизация производительности

**Файл**: `src/core/log_aggregator/table_formatter.py`

**Кэширование конфигурации**:
```python
class OperationTableFormatter:
    def __init__(self, table_format: str = "grid", max_cell_width: int = 50, config: Optional[Dict] = None):
        # ...existing init...
        
        # Кэширование часто используемых значений конфигурации
        self._is_minimalist = self._config.get("mode") == "minimalist"
        self._cached_table_format = self._get_table_format()
        self._show_borders = self._config.get("show_decorative_borders", True)
        self._show_footer = self._config.get("show_completion_footer", True)
        self._table_separator = self._config.get("table_separator", "\n\n")
    
    def _get_table_format(self) -> str:
        """Оптимизированное получение формата таблицы."""
        if self._is_minimalist:
            return "simple"
        return self._config.get("table_format", "grid")
```

## Критерии готовности

### Функциональные критерии
- ✅ Таблицы используют минимальное ASCII оформление в минималистичном режиме
- ✅ Между таблицами используется разделитель `\n\n`
- ✅ Декоративные рамки отсутствуют в минималистичном режиме
- ✅ Стандартный режим сохраняет прежнее поведение

### Технические критерии
- ✅ Конфигурационное переключение между форматами работает корректно
- ✅ Производительность не деградирует
- ✅ Все существующие тесты проходят
- ✅ Форматирование консистентно для всех типов операций

### Критерии качества
- ✅ Таблицы остаются читаемыми в простом формате
- ✅ Информация не теряется при упрощении
- ✅ Визуальная структура сохраняется

## Входные данные

**От Этапа 2**:
- Система конфигурации форматирования
- Готовые заголовки в минималистичном формате
- Инфраструктура для переключения режимов

## Выходные данные

**Для Этапа 4**:
- Упрощенные таблицы с минимальным оформлением
- Настроенные разделители между операциями
- Конфигурационная поддержка для удаления footer

## Примеры результата

### Минималистичная таблица
```
calculations_data.py:127 "ADD_REACTION" (id=3, 2025-06-17 00:47:51)

   | Step | Sub-operation        | Target    | Result data type | Status | Time, s |
   | ---- | -------------------- | --------- | ---------------- | ------ | ------- |
   | 1    | CHECK_EXPERIMENT_... | file_data | bool             | OK     | 0.001   |
   | 2    | GET_DF_DATA          | file_data | DataFrame        | OK     | 0.003   |

SUMMARY: steps 2, successful 2, with errors 0, total time 0.004 s.


file_data.py:89 "LOAD_FILE" (id=4, 2025-06-17 00:48:15)

   | Step | Sub-operation | Target    | Result data type | Status | Time, s |
   | ---- | ------------- | --------- | ---------------- | ------ | ------- |
   | 1    | VALIDATE_FILE | file_data | bool             | OK     | 0.002   |

SUMMARY: steps 1, successful 1, with errors 0, total time 0.002 s.

```

### Стандартная таблица (для сравнения)
```
================================================================================
Operation "ADD_REACTION" – STARTED (id=3, 2025-06-17 00:47:51)

+--------+----------------------+-----------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target    | Result data type   |  Status  |   Time, s |
+========+======================+===========+====================+==========+===========+
|      1 | CHECK_EXPERIMENT_... | file_data | bool               |    OK    |     0.001 |
+--------+----------------------+-----------+--------------------+----------+-----------+

SUMMARY: steps 1, successful 1, with errors 0, total time 0.001 s.
Operation "ADD_REACTION" – COMPLETED (status: successful)
================================================================================
```

## Риски и митигации

**Риск**: Потеря читаемости при упрощении
- **Митигация**: Тщательный выбор ASCII символов для разделителей
- **Тестирование**: Визуальная проверка различных размеров таблиц

**Риск**: Проблемы с выравниванием в simple формате
- **Митигация**: Настройка параметров tabulate для корректного выравнивания
- **Fallback**: Возможность принудительного возврата к grid формату

**Риск**: Конфликты между разделителями и содержимым
- **Митигация**: Конфигурируемые разделители с escape-последовательностями
- **Валидация**: Проверка корректности разделителей

## Результат этапа

После завершения этапа:
1. Таблицы используют минималистичное ASCII оформление
2. Система поддерживает настраиваемые разделители между операциями
3. Декоративные элементы удалены из минималистичного режима
4. Сохранена полная функциональность стандартного режима
