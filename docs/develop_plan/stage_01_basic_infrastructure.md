# Этап 1: Базовая инфраструктура

**Время выполнения**: 2-3 часа  
**Приоритет**: Высокий  
**Статус**: К разработке  

## Задачи

### Задача 1.1: Добавить новые поля в OperationLog

**Файл**: `src/core/log_aggregator/operation_log.py`

**Изменения**:
```python
@dataclass
class OperationLog:
    operation_name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: str = "running"
    execution_time: Optional[float] = None
    exception_info: Optional[str] = None
    sub_operations: List[SubOperationLog] = field(default_factory=list)
    # Новые поля
    source_module: Optional[str] = None      # Имя модуля
    source_line: Optional[int] = None        # Номер строки
    caller_info: Optional[str] = None        # Дополнительная информация о вызывающем коде
```

**Тестирование**:
- Проверить, что новые поля корректно инициализируются
- Убедиться в обратной совместимости с существующим кодом

### Задача 1.2: Реализовать захват информации о вызывающем коде

**Файл**: `src/core/log_aggregator/operation_logger.py`

**Новый метод**:
```python
import inspect
import traceback
from pathlib import Path

class OperationLogger:
    def __init__(self, operation_name: str):
        self.operation_log = OperationLog(operation_name)
        self._capture_caller_info()  # Новый метод
    
    def _capture_caller_info(self):
        """Захват информации о вызывающем коде."""
        frame = inspect.currentframe()
        try:
            # Поднимаемся по стеку до декорированной функции
            for _ in range(3):  # @operation -> wrapper -> __init__
                frame = frame.f_back
                if frame is None:
                    break
            
            if frame:
                filename = frame.f_code.co_filename
                line_number = frame.f_lineno
                module_name = Path(filename).name
                
                self.operation_log.source_module = module_name
                self.operation_log.source_line = line_number
                
                # Дополнительная информация о контексте
                function_name = frame.f_code.co_name
                self.operation_log.caller_info = f"{module_name}:{line_number} in {function_name}()"
                
        except Exception as e:
            # Graceful fallback - не должно прерывать основную операцию
            self.operation_log.source_module = "unknown"
            self.operation_log.source_line = 0
            self.operation_log.caller_info = f"capture_failed: {str(e)}"
        finally:
            del frame
```

**Тестирование**:
- Проверить корректность захвата модуля и номера строки
- Протестировать fallback поведение при ошибках
- Убедиться в отсутствии memory leaks

### Задача 1.3: Добавить конфигурационные параметры

**Файл**: `src/core/log_aggregator/meta_operation_config.py`

**Новые параметры конфигурации**:
```python
META_OPERATION_CONFIG = {
    "enabled": True,
    "formatting": {
        "mode": "standard",  # "standard" или "minimalist"
        "table_format": "grid",  # "grid" или "simple" 
        "show_decorative_borders": True,  # Показывать рамки
        "show_completion_footer": True,   # Показывать footer
        "table_separator": "\n\n",        # Разделитель между таблицами
        "include_source_info": True,      # Включать информацию о модуле
        "header_format": "standard"       # "standard" или "minimalist"
    },
    "minimalist_settings": {
        "table_format": "simple",
        "show_decorative_borders": False,
        "show_completion_footer": False, 
        "header_format": "source_based"   # модуль:строка формат
    },
    # ...existing config...
}
```

**Файл**: `src/core/log_aggregator/aggregated_operation_logger.py`

**Интеграция конфигурации**:
```python
class AggregatedOperationLogger:
    def __init__(self):
        self._config = META_OPERATION_CONFIG["formatting"]
        self._minimalist_mode = self._config.get("mode") == "minimalist"
        
        # Применение настроек минималистичного режима
        if self._minimalist_mode:
            minimalist_config = META_OPERATION_CONFIG["minimalist_settings"]
            self._config.update(minimalist_config)
```

## Критерии готовности

### Функциональные критерии
- ✅ Новые поля `source_module`, `source_line`, `caller_info` добавлены в `OperationLog`
- ✅ Метод `_capture_caller_info()` корректно извлекает информацию о вызывающем коде
- ✅ Конфигурационные параметры позволяют переключение между режимами
- ✅ Fallback механизм работает при ошибках захвата caller info

### Технические критерии
- ✅ Обратная совместимость сохранена
- ✅ Нет деградации производительности
- ✅ Memory leaks отсутствуют
- ✅ Exception handling не влияет на основную функциональность

### Критерии тестирования
- ✅ Unit тесты для новых полей `OperationLog`
- ✅ Тесты захвата caller info в различных сценариях
- ✅ Тесты конфигурационных переключений
- ✅ Performance тесты с включенным inspect

## Зависимости

- **Входящие**: Нет
- **Исходящие**: Этап 2 (использует новые поля для форматирования заголовков)

## Риски и митигации

**Риск**: Неточность захвата caller info
- **Митигация**: Использование inspect.stack() с подробным анализом фреймов
- **Fallback**: Установка значений по умолчанию при ошибках

**Риск**: Производительность inspect операций  
- **Митигация**: Кэширование результатов, ленивые вычисления
- **Измерение**: Benchmark тесты до и после изменений

## Результат этапа

После завершения этапа:
1. Система сможет захватывать точную информацию о местоположении операций в коде
2. Конфигурация поддержит переключение между стандартным и минималистичным режимами
3. Основа для последующих этапов форматирования будет готова
