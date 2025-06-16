# Этап 3: Архитектурное решение и интерфейсы

## Общий подход к архитектуре

Новый модуль будет реализован в виде компонента пост-обработки, который интегрируется в существующий процесс логирования **после** сбора данных операций, но **до** форматирования и вывода в файл. Согласно текущему жизненному циклу операции, после финализации операции на шаге 8 формируется форматированный лог и он отправляется в AggregatedOperationLogger для записи. Мы вставим этап кластеризации метаопераций между финализацией операции и форматированием лога.

### Преимущества выбранного подхода:
- **Неинвазивность**: Не затрагивает перехват `handle_request_cycle`, декоратор `@operation` или сбор данных
- **Полнота информации**: Вся информация о операциях уже собрана
- **Гибкость представления**: Представление ещё не зафиксировано в тексте
- **Обратная совместимость**: Легко отключить без изменения основной логики

## Основные компоненты архитектуры

### 1. Интерфейс MetaOperationDetector

Определяет контракт на обнаружение метаопераций:

```python
from abc import ABC, abstractmethod
from typing import Optional
from src.core.log_aggregator.operation_log import OperationLog

class MetaOperationDetector(ABC):
    """Абстрактный интерфейс для детекторов метаопераций"""
    
    @abstractmethod
    def detect_meta_operations(self, operation_log: OperationLog) -> None:
        """
        Основной метод обнаружения метаопераций.
        
        Args:
            operation_log: Завершённый лог операции для анализа
            
        Note:
            Метод изменяет operation_log напрямую, добавляя найденные
            метаоперации в поле meta_operations
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Проверка, включен ли детектор"""
        pass
```

### 2. Интерфейс стратегии кластеризации

Базовый класс для всех эвристик:

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from src.core.log_aggregator.sub_operation_log import SubOperationLog
from src.core.log_aggregator.operation_log import OperationLog

