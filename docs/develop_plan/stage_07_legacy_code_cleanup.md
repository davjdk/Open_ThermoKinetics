# Этап 7: Очистка устаревшего кода

## Цель этапа
Удалить или переписать весь устаревший код, который не является минимально необходимым для реализации логирования операций по новой схеме.

## Задачи этапа

### 7.1 Аудит и инвентаризация устаревшего кода
- Провести полный аудит модуля logger_handler
- Идентифицировать компоненты для удаления
- Составить план поэтапного удаления с минимизацией рисков
- Создать резервные копии критических компонентов

### 7.2 Удаление автоматического обнаружения операций
- Отключить или удалить auto_mode в OperationAggregator
- Удалить регекс-шаблоны для парсинга логов
- Убрать эвристики обнаружения последовательностей операций
- Очистить код анализа текстовых сообщений логов

### 7.3 Упрощение системы агрегации
- Удалить устаревшие классы ValueAggregator
- Убрать дублирующие функции компрессии данных
- Очистить неиспользуемые методы кэширования метрик
- Упростить OperationAggregator до explicit mode только

### 7.4 Очистка OperationLogger
- Удалить альтернативные способы инициации логирования
- Убрать неиспользуемые контекст-менеджеры
- Очистить отладочные выводы и временный код
- Упростить API до минимально необходимого

## Компоненты для удаления

### 7.5 Автоматическое обнаружение операций
```python
# УДАЛИТЬ: Код автоматического парсинга логов
class LogPatternMatcher:
    def find_operation_patterns(self, log_text: str):
        # Удалить весь код парсинга по шаблонам
        pass

# УДАЛИТЬ: Эвристики обнаружения операций
OPERATION_DETECTION_PATTERNS = [
    r"OPERATION_START:\s*(\w+)",
    r"(\w+)\s*operation\s*started",
    # Все регулярные выражения для автообнаружения
]

# УДАЛИТЬ: Автоматический режим агрегатора
class OperationAggregator:
    def __init__(self, mode='auto'):  # УДАЛИТЬ auto mode
        if mode == 'auto':
            # Весь код автоматического режима
            pass
```

### 7.6 Устаревшие классы агрегации
```python
# УДАЛИТЬ: Устаревший ValueAggregator
class ValueAggregator:
    def aggregate_large_datasets(self, data):
        # Функциональность интегрирована в OperationLogger
        pass
    
    def compress_metrics(self, metrics):
        # Теперь часть внутренней логики OperationLogger
        pass

# УДАЛИТЬ: Старые функции компрессии
def legacy_compress_data(data_array):
    # Устаревшая логика компрессии
    pass

def legacy_cache_metrics(operation_id, metrics):
    # Старое кэширование, заменено на thread-local
    pass
```

### 7.7 Неиспользуемые методы OperationLogger
```python
class OperationLogger:
    # УДАЛИТЬ: Альтернативные способы инициации
    def start_with_context_manager(self):
        # Заменено на декоратор @operation
        pass
    
    def manual_operation_wrapper(self, func):
        # Заменено на автоматическое декорирование
        pass
    
    # УДАЛИТЬ: Отладочные методы
    def debug_print_operation_stack(self):
        # Временный отладочный код
        pass
    
    def _legacy_reset_logger(self):
        # Устаревший метод сброса
        pass
```

### 7.8 Лишние конфигурационные опции
```python
# В app_settings.py - УДАЛИТЬ или установить в False
class OperationAggregationConfig:
    auto_mode_enabled: bool = False  # УДАЛИТЬ или зафиксировать False
    legacy_pattern_matching: bool = False  # УДАЛИТЬ
    use_old_compression: bool = False  # УДАЛИТЬ
    debug_mode: bool = False  # УДАЛИТЬ если не используется
    
    # УДАЛИТЬ: Настройки автообнаружения
    auto_detection_patterns: List[str] = []  # УДАЛИТЬ
    pattern_matching_timeout: float = 5.0  # УДАЛИТЬ
```

## План поэтапного удаления

### 7.9 Фаза 1: Отключение автоматических механизмов
```python
# Шаг 1: Отключить auto_mode везде где используется
def disable_auto_mode():
    # В OperationAggregator
    aggregator.mode = 'explicit'
    
    # В конфигурации
    config.auto_mode_enabled = False
    
    # Добавить warnings для устаревших вызовов
    if aggregator.mode == 'auto':
        warnings.warn(
            "Auto mode is deprecated, use explicit mode",
            DeprecationWarning
        )
```

### 7.10 Фаза 2: Удаление неиспользуемых классов
```python
# Шаг 2: Постепенное удаление классов
# 1. Пометить как deprecated
@deprecated("Use OperationLogger.add_metric() instead")
class ValueAggregator:
    pass

# 2. Удалить импорты и ссылки
# from .value_aggregator import ValueAggregator  # УДАЛИТЬ

# 3. Удалить файлы
# rm src/core/value_aggregator.py
# rm src/core/legacy_compression.py
```

