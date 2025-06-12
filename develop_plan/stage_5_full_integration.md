# Этап 5: Полная интеграция и расширенная конфигурация

**Место в общем плане:** Финальный пятый этап из 5. Полная интеграция всех компонентов с расширенной конфигурацией, пресетами и продвинутыми возможностями управления.

## Цель этапа
Завершить интеграцию всех компонентов модуля агрегации логов, добавить расширенную конфигурацию с пресетами, улучшить LoggerManager и провести финальное тестирование системы.

## Обновляемые и создаваемые файлы

### Расширенная конфигурация (config.py)
- Объединение всех конфигурационных классов
- Добавление пресетов: "minimal", "performance", "detailed"
- Методы создания предустановленных конфигураций
- Сериализация и экспорт конфигурации

### Полная интеграция с LoggerManager (logger_config.py)
- Расширенный метод `configure_logging()` с новыми параметрами
- Методы управления агрегацией в runtime
- Получение статистики и мониторинг
- Обновление конфигурации без перезапуска

### Финальная версия AggregatingHandler (realtime_handler.py)
- Интеграция всех компонентов (ErrorExpansion + TabularFormatter)
- Улучшенная статистика и мониторинг
- Оптимизация производительности
- Обработка edge cases и error handling

## Расширенная конфигурация

### Финальный AggregationConfig
```python
@dataclass
class AggregationConfig:
    # Параметры буферизации
    buffer_size: int = 1000
    flush_interval: float = 2.0
    context_buffer_size: int = 20
    
    # Параметры детекции паттернов
    min_pattern_entries: int = 3
    time_window_seconds: int = 5
    pattern_priority_threshold: str = "medium"
    
    # Компоненты расширений
    error_expansion: ErrorExpansionConfig = None
    tabular_formatting: TabularFormattingConfig = None
    
    # Параметры производительности
    max_processing_time_ms: float = 100.0
    enable_async_processing: bool = False
    
    # Параметры вывода
    compression_threshold: float = 0.3
    output_format: str = "enhanced"  # "simple", "enhanced", "tabular"
    
    # Отладка и мониторинг
    enable_stats_logging: bool = True
    stats_interval_seconds: int = 60
    debug_mode: bool = False
```

### Пресеты конфигурации
```python
@classmethod
def create_minimal(cls) -> 'AggregationConfig':
    """Минимальная конфигурация для базового использования"""
    return cls(
        buffer_size=500,
        flush_interval=1.0,
        min_pattern_entries=2,
        error_expansion=ErrorExpansionConfig(
            enabled=True,
            immediate_expansion=True
        ),
        tabular_formatting=TabularFormattingConfig(
            enabled=True,
            max_rows_per_table=10
        )
    )

@classmethod  
def create_performance(cls) -> 'AggregationConfig':
    """Конфигурация для высокой производительности"""
    return cls(
        buffer_size=2000,
        flush_interval=0.5,
        min_pattern_entries=5,
        max_processing_time_ms=50.0,
        enable_async_processing=True,
        error_expansion=ErrorExpansionConfig(
            enabled=True,
            immediate_expansion=False
        ),
        tabular_formatting=TabularFormattingConfig(
            enabled=False  # Отключено для производительности
        )
    )

@classmethod
def create_detailed(cls) -> 'AggregationConfig':
    """Конфигурация для максимальной детализации"""
    return cls(
        buffer_size=1500,
        flush_interval=3.0,
        min_pattern_entries=2,
        context_buffer_size=50,
        error_expansion=ErrorExpansionConfig(
            enabled=True,
            context_lines=10,
            save_context=True
        ),
        tabular_formatting=TabularFormattingConfig(
            enabled=True,
            include_summaries=True,
            max_rows_per_table=30
        ),
        enable_stats_logging=True,
        debug_mode=True
    )
```

## Расширенная интеграция с LoggerManager

### Обновленный метод configure_logging
```python
@classmethod
def configure_logging(
    cls,
    log_level: int = logging.DEBUG,
    console_level: Optional[int] = None,
    file_level: Optional[int] = None,
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    enable_aggregation: bool = False,
    aggregation_config: Optional[dict] = None,
    enable_error_expansion: bool = True,  # НОВЫЙ
    enable_tabular_format: bool = True,   # НОВЫЙ
    aggregation_preset: str = "default", # НОВЫЙ: "minimal", "performance", "detailed"
) -> None:
```

