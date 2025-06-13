# Этап 3: Улучшение конфигурации и оптимизация производительности

## Цель этапа
Оптимизировать конфигурационные параметры агрегатора, устранить избыточность и повысить производительность системы логирования.

## Проблемы для решения
- **Избыточные debug-сообщения** в продуктивной среде
- **Дублирование статистики** от нескольких AggregatingHandler'ов
- **Неоптимальные пороги** для расширения ошибок
- **Отсутствие адаптивности** в зависимости от режима работы

## Конфигурационные улучшения

### 1. Оптимизация ErrorExpansionConfig
**Файл**: `src/log_aggregator/config.py`

**Изменение порогов**:
```python
@dataclass 
class ErrorExpansionConfig:
    # Повышение порога с WARNING до ERROR
    error_threshold_level: str = "ERROR"  # Было: "WARNING"
    
    # Оптимизация временных окон
    context_time_window: float = 5.0     # Было: 10.0
    context_lines: int = 3               # Было: 5
    
    # Адаптивное поведение
    adaptive_threshold: bool = True
    disable_on_high_load: bool = True
    max_expansions_per_minute: int = 10
```

**Обоснование**:
- Снижение нагрузки от WARNING-сообщений
- Фокус на критических ошибках
- Предотвращение перегрузки при высокой активности

### 2. Устранение дублирования статистики
**Файл**: `src/log_aggregator/realtime_handler.py`

**Централизованная статистика**:
```python
class AggregatingHandler:
    _statistics_handler = None  # Класс-переменная
    
    def __init__(self, target_handler, config, handler_id: str = None):
        self.handler_id = handler_id or f"handler_{id(self)}"
        
        # Только файловый handler логирует статистику
        self.should_log_statistics = handler_id == "file_handler"
    
    def _log_processing_statistics(self, processed_count: int, patterns_count: int):
        if not self.should_log_statistics:
            return  # Консольный handler не логирует статистику
            
        # Existing statistics logging...
```

### 3. Режимы работы агрегатора
**Файл**: `src/log_aggregator/config.py`

**Новые пресеты конфигурации**:
```python
class AggregationPresets:
    """Predefined configuration presets for different scenarios."""
    
    @staticmethod
    def production() -> AggregationConfig:
        """Production preset - minimal overhead, critical errors only."""
        return AggregationConfig(
            buffer_size=50,
            flush_interval=10.0,
            pattern_similarity_threshold=0.9,
            min_pattern_entries=3,
            
            error_expansion=ErrorExpansionConfig(
                error_threshold_level="ERROR",
                context_lines=3,
                immediate_expansion=False,  # Batch processing
                disable_on_high_load=True
            ),
            
            value_aggregation=ValueAggregationConfig(
                array_threshold=20,     # Более высокие пороги
                string_threshold=500,
                cache_size_limit=50
            ),
            
            tabular_formatting=TabularFormattingConfig(
                max_table_width=120,
                enabled_tables=["request_response_cycle", "operation_cascade"]
            )
        )
    
    @staticmethod
    def development() -> AggregationConfig:
        """Development preset - detailed logging, lower thresholds."""
        return AggregationConfig(
            buffer_size=100,
            flush_interval=3.0,
            pattern_similarity_threshold=0.7,
            
            error_expansion=ErrorExpansionConfig(
                error_threshold_level="WARNING",
                context_lines=5,
                immediate_expansion=True
            ),
            
            # Полная функциональность для отладки
            tabular_formatting=TabularFormattingConfig(enabled=True),
            operation_aggregation=OperationAggregationConfig(enabled=True),
            value_aggregation=ValueAggregationConfig(enabled=True)
        )
    
    @staticmethod
    def minimal() -> AggregationConfig:
        """Minimal preset - basic aggregation only."""
        return AggregationConfig(
            buffer_size=30,
            flush_interval=15.0,
            
            error_expansion=ErrorExpansionConfig(enabled=False),
            tabular_formatting=TabularFormattingConfig(enabled=False),
            operation_aggregation=OperationAggregationConfig(enabled=False),
            value_aggregation=ValueAggregationConfig(enabled=False)
        )
```

