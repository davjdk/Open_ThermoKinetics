# Этап 2: Форматирование заголовков

**Время выполнения**: 1-2 часа  
**Приоритет**: Высокий  
**Статус**: К разработке  
**Зависимости**: Этап 1 (Базовая инфраструктура)

## Задачи

### Задача 2.1: Модифицировать _format_operation_header()

**Файл**: `src/core/log_aggregator/table_formatter.py`

**Текущий метод**:
```python
def _format_operation_header(self, operation_log: OperationLog) -> str:
    operation_id = self._get_next_operation_id()
    start_time_str = self._format_timestamp(operation_log.start_time)
    return f'Operation "{operation_log.operation_name}" – STARTED (id={operation_id}, {start_time_str})'
```

**Новый метод с поддержкой минималистичного формата**:
```python
def _format_operation_header(self, operation_log: OperationLog) -> str:
    operation_id = self._get_next_operation_id()
    start_time_str = self._format_timestamp(operation_log.start_time)
    
    # Выбор формата на основе конфигурации
    header_format = self._config.get("header_format", "standard")
    
    if header_format == "source_based" and operation_log.source_module:
        # Минималистичный формат: модуль.py:строка "ОПЕРАЦИЯ" (id=X, timestamp)
        source_info = f"{operation_log.source_module}:{operation_log.source_line}"
        return f'{source_info} "{operation_log.operation_name}" (id={operation_id}, {start_time_str})'
    else:
        # Стандартный формат
        return f'Operation "{operation_log.operation_name}" – STARTED (id={operation_id}, {start_time_str})'
```

**Тестирование**:
- Проверить корректность обоих форматов заголовков
- Протестировать fallback на стандартный формат при отсутствии source info

### Задача 2.2: Реализовать extraction модуля и номера строки

**Файл**: `src/core/log_aggregator/table_formatter.py`

**Вспомогательные методы**:
```python
def _format_source_info(self, operation_log: OperationLog) -> str:
    """Форматирование информации о источнике операции."""
    if not operation_log.source_module or not operation_log.source_line:
        return "unknown:0"
    
    # Сокращение длинных имен модулей если необходимо
    module_name = operation_log.source_module
    if len(module_name) > 25:  # Ограничение для читаемости
        module_name = "..." + module_name[-22:]
    
    return f"{module_name}:{operation_log.source_line}"

def _should_use_minimalist_header(self) -> bool:
    """Определение необходимости использования минималистичного заголовка."""
    return (self._config.get("mode") == "minimalist" or 
            self._config.get("header_format") == "source_based")
```

### Задача 2.3: Тестирование корректности заголовков

**Файл**: `tests/test_log_aggregator/test_header_formatting.py`

**Тестовые сценарии**:
```python
import pytest
from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.table_formatter import OperationTableFormatter

class TestHeaderFormatting:
    
    def test_standard_header_format(self):
        """Тест стандартного формата заголовка."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0  # 2022-01-01 00:00:00
        
        formatter = OperationTableFormatter()
        formatter._config = {"header_format": "standard"}
        
        header = formatter._format_operation_header(operation_log)
        
        assert 'Operation "TEST_OPERATION" – STARTED' in header
        assert "id=" in header
        assert "2022-01-01" in header
    
    def test_minimalist_header_format(self):
        """Тест минималистичного формата заголовка."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        operation_log.source_module = "test_module.py"
        operation_log.source_line = 42
        
        formatter = OperationTableFormatter()
        formatter._config = {"header_format": "source_based"}
        
        header = formatter._format_operation_header(operation_log)
        
        assert header.startswith('test_module.py:42 "TEST_OPERATION"')
        assert "(id=" in header
        assert "2022-01-01" in header
    
    def test_fallback_to_standard_when_no_source_info(self):
        """Тест fallback на стандартный формат при отсутствии source info."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        # source_module и source_line не установлены
        
        formatter = OperationTableFormatter()
        formatter._config = {"header_format": "source_based"}
        
        header = formatter._format_operation_header(operation_log)
        
        # Должен использовать стандартный формат
        assert 'Operation "TEST_OPERATION" – STARTED' in header
    
    def test_long_module_name_truncation(self):
        """Тест сокращения длинных имен модулей."""
        operation_log = OperationLog("TEST_OPERATION")
        operation_log.start_time = 1640995200.0
        operation_log.source_module = "very_long_module_name_that_should_be_truncated.py"
        operation_log.source_line = 100
        
        formatter = OperationTableFormatter()
        formatter._config = {"header_format": "source_based"}
        
        header = formatter._format_operation_header(operation_log)
        
        # Проверяем, что имя модуля сокращено
        assert "..." in header
        assert len(header.split('"')[0]) < 30  # Разумная длина заголовка
```

