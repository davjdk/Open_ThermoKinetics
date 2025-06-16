# Этап 1: Улучшение отображения операций

**Проект:** Open ThermoKinetics - Анализ кинетики твердофазных реакций  
**Модуль:** `src/core/log_aggregator`  
**Этап:** 1 из 4  
**Продолжительность:** 1-2 дня  
**Приоритет:** Высокий  

## Цель этапа

Убрать префикс `OperationType` из названий операций в колонке Sub-operation и обеспечить отображение полных читаемых названий операций без сокращений.

## Задачи этапа

### 1.1 Модификация SubOperationLog

**Целевой файл:** `src/core/log_aggregator/sub_operation_log.py`

**Требуемые изменения:**

1. **Добавить свойство `clean_operation_name`:**
```python
@property
def clean_operation_name(self) -> str:
    """
    Get operation name without OperationType prefix.
    
    Returns:
        str: Clean operation name (e.g., 'CHECK_FILE_EXISTS' instead of 'OperationType.CHECK_FILE_EXISTS')
    """
    if self.operation_name.startswith("OperationType."):
        return self.operation_name[len("OperationType."):]
    
    # Handle enum string representation
    if "." in self.operation_name:
        parts = self.operation_name.split(".")
        if len(parts) >= 2 and parts[0] == "OperationType":
            return parts[1]
    
    # Fallback to original name if no prefix found
    return self.operation_name
```

2. **Обновить существующее свойство `operation_display_name`:**
```python
@property
def operation_display_name(self) -> str:
    """Get a display-friendly operation name."""
    return self.clean_operation_name
```

### 1.2 Обновление OperationTableFormatter

**Целевой файл:** `src/core/log_aggregator/table_formatter.py`

**Требуемые изменения:**

1. **Изменить метод `_format_sub_operations_table()`:**

Заменить строку:
```python
self._truncate_text(sub_op.operation_name, 20),
```

На:
```python
sub_op.clean_operation_name,
```

2. **Увеличить ширину колонки Sub-operation:**

Изменить конфигурацию обрезки с 20 до 25 символов (если необходимо сохранить обрезку):
```python
self._truncate_text(sub_op.clean_operation_name, 25),
```

3. **Обновить заголовки таблицы (опционально):**
```python
headers = [
    "Step",
    "Sub-operation",      # Может быть изменено на "Operation" для краткости
    "Target", 
    "Result data type",
    "Status",
    "Time, s",
]
```

## Ожидаемый результат

### До изменений:
```
+--------+----------------------+-----------------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target          | Result data type   |  Status  |   Time, s |
+========+======================+=================+====================+==========+===========+
|      1 | OperationType.CHE... | file_data       | bool               |    OK    |     0.001 |
|      2 | OperationType.GET... | file_data       | DataFrame          |    OK    |     0.003 |
|      3 | OperationType.SET... | calculations... | bool               |    OK    |     0.004 |
+--------+----------------------+-----------------+--------------------+----------+-----------+
```

### После изменений:
```
+--------+----------------------+-----------------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target          | Result data type   |  Status  |   Time, s |
+========+======================+=================+====================+==========+===========+
|      1 | CHECK_FILE_EXISTS    | file_data       | bool               |    OK    |     0.001 |
|      2 | GET_DF_DATA          | file_data       | DataFrame          |    OK    |     0.003 |
|      3 | SET_VALUE            | calculations... | bool               |    OK    |     0.004 |
+--------+----------------------+-----------------+--------------------+----------+-----------+
```

## Тестирование

### 1.3 Unit тесты для нового функционала

**Создать тестовый файл:** `tests/test_log_aggregator/test_sub_operation_display.py`

**Тест-кейсы:**

1. **Тест очистки названия операции:**
```python
def test_clean_operation_name_removes_operationtype_prefix():
    """Test that OperationType prefix is properly removed."""
    sub_op = SubOperationLog(
        step_number=1,
        operation_name="OperationType.CHECK_FILE_EXISTS",
        target="file_data",
        start_time=time.time()
    )
    assert sub_op.clean_operation_name == "CHECK_FILE_EXISTS"

def test_clean_operation_name_handles_enum_string():
    """Test handling of enum string representation."""
    sub_op = SubOperationLog(
        step_number=1,
        operation_name="OperationType.GET_DF_DATA",
        target="file_data", 
        start_time=time.time()
    )
    assert sub_op.clean_operation_name == "GET_DF_DATA"

def test_clean_operation_name_fallback():
    """Test fallback to original name when no prefix."""
    sub_op = SubOperationLog(
        step_number=1,
        operation_name="CUSTOM_OPERATION",
        target="file_data",
        start_time=time.time()
    )
    assert sub_op.clean_operation_name == "CUSTOM_OPERATION"
```

2. **Тест форматирования таблицы:**
```python
def test_table_formatter_uses_clean_names():
    """Test that table formatter uses clean operation names."""
    # Создать mock данные с OperationType префиксами
    # Проверить, что в результирующей таблице нет префиксов
    pass
```

### 1.4 Интеграционные тесты

**Обновить существующие тесты:**
- `tests/test_log_aggregator/test_table_formatter.py`
- Проверить, что изменения не нарушают существующую функциональность
- Убедиться, что форматирование таблиц работает корректно

## Критерии завершения этапа

- ✅ Свойство `clean_operation_name` добавлено в `SubOperationLog`
- ✅ `OperationTableFormatter` использует чистые названия операций
- ✅ Все существующие тесты проходят успешно
- ✅ Новые unit тесты созданы и проходят
- ✅ Интеграционные тесты обновлены
- ✅ Code review пройден
- ✅ Ручное тестирование на реальных данных завершено

## Файлы для изменения

1. `src/core/log_aggregator/sub_operation_log.py` - добавление `clean_operation_name`
2. `src/core/log_aggregator/table_formatter.py` - использование чистых названий
3. `tests/test_log_aggregator/test_sub_operation_display.py` - новые тесты
4. `tests/test_log_aggregator/test_table_formatter.py` - обновление тестов

## Зависимости

- Нет внешних зависимостей
- Не требует изменений в других модулях
- Изменения полностью обратно совместимы

## Следующий этап

После завершения Этапа 1 переходить к **Этапу 2: Создание системы обработки ошибок**.