### 4. Адаптивное управление нагрузкой
**Файл**: `src/log_aggregator/realtime_handler.py`

**Мониторинг производительности**:
```python
@dataclass
class PerformanceMetrics:
    """Performance metrics for adaptive behavior."""
    
    records_per_second: float = 0.0
    processing_time_avg: float = 0.0
    error_expansion_time_avg: float = 0.0
    high_load_threshold: float = 100.0  # records/second
    
class AggregatingHandler:
    def __init__(self, ...):
        self.performance_metrics = PerformanceMetrics()
        self._performance_window = []  # Скользящее окно
        self._last_performance_check = time.time()
    
    def _update_performance_metrics(self, processing_time: float):
        """Update performance metrics and adapt behavior."""
        current_time = time.time()
        
        # Обновление метрик
        self._performance_window.append((current_time, processing_time))
        
        # Очистка старых данных (последние 60 секунд)
        cutoff_time = current_time - 60.0
        self._performance_window = [
            (t, pt) for t, pt in self._performance_window if t > cutoff_time
        ]
        
        # Расчет RPS и среднего времени
        if len(self._performance_window) > 1:
            time_span = current_time - self._performance_window[0][0]
            self.performance_metrics.records_per_second = len(self._performance_window) / time_span
            self.performance_metrics.processing_time_avg = sum(
                pt for _, pt in self._performance_window
            ) / len(self._performance_window)
            
            # Адаптивное отключение при высокой нагрузке
            if (self.performance_metrics.records_per_second > 
                self.performance_metrics.high_load_threshold):
                if self.enable_error_expansion:
                    self._logger.info("High load detected. Disabling error expansion temporarily.")
                    self.toggle_error_expansion(False)
                    self.toggle_value_aggregation(False)
```

## Производственные оптимизации

### 1. Консольная фильтрация
**Файл**: `src/core/logger_config.py`

**Уровни вывода**:
```python
def configure_logging(cls, environment: str = "production", ...):
    # Консольные уровни в зависимости от окружения
    console_levels = {
        "production": logging.WARNING,    # Только важные сообщения
        "development": logging.INFO,      # Включая агрегированные таблицы  
        "debug": logging.DEBUG           # Все подробности
    }
    
    console_handler = cls._create_console_aggregating_handler()
    console_handler.setLevel(console_levels.get(environment, logging.INFO))
```

### 2. Условное табличное форматирование
**Файл**: `src/log_aggregator/tabular_formatter.py`

**Приоритизация таблиц**:
```python
class TabularFormattingConfig:
    priority_tables: List[str] = field(default_factory=lambda: [
        "operation_cascade",      # Высокий приоритет
        "request_response_cycle", 
        "error_analysis"
    ])
    
    low_priority_tables: List[str] = field(default_factory=lambda: [
        "plot_lines_addition",    # Низкий приоритет
        "gui_updates",
        "file_operations"
    ])
    
    disable_low_priority_on_load: bool = True
```

### 3. Кэширование и оптимизация памяти
**Файл**: `src/log_aggregator/value_aggregator.py`

**Улучшенное управление кэшем**:
```python
class ValueAggregator:
    def _cleanup_cache(self):
        """Intelligent cache cleanup based on usage patterns."""
        if len(self._value_cache) <= self.config.cache_size_limit:
            return
            
        # Сортировка по времени использования и размеру
        cache_items = [
            (key, summary, self._get_cache_priority(key, summary))
            for key, summary in self._value_cache.items()
        ]
        
        # Удаление элементов с низким приоритетом
        cache_items.sort(key=lambda x: x[2])
        items_to_remove = len(cache_items) - self.config.cache_size_limit
        
        for key, _, _ in cache_items[:items_to_remove]:
            del self._value_cache[key]
            if key in self._cache_order:
                self._cache_order.remove(key)
    
    def _get_cache_priority(self, key: str, summary: ValueSummary) -> float:
        """Calculate cache priority (lower = remove first)."""
        age_factor = time.time() - getattr(summary, 'last_access', 0)
        size_factor = len(summary.full_content)
        return -age_factor + (size_factor / 10000)  # Prefer recent, small items
```