### Задача 2.4: Интеграция с существующей системой

**Файл**: `src/core/log_aggregator/table_formatter.py`

**Обновление конструктора**:
```python
class OperationTableFormatter:
    def __init__(self, 
                 table_format: str = "grid",
                 max_cell_width: int = 50,
                 config: Optional[Dict] = None):
        self.table_format = table_format
        self.max_cell_width = max_cell_width
        self._operation_counter = 0
        
        # Загрузка конфигурации
        if config is None:
            from .meta_operation_config import META_OPERATION_CONFIG
            self._config = META_OPERATION_CONFIG["formatting"]
        else:
            self._config = config
        
        # Применение минималистичных настроек
        if self._config.get("mode") == "minimalist":
            minimalist_config = META_OPERATION_CONFIG.get("minimalist_settings", {})
            self._config.update(minimalist_config)
```

## Критерии готовности

### Функциональные критерии
- ✅ Заголовки отображаются в формате `модуль.py:строка "ОПЕРАЦИЯ" (id=X, timestamp)` в минималистичном режиме
- ✅ Стандартный формат заголовков сохранен для обратной совместимости
- ✅ Корректно работает fallback для случаев без source info
- ✅ Длинные имена модулей корректно сокращаются

### Технические критерии
- ✅ Конфигурационное переключение между форматами работает
- ✅ Нет нарушения существующей функциональности
- ✅ Performance не деградирует
- ✅ Все unit тесты проходят

### Критерии качества
- ✅ Заголовки читаемы и информативны
- ✅ Формат консистентен во всех операциях
- ✅ Graceful handling edge cases

## Входные данные

**От Этапа 1**:
- Поля `source_module`, `source_line` в `OperationLog`
- Конфигурационные параметры для режимов форматирования
- Система fallback для отсутствующей source info

## Выходные данные

**Для Этапа 3**:
- Готовая система форматирования заголовков
- Конфигурационная инфраструктура для дальнейших изменений
- Тестовые примеры различных форматов

## Примеры результата

### Стандартный заголовок
```
Operation "ADD_REACTION" – STARTED (id=15, 2025-06-17 10:30:45)
```

### Минималистичный заголовок
```
calculations_data.py:127 "ADD_REACTION" (id=15, 2025-06-17 10:30:45)
```

### Заголовок с сокращенным модулем
```
...long_module_name.py:89 "LOAD_FILE" (id=16, 2025-06-17 10:31:12)
```

### Fallback заголовок (нет source info)
```
Operation "UNKNOWN_OPERATION" – STARTED (id=17, 2025-06-17 10:31:30)
```

## Риски и митигации

**Риск**: Неправильное определение source info
- **Митигация**: Тщательное тестирование с различными сценариями вызовов
- **Fallback**: Автоматическое переключение на стандартный формат

**Риск**: Слишком длинные заголовки
- **Митигация**: Интеллектуальное сокращение имен модулей
- **Ограничение**: Максимальная длина заголовка 80 символов

**Риск**: Конфликт форматов при обновлении
- **Митигация**: Четкое версионирование конфигурации
- **Совместимость**: Поддержка старых форматов конфигурации

## Результат этапа

После завершения этапа:
1. Система поддерживает два формата заголовков (стандартный и минималистичный)
2. Заголовки содержат точную информацию о местоположении операций в коде
3. Готова основа для дальнейшего упрощения форматирования таблиц