### 7.11 Фаза 3: Очистка API OperationLogger
```python
class OperationLogger:
    # СОХРАНИТЬ: Основной API
    def start_operation(self, operation_name: str, **context) -> None: pass
    def end_operation(self, status: str = "SUCCESS", error_info: dict = None) -> None: pass
    def add_metric(self, key: str, value: Any) -> None: pass
    def get_current_operation(self) -> Optional[dict]: pass
    
    # УДАЛИТЬ: Устаревшие методы
    # def legacy_start_operation(self, name): pass
    # def manual_wrapper(self, func): pass
    # def debug_operations(self): pass
    # def reset_all_state(self): pass
```

### 7.12 Фаза 4: Упрощение OperationAggregator
```python
class OperationAggregator:
    def __init__(self):
        # УДАЛИТЬ: Поддержку режимов
        # self.mode = mode
        
        # СОХРАНИТЬ: Только explicit функциональность
        self._explicit_operations = {}
        self._current_cascade = None
    
    # УДАЛИТЬ: Автоматические методы
    # def auto_detect_operations(self, log_stream): pass
    # def parse_log_patterns(self, text): pass
    
    # СОХРАНИТЬ: Explicit методы
    def start_operation_explicit(self, operation_id, operation_data): pass
    def end_operation_explicit(self, operation_id, result_data): pass
```

## Валидация после очистки

### 7.13 Проверки корректности удаления
```python
def validate_cleanup():
    """Проверить корректность удаления устаревшего кода"""
    
    # Проверка 1: Нет импортов удалённых модулей
    try:
        from .value_aggregator import ValueAggregator
        raise AssertionError("ValueAggregator should be removed")
    except ImportError:
        pass  # Ожидаемо
    
    # Проверка 2: Нет вызовов устаревших методов
    logger = OperationLogger()
    assert not hasattr(logger, 'legacy_start_operation')
    assert not hasattr(logger, 'manual_wrapper')
    
    # Проверка 3: Конфигурация очищена
    assert not hasattr(config, 'auto_mode_enabled')
    assert not hasattr(config, 'legacy_pattern_matching')
    
    # Проверка 4: Файлы удалены
    import os
    assert not os.path.exists('src/core/value_aggregator.py')
    assert not os.path.exists('src/core/legacy_compression.py')
```

### 7.14 Обновление документации
- Удалить ссылки на устаревшие компоненты из README
- Обновить API документацию OperationLogger
- Создать migration guide для перехода на новую архитектуру
- Документировать изменения в CHANGELOG

### 7.15 Обновление тестов
```python
# УДАЛИТЬ: Тесты устаревшей функциональности
# class TestValueAggregator: pass
# class TestAutoModeOperations: pass
# class TestLegacyCompression: pass

# ОБНОВИТЬ: Тесты новой архитектуры
class TestOperationDecoratorIntegration:
    def test_decorator_replaces_manual_wrapper(self):
        # Тест что декоратор заменил ручные обёртки
        pass

class TestCleanOperationLogger:
    def test_only_essential_methods_present(self):
        # Проверить что остались только нужные методы
        logger = OperationLogger()
        essential_methods = {
            'start_operation', 'end_operation', 
            'add_metric', 'get_current_operation'
        }
        actual_methods = {
            name for name in dir(logger) 
            if not name.startswith('_') and callable(getattr(logger, name))
        }
        assert actual_methods == essential_methods
```

## Метрики очистки

### 7.16 Измерение результатов очистки
```python
def cleanup_metrics():
    """Собрать метрики по очистке кода"""
    
    # Удалённые строки кода
    removed_lines = count_removed_lines()
    
    # Удалённые файлы
    removed_files = [
        'value_aggregator.py',
        'legacy_compression.py', 
        'pattern_matcher.py',
        'auto_detector.py'
    ]
    
    # Упрощённые классы
    simplified_classes = {
        'OperationLogger': {'removed_methods': 8, 'kept_methods': 4},
        'OperationAggregator': {'removed_methods': 12, 'kept_methods': 3}
    }
    
    # Удалённые конфигурационные опции
    removed_config_options = [
        'auto_mode_enabled',
        'legacy_pattern_matching', 
        'auto_detection_patterns',
        'pattern_matching_timeout'
    ]
    
    return {
        'removed_lines': removed_lines,
        'removed_files': len(removed_files),
        'simplified_classes': len(simplified_classes),
        'removed_config_options': len(removed_config_options)
    }
```

## Ожидаемые результаты
- Удаление всей логики автоматического обнаружения операций
- Упрощение OperationLogger до минимально необходимого API
- Очистка OperationAggregator от auto_mode
- Удаление устаревших классов и функций агрегации

## Критерии готовности
- Весь код автообнаружения операций удалён
- OperationAggregator работает только в explicit режиме
- OperationLogger содержит только актуальные методы
- Все тесты проходят после очистки

## Риски и меры безопасности
- Создание резервных копий перед удалением
- Поэтапное удаление с проверкой на каждом шаге
- Полное тестирование после каждого этапа очистки
- Возможность отката изменений при критических ошибках

## Финальная валидация
- Автоматические тесты всей системы логирования
- Проверка производительности после очистки
- Валидация API совместимости
- Подтверждение что все операции корректно логируются
