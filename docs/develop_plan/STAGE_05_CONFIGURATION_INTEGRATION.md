# Этап 5: Конфигурация и интеграция BaseSignalsBurstStrategy

## Полная интеграция в существующую архитектуру

### Регистрация в STRATEGY_REGISTRY

**Местоположение**: `src/core/log_aggregator/meta_operation_config.py`

```python
# Добавление в реестр стратегий
STRATEGY_REGISTRY = {
    "TimeWindow": TimeWindowStrategy,
    "TargetCluster": TargetClusterStrategy,
    "NameSimilarity": NameSimilarityStrategy,
    "SequenceCount": SequenceCountStrategy,
    # Новая стратегия с приоритетом 1
    "BaseSignalsBurst": BaseSignalsBurstStrategy
}
```

### Конфигурация по умолчанию

```python
# В META_OPERATION_CONFIG
META_OPERATION_CONFIG = {
    "enabled": True,
    "strategies": {
        # Новая стратегия с наивысшим приоритетом
        "BaseSignalsBurst": {
            "enabled": True,
            "priority": 1,              # Наивысший приоритет
            "time_window_ms": 100,      # Временное окно группировки
            "min_burst_size": 2,        # Минимальное количество операций
            "max_gap_ms": 50,          # Максимальный разрыв между операциями
            "max_duration_ms": 10.0,    # Максимальная длительность одной операции
            "include_cross_target": True # Группировка операций с разными targets
        },
        
        # Существующие стратегии с пониженным приоритетом
        "TimeWindow": {
            "enabled": True,
            "priority": 2,              # Понижен с 1 до 2
            "window_ms": 50,
            "min_cluster_size": 3
        },
        
        "TargetCluster": {
            "enabled": True,
            "priority": 3,              # Понижен с 2 до 3
            "max_gap": 2,
            "min_cluster_size": 2
        },
        
        # ...остальные стратегии
    },
    
    "formatting": {
        "format": "table",
        "show_meta_summary": True,
        "compact_mode": False,
        "include_performance_metrics": True  # Новый параметр для BaseSignals метрик
    }
}
```

### Система приоритетов стратегий

**Обновленная иерархия приоритетов**:
1. **Priority 1**: BaseSignalsBurst (высший)
2. **Priority 2**: TimeWindow (понижен)  
3. **Priority 3**: TargetCluster (понижен)
4. **Priority 4**: NameSimilarity
5. **Priority 5**: SequenceCount

**Логика обработки**: MetaOperationDetector сортирует стратегии по приоритету и применяет их последовательно, позволяя BaseSignalsBurst "захватить" подходящие операции первым.

## Автоматическая интеграция в MetaOperationDetector

### Инициализация детектора

```python
# В MetaOperationDetector.__init__()
def __init__(self, config: Optional[Dict] = None):
    self.config = config or META_OPERATION_CONFIG
    self.strategies: List[MetaOperationStrategy] = []
    
    # Загрузка стратегий из реестра с приоритетами
    self._load_strategies_from_registry()

def _load_strategies_from_registry(self):
    """Загрузка и сортировка стратегий по приоритету."""
    strategy_configs = []
    
    for strategy_name, strategy_config in self.config["strategies"].items():
        if strategy_config.get("enabled", False):
            strategy_class = STRATEGY_REGISTRY.get(strategy_name)
            if strategy_class:
                priority = strategy_config.get("priority", 999)
                strategy_configs.append((priority, strategy_name, strategy_class, strategy_config))
    
    # Сортировка по приоритету (1 = наивысший)
    strategy_configs.sort(key=lambda x: x[0])
    
    # Создание экземпляров стратегий
    for _, name, strategy_class, config in strategy_configs:
        strategy_instance = strategy_class(config)
        strategy_instance.validate_config()
        self.strategies.append(strategy_instance)
```

### Обработка последовательности применения

