# Этап 4: Интеграция в систему конфигурации и регистрация

## Цель этапа
Полная интеграция стратегии BaseSignalsBurstStrategy в существующую архитектуру метаопераций с поддержкой конфигурации, приоритизации и управления жизненным циклом.

## Задачи

### 4.1 Регистрация в STRATEGY_REGISTRY

**Обновление meta_operation_config.py:**

```python
# В классе MetaOperationConfig добавить:
STRATEGY_REGISTRY: Dict[str, Type[MetaOperationStrategy]] = {
    "time_window": TimeWindowStrategy,
    "name_similarity": NameSimilarityStrategy,
    "target_cluster": TargetClusterStrategy,
    "sequence_count": SequenceCountStrategy,
    "base_signals_burst": BaseSignalsBurstStrategy,  # НОВАЯ СТРАТЕГИЯ
}
```

### 4.2 Конфигурация по умолчанию

**Расширение DEFAULT_CONFIG:**

```python
DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    # ...существующие стратегии...
    "base_signals_burst": {
        "window_ms": 100.0,           # Временное окно кластеризации (мс)
        "min_cluster_size": 2,        # Минимум base_signals операций в кластере
        "include_noise": True,        # Включать промежуточные операции как шум
        "max_cluster_duration_ms": 5000,  # Максимальная длительность кластера (мс)
        "priority": 1,                # Высокий приоритет (выполняется первой)
    },
}
```

### 4.3 Приоритизация стратегии

**Добавление в предустановленные конфигурации:**

```python
PRESET_CONFIGS = {
    "comprehensive": {
        "enabled": True,
        "strategies": {
            "base_signals_burst": {
                "enabled": True,
                "priority": 1,          # Высокий приоритет
                "window_ms": 100.0,
                "min_cluster_size": 2,
                "include_noise": True,
            },
            "time_window": {
                "enabled": True,
                "priority": 2,          # Выполняется после base_signals_burst
                "window_ms": 50.0,
                "min_cluster_size": 2,
            },
            "target_cluster": {
                "enabled": True,
                "priority": 3,
                "min_cluster_size": 2,
            },
            # ...остальные стратегии...
        },
    },
    
    "base_signals_focused": {
        "enabled": True,
        "strategies": {
            "base_signals_burst": {
                "enabled": True,
                "window_ms": 150.0,     # Увеличенное окно для специализированного анализа
                "min_cluster_size": 1,  # Даже одиночные операции
                "include_noise": True,
                "max_cluster_duration_ms": 10000,
            },
        },
    },
}
```

### 4.4 Обновление импортов

**В detection_strategies.py добавить в конец файла:**

```python
# В самом конце файла после всех классов
__all__ = [
    'TimeWindowStrategy', 
    'NameSimilarityStrategy', 
    'TargetClusterStrategy', 
    'SequenceCountStrategy',
    'BaseSignalsBurstStrategy',  # НОВЫЙ ЭКСПОРТ
    'MetaOperationStrategy'
]
```

**В meta_operation_config.py обновить импорт:**

```python
from .detection_strategies import (
    NameSimilarityStrategy,
    SequenceCountStrategy,
    TargetClusterStrategy,
    TimeWindowStrategy,
    BaseSignalsBurstStrategy,  # НОВЫЙ ИМПОРТ
)
```

### 4.5 Конфигурация включения/отключения

**Поддержка runtime конфигурации:**

```python
# Пример использования в коде приложения
META_OPERATION_CONFIG = {
    "enabled": True,
    "strategies": {
        "base_signals_burst": {
            "enabled": True,              # Включить стратегию
            "window_ms": 80,             # Настроенное временное окно  
            "min_cluster_size": 2,       # Минимум 2 base_signals операций
            "include_noise": True,       # Включать шумовые операции
            "max_cluster_duration_ms": 3000,  # Лимит длительности
            "debug_mode": False,         # Отладочный режим (дополнительные логи)
        },
        # Отключение других стратегий для фокуса на base_signals
        "time_window": {"enabled": False},
        "target_cluster": {"enabled": False},
    },
    "formatting": {
        "table_format": "enhanced",
        "show_meta_operations": True,
        "compact_mode": False,
    }
}
```

### 4.6 Фабричные методы

**Расширение фабричных методов в MetaOperationConfig:**

