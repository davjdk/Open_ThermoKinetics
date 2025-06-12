# Этап 4: ErrorExpansionEngine - детальный анализ ошибок

**Место в общем плане:** Четвертый этап из 5. Добавление ErrorExpansionEngine для автоматического расширения контекста ошибок с детальным анализом и рекомендациями.

## Цель этапа
Создать ErrorExpansionEngine для немедленной обработки критических ошибок (WARNING/ERROR/CRITICAL) с расширенным контекстом, анализом предшествующих операций и генерацией рекомендаций.

## Создаваемые файлы

### ErrorExpansionEngine (error_expansion.py)
- Основной класс для анализа ошибок
- ErrorContext dataclass для структурированного контекста
- Классификация типов ошибок
- Генерация рекомендаций по устранению
- Анализ предшествующих операций

### Обновление конфигурации (config.py)
```python
@dataclass
class ErrorExpansionConfig:
    enabled: bool = True
    context_lines: int = 5
    trace_depth: int = 10
    immediate_expansion: bool = True
    save_context: bool = True
    error_threshold_level: str = "WARNING"
```

## Новая функциональность

### ErrorContext структура
```python
@dataclass
class ErrorContext:
    error_record: LogRecord
    preceding_records: List[LogRecord]
    following_records: List[LogRecord]
    related_operations: List[LogRecord]
    error_trace: Optional[str] = None
    suggested_actions: List[str] = None
```

### Типы ошибок и паттерны
```python
self.error_patterns = {
    'file_not_found': {
        'keywords': ['file not found', 'no such file', 'cannot open'],
        'context_keywords': ['loading', 'opening', 'reading'],
        'suggestions': [
            'Проверьте существование файла',
            'Убедитесь в правильности пути', 
            'Проверьте права доступа'
        ]
    },
    'memory_error': {
        'keywords': ['memory error', 'out of memory', 'allocation failed'],
        'suggestions': [
            'Уменьшите размер обрабатываемых данных',
            'Закройте неиспользуемые приложения',
            'Проверьте доступную память'
        ]
    },
    'gui_error': {
        'keywords': ['widget', 'window', 'display', 'render'],
        'suggestions': [
            'Перезапустите GUI компонент',
            'Проверьте состояние окна',
            'Обновите отображение'
        ]
    },
    'calculation_error': {
        'keywords': ['division by zero', 'invalid value', 'nan', 'inf'],
        'suggestions': [
            'Проверьте входные данные',
            'Убедитесь в корректности параметров',
            'Проверьте граничные условия'
        ]
    }
}
```

## Основные методы

### Анализ ошибок
- `expand_error()` - главный метод расширения ошибки
- `_analyze_error_context()` - анализ контекста ошибки
- `_classify_error()` - классификация типа ошибки
- `_generate_suggestions()` - генерация рекомендаций

### Контекстный анализ  
- `_find_preceding_context()` - поиск предшествующих записей
- `_find_related_operations()` - поиск связанных операций
- `_extract_error_trace()` - извлечение трассировки
- `_extract_keywords()` - извлечение ключевых слов

### Форматирование вывода
- `_generate_expanded_message()` - создание расширенного сообщения
- `_create_expanded_record()` - создание LogRecord с контекстом

## Примеры расширенного вывода

### Пример детального анализа ошибки файла
```
================================================================================
🚨 DETAILED ERROR ANALYSIS - ERROR
================================================================================
📍 Location: data_loader.py:45
⏰ Time: 2024-01-15 10:30:46
💬 Message: Failed to load data file: /path/to/data.csv

📋 PRECEDING CONTEXT:
----------------------------------------
  1. [INFO] Setting up plot window (0.2s ago)
  2. [INFO] Initializing GUI components (1.0s ago)
  3. [INFO] Loading configuration file... (1.1s ago)

🔗 RELATED OPERATIONS:
----------------------------------------
  1. [INFO] data_loader.py:23 - Opening file dialog
  2. [INFO] data_loader.py:35 - User selected file: /path/to/data.csv

💡 SUGGESTED ACTIONS:
----------------------------------------
  1. Проверьте существование файла
  2. Убедитесь в правильности пути
  3. Проверьте права доступа
  4. Проверьте код в файле data_loader.py:45

================================================================================
```

### Пример анализа ошибки памяти
```
================================================================================
🚨 DETAILED ERROR ANALYSIS - ERROR  
================================================================================
📍 Location: calculation_engine.py:128
⏰ Time: 2024-01-15 14:22:15
💬 Message: Memory allocation failed during matrix calculation

📋 PRECEDING CONTEXT:
----------------------------------------
  1. [INFO] Processing large dataset (2.1s ago)
  2. [INFO] Allocating calculation buffers (1.8s ago)
  3. [INFO] Starting matrix operations (0.5s ago)

🔗 RELATED OPERATIONS:
----------------------------------------
  1. [INFO] calculation_engine.py:115 - Loading 1000x1000 matrix
  2. [INFO] calculation_engine.py:120 - Allocating result buffer

📊 ERROR TRACE:
----------------------------------------
[14:22:13] Matrix size: 1000000 elements
[14:22:14] Available memory: 512MB
[14:22:15] Requested allocation: 800MB

💡 SUGGESTED ACTIONS:
----------------------------------------
  1. Уменьшите размер обрабатываемых данных
  2. Закройте неиспользуемые приложения  
  3. Проверьте доступную память
  4. Проверьте код в файле calculation_engine.py:128

================================================================================
```

