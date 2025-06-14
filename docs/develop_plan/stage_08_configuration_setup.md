# Этап 8: Настройка конфигурации и временных параметров

## Цель этапа
Настроить систему конфигурации для управления временными рамками операций, параметрами агрегирования и форматирования вывода.

## Задачи этапа

### 8.1 Анализ существующей конфигурации
- Изучить текущую структуру app_settings.py
- Проверить наличие OperationAggregationConfig
- Оценить существующие параметры cascade_window и timeout
- Определить требования к новым конфигурационным параметрам

### 8.2 Разработка новой структуры конфигурации
- Создать централизованную конфигурацию операций
- Определить параметры временных окон и группировки
- Настроить параметры форматирования таблиц
- Обеспечить обратную совместимость с существующими настройками

### 8.3 Интеграция с системой логирования
- Подключить конфигурацию к OperationLogger
- Реализовать динамическое обновление параметров
- Обеспечить валидацию конфигурационных значений
- Добавить поддержку конфигурации из файлов и переменных окружения

## Структура новой конфигурации

### 8.4 Основная конфигурация операций
```python
# В src/core/app_settings.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from enum import Enum

@dataclass
class OperationLoggingConfig:
    """Конфигурация системы логирования операций"""
    
    # Временные параметры
    operation_time_frame: float = 1.0           # Окно группировки операций (сек)
    cascade_window: float = 1.0                 # Окно каскадных операций (сек)
    operation_timeout: float = 300.0            # Таймаут операций (сек)
    nested_operation_timeout: float = 60.0      # Таймаут вложенных операций (сек)
    
    # Параметры агрегирования
    aggregate_nested_operations: bool = True    # Агрегировать вложенные операции
    max_operation_depth: int = 10              # Максимальная глубина вложенности
    enable_operation_grouping: bool = True      # Включить группировку операций
    group_by_thread: bool = True               # Группировать по потокам
      # Форматирование вывода (Rich)
    rich_enabled: bool = True                  # Включить Rich форматирование
    rich_force_terminal: bool = False          # Принудительный терминальный режим
    rich_width: Optional[int] = None           # Ширина консоли Rich
    rich_color_system: str = "auto"            # auto/standard/256/truecolor
    rich_theme: str = "default"                # Тема Rich
    
    # Настройки Rich таблиц
    rich_table_box: str = "ROUNDED"            # ROUNDED/SQUARE/SIMPLE/HEAVY
    rich_header_style: str = "bold blue"       # Стиль заголовков Rich
    rich_title_style: str = "bold cyan"        # Стиль заголовка Rich таблицы
    
    # Настройки Rich панелей ошибок
    rich_error_panel_style: str = "red"        # Стиль панели ошибок
    rich_error_box: str = "HEAVY"              # Стиль рамки ошибок
    show_rich_error_panels: bool = True        # Показывать Rich панели ошибок
    
    # Символы и форматирование
    use_unicode_symbols: bool = True           # ✅/❌ символы
    timestamp_format: str = "%Y-%m-%d %H:%M:%S" # Формат времени
    duration_precision: int = 3                # Точность времени (знаков после запятой)
    max_error_message_length: int = 100        # Максимальная длина сообщения об ошибке
    
    # Уровни детализации
    detail_level: str = "normal"               # minimal/normal/detailed/debug
    include_user_metrics: bool = True          # Включать пользовательские метрики
    include_file_metrics: bool = True          # Включать файловые метрики
    include_performance_metrics: bool = True   # Включать метрики производительности
    
    # Фильтрация операций
    exclude_operations: List[str] = field(default_factory=list)  # Исключённые операции
    include_only_operations: List[str] = field(default_factory=list)  # Только эти операции
    min_operation_duration: float = 0.0        # Минимальная длительность для логирования
    
    # Обработка ошибок
    log_full_traceback: bool = False           # Логировать полный traceback
    auto_recovery_enabled: bool = True         # Включить автовосстановление
    max_recovery_attempts: int = 3             # Максимум попыток восстановления
    
    # Производительность
    enable_async_logging: bool = False         # Асинхронное логирование
    buffer_size: int = 1000                    # Размер буфера логов
    flush_interval: float = 5.0                # Интервал сброса буфера (сек)
```