```python
@classmethod
def create_base_signals_detector(cls, 
                                window_ms: float = 100.0,
                                min_cluster_size: int = 2,
                                include_noise: bool = True) -> MetaOperationDetector:
    """
    Создает детектор, сфокусированный на анализе base_signals операций.
    
    Args:
        window_ms: Временное окно кластеризации
        min_cluster_size: Минимальное количество base_signals операций в кластере
        include_noise: Включать ли промежуточные операции
    
    Returns:
        MetaOperationDetector: Настроенный детектор
    """
    config = {
        "enabled": True,
        "strategies": {
            "base_signals_burst": {
                "enabled": True,
                "window_ms": window_ms,
                "min_cluster_size": min_cluster_size,
                "include_noise": include_noise,
                "priority": 1,
            }
        }
    }
    
    return cls.create_detector(config)

@classmethod  
def create_hybrid_detector(cls) -> MetaOperationDetector:
    """
    Создает детектор с комбинацией base_signals и общих стратегий.
    
    Returns:
        MetaOperationDetector: Гибридный детектор
    """
    return cls.create_detector(cls.PRESET_CONFIGS["comprehensive"])
```

### 4.7 Валидация конфигурации стратегии

**Расширенная валидация в BaseSignalsBurstStrategy:**

```python
def validate_config(self) -> None:
    """Расширенная валидация конфигурации стратегии."""
    # Базовые обязательные параметры
    required_params = ["window_ms", "min_cluster_size"]
    for param in required_params:
        if param not in self.config:
            raise ValueError(f"BaseSignalsBurstStrategy missing required parameter: {param}")
    
    # Валидация типов и диапазонов
    window_ms = self.config["window_ms"]
    if not isinstance(window_ms, (int, float)) or window_ms <= 0:
        raise ValueError("BaseSignalsBurstStrategy window_ms must be positive number")
    
    min_cluster_size = self.config["min_cluster_size"]
    if not isinstance(min_cluster_size, int) or min_cluster_size < 1:
        raise ValueError("BaseSignalsBurstStrategy min_cluster_size must be integer >= 1")
    
    # Валидация опциональных параметров
    if "max_cluster_duration_ms" in self.config:
        max_duration = self.config["max_cluster_duration_ms"]
        if not isinstance(max_duration, (int, float)) or max_duration <= 0:
            raise ValueError("BaseSignalsBurstStrategy max_cluster_duration_ms must be positive")
        
        # Логическая проверка: максимальная длительность должна быть больше окна
        if max_duration < window_ms:
            raise ValueError("max_cluster_duration_ms must be >= window_ms")
    
    if "include_noise" in self.config:
        if not isinstance(self.config["include_noise"], bool):
            raise ValueError("BaseSignalsBurstStrategy include_noise must be boolean")
```

### 4.8 Документация конфигурации

**Добавление в configuration_examples.py:**

```python
# Пример конфигурации BaseSignalsMetaBurst
BASE_SIGNALS_BURST_EXAMPLES = {
    "minimal": {
        "base_signals_burst": {
            "enabled": True,
            "window_ms": 100.0,
            "min_cluster_size": 2,
        }
    },
    
    "detailed": {
        "base_signals_burst": {
            "enabled": True,
            "window_ms": 80.0,
            "min_cluster_size": 2,
            "include_noise": True,
            "max_cluster_duration_ms": 5000,
            "priority": 1,
        }
    },
    
    "permissive": {
        "base_signals_burst": {
            "enabled": True,
            "window_ms": 200.0,        # Большое окно
            "min_cluster_size": 1,     # Даже одиночные операции
            "include_noise": True,
            "max_cluster_duration_ms": 10000,
        }
    },
}
```

## Результат этапа
- Полная интеграция стратегии в систему конфигурации
- Поддержка различных режимов работы через конфигурацию
- Корректная приоритизация относительно других стратегий  
- Фабричные методы для упрощения создания детекторов
- Расширенная валидация конфигурационных параметров
- Документация и примеры использования

## Файлы для изменения
- `src/core/log_aggregator/meta_operation_config.py` - регистрация и конфигурация
- `src/core/log_aggregator/detection_strategies.py` - обновление экспортов
- `src/core/log_aggregator/configuration_examples.py` - примеры конфигураций

## Критерии готовности  
- [ ] Стратегия зарегистрирована в STRATEGY_REGISTRY
- [ ] DEFAULT_CONFIG содержит конфигурацию base_signals_burst
- [ ] Предустановленные конфигурации включают новую стратегию
- [ ] Импорты и экспорты обновлены
- [ ] Фабричные методы работают корректно
- [ ] Валидация конфигурации покрывает все параметры
- [ ] Документация и примеры добавлены