### Методы управления в runtime
```python
@classmethod
def toggle_aggregation(cls, enabled: bool) -> None:
    """Включение/выключение агрегации в runtime"""

@classmethod
def toggle_error_expansion(cls, enabled: bool) -> None:
    """Включение/выключение детализации ошибок в runtime"""

@classmethod
def toggle_tabular_format(cls, enabled: bool) -> None:
    """Включение/выключение табличного формата в runtime"""

@classmethod
def get_aggregation_stats(cls) -> dict:
    """Получение расширенной статистики агрегации"""

@classmethod  
def export_aggregation_config(cls) -> dict:
    """Экспорт текущей конфигурации агрегации"""

@classmethod
def update_aggregation_config(cls, config_updates: dict) -> None:
    """Обновление конфигурации агрегации в runtime"""
```

## Расширенная статистика и мониторинг

### Комплексная статистика
```python
def get_aggregation_stats(cls) -> dict:
    combined_stats = {
        'handlers': {},
        'total_stats': {
            'total_records': 0,
            'aggregated_records': 0, 
            'patterns_detected': 0,
            'errors_expanded': 0,
            'tables_generated': 0,
            'buffer_flushes': 0
        }
    }
    
    # Вычисляемые метрики
    total_processed = combined_stats['total_stats']['total_records']
    if total_processed > 0:
        combined_stats['total_stats']['compression_ratio'] = (
            1 - combined_stats['total_stats']['aggregated_records'] / total_processed
        )
        combined_stats['total_stats']['error_expansion_ratio'] = (
            combined_stats['total_stats']['errors_expanded'] / total_processed
        )
    
    return combined_stats
```

## Примеры из проекта

### Загрузка файлов данных 
```
2025-06-12 12:53:30 - DEBUG - load_file_button.py:36 - Selected file: C:/IDE/repository/solid-state_kinetics/resources/NH4_rate_3.csv
2025-06-12 12:53:44 - DEBUG - load_file_button.py:36 - Selected file: C:/IDE/repository/solid-state_kinetics/resources/NH4_rate_5.csv
2025-06-12 12:53:30 - DEBUG - load_file_button.py:148 - Detected delimiter: ","
2025-06-12 12:53:31 - DEBUG - load_file_button.py:211 - Extracted column names: temperature,rate_3
```

### Обновления интерфейса компонентов
```
2025-06-12 12:53:53 - DEBUG - coefficients_view.py:90 - Received reaction parameters for the table: {'coeffs': ((32.18783, 498.18635), 'gauss', (0.005452850632157724, 265.18708750511246, 46.599852))}
2025-06-12 12:53:53 - DEBUG - plot_canvas.py:184 - Received reaction data for anchors: {'coeffs': ((32.18783, 498.18635), 'gauss', (0.005452850632157724, 265.18708750511246, 46.599852))}
2025-06-12 12:53:31 - DEBUG - experiment_sub_bar.py:192 - Resized ExperimentSubBar to match parent width: 220px.
```

### Операции с данными серий
```
2025-06-12 12:55:29 - DEBUG - main_window.py:606 - Experimental data columns: ['temperature', '3.0', '5.0']
2025-06-12 12:55:29 - DEBUG - main_window.py:607 - Reaction scheme components: 4
2025-06-12 12:55:29 - DEBUG - main_window.py:608 - Reaction scheme reactions: 3
2025-06-12 12:55:29 - DEBUG - main_window.py:624 - Adding simulation curve for heating rate: 3.0
2025-06-12 12:55:29 - DEBUG - main_window.py:624 - Adding simulation curve for heating rate: 5.0
```

## Примеры использования финальной системы

### Инициализация с пресетом "detailed"
```python
from src.core.logger_config import LoggerManager

LoggerManager.configure_logging(
    log_level=logging.DEBUG,
    enable_aggregation=True,
    aggregation_preset="detailed",
    enable_error_expansion=True,
    enable_tabular_format=True
)
```

