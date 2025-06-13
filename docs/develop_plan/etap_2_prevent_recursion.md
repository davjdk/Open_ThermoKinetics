# Этап 2: Предотвращение рекурсивной обработки внутренних логов

## Цель этапа
Устранить рекурсивное наложение ошибок агрегатора, когда внутренние сообщения агрегатора повторно обрабатываются тем же агрегатором, создавая каскад ошибок.

## Проблемы для решения
- **Рекурсивное самопожирание**: агрегатор обрабатывает собственные сообщения об ошибках
- **Лавинообразный рост сообщений**: каждая внутренняя ошибка провоцирует следующую
- **Дублирование анализа**: повторный анализ уже внутренних ошибок агрегатора

## Наблюдаемые проблемы в логах
- Дублирование сообщений `"Expanded error: Error in immediate error expansion..."`
- Цепочка: ошибка обработки буфера → ошибка расширения ошибки → ошибка emit
- Агрегатор анализирует собственные ошибки как внешние

## Технические решения

### 1. Фильтрация в AggregatingHandler.emit()
**Файл**: `src/log_aggregator/realtime_handler.py`
**Метод**: `emit()`

**Основное решение** - проверка имени логгера:
```python
def emit(self, record: logging.LogRecord) -> None:
    """Process a log record with aggregation."""
    # Skip internal log_aggregator messages to prevent recursion
    if record.name.startswith("log_aggregator"):
        self._forward_to_target(record)
        return
    
    # Existing aggregation logic...
```

**Преимущества**:
- Простота реализации
- Немедленное решение проблемы рекурсии
- Сохранение внутренних логов для отладки

### 2. Альтернативное решение: настройка propagate=False
**Файл**: `src/core/logger_config.py`
**Класс**: `LoggerManager`

**Изменения в конфигурации логгеров**:
```python
def configure_logging(cls, ...):
    # Настройка внутренних логгеров без пропагирования
    internal_loggers = [
        "log_aggregator.realtime_handler",
        "log_aggregator.pattern_detector", 
        "log_aggregator.error_expansion",
        "log_aggregator.value_aggregator",
        "log_aggregator.operation_aggregator"
    ]
    
    for logger_name in internal_loggers:
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.addHandler(file_handler)  # Только в основной файл
```

**Преимущества**:
- Четкое разделение внутренних и внешних логов
- Внутренние логи идут только в debug-файл
- Полная изоляция логгеров агрегатора

### 3. Рекомендуемый гибридный подход

**Реализация**:
1. **Проверка в emit()** - как первая линия защиты
2. **Конфигурация propagate=False** - для долгосрочного решения  
3. **Отдельный debug-файл** - для внутренних логов агрегатора

**Структура файлов логов**:
- `logs/solid_state_kinetics.log` - ВСЕ логи приложения + внутренние логи агрегатора
- `logs/aggregated.log` - ТОЛЬКО агрегированные логи для пользователя
- `logs/debug_aggregator.log` - ТОЛЬКО внутренние логи агрегатора (новый файл)

## Дополнительные улучшения

### 1. Улучшенная обработка fallback в emit()
**Файл**: `src/log_aggregator/realtime_handler.py`

**Улучшение fallback-поведения**:
```python
except Exception as e:
    # Безопасная обработка проблемной записи
    try:
        from .safe_message_utils import safe_get_message
        safe_msg = safe_get_message(record)
        record.msg = f"[UNFORMATTED] {safe_msg}"
        record.args = ()
    except Exception:
        record.msg = f"[FORMATTING_ERROR] {record.msg}"
        record.args = ()
    
    self._logger.error(f"Error in AggregatingHandler.emit: {e}")
    self._forward_to_target(record)
```

### 2. Счетчик внутренних ошибок
**Мониторинг сбоев агрегатора**:
```python
class AggregatingHandler:
    def __init__(self, ...):
        self._internal_error_count = 0
        self._max_internal_errors = 10
        self._error_reset_interval = 300  # 5 минут
        self._last_error_reset = time.time()
    
    def _handle_internal_error(self, error: Exception):
        current_time = time.time()
        
        # Сброс счетчика ошибок
        if current_time - self._last_error_reset > self._error_reset_interval:
            self._internal_error_count = 0
            self._last_error_reset = current_time
        
        self._internal_error_count += 1
        
        # Деградация при превышении порога
        if self._internal_error_count >= self._max_internal_errors:
            self._logger.warning(
                f"Too many internal errors ({self._internal_error_count}). "
                "Disabling advanced aggregation features."
            )
            self.toggle_error_expansion(False)
            self.toggle_value_aggregation(False)
```

## Конфигурационные изменения

### 1. Новый debug-файл для агрегатора
**Добавление в LoggerManager**:
```python
def _setup_debug_aggregator_logging(cls):
    """Setup separate debug logging for aggregator internals."""
    debug_handler = RotatingFileHandler(
        "logs/debug_aggregator.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    debug_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    debug_handler.setFormatter(debug_formatter)
    
    # Настройка внутренних логгеров
    internal_loggers = ["log_aggregator.realtime_handler", ...]
    for logger_name in internal_loggers:
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.addHandler(debug_handler)
        logger.setLevel(logging.DEBUG)
```

### 2. Обновление AggregationConfig
**Добавление параметров мониторинга**:
```python
@dataclass
class AggregationConfig:
    # Existing fields...
    
    # Новые параметры для предотвращения рекурсии
    prevent_internal_recursion: bool = True
    max_internal_errors: int = 10
    error_reset_interval: int = 300
    separate_debug_logging: bool = True
```

## Тестирование

### Тестовые сценарии
1. **Искусственные ошибки форматирования** - проверка отсутствия каскада
2. **Множественные внутренние ошибки** - проверка деградации
3. **Восстановление после ошибок** - проверка сброса счетчика
4. **Изоляция логгеров** - проверка отсутствия пропагирования

### Критерии успеха
- ✅ Отсутствие рекурсивных цепочек ошибок
- ✅ Внутренние логи не обрабатываются агрегатором
- ✅ Деградация при превышении порога ошибок
- ✅ Чистые агрегированные логи без debug-спама
- ✅ Восстановление функциональности после снижения ошибок

## Результат этапа
По завершении этапа 2:
- Агрегатор не обрабатывает собственные логи
- Каскады внутренних ошибок устранены
- Внутренние логи изолированы в отдельный файл
- Система способна к самовосстановлению при сбоях
- Четкое разделение пользовательских и отладочных логов

## Pull Request
**Название**: `feat: Prevent recursive processing of internal aggregator logs`

**Описание**:
- Добавляет проверку имени логгера в `emit()` для предотвращения рекурсии
- Настраивает `propagate=False` для внутренних логгеров агрегатора
- Создает отдельный debug-файл для внутренних логов
- Добавляет механизм деградации при превышении порога ошибок
- Улучшает fallback-поведение при обработке проблемных записей

**Файлы для изменения**:
- `src/log_aggregator/realtime_handler.py`
- `src/core/logger_config.py`
- `src/log_aggregator/config.py`

**Новые файлы**:
- `logs/debug_aggregator.log` (создается автоматически)

**Тесты для добавления**:
- Тесты предотвращения рекурсии
- Тесты изоляции логгеров
- Тесты деградации при ошибках
- Интеграционные тесты конфигурации