class MetaOperationStrategy(ABC):
    """Абстрактный базовый класс для стратегий кластеризации"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация стратегии с конфигурацией
        
        Args:
            config: Словарь параметров конфигурации для стратегии
        """
        self.config = config
        self.validate_config()
    
    @abstractmethod
    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Определяет, относится ли операция к метаоперации.
        
        Args:
            sub_op: Анализируемая подоперация
            context: Контекст всей операции для анализа
            
        Returns:
            Optional[str]: Идентификатор метаоперации или None
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> None:
        """Валидация параметров конфигурации"""
        pass
    
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Имя стратегии для идентификации"""
        pass
    
    def get_meta_operation_description(self, meta_id: str, operations: list) -> str:
        """
        Формирует описание метаоперации для вывода
        
        Args:
            meta_id: Идентификатор метаоперации
            operations: Список операций в группе
            
        Returns:
            str: Описательное название метаоперации
        """
        return f"{self.strategy_name}_{meta_id}"
```

### 3. Структура данных MetaOperation

Представление найденных кластеров:

```python
from dataclasses import dataclass, field
from typing import List, Optional
from src.core.log_aggregator.sub_operation_log import SubOperationLog

@dataclass
class MetaOperation:
    """Структура данных для представления метаоперации"""
    
    meta_id: str                                    # Уникальный идентификатор группы
    strategy_name: str                              # Имя стратегии, создавшей группу
    description: str                                # Описательное название
    sub_operations: List[SubOperationLog] = field(default_factory=list)  # Операции в группе
    start_time: Optional[float] = None              # Время начала первой операции
    end_time: Optional[float] = None                # Время завершения последней операции
    total_execution_time: Optional[float] = None    # Общее время выполнения группы
    success_count: int = 0                          # Количество успешных операций
    error_count: int = 0                            # Количество ошибок
    
    def __post_init__(self):
        """Автоматический расчёт метрик после инициализации"""
        if self.sub_operations:
            self.calculate_metrics()
    
    def calculate_metrics(self) -> None:
        """Вычисление метрик производительности группы"""
        if not self.sub_operations:
            return
            
        # Временные метрики
        self.start_time = min(op.start_time for op in self.sub_operations)
        self.end_time = max(op.end_time or op.start_time for op in self.sub_operations)
        self.total_execution_time = sum(op.execution_time or 0 for op in self.sub_operations)
        
        # Счётчики статусов
        self.success_count = sum(1 for op in self.sub_operations if op.status == "OK")
        self.error_count = sum(1 for op in self.sub_operations if op.status == "Error")
    
    @property
    def operations_count(self) -> int:
        """Общее количество операций в группе"""
        return len(self.sub_operations)
    
    @property
    def duration_ms(self) -> float:
        """Продолжительность группы в миллисекундах"""
        if self.start_time is not None and self.end_time is not None:
            return (self.end_time - self.start_time) * 1000
        return 0.0
```

### 4. Контейнер плагинов (MetaOperationDetectorImpl)

Основная реализация детектора, объединяющая стратегии:

```python
from typing import List, Dict, Any
import logging
from src.core.log_aggregator.operation_log import OperationLog

class MetaOperationDetectorImpl(MetaOperationDetector):
    """Основная реализация детектора метаопераций"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация детектора с конфигурацией
        
        Args:
            config: Конфигурация с настройками стратегий
        """
        self.config = config
        self.enabled = config.get("enabled", False)
        self.strategies: List[MetaOperationStrategy] = []
        self.logger = logging.getLogger(__name__)
        
        if self.enabled:
            self._load_strategies()
    
    def _load_strategies(self) -> None:
        """Загрузка и инициализация стратегий из конфигурации"""
        strategies_config = self.config.get("strategies", [])
        
        for strategy_config in strategies_config:
            try:
                strategy_class = self._get_strategy_class(strategy_config["name"])
                strategy = strategy_class(strategy_config.get("params", {}))
                self.strategies.append(strategy)
                self.logger.debug(f"Loaded strategy: {strategy.strategy_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load strategy {strategy_config['name']}: {e}")
    
    def _get_strategy_class(self, strategy_name: str) -> type:
        """
        Получение класса стратегии по имени
        
        Args:
            strategy_name: Имя стратегии для загрузки
            
        Returns:
            type: Класс стратегии
        """
        # Фабрика стратегий - мапинг имён на классы
        strategy_mapping = {
            "TimeWindowStrategy": TimeWindowStrategy,
            "TargetClusterStrategy": TargetClusterStrategy,
            "NameSimilarityStrategy": NameSimilarityStrategy,
            "SequenceCountStrategy": SequenceCountStrategy,
            "FrequencyThresholdStrategy": FrequencyThresholdStrategy,
        }
        
        if strategy_name not in strategy_mapping:
            raise ValueError(f"Unknown strategy: {strategy_name}")
            
        return strategy_mapping[strategy_name]
    
    def detect_meta_operations(self, operation_log: OperationLog) -> None:
        """
        Обнаружение метаопераций в логе операции
        
        Args:
            operation_log: Лог операции для анализа
        """
        if not self.enabled or not self.strategies:
            return
        
        # Словарь для накопления групп: {meta_op_id: MetaOperation}
        meta_operations_dict: Dict[str, MetaOperation] = {}
        
        # Проход по всем подоперациям
        for sub_op in operation_log.sub_operations:
            for strategy in self.strategies:
                try:
                    meta_id = strategy.detect(sub_op, operation_log)
                    if meta_id:
                        # Создаём или дополняем метаоперацию
                        if meta_id not in meta_operations_dict:
                            meta_operations_dict[meta_id] = MetaOperation(
                                meta_id=meta_id,
                                strategy_name=strategy.strategy_name,
                                description=strategy.get_meta_operation_description(meta_id, [sub_op])
                            )
                        
                        meta_operations_dict[meta_id].sub_operations.append(sub_op)
                        break  # Приоритет первой сработавшей стратегии
                        
                except Exception as e:
                    self.logger.warning(f"Strategy {strategy.strategy_name} failed: {e}")
        
        # Финализация метаопераций
        meta_operations = list(meta_operations_dict.values())
        for meta_op in meta_operations:
            meta_op.calculate_metrics()
        
        # Добавление в operation_log
        operation_log.meta_operations = meta_operations
        
        if meta_operations:
            self.logger.debug(f"Detected {len(meta_operations)} meta-operations")
    
    def is_enabled(self) -> bool:
        """Проверка состояния детектора"""
        return self.enabled
```

## Интеграция в существующую систему

### Модификация OperationLog

Добавление поля для метаопераций в существующую структуру:

```python
# В src/core/log_aggregator/operation_log.py

from dataclasses import dataclass, field
from typing import List, Optional
# ...existing imports...

@dataclass
class OperationLog:
    operation_name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: str = "running"
    execution_time: Optional[float] = None
    exception_info: Optional[str] = None
    sub_operations: List[SubOperationLog] = field(default_factory=list)
    
    # Новое поле для метаопераций
    meta_operations: List[MetaOperation] = field(default_factory=list)
    
    # ...existing methods...
```

### Модификация AggregatedOperationLogger

Интеграция детектора в процесс логирования:

```python
# В src/core/log_aggregator/aggregated_operation_logger.py

class AggregatedOperationLogger:
    def __init__(self):
        # ...existing initialization...
        
        # Инициализация детектора метаопераций
        self._meta_detector = self._create_meta_detector()
    
    def _create_meta_detector(self) -> Optional[MetaOperationDetector]:
        """Создание детектора метаопераций из конфигурации"""
        try:
            from src.core.logger_config import META_OPERATION_CONFIG
            return MetaOperationDetectorImpl(META_OPERATION_CONFIG)
        except ImportError:
            logger.warning("Meta-operation config not found, feature disabled")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize meta-operation detector: {e}")
            return None
    
    def log_operation(self, operation_log: OperationLog) -> None:
        """
        Логирование операции с опциональной кластеризацией
        
        Args:
            operation_log: Лог операции для записи
        """
        # Применение кластеризации метаопераций
        if self._meta_detector and self._meta_detector.is_enabled():
            try:
                self._meta_detector.detect_meta_operations(operation_log)
            except Exception as e:
                # Ошибки кластеризации не должны прерывать логирование
                logger.warning(f"Meta-operation detection failed: {e}")
        
        # Существующая логика форматирования и записи
        formatted_log = self._formatter.format_operation_log(operation_log)
        self._aggregated_logger.info(formatted_log)
```

## Конфигурация системы

### Файл конфигурации

Добавление в `src/core/logger_config.py`:

```python
# Конфигурация модуля кластеризации метаопераций
META_OPERATION_CONFIG = {
    "enabled": True,  # Глобальное включение/выключение
    "debug_mode": False,  # Подробное логирование работы модуля
    
    "strategies": [
        {
            "name": "TimeWindowStrategy",
            "priority": 1,
            "params": {
                "time_window_ms": 50,
                "min_operations": 2
            }
        },
        {
            "name": "TargetClusterStrategy",
            "priority": 2, 
            "params": {
                "target_list": ["file_data", "series_data", "calculation_data"],
                "max_gap": 1,
                "strict_sequence": False
            }
        },
        {
            "name": "NameSimilarityStrategy",
            "priority": 3,
            "params": {
                "name_pattern": "GET_.*|SET_.*|UPDATE_.*",
                "prefix_length": 3,
                "case_sensitive": False
            }
        }
    ],
    
    # Настройки форматирования
    "formatting": {
        "compact_view": True,  # Компактное отображение метаопераций
        "show_individual_ops": False,  # Показывать ли отдельные операции внутри групп
        "max_operations_inline": 5  # Максимум операций для inline отображения
    }
}
```

### Система отключения

Возможность полного отключения функциональности:

```python
# Полное отключение
META_OPERATION_CONFIG = {
    "enabled": False
}

# Отключение всех стратегий (система работает, но ничего не группирует)
META_OPERATION_CONFIG = {
    "enabled": True,
    "strategies": []
}

# Отключение конкретной стратегии
# Удалить нужную стратегию из списка strategies
```

## Преимущества архитектуры

### 1. Модульность и расширяемость
- **Плагинная архитектура**: Легко добавлять новые стратегии
- **Независимые компоненты**: Стратегии не зависят друг от друга
- **Конфигурируемость**: Гибкая настройка через конфигурационные файлы

### 2. Производительность
- **Ленивая инициализация**: Детектор создаётся только при необходимости
- **Опциональность**: Можно полностью отключить без влияния на производительность
- **Эффективные алгоритмы**: Однопроходные алгоритмы с минимальными накладными расходами

### 3. Надёжность
- **Graceful degradation**: Ошибки кластеризации не влияют на основное логирование
- **Изоляция**: Модуль изолирован от основной логики приложения
- **Обратная совместимость**: Старые логи остаются читаемыми

### 4. Удобство использования
- **Прозрачная интеграция**: Не требует изменений в бизнес-коде
- **Гибкая конфигурация**: Настройка под различные сценарии использования
- **Отладочные возможности**: Подробное логирование работы модуля

## Следующий этап

**Этап 4**: Детальная логика работы детектора - реализация конкретных стратегий и алгоритмов кластеризации.
