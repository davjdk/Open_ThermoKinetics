# OperationLogger Stage 3 Migration Guide

## Обзор изменений

Этап 3 рефакторизации OperationLogger завершил переход к упрощенной архитектуре с автоматическим генерированием ASCII таблиц и расширенной обработкой ошибок.

## Ключевые изменения

### 1. Упрощенная архитектура

**До (Stage 2):**
```python
# Старый способ с auto/explicit режимами
logger = OperationLogger(aggregator=aggregator, auto_mode=True)
```

**После (Stage 3):**
```python
# Новый упрощенный explicit-only режим с таблицами
logger = OperationLogger(enable_tables=True, aggregator=aggregator)
```

### 2. Автоматическое генерирование таблиц

**Новая функциональность:**
- ASCII таблицы автоматически генерируются после каждой root операции
- Таблицы включают все метрики, статус, время выполнения и вложенные операции
- Поддержка отключения через `enable_tables=False`

**Пример вывода:**
```
┌─────────────────────────────────────┐
│ ✅ Operation Summary: LOAD_FILE      │
├─────────────────────────────────────┤
│ Metric         │ Value             │
├────────────────┼───────────────────┤
│ Operation      │ LOAD_FILE         │
│ Status         │ SUCCESS           │
│ Duration (s)   │ 0.125             │
│ Sub-operations │ 2                 │
│ Files Modified │ 1                 │
│   file_name    │ experiment.csv    │
│   file_size    │ 2048              │
└─────────────────────────────────────┘
```

### 3. Расширенная обработка ошибок

**Новые возможности:**
```python
# Автоматическая обработка ошибок в контекстном менеджере
with logger.log_operation("RISKY_OPERATION"):
    raise ValueError("Something went wrong")
# Ошибка автоматически захватывается и логируется

# Ручная обработка ошибок
logger.start_operation("MANUAL_OP")
try:
    risky_function()
except Exception as e:
    error_info = {
        "type": type(e).__name__,
        "message": str(e),
        "context": "additional_context"
    }
    logger.end_operation("ERROR", error_info)
```

### 4. Улучшенный OperationContext

**Новые поля:**
```python
@dataclass
class OperationContext:
    # ...существующие поля...
    error_info: Optional[Dict[str, Any]] = None  # Информация об ошибках
    sub_operations_count: int = 0                # Счетчик вложенных операций
    files_modified: int = 0                      # Количество измененных файлов
    
    def add_error_info(self, exc_type, exc_val, exc_tb=None):
        """Добавить информацию об ошибке"""
```

### 5. Улучшенный декоратор

**Новые возможности:**
```python
@logger.operation("PROCESS_DATA")
def process_data(data):
    # Автоматически добавляются метрики:
    # - module: имя модуля функции
    # - class: класс объекта (если применимо)
    # Автоматическая обработка ошибок
    return processed_data
```

## Миграционная карта

### Шаг 1: Обновление создания логгера

**До:**
```python
from src.log_aggregator.operation_logger import OperationLogger

logger = OperationLogger(
    aggregator=aggregator,
    auto_mode=False  # Явно explicit mode
)
```

**После:**
```python
from src.log_aggregator.operation_logger import OperationLogger

logger = OperationLogger(
    enable_tables=True,    # Включить автоматические таблицы
    aggregator=aggregator  # Aggregator автоматически переходит в explicit mode
)
```

### Шаг 2: Обновление обработки ошибок

**До:**
```python
logger.start_operation("OPERATION")
try:
    risky_function()
    logger.end_operation(status="SUCCESS")
except Exception as e:
    logger.add_metric("error", str(e))
    logger.end_operation(status="ERROR")
```

**После:**
```python
# Способ 1: Контекстный менеджер (рекомендуется)
with logger.log_operation("OPERATION"):
    risky_function()  # Ошибки обрабатываются автоматически

# Способ 2: Ручное управление с расширенной информацией об ошибках
logger.start_operation("OPERATION")
try:
    risky_function()
    logger.end_operation("SUCCESS")
except Exception as e:
    error_info = {
        "type": type(e).__name__,
        "message": str(e),
        "traceback": traceback.format_exc()
    }
    logger.end_operation("ERROR", error_info)
```

### Шаг 3: Использование новых возможностей

**Метрики с автоматической компрессией:**
```python
with logger.log_operation("DATA_PROCESSING"):
    # Большие данные автоматически сжимаются
    logger.add_metric("large_dataset", huge_dataframe)
    logger.add_metric("config", large_config_dict)
    
    # Метрики автоматически отображаются в финальной таблице
    logger.add_metric("processing_mode", "advanced")
    logger.add_metric("rows_processed", 10000)
```