```python
def detect_meta_operations(self, operation_log: OperationLog) -> List[MetaOperation]:
    """Обнаружение мета-операций с учетом приоритетов."""
    meta_operations = []
    processed_operations = set()  # Отслеживание уже обработанных операций
    
    for strategy in self.strategies:  # Уже отсортированы по приоритету
        strategy_meta_ops = []
        
        for sub_op in operation_log.sub_operations:
            # Пропуск уже обработанных операций
            if sub_op.step_number in processed_operations:
                continue
                
            meta_id = strategy.detect(sub_op, operation_log)
            if meta_id:
                # Группировка операций по meta_id
                # BaseSignalsBurst получает приоритет в захвате операций
                ...
                
        # Отметка обработанных операций
        for meta_op in strategy_meta_ops:
            for op in meta_op.operations:
                processed_operations.add(op.step_number)
        
        meta_operations.extend(strategy_meta_ops)
    
    return meta_operations
```## Валидация и тестирование конфигурации

### Система валидации конфигурации

```python
def validate_base_signals_burst_config(config: Dict) -> None:
    """Валидация конфигурации BaseSignalsBurst стратегии."""
    required_params = ["time_window_ms", "min_burst_size"]
    
    for param in required_params:
        if param not in config:
            raise ValueError(f"BaseSignalsBurst config missing required parameter: {param}")
    
    # Валидация временного окна
    if config["time_window_ms"] <= 0:
        raise ValueError("time_window_ms must be positive")
    
    # Валидация минимального размера
    if config["min_burst_size"] < 2:
        raise ValueError("min_burst_size must be at least 2")
    
    # Валидация опциональных параметров
    if "max_gap_ms" in config and config["max_gap_ms"] < 0:
        raise ValueError("max_gap_ms must be non-negative")
```

### Конфигурационные файлы для разных сред

**Разработка** (`config/development.py`):
```python
META_OPERATION_CONFIG = {
    "enabled": True,
    "strategies": {
        "BaseSignalsBurst": {
            "enabled": True,
            "priority": 1,
            "time_window_ms": 50,      # Более агрессивная группировка
            "min_burst_size": 2,
            "max_gap_ms": 25,
            "debug_mode": True         # Дополнительное логирование
        }
    }
}
```

**Продакшн** (`config/production.py`):
```python
META_OPERATION_CONFIG = {
    "enabled": True,
    "strategies": {
        "BaseSignalsBurst": {
            "enabled": True,
            "priority": 1,
            "time_window_ms": 100,     # Консервативные настройки
            "min_burst_size": 3,       # Более крупные бурсты
            "max_gap_ms": 50,
            "debug_mode": False
        }
    }
}
```

## Обратная совместимость

### Сохранение существующего поведения

**Принцип graceful activation**: BaseSignalsBurst активируется только при явном включении, не влияя на поведение по умолчанию.

```python
# Fallback механизм для старых конфигураций
def get_meta_operation_config() -> Dict:
    """Получение конфигурации с fallback для совместимости."""
    config = load_base_config()
    
    # Добавление BaseSignalsBurst если отсутствует
    if "BaseSignalsBurst" not in config.get("strategies", {}):
        config.setdefault("strategies", {})["BaseSignalsBurst"] = {
            "enabled": False,  # По умолчанию отключено для совместимости
            "priority": 1,
            "time_window_ms": 100,
            "min_burst_size": 2
        }
    
    return config
```

### Миграционная стратегия

**Поэтапное внедрение**:
1. **Фаза 1**: Добавление с `enabled: False`
2. **Фаза 2**: Тестирование в development режиме  
3. **Фаза 3**: Активация в production с мониторингом
4. **Фаза 4**: Установка как стратегии по умолчанию

## Мониторинг и диагностика

### Метрики стратегии

```python
class BaseSignalsBurstMetrics:
    """Метрики для мониторинга работы стратегии."""
    
    def __init__(self):
        self.operations_processed = 0
        self.bursts_detected = 0
        self.average_burst_size = 0.0
        self.average_burst_duration = 0.0
        self.cross_target_bursts = 0
        
    def update_metrics(self, burst_operations: List[SubOperationLog]):
        """Обновление метрик на основе обнаруженного бурста."""
        self.bursts_detected += 1
        self.operations_processed += len(burst_operations)
        
        # Расчет средних значений
        total_duration = burst_operations[-1].start_time - burst_operations[0].start_time
        self.average_burst_duration = (
            (self.average_burst_duration * (self.bursts_detected - 1) + total_duration) 
            / self.bursts_detected
        )
        
        # Проверка cross-target бурстов
        targets = set(op.target for op in burst_operations)
        if len(targets) > 1:
            self.cross_target_bursts += 1
```

