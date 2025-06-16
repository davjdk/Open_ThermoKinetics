# Этап 4: Удаление footer

**Время выполнения**: 30 минут  
**Приоритет**: Средний  
**Статус**: К разработке  
**Зависимости**: Этап 3 (Упрощение таблиц)

## Задачи

### Задача 4.1: Модифицировать format_operation_log() для пропуска footer

**Файл**: `src/core/log_aggregator/table_formatter.py`

**Текущее поведение**:
```
SUMMARY: steps 1, successful 1, with errors 0, total time 0.001 s.
Operation "TO_A_T" – COMPLETED (status: successful)
================================================================================
```

**Целевое поведение** (минималистичный режим):
```
SUMMARY: steps 1, successful 1, with errors 0, total time 0.001 s.


```

**Модификация метода**:
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
    
    # Footer и декоративная рамка только в стандартном режиме
    show_footer = self._config.get("show_completion_footer", True)
    if show_footer:
        footer = self._format_operation_footer(operation_log)
        parts.append(footer)
        
        if show_borders:
            parts.append("=" * 80)
    
    # Разделитель между операциями в минималистичном режиме
    if not show_footer and self._config.get("table_separator"):
        parts.append(self._config.get("table_separator"))
    
    return "\n".join(parts)
```

### Задача 4.2: Сохранить только SUMMARY блок

**Файл**: `src/core/log_aggregator/table_formatter.py`

**Анализ существующего _format_summary()**:
```python
def _format_summary(self, operation_log: OperationLog) -> str:
    """Форматирование блока summary (сохраняется во всех режимах)."""
    sub_ops_count = len(operation_log.sub_operations)
    successful_count = operation_log.successful_sub_operations_count
    failed_count = operation_log.failed_sub_operations_count
    total_time = operation_log.execution_time or 0.0
    
    summary_parts = [
        f"steps {sub_ops_count}",
        f"successful {successful_count}",
        f"with errors {failed_count}",
        f"total time {total_time:.3f} s"
    ]
    
    # Добавление информации о мета-операциях (если есть)
    if hasattr(operation_log, 'meta_operations') and operation_log.meta_operations:
        meta_count = len(operation_log.meta_operations)
        summary_parts.insert(-1, f"meta-operations {meta_count}")  # Вставляем перед total time
    
    return f"SUMMARY: {', '.join(summary_parts)}."
```

**Проверка, что SUMMARY всегда включается**:
- SUMMARY блок должен присутствовать во всех режимах
- Содержит статистику выполнения операции
- Информативен для анализа производительности

### Задача 4.3: Тестирование удаления footer

**Файл**: `tests/test_log_aggregator/test_footer_removal.py`

```python
import pytest
from src.core.log_aggregator.operation_log import OperationLog, SubOperationLog
from src.core.log_aggregator.table_formatter import OperationTableFormatter