### 8.5 Конфигурация Rich форматирования
```python
@dataclass
class RichFormattingConfig:
    """Конфигурация Rich форматирования таблиц"""
    
    # Основные настройки Rich
    enabled: bool = True                       # Включить Rich
    force_terminal: bool = False               # Принудительный терминальный режим
    width: Optional[int] = None                # Ширина консоли (None = авто)
    color_system: str = "auto"                 # Система цветов
    theme: str = "default"                     # Тема оформления
    
    # Настройки таблиц
    table_box_style: str = "ROUNDED"           # Стиль рамки таблиц
    show_table_header: bool = False            # Показывать заголовки колонок
    table_title_style: str = "bold cyan"       # Стиль заголовка таблицы
    table_border_style: str = "blue"           # Стиль границ таблицы
    
    # Настройки колонок
    property_column_style: str = "cyan"        # Стиль колонки свойств
    value_column_style: str = "white"          # Стиль колонки значений
    property_column_width: int = 20            # Ширина колонки свойств
    value_column_width: int = 40               # Ширина колонки значений
    
    # Настройки панелей ошибок
    error_panel_enabled: bool = True           # Включить панели ошибок
    error_panel_style: str = "red"             # Стиль панели ошибок
    error_border_style: str = "red"            # Стиль границ панели ошибок
    error_box_style: str = "HEAVY"             # Стиль рамки ошибок
    
    # Экспорт и запись
    export_svg: bool = False                   # Экспорт в SVG
    export_html: bool = False                  # Экспорт в HTML
    record_mode: bool = False                  # Режим записи
    
    # Символы статуса
    success_icon: str = "✅"                   # Иконка успеха
    error_icon: str = "❌"                     # Иконка ошибки
    timeout_icon: str = "⏱️"                  # Иконка таймаута
    running_icon: str = "🔄"                   # Иконка выполнения
```

### 8.6 Конфигурация метрик операций
```python
@dataclass 
class OperationMetricsConfig:
    """Конфигурация сбора метрик операций"""
    
    # Базовые метрики
    collect_timing_metrics: bool = True        # Собирать метрики времени
    collect_memory_metrics: bool = False       # Собирать метрики памяти
    collect_cpu_metrics: bool = False          # Собирать метрики CPU
    collect_io_metrics: bool = True            # Собирать метрики I/O
    
    # Файловые метрики
    track_file_operations: bool = True         # Отслеживать операции с файлами
    track_file_sizes: bool = True              # Отслеживать размеры файлов
    track_file_modifications: bool = True      # Отслеживать изменения файлов
    
    # Доменные метрики (для кинетического анализа)
    track_reaction_metrics: bool = True        # Метрики реакций
    track_optimization_metrics: bool = True    # Метрики оптимизации
    track_convergence_metrics: bool = True     # Метрики сходимости
    track_quality_metrics: bool = True         # Метрики качества (R², RMSE)
    
    # Пользовательские метрики
    allow_custom_metrics: bool = True          # Разрешить пользовательские метрики
    max_custom_metrics: int = 50               # Максимум пользовательских метрик
    custom_metrics_prefix: str = "user_"       # Префикс пользовательских метрик
```

## Система управления конфигурацией

### 8.7 Менеджер конфигурации
```python
class OperationConfigManager:
    """Менеджер конфигурации операций"""
    
    def __init__(self):
        self._logging_config = OperationLoggingConfig()
        self._rich_config = RichFormattingConfig()
        self._metrics_config = OperationMetricsConfig()
        self._observers: List[Callable] = []
    
    def get_logging_config(self) -> OperationLoggingConfig:
        """Получить конфигурацию логирования"""
        return self._logging_config
    
    def get_rich_config(self) -> RichFormattingConfig:
        """Получить конфигурацию Rich форматирования"""
        return self._rich_config
    
    def get_metrics_config(self) -> OperationMetricsConfig:
        """Получить конфигурацию метрик"""
        return self._metrics_config
    
    def update_config(self, config_dict: Dict[str, Any]):
        """Обновить конфигурацию из словаря"""
        for key, value in config_dict.items():
            if hasattr(self._logging_config, key):
                setattr(self._logging_config, key, value)
                self._notify_observers("logging", key, value)
            elif hasattr(self._table_config, key):
                setattr(self._table_config, key, value)
                self._notify_observers("table", key, value)
            elif hasattr(self._metrics_config, key):
                setattr(self._metrics_config, key, value)
                self._notify_observers("metrics", key, value)
    
    def load_from_file(self, config_path: str):
        """Загрузить конфигурацию из файла"""
        import json
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        self.update_config(config_data)
    
    def save_to_file(self, config_path: str):
        """Сохранить конфигурацию в файл"""
        import json
        from dataclasses import asdict
          config_data = {
            "logging": asdict(self._logging_config),
            "rich": asdict(self._rich_config),
            "metrics": asdict(self._metrics_config)
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def add_observer(self, observer: Callable):
        """Добавить наблюдателя за изменениями конфигурации"""
        self._observers.append(observer)
    
    def _notify_observers(self, section: str, key: str, value: Any):
        """Уведомить наблюдателей об изменении"""
        for observer in self._observers:
            observer(section, key, value)

# Глобальный экземпляр менеджера конфигурации
config_manager = OperationConfigManager()
```

### 8.8 Интеграция с переменными окружения
```python
def load_config_from_env():
    """Загрузить конфигурацию из переменных окружения"""
    import os
    
    env_mapping = {
        'SSK_OPERATION_TIME_FRAME': 'operation_time_frame',
        'SSK_OPERATION_TIMEOUT': 'operation_timeout',
        'SSK_ASCII_TABLES': 'ascii_tables_enabled',
        'SSK_TABLE_FORMAT': 'table_format',
        'SSK_DETAIL_LEVEL': 'detail_level',
        'SSK_USE_UNICODE': 'use_unicode_symbols',
    }
    
    config_updates = {}
    for env_var, config_key in env_mapping.items():
        if env_var in os.environ:
            value = os.environ[env_var]
            # Конвертация типов
            if config_key.endswith('_enabled') or config_key.startswith('use_'):
                value = value.lower() in ('true', '1', 'yes', 'on')
            elif config_key.endswith('_frame') or config_key.endswith('_timeout'):
                value = float(value)
            
            config_updates[config_key] = value
    
    if config_updates:
        config_manager.update_config(config_updates)
```