## Мониторинг и диагностика

### 1. Расширенная статистика
**Файл**: `src/log_aggregator/realtime_handler.py`

**Детальные метрики**:
```python
def get_detailed_statistics(self) -> Dict[str, Any]:
    """Get comprehensive aggregator statistics."""
    return {
        "performance": {
            "records_per_second": self.performance_metrics.records_per_second,
            "avg_processing_time_ms": self.performance_metrics.processing_time_avg * 1000,
            "buffer_utilization": len(self.buffer_manager._buffer) / self.buffer_manager.max_size
        },
        
        "aggregation": {
            "patterns_detected": len(self.pattern_detector._active_patterns),
            "error_expansions_count": getattr(self.error_expansion_engine, '_expansion_count', 0),
            "value_cache_size": len(getattr(self.value_aggregator, '_value_cache', {}))
        },
        
        "features": {
            "error_expansion_enabled": self.enable_error_expansion,
            "value_aggregation_enabled": self.enable_value_aggregation,
            "tabular_formatting_enabled": self.enable_tabular_format
        }
    }
```

### 2. Health check endpoint
**Файл**: `src/core/logger_config.py`

**Проверка состояния**:
```python
@classmethod
def get_logger_health_status(cls) -> Dict[str, Any]:
    """Get health status of logging system."""
    status = {
        "status": "healthy",
        "aggregators": [],
        "issues": []
    }
    
    for handler in cls._aggregating_handlers:
        handler_stats = handler.get_detailed_statistics()
        
        # Проверка производительности
        if handler_stats["performance"]["records_per_second"] > 200:
            status["issues"].append(f"High load on {handler.handler_id}")
            
        # Проверка буферизации
        if handler_stats["performance"]["buffer_utilization"] > 0.9:
            status["issues"].append(f"Buffer near capacity on {handler.handler_id}")
            
        status["aggregators"].append({
            "handler_id": handler.handler_id,
            "stats": handler_stats
        })
    
    if status["issues"]:
        status["status"] = "degraded" if len(status["issues"]) < 3 else "unhealthy"
        
    return status
```

## Тестирование

### Нагрузочные тесты
1. **Высокочастотное логирование** - 1000+ записей/сек
2. **Массовые ошибки** - проверка адаптивного отключения
3. **Длительная работа** - memory leaks, cache overflow
4. **Разные пресеты** - корректность конфигурации

### Критерии производительности
- ✅ Обработка до 500 записей/сек без деградации
- ✅ Адаптивное отключение функций при нагрузке
- ✅ Стабильное потребление памяти
- ✅ Отсутствие дублирования статистики

## Результат этапа
По завершении этапа 3:
- Оптимизированные конфигурационные пресеты для разных сред
- Адаптивное управление производительностью
- Устранение избыточности и дублирования
- Улучшенный мониторинг состояния системы
- Повышенная производительность при высокой нагрузке

## Pull Request
**Название**: `feat: Optimize aggregator configuration and performance monitoring`

**Описание**:
- Добавляет конфигурационные пресеты для production/development/minimal
- Реализует адаптивное управление нагрузкой с автоматическим отключением функций
- Устраняет дублирование статистики между handler'ами
- Оптимизирует пороги для расширения ошибок и табличного форматирования
- Добавляет детальный мониторинг производительности и health check

**Файлы для изменения**:
- `src/log_aggregator/config.py`
- `src/log_aggregator/realtime_handler.py`
- `src/log_aggregator/value_aggregator.py`
- `src/log_aggregator/tabular_formatter.py`
- `src/core/logger_config.py`

**Тесты для добавления**:
- Нагрузочные тесты производительности
- Тесты адаптивного управления
- Тесты конфигурационных пресетов
- Тесты мониторинга и health check