class TestFooterRemoval:
    
    def test_no_footer_in_minimalist_mode(self):
        """Тест отсутствия footer в минималистичном режиме."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        operation_log.end_time = 1640995201.0
        operation_log.status = "success"
        operation_log.execution_time = 1.0
        
        formatter = OperationTableFormatter()
        formatter._config = {
            "mode": "minimalist",
            "show_completion_footer": False,
            "show_decorative_borders": False
        }
        
        result = formatter.format_operation_log(operation_log)
        
        # Footer элементы не должны присутствовать
        assert "COMPLETED" not in result
        assert "– STARTED" not in result  # Кроме заголовка, если используется стандартный формат
        assert "status: successful" not in result
        assert "=" * 80 not in result
        
        # SUMMARY должен присутствовать
        assert "SUMMARY:" in result
    
    def test_footer_present_in_standard_mode(self):
        """Тест наличия footer в стандартном режиме."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        operation_log.end_time = 1640995201.0
        operation_log.status = "success"
        operation_log.execution_time = 1.0
        
        formatter = OperationTableFormatter()
        formatter._config = {
            "mode": "standard",
            "show_completion_footer": True,
            "show_decorative_borders": True
        }
        
        result = formatter.format_operation_log(operation_log)
        
        # Footer элементы должны присутствовать
        assert "COMPLETED" in result
        assert "status: successful" in result
        assert "=" * 80 in result
        
        # SUMMARY также должен присутствовать
        assert "SUMMARY:" in result
    
    def test_summary_always_present(self):
        """Тест того, что SUMMARY всегда присутствует."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.sub_operations = [
            SubOperationLog(1, "GET_DATA", "file_data", 1640995200.0, 1640995200.1, 0.1, "DataFrame", "OK"),
            SubOperationLog(2, "SET_VALUE", "calc_data", 1640995200.1, 1640995200.2, 0.1, "dict", "Error")
        ]
        operation_log.execution_time = 0.2
        
        # Тест в минималистичном режиме
        formatter_min = OperationTableFormatter()
        formatter_min._config = {"mode": "minimalist", "show_completion_footer": False}
        
        result_min = formatter_min.format_operation_log(operation_log)
        assert "SUMMARY: steps 2, successful 1, with errors 1, total time 0.200 s." in result_min
        
        # Тест в стандартном режиме
        formatter_std = OperationTableFormatter()
        formatter_std._config = {"mode": "standard", "show_completion_footer": True}
        
        result_std = formatter_std.format_operation_log(operation_log)
        assert "SUMMARY: steps 2, successful 1, with errors 1, total time 0.200 s." in result_std
    
    def test_table_separator_after_summary_in_minimalist_mode(self):
        """Тест разделителя после SUMMARY в минималистичном режиме."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.execution_time = 0.1
        
        formatter = OperationTableFormatter()
        formatter._config = {
            "mode": "minimalist",
            "show_completion_footer": False,
            "table_separator": "\n\n"
        }
        
        result = formatter.format_operation_log(operation_log)
        
        # Должен заканчиваться разделителем
        assert result.endswith("\n\n")
        
        # Не должно быть footer
        assert "COMPLETED" not in result
    
    def test_configurable_footer_behavior(self):
        """Тест конфигурируемого поведения footer."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.status = "success"
        
        # Тест принудительного отключения footer
        formatter = OperationTableFormatter()
        formatter._config = {
            "mode": "standard",  # Стандартный режим
            "show_completion_footer": False  # Но footer отключен
        }
        
        result = formatter.format_operation_log(operation_log)
        
        # Footer не должен присутствовать даже в стандартном режиме
        assert "COMPLETED" not in result
        assert "status: successful" not in result
```

### Задача 4.4: Валидация конфигурации

**Файл**: `src/core/log_aggregator/meta_operation_config.py`

**Обновление конфигурации**:
```python
META_OPERATION_CONFIG = {
    "enabled": True,
    "formatting": {
        "mode": "standard",  # "standard" или "minimalist"
        "table_format": "grid",
        "show_decorative_borders": True,
        "show_completion_footer": True,   # Управление footer
        "table_separator": "\n\n",
        "include_source_info": True,
        "header_format": "standard"
    },
    "minimalist_settings": {
        "table_format": "simple",
        "show_decorative_borders": False,
        "show_completion_footer": False,  # Footer отключен в минималистичном режиме
        "header_format": "source_based",
        "table_separator": "\n\n"
    },
    # ...existing config...
}
```

**Валидация настроек**:
```python
def validate_formatting_config(config: Dict) -> Dict:
    """Валидация конфигурации форматирования."""
    validated_config = config.copy()
    
    # Проверка корректности режима
    mode = validated_config.get("mode", "standard")
    if mode not in ["standard", "minimalist"]:
        validated_config["mode"] = "standard"
    
    # Проверка table_format
    table_format = validated_config.get("table_format", "grid")
    if table_format not in ["grid", "simple", "plain", "fancy"]:
        validated_config["table_format"] = "grid"
    
    # Проверка boolean параметров
    bool_params = ["show_decorative_borders", "show_completion_footer", "include_source_info"]
    for param in bool_params:
        if param in validated_config and not isinstance(validated_config[param], bool):
            validated_config[param] = bool(validated_config[param])
    
    return validated_config
```

## Критерии готовности

### Функциональные критерии
- ✅ Footer "Operation COMPLETED" не выводится в минималистичном режиме
- ✅ SUMMARY строка сохраняется во всех режимах
- ✅ Декоративные рамки удалены в минималистичном режиме
- ✅ Стандартный режим сохраняет footer и рамки

### Технические критерии
- ✅ Конфигурационное управление footer работает корректно
- ✅ Все существующие тесты проходят
- ✅ Валидация конфигурации предотвращает некорректные настройки
- ✅ Производительность не деградирует

### Критерии качества
- ✅ Логи в минималистичном режиме чище и компактнее
- ✅ Важная информация (SUMMARY) сохраняется
- ✅ Переключение между режимами работает без сбоев

## Входные данные

**От Этапа 3**:
- Упрощенные таблицы с minimal ASCII оформлением
- Настроенные разделители между операциями
- Конфигурационная инфраструктура

## Выходные данные

**Для Этапа 5**:
- Полностью минималистичный формат логов
- Готовая система для финального тестирования
- Всесторонняя конфигурация форматирования

## Примеры результата

### До изменений (стандартный режим)
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

### После изменений (минималистичный режим)
```
calculations_data.py:127 "ADD_REACTION" (id=3, 2025-06-17 00:47:51)

   | Step | Sub-operation        | Target    | Result data type | Status | Time, s |
   | ---- | -------------------- | --------- | ---------------- | ------ | ------- |
   | 1    | CHECK_EXPERIMENT_... | file_data | bool             | OK     | 0.001   |

SUMMARY: steps 1, successful 1, with errors 0, total time 0.001 s.


```

## Риски и митигации

**Риск**: Потеря важной информации при удалении footer
- **Митигация**: Анализ содержимого footer для выявления критической информации
- **Решение**: Перенос важных данных в SUMMARY блок

**Риск**: Нарушение обратной совместимости
- **Митигация**: Сохранение полной функциональности стандартного режима
- **Тестирование**: Проверка всех существующих тестов

**Риск**: Некорректная конфигурация
- **Митигация**: Валидация настроек с fallback на безопасные значения
- **Документация**: Четкое описание всех параметров конфигурации

## Результат этапа

После завершения этапа:
1. Footer полностью удален из минималистичного режима
2. SUMMARY блок сохранен как единственный источник итоговой информации
3. Конфигурационная система позволяет гибкое управление поведением footer
4. Готов финальный минималистичный формат для тестирования

**Достигнутая цель**: Значительное упрощение визуального представления логов при сохранении всей критической информации о выполнении операций.