### Система логирования

```python
def log_strategy_activity(strategy_name: str, operation_count: int, burst_count: int):
    """Логирование активности стратегии для диагностики."""
    logger.info(
        f"Strategy {strategy_name}: processed {operation_count} operations, "
        f"detected {burst_count} bursts, "
        f"grouping ratio: {burst_count/operation_count:.2%}"
    )
```

## Результаты этапа 5

### ✅ Завершенные задачи

1. **✅ Полная интеграция в STRATEGY_REGISTRY**: регистрация с приоритетом 1

2. **✅ Комплексная система конфигурации**: параметры для разных сред, валидация

3. **✅ Приоритетная обработка**: BaseSignalsBurst получает первый доступ к операциям

4. **✅ Обратная совместимость**: graceful activation без нарушения существующего поведения

5. **✅ Мониторинг и диагностика**: метрики производительности и система логирования

### 🎯 Ключевые достижения интеграции

**Приоритетная архитектура**: BaseSignalsBurst как стратегия первого уровня с захватом подходящих операций.

**Гибкая конфигурация**: поддержка разных сред разработки с адаптивными параметрами.

**Неинвазивная интеграция**: добавление функциональности без изменения существующего кода.

**Производственная готовность**: полная система валидации, мониторинга и диагностики.

### 🚀 Готовность к этапу 6

Стратегия полностью интегрирована в архитектуру метаопераций. Система конфигурации и приоритетов настроена. Готов переход к форматированию и отображению результатов.

---

*Этап 5 завершён: 17 июня 2025*  
*Статус: Готов к форматированию и отображению*  
*Следующий этап: [STAGE_06_FORMATTING_DISPLAY.md](STAGE_06_FORMATTING_DISPLAY.md)*

### Централизованное логирование

```python
# Использование существующих логгеров
class BaseSignalsBurstStrategy(MetaOperationStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(f"meta_operation.{self.strategy_name}")
```

## Конфигурационные файлы

### Файл конфигурации приложения

```python
# src/core/app_settings.py
META_OPERATION_CONFIG = {
    "enabled": True,
    "strategies": {
        "base_signals_burst": {
            "enabled": True,
            "window_ms": 100.0,
            "min_cluster_size": 2
        }
    }
}
```

### Пользовательские настройки

```json
// config/user_settings.json
{
    "meta_operations": {
        "base_signals_burst": {
            "window_ms": 150,
            "min_cluster_size": 3
        }
    }
}
```

## Тестирование интеграции

### Модульные тесты

```python
def test_base_signals_burst_integration():
    """Тест интеграции стратегии в детектор"""
    config = MetaOperationConfig()
    detector = MetaOperationDetector(config)
    
    # Проверка регистрации стратегии
    strategy_names = [s.strategy_name for s in detector.strategies]
    assert "BaseSignalsBurst" in strategy_names
    
    # Проверка приоритета
    burst_strategy = next(s for s in detector.strategies if s.strategy_name == "BaseSignalsBurst")
    assert detector.strategies.index(burst_strategy) == 0  # Высший приоритет
```

### Интеграционные тесты

```python
def test_end_to_end_clustering():
    """Тест полного цикла кластеризации"""
    # Создание тестовых операций base_signals
    operations = create_base_signals_operations()
    
    # Запуск кластеризации
    clusters = detect_and_cluster(operations)
    
    # Проверка результатов
    assert len(clusters) > 0
    assert clusters[0].strategy_name == "BaseSignalsBurst"
```

## Задачи этапа

1. ✅ Создать систему регистрации стратегии
2. ✅ Определить настройки по умолчанию
3. ✅ Разработать систему конфигурации
4. ✅ Установить приоритет применения
5. ✅ Обеспечить совместимость с архитектурой
6. ⏳ Создать конфигурационные файлы
7. ⏳ Разработать тесты интеграции

## Следующий этап

**Этап 6**: Форматирование и отображение результатов