## Интеграция с OperationLogger

### 8.9 Подключение конфигурации к логгеру
```python
class OperationLogger:
    def __init__(self):
        self._config_manager = config_manager
        self._config = self._config_manager.get_logging_config()
        
        # Подписаться на изменения конфигурации
        self._config_manager.add_observer(self._on_config_changed)
    
    def _on_config_changed(self, section: str, key: str, value: Any):
        """Обработать изменение конфигурации"""
        if section == "logging":
            self._config = self._config_manager.get_logging_config()
            
            # Применить изменения немедленно
            if key == "operation_timeout":
                self._update_operation_timeouts()
            elif key == "ascii_tables_enabled":
                self._toggle_table_output(value)
    
    def start_operation(self, operation_name: str, **context):
        """Начать операцию с учётом конфигурации"""
        
        # Проверить фильтры операций
        if self._config.exclude_operations and operation_name in self._config.exclude_operations:
            return
        
        if (self._config.include_only_operations and 
            operation_name not in self._config.include_only_operations):
            return
        
        # Применить настройки группировки
        if self._config.enable_operation_grouping:
            self._check_operation_grouping(operation_name)
        
        # Стандартная логика start_operation
        super().start_operation(operation_name, **context)
    
    def end_operation(self, status: str = "SUCCESS", error_info: dict = None):
        """Завершить операцию с учётом конфигурации"""
        
        operation = self.get_current_operation()
        if not operation:
            return
        
        duration = time.time() - operation['start_time']
        
        # Проверить минимальную длительность для логирования
        if duration < self._config.min_operation_duration:
            return
        
        # Стандартная логика end_operation
        super().end_operation(status, error_info)
        
        # Вывести таблицу если включено
        if self._config.ascii_tables_enabled:
            table_formatter = self._get_table_formatter()
            table = table_formatter.format_operation_summary(operation)
            print(table)
```

### 8.10 Применение временных параметров
```python
def apply_timing_configuration():
    """Применить настройки временных параметров"""
    
    config = config_manager.get_logging_config()
    
    # Настроить агрегатор операций
    aggregator = get_operation_aggregator()
    aggregator.set_cascade_window(config.cascade_window)
    aggregator.set_grouping_timeframe(config.operation_time_frame)
    
    # Настроить таймауты
    operation_logger = get_operation_logger()
    operation_logger.set_operation_timeout(config.operation_timeout)
    operation_logger.set_nested_timeout(config.nested_operation_timeout)
    
    # Настроить группировку
    if config.enable_operation_grouping:
        aggregator.enable_grouping()
        if config.group_by_thread:
            aggregator.set_group_by_thread(True)
    else:
        aggregator.disable_grouping()
```

## Валидация конфигурации

### 8.11 Валидация параметров
```python
def validate_operation_config(config: OperationLoggingConfig) -> List[str]:
    """Валидировать конфигурацию операций"""
    
    errors = []
    
    # Валидация временных параметров
    if config.operation_time_frame <= 0:
        errors.append("operation_time_frame must be positive")
    
    if config.operation_timeout <= 0:
        errors.append("operation_timeout must be positive") 
    
    if config.cascade_window < 0:
        errors.append("cascade_window must be non-negative")
    
    # Валидация уровней детализации
    valid_detail_levels = ["minimal", "normal", "detailed", "debug"]
    if config.detail_level not in valid_detail_levels:
        errors.append(f"detail_level must be one of {valid_detail_levels}")
    
    # Валидация форматов
    valid_table_formats = ["ascii", "simple", "markdown", "none"]
    if config.table_format not in valid_table_formats:
        errors.append(f"table_format must be one of {valid_table_formats}")
    
    # Валидация списков операций
    if (config.exclude_operations and config.include_only_operations):
        errors.append("Cannot specify both exclude_operations and include_only_operations")
    
    return errors
```

## Ожидаемые результаты
- Централизованная система конфигурации операций
- Настраиваемые временные параметры и форматирование
- Динамическое обновление конфигурации без перезапуска
- Поддержка конфигурации через файлы и переменные окружения

## Критерии готовности
- Все временные параметры настраиваются через конфигурацию
- Изменения конфигурации применяются немедленно
- Валидация предотвращает некорректные значения
- Конфигурация может быть сохранена и загружена из файлов

## Тестирование
- Тест загрузки конфигурации из различных источников
- Тест валидации конфигурационных параметров
- Тест динамического обновления настроек
- Тест применения временных окон и группировки
- Тест различных форматов таблиц и уровней детализации
