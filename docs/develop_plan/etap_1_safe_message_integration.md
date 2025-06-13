# Этап 1: Интеграция безопасного получения сообщений

## Цель этапа
Устранить основную причину ошибок форматирования в системе логирования путем внедрения безопасного получения сообщений (`safe_get_message`) во всех критических местах агрегатора.

## Проблемы для решения
- **Error in AggregatingHandler.emit**: TypeError при форматировании в `ValueAggregator.process_message()`
- **Error processing buffer**: TypeError при анализе паттернов в `PatternDetector.detect_patterns()`
- **Error in immediate error expansion**: TypeError при расширении ошибок в `ErrorExpansionEngine.expand_error()`

## Технические изменения

### 1. ValueAggregator (`src/log_aggregator/value_aggregator.py`)
**Файл**: `src/log_aggregator/value_aggregator.py`
**Метод**: `process_message()`

**Изменения**:
- Заменить прямой вызов `record.record.getMessage()` на `safe_get_message(record.record)`
- Добавить импорт `from .safe_message_utils import safe_get_message`
- Обеспечить обработку случаев, когда `getMessage()` возвращает нестроковые объекты

**Детали**:
```python
# До:
message = record.record.getMessage()

# После:
from .safe_message_utils import safe_get_message
message = safe_get_message(record.record)
```

### 2. PatternDetector (`src/log_aggregator/pattern_detector.py`)
**Файл**: `src/log_aggregator/pattern_detector.py`
**Методы**: `_group_by_basic_criteria()`, `_detect_patterns_in_group()`, `_create_pattern()`

**Изменения**:
- Заменить все вызовы `buffered_record.record.getMessage()` на `safe_get_message(buffered_record.record)`
- Добавить импорт `from .safe_message_utils import safe_get_message`
- Особое внимание к циклам сравнения сообщений и создания шаблонов паттернов

**Детали**:
```python
# До:
current_message = current_record.record.getMessage()
other_message = other_record.record.getMessage()

# После:
from .safe_message_utils import safe_get_message
current_message = safe_get_message(current_record.record)
other_message = safe_get_message(other_record.record)
```

### 3. ErrorExpansionEngine (`src/log_aggregator/error_expansion.py`)
**Файл**: `src/log_aggregator/error_expansion.py`
**Методы**: `_analyze_error_context()`, `_generate_expanded_message()`

**Изменения**:
- Заменить `error_record.record.getMessage()` на `safe_get_message(error_record.record)`
- Добавить импорт `from .safe_message_utils import safe_get_message`
- Обеспечить безопасность при извлечении ключевых слов и классификации ошибок

**Детали**:
```python
# До:
error_message = error_record.record.getMessage().lower()

# После:
from .safe_message_utils import safe_get_message
error_message = safe_get_message(error_record.record).lower()
```

### 4. AggregationEngine (`src/log_aggregator/aggregation_engine.py`)
**Файл**: `src/log_aggregator/aggregation_engine.py`
**Метод**: создание `sample_messages` для агрегированных записей

**Изменения**:
- Заменить прямые вызовы `record.record.getMessage()` на `safe_get_message(record.record)`
- Добавить импорт `from .safe_message_utils import safe_get_message`

**Детали**:
```python
# До:
for record in pattern.records[:3]:
    message = record.record.getMessage()

# После:
from .safe_message_utils import safe_get_message
for record in pattern.records[:3]:
    message = safe_get_message(record.record)
```

## Улучшения в safe_message_utils.py

### Дополнительные функции
1. **safe_get_raw_message()** - для получения необработанной строки без форматирования
2. **Улучшенная обработка ошибок** - дополнительные проверки типов
3. **Fallback механизмы** - более надежные стратегии восстановления

## Тестирование

### Тестовые сценарии
1. **Сообщения с неправильным форматированием**:
   ```python
   logger.error("Test error %d %s", 42)  # недостаточно аргументов
   logger.info("Value: %d", "text")      # неправильный тип
   logger.warning("Format %s", 1, 2)     # лишний аргумент
   ```

2. **Большие сложные объекты** - убедиться в корректной работе ValueAggregator
3. **Граничные случаи** - нестроковые объекты в LogRecord.msg

### Критерии успеха
- ✅ Отсутствие исключений TypeError в агрегаторе
- ✅ Корректная обработка проблемных сообщений
- ✅ Сохранение функциональности компрессии значений
- ✅ Работоспособность детектирования паттернов
- ✅ Функциональность расширения ошибок

## Результат этапа
По завершении этапа 1:
- Система логирования устойчива к ошибкам форматирования сообщений
- Все компоненты агрегатора используют безопасное получение сообщений
- Агрегатор не падает на "кривых" логах
- Основная причина каскада ошибок устранена

## Pull Request
**Название**: `feat: Integrate safe message handling across log aggregator components`

**Описание**:
- Интегрирует `safe_get_message` во все критические компоненты агрегатора
- Устраняет TypeError при обработке некорректно форматированных сообщений
- Повышает стабильность системы логирования
- Сохраняет полную функциональность агрегации

**Файлы для изменения**:
- `src/log_aggregator/value_aggregator.py`
- `src/log_aggregator/pattern_detector.py` 
- `src/log_aggregator/error_expansion.py`
- `src/log_aggregator/aggregation_engine.py`
- `src/log_aggregator/safe_message_utils.py` (улучшения)

**Тесты для добавления**:
- Тесты с некорректным форматированием
- Граничные случаи с нестроковыми объектами
- Интеграционные тесты компонентов агрегатора
