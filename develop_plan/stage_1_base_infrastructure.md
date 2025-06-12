# Этап 1: Базовая инфраструктура модуля агрегации логов

**Место в общем плане:** Первый этап из 5. Создание основной архитектуры и базовых компонентов без расширенных функций.

## Цель этапа
Создать базовую инфраструктуру модуля агрегации логов с основными компонентами: 
- Структура каталогов и модулей
- Базовый AggregatingHandler 
- BufferManager для управления буферами
- PatternDetector для обнаружения паттернов
- AggregationEngine для базовой агрегации
- Базовые конфигурационные компоненты

## Создаваемые файлы

### 1. Структура модуля
```
src/log_aggregator/
├── __init__.py
├── realtime_handler.py     # Базовый AggregatingHandler
├── buffer_manager.py       # Управление буферами в памяти  
├── pattern_detector.py     # Детекция базовых паттернов
├── aggregation_engine.py   # Базовый движок агрегации
└── config.py              # Базовая конфигурация
```

### 2. Базовые тесты
```
tests/test_log_aggregator/
├── __init__.py
├── test_realtime_handler.py
├── test_buffer_manager.py
├── test_pattern_detector.py
├── test_aggregation_engine.py
└── test_config.py
```

## Функциональность этапа

### AggregatingHandler (realtime_handler.py)
- Базовая интеграция с LoggerManager
- Простая буферизация записей
- Проброс записей к target_handler
- Базовая статистика (total_records, buffer_flushes)
- **БЕЗ** ErrorExpansionEngine и TabularFormatter

### BufferManager (buffer_manager.py)  
- Управление буфером в памяти с максимальным размером
- Временные окна для сброса буфера
- Базовые методы: add_record, get_records_for_processing, should_process

### PatternDetector (pattern_detector.py)
- Обнаружение простых паттернов:
  - Повторяющиеся сообщения
  - Временные кластеры
  - Сообщения из одного файла/модуля
- **БЕЗ** расширенных типов паттернов и метаданных

### AggregationEngine (aggregation_engine.py)
- Простая агрегация записей в группы
- Создание базовых AggregatedLogRecord
- Базовая статистика агрегации

### Config (config.py)
- Базовый AggregationConfig класс
- Основные параметры: buffer_size, flush_interval, min_pattern_entries
- **БЕЗ** ErrorExpansionConfig и TabularFormattingConfig

## Интеграция с LoggerManager

### Минимальные изменения в logger_config.py
```python
@classmethod
def configure_logging(
    cls,
    # ...existing parameters...
    enable_aggregation: bool = False,
    aggregation_config: Optional[dict] = None
) -> None:
    # Existing code...
    
    if enable_aggregation:
        cls._setup_basic_aggregation(root_logger, aggregation_config or {})
```

## Критерии готовности этапа
- [ ] Все базовые модули созданы и работают
- [ ] Тесты покрывают основную функциональность (>80%)  
- [ ] AggregatingHandler корректно интегрируется с LoggerManager
- [ ] Базовая агрегация работает без ошибок
- [ ] Статистика собирается и отображается
- [ ] Можно включить/выключить агрегацию через конфигурацию
- [ ] Производительность не деградирует при отключенной агрегации

## Ограничения этапа
- Нет детального анализа ошибок
- Нет табличного форматирования 
- Нет расширенных типов паттернов
- Простая конфигурация без пресетов
- Минимальная статистика

## Следующий этап
Этап 2: Расширенная детекция паттернов - добавление сложных паттернов с метаданными для подготовки к табличному форматированию.