**Вложенные операции с счетчиками:**
```python
with logger.log_operation("PARENT_OPERATION"):
    # Эта операция будет засчитана в parent
    with logger.log_operation("CHILD_OPERATION_1"):
        process_part_1()
    
    # И эта тоже
    with logger.log_operation("CHILD_OPERATION_2"):
        process_part_2()
    
    # В финальной таблице parent операции будет показано:
    # Sub-operations: 2
```

### Шаг 4: Интеграция с BaseSlots

**Пример интеграции с существующей архитектурой:**
```python
class FileData(BaseSlots):
    def __init__(self, actor_name: str, signals: BaseSignals):
        super().__init__(actor_name, signals)
        self.operation_logger = OperationLogger(enable_tables=True)
    
    @operation(OperationType.LOAD_FILE)
    def process_request(self, params: dict) -> None:
        """Обработка запроса с автоматическим логированием."""
        operation = params.get("operation")
        
        if operation == OperationType.LOAD_FILE.value:
            self._handle_load_file(params)
    
    def _handle_load_file(self, params: dict):
        """Операция уже обернута декоратором @operation."""
        file_path = params.get("file_path")
        
        # Добавляем метрики
        self.operation_logger.add_metric("file_path", file_path)
        self.operation_logger.add_metric("actor", self.actor_name)
        
        # Вложенные операции
        with self.operation_logger.log_operation("VALIDATE_FILE"):
            self._validate_file(file_path)
        
        with self.operation_logger.log_operation("PARSE_FILE"):
            data = self._parse_file(file_path)
        
        self.operation_logger.add_metric("rows_loaded", len(data))
        # Автоматическая таблица будет сгенерирована при завершении
```

## Совместимость

### Обратная совместимость

Большинство существующего кода будет работать без изменений:

✅ **Сохранено:**
- `start_operation()` / `end_operation()` API
- `add_metric()` функциональность  
- `log_operation()` контекстный менеджер
- `@operation()` декоратор
- Thread-local storage операций
- Интеграция с OperationAggregator и OperationMonitor

🔄 **Изменено (но совместимо):**
- `end_operation()` теперь принимает `status` и `error_info`
- Автоматическое генерирование таблиц для root операций
- Aggregator автоматически переключается в explicit mode

❌ **Удалено:**
- `auto_mode` поддержка в OperationAggregator
- Старые параметры `operation_id` в `end_operation()`

### Примеры миграции реального кода

**Файл: MainWindow operations**
```python
# До
@operation(OperationType.LOAD_FILE)
def _handle_load_file(self, params: dict):
    # операция обрабатывается
    pass

# После (без изменений - все работает)
@operation(OperationType.LOAD_FILE)  
def _handle_load_file(self, params: dict):
    # операция обрабатывается + автоматическая таблица
    pass
```

**Файл: Calculations module**
```python
# До
with operation_logger.log_operation("DECONVOLUTION"):
    result = perform_deconvolution(data)

# После (без изменений + автоматическая таблица)
with operation_logger.log_operation("DECONVOLUTION"):
    result = perform_deconvolution(data)
```

## Преимущества миграции

### 1. Улучшенная видимость операций
- Автоматические ASCII таблицы после каждой операции
- Полная информация о времени выполнения, вложенных операциях и метриках
- Визуальное различение успешных и ошибочных операций

### 2. Упрощенная обработка ошибок
- Автоматический захват исключений в контекстных менеджерах
- Расширенная информация об ошибках с контекстом
- Консистентное логирование ошибок

### 3. Лучшая производительность
- Удаление auto-mode логики
- Упрощенная архитектура с меньшими накладными расходами
- Более эффективная thread-local обработка

### 4. Улучшенная отладка
- Четкие визуальные индикаторы состояния операций
- Счетчики вложенных операций
- Автоматическая компрессия больших данных для читаемости

## Рекомендации

### Для новых проектов
- Используйте `enable_tables=True` по умолчанию
- Предпочитайте контекстные менеджеры для автоматической обработки ошибок
- Используйте декораторы `@operation()` для методов BaseSlots

### Для существующих проектов
- Постепенно мигрируйте к контекстным менеджерам
- Добавьте `enable_tables=True` в конфигурацию логгеров
- Обновите обработку ошибок для использования новых возможностей

### Производительность
- Отключайте таблицы (`enable_tables=False`) в production для высоконагруженных операций
- Настройте компрессию данных через `DataCompressionConfig`
- Используйте thread-local storage для многопоточных приложений

## Заключение

Stage 3 рефакторизации приносит значительные улучшения в удобство использования и отладку OperationLogger, сохраняя при этом полную обратную совместимость с существующим кодом. Автоматические ASCII таблицы и улучшенная обработка ошибок делают систему более прозрачной и удобной для разработчиков.