### Управление в runtime
```python
# Отключение табличного формата для повышения производительности
LoggerManager.toggle_tabular_format(False)

# Получение статистики
stats = LoggerManager.get_aggregation_stats()
print(f"Compression ratio: {stats['total_stats']['compression_ratio']:.2f}")
print(f"Tables generated: {stats['total_stats']['tables_generated']}")

# Обновление конфигурации
LoggerManager.update_aggregation_config({
    'buffer_size': 2000,
    'flush_interval': 1.0
})
```

### Комбинированный вывод (таблицы + детальные ошибки)
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 📊 Plot Lines Addition Summary                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ Line Name      │ Time        │ Duration (ms) │ Status     │
├────┼────────────────┼─────────────┼───────────────┼────────────┤
│ 1  │ Temperature_1  │ +0.0ms      │ 0.0           │ ✅ Success │
│ 2  │ Temperature_2  │ +150.2ms    │ 150.2         │ ✅ Success │
└────────────────────────────────────────────────────────────────────────────┘
📊 Total: 2 lines added in 150.2ms (avg: 75.1ms per line)

================================================================================
🚨 DETAILED ERROR ANALYSIS - ERROR
================================================================================
📍 Location: plot_canvas.py:245
⏰ Time: 2024-01-15 10:31:05
💬 Message: Failed to add line 'Pressure_1' - invalid data format

📋 PRECEDING CONTEXT:
----------------------------------------
  1. [INFO] Adding a new line 'Temperature_2' to the plot (5.1s ago)
  2. [INFO] Adding a new line 'Temperature_1' to the plot (5.3s ago)

💡 SUGGESTED ACTIONS:
----------------------------------------
  1. Проверьте формат данных для линии 'Pressure_1'
  2. Убедитесь в корректности массива данных
  3. Проверьте код в файле plot_canvas.py:245

================================================================================
```

## Финальное тестирование

### Интеграционные тесты системы
```python
# tests/test_full_integration.py
class TestFullIntegration(unittest.TestCase):
    
    def test_complete_workflow_with_all_components(self):
        """Тест полного workflow с таблицами и анализом ошибок"""
    
    def test_preset_configurations(self):
        """Тест всех пресетов конфигурации"""
    
    def test_runtime_configuration_updates(self):
        """Тест обновления конфигурации в runtime"""
    
    def test_performance_under_load(self):
        """Тест производительности под нагрузкой"""
    
    def test_error_handling_and_recovery(self):
        """Тест обработки ошибок и восстановления"""
```

### Тесты производительности
```python
# tests/test_performance.py
class TestPerformance(unittest.TestCase):
    
    def test_high_volume_logging(self):
        """Тест с большим объемом логов (10000+ записей)"""
    
    def test_memory_usage(self):
        """Тест потребления памяти"""
    
    def test_cpu_overhead(self):
        """Тест нагрузки на CPU"""
```

## Критерии готовности финального этапа
- [ ] Все компоненты интегрированы и работают совместно
- [ ] Все 3 пресета конфигурации ("minimal", "performance", "detailed") работают
- [ ] LoggerManager поддерживает все новые параметры
- [ ] Runtime управление работает без перезапуска
- [ ] Расширенная статистика собирается и отображается корректно
- [ ] Полный набор интеграционных тестов проходит (>90% покрытие)
- [ ] Тесты производительности показывают приемлемые результаты
- [ ] Документация обновлена для всех новых возможностей
- [ ] Обратная совместимость сохранена
- [ ] Система стабильно работает под нагрузкой

## Финальные возможности системы
✅ **Базовая агрегация** - группировка логов по паттернам  
✅ **Расширенные паттерны** - 5 типов специализированных паттернов с метаданными  
✅ **Табличное форматирование** - ASCII таблицы для структурированного вывода  
✅ **Детальный анализ ошибок** - расширенный контекст с рекомендациями  
✅ **Гибкая конфигурация** - 3 пресета + возможность кастомизации  
✅ **Runtime управление** - включение/выключение компонентов без перезапуска  
✅ **Мониторинг и статистика** - комплексная отчетность по работе системы  
✅ **Высокая производительность** - оптимизация для минимального overhead  
✅ **Обратная совместимость** - работа с существующим кодом без изменений

## Результат
Полнофункциональный модуль агрегации логов в реальном времени с табличным представлением и детальным анализом ошибок, готовый к продакшену.