## Примеры из проекта

### Операции с данными реакций
```
2025-06-12 12:53:55 - DEBUG - calculation_data_operations.py:52 - Processing operation 'OperationType.UPDATE_VALUE' with path_keys: ['NH4_rate_3.csv', 'reaction_0', 'upper_bound_coeffs', 'z']
2025-06-12 12:53:55 - DEBUG - calculation_data_operations.py:317 - Data at ['NH4_rate_3.csv', 'reaction_0', 'upper_bound_coeffs', 'z'] updated to 307.0422075156969.
2025-06-12 12:53:55 - DEBUG - calculation_data_operations.py:52 - Processing operation 'OperationType.UPDATE_VALUE' with path_keys: ['NH4_rate_3.csv', 'reaction_0', 'lower_bound_coeffs', 'z']
```

### Обработка запросов с операциями файлов
```
2025-06-12 12:53:47 - DEBUG - file_data.py:221 - file_data processing request 'OperationType.TO_A_T' from 'main_window'
2025-06-12 12:53:47 - INFO - file_data.py:210 - Data has been successfully modified.
2025-06-12 12:53:47 - DEBUG - file_data.py:221 - file_data processing request 'OperationType.GET_DF_DATA' from 'main_window'
```

### Предупреждения при обработке операций
```
2025-06-12 12:53:32 - WARNING - file_operations.py:25 - active_file_operations received unknown operation 'OperationType.TO_DTG'
2025-06-12 12:53:52 - WARNING - calculation_data_operations.py:181 - Data already exists at path: ['NH4_rate_3.csv', 'reaction_0'] - overwriting not performed.
```

## Интеграция с AggregatingHandler

### Немедленная обработка ошибок
```python
def emit(self, record: logging.LogRecord) -> None:
    if not self.enabled:
        self.target_handler.emit(record)
        return
    
    try:
        with self._lock:
            log_record = self._convert_record(record)
            
            # Проверка на ошибку для немедленной обработки
            if self._is_error_record(log_record) and self.enable_error_expansion:
                self._handle_error_immediately(log_record)
                return
            
            # Обычная обработка...
```

### Методы управления ошибками
```python
def _is_error_record(self, record: LogRecord) -> bool:
    """Проверка является ли запись ошибкой"""
    return record.level in ['WARNING', 'ERROR', 'CRITICAL']

def _handle_error_immediately(self, record: LogRecord) -> None:
    """Немедленная обработка ошибки с расширенным контекстом"""
    expanded_record = self.error_expansion_engine.expand_error(
        record, 
        self.buffer_manager.get_recent_context()
    )
    self.target_handler.emit(expanded_record)
    self.stats['errors_expanded'] += 1

def toggle_error_expansion(self, enabled: bool) -> None:
    """Включение/выключение детализации ошибок"""
    self.enable_error_expansion = enabled
```

## Обновление BufferManager

### Метод получения контекста
```python
def get_recent_context(self, max_records: int = 20) -> List[LogRecord]:
    """Получение недавних записей для контекста ошибки"""
    with self._lock:
        # Возврат последних записей для анализа контекста
        return list(self.context_buffer)[-max_records:]
```

### Контекстный буфер
```python
def __init__(self, max_size: int = 1000, flush_interval: float = 2.0):
    # Existing code...
    self.context_buffer: deque[LogRecord] = deque(maxlen=50)  # Для контекста ошибок

def add_record(self, record: LogRecord) -> None:
    # Existing code...
    self.context_buffer.append(record)  # Сохранение для контекста
```

## Тестирование

### test_error_expansion.py
- Тесты расширения ошибок с контекстом
- Проверка классификации типов ошибок  
- Тесты генерации рекомендаций
- Валидация ErrorContext структур
- Тесты извлечения трассировки

### test_integration_errors.py
- Интеграционные тесты с AggregatingHandler
- Тесты немедленной обработки ошибок
- Проверка включения/выключения анализа ошибок
- Тесты производительности при большом количестве ошибок

## Критерии готовности этапа
- [ ] ErrorExpansionEngine создан и работает
- [ ] Все 4 типа ошибок классифицируются корректно
- [ ] Контекстный анализ работает с предшествующими операциями
- [ ] Рекомендации генерируются для каждого типа ошибки
- [ ] Немедленная обработка ошибок интегрирована в AggregatingHandler
- [ ] BufferManager поддерживает контекстный буфер
- [ ] Тесты покрывают функциональность (>85%)
- [ ] Можно включать/выключать анализ ошибок в runtime
- [ ] Производительность остается приемлемой

## Ограничения этапа
- Базовая классификация ошибок (без ML/NLP)
- Фиксированный набор типов ошибок
- Простые правила извлечения контекста

## Следующий этап
Этап 5: Полная интеграция и расширенная конфигурация - объединение всех компонентов с продвинутыми настройками и пресетами.
