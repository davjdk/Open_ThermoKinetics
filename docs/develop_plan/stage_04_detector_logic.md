# Этап 4: Детальная логика работы детектора

## Логика работы модульного детектора

При вызове `MetaOperationDetector.detect_meta_operations(operation_log)` выполняются следующие шаги:

### 1. Инициализация процесса

```python
def detect_meta_operations(self, operation_log: OperationLog) -> None:
    """Основной алгоритм обнаружения метаопераций"""
    
    # Проверка предусловий
    if not self.enabled or not self.strategies or not operation_log.sub_operations:
        return
    
    # Создание контейнера для обнаруженных групп
    meta_operations_dict: Dict[str, MetaOperation] = {}
    operation_assignments: Dict[int, str] = {}  # step_number -> meta_op_id
    
    # Подготовка контекста для стратегий
    context = self._prepare_analysis_context(operation_log)
```

### 2. Анализ операций с применением стратегий

```python
def _analyze_operations_with_strategies(
    self, 
    operation_log: OperationLog,
    meta_operations_dict: Dict[str, MetaOperation],
    operation_assignments: Dict[int, str]
) -> None:
    """Применение стратегий к операциям для обнаружения групп"""
    
    for sub_op in operation_log.sub_operations:
        # Проверка, не была ли операция уже назначена
        if sub_op.step_number in operation_assignments:
            continue
            
        # Применение стратегий в порядке приоритета
        for strategy in self.strategies:
            try:
                meta_id = strategy.detect(sub_op, operation_log)
                if meta_id:
                    # Операция найдена для группировки
                    self._assign_operation_to_meta(
                        sub_op, meta_id, strategy, 
                        meta_operations_dict, operation_assignments
                    )
                    break  # Приоритет первой сработавшей стратегии
                    
            except Exception as e:
                self.logger.warning(
                    f"Strategy {strategy.strategy_name} failed for operation "
                    f"{sub_op.step_number}: {e}"
                )
```

### 3. Назначение операций в метагруппы

```python
def _assign_operation_to_meta(
    self,
    sub_op: SubOperationLog,
    meta_id: str,
    strategy: MetaOperationStrategy,
    meta_operations_dict: Dict[str, MetaOperation],
    operation_assignments: Dict[int, str]
) -> None:
    """Назначение операции в метагруппу"""
    
    # Создание новой метаоперации при необходимости
    if meta_id not in meta_operations_dict:
        meta_operations_dict[meta_id] = MetaOperation(
            meta_id=meta_id,
            strategy_name=strategy.strategy_name,
            description=strategy.get_meta_operation_description(meta_id, [sub_op])
        )
    
    # Добавление операции в группу
    meta_operations_dict[meta_id].sub_operations.append(sub_op)
    operation_assignments[sub_op.step_number] = meta_id
    
    # Логирование для отладки
    if self.config.get("debug_mode", False):
        self.logger.debug(
            f"Operation {sub_op.step_number} ({sub_op.operation_name}) "
            f"assigned to meta-operation '{meta_id}' by {strategy.strategy_name}"
        )
```

### 4. Пост-обработка и финализация

```python
def _finalize_meta_operations(
    self, 
    operation_log: OperationLog,
    meta_operations_dict: Dict[str, MetaOperation]
) -> None:
    """Финализация обнаруженных метаопераций"""
    
    # Фильтрация групп по минимальному размеру
    valid_meta_operations = []
    min_group_size = self.config.get("min_group_size", 2)
    
    for meta_op in meta_operations_dict.values():
        if len(meta_op.sub_operations) >= min_group_size:
            # Сортировка операций по step_number
            meta_op.sub_operations.sort(key=lambda op: op.step_number)
            
            # Вычисление метрик
            meta_op.calculate_metrics()
            
            # Обновление описания с учётом финальных данных
            meta_op.description = self._generate_final_description(meta_op)
            
            valid_meta_operations.append(meta_op)
        else:
            # Логирование отфильтрованных групп
            self.logger.debug(
                f"Meta-operation '{meta_op.meta_id}' filtered out: "
                f"size {len(meta_op.sub_operations)} < {min_group_size}"
            )
    
    # Сортировка метаопераций по времени начала
    valid_meta_operations.sort(key=lambda mo: mo.start_time or 0)
    
    # Добавление в operation_log
    operation_log.meta_operations = valid_meta_operations
    
    # Статистика для отладки
    if self.config.get("debug_mode", False):
        self._log_detection_statistics(operation_log, meta_operations_dict)
```

## Реализация конкретных стратегий

### TimeWindowStrategy - Кластеризация по времени

```python
class TimeWindowStrategy(MetaOperationStrategy):
    """Стратегия группировки операций по временной близости"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.current_cluster_id: Optional[str] = None
        self.cluster_start_time: Optional[float] = None
        self.cluster_counter = 0
    
    def validate_config(self) -> None:
        """Валидация конфигурации"""
        required_params = ["time_window_ms"]
        for param in required_params:
            if param not in self.config:
                raise ValueError(f"TimeWindowStrategy requires parameter: {param}")
        
        if self.config["time_window_ms"] <= 0:
            raise ValueError("time_window_ms must be positive")
    
    @property
    def strategy_name(self) -> str:
        return "TimeWindow"
    
    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Детекция временных кластеров
        
        Алгоритм:
        1. Если это первая операция или прошло больше time_window_ms - начать новый кластер
        2. Иначе добавить в текущий кластер
        """
        window_ms = self.config["time_window_ms"]
        current_time = sub_op.start_time
        
        # Проверка необходимости нового кластера
        if (self.cluster_start_time is None or 
            (current_time - self.cluster_start_time) * 1000 > window_ms):
            
            # Начать новый кластер
            self.cluster_counter += 1
            self.current_cluster_id = f"time_cluster_{self.cluster_counter}"
            self.cluster_start_time = current_time
        
        return self.current_cluster_id
    
    def get_meta_operation_description(self, meta_id: str, operations: list) -> str:
        """Генерация описания временного кластера"""
        if len(operations) == 1:
            return f"Time cluster (window: {self.config['time_window_ms']}ms)"
        
        time_span = (operations[-1].start_time - operations[0].start_time) * 1000
        return f"Time cluster: {len(operations)} ops in {time_span:.1f}ms"
```

### TargetClusterStrategy - Кластеризация по целевому модулю

```python
class TargetClusterStrategy(MetaOperationStrategy):
    """Стратегия группировки операций по целевому модулю"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.current_target: Optional[str] = None
        self.current_cluster_id: Optional[str] = None
        self.gap_count = 0
        self.cluster_counter = 0
    
    def validate_config(self) -> None:
        """Валидация конфигурации"""
        self.target_list = self.config.get("target_list", [])
        self.max_gap = self.config.get("max_gap", 1)
        self.strict_sequence = self.config.get("strict_sequence", False)
        
        if self.max_gap < 0:
            raise ValueError("max_gap must be non-negative")
    
    @property
    def strategy_name(self) -> str:
        return "TargetCluster"
    
    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Детекция кластеров по target
        
        Алгоритм:
        1. Если target совпадает с текущим - продолжить кластер
        2. Если не совпадает, но gap_count < max_gap - увеличить счётчик
        3. Иначе начать новый кластер
        """
        target = sub_op.target
        
        # Фильтрация по списку целевых модулей
        if self.target_list and target not in self.target_list:
            return None
        
        # Логика кластеризации
        if target == self.current_target:
            # Продолжение текущего кластера
            self.gap_count = 0
            return self.current_cluster_id
            
        elif not self.strict_sequence and self.gap_count < self.max_gap:
            # Допустимый разрыв в последовательности
            self.gap_count += 1
            return self.current_cluster_id
            
        else:
            # Начало нового кластера
            self.cluster_counter += 1
            self.current_target = target
            self.current_cluster_id = f"target_{target}_{self.cluster_counter}"
            self.gap_count = 0
            return self.current_cluster_id
    
    def get_meta_operation_description(self, meta_id: str, operations: list) -> str:
        """Генерация описания кластера по target"""
        if not operations:
            return f"Target cluster: {meta_id}"
        
        target = operations[0].target
        op_count = len(operations)
        return f"Target '{target}' batch: {op_count} operations"
```

### NameSimilarityStrategy - Кластеризация по схожести имён

```python
import re
from typing import Set

class NameSimilarityStrategy(MetaOperationStrategy):
    """Стратегия группировки операций по схожести имён"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name_pattern = None
        self.current_prefix: Optional[str] = None
        self.current_cluster_id: Optional[str] = None
        self.cluster_counter = 0
    
    def validate_config(self) -> None:
        """Валидация конфигурации"""
        pattern = self.config.get("name_pattern")
        if pattern:
            try:
                self.name_pattern = re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
        
        self.prefix_length = self.config.get("prefix_length", 3)
        self.case_sensitive = self.config.get("case_sensitive", False)
        
        if self.prefix_length <= 0:
            raise ValueError("prefix_length must be positive")
    
    @property
    def strategy_name(self) -> str:
        return "NameSimilarity"
    
    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Детекция кластеров по схожести имён
        
        Алгоритм:
        1. Проверка соответствия regex-паттерну (если задан)
        2. Извлечение префикса операции
        3. Группировка операций с одинаковым префиксом
        """
        operation_name = sub_op.operation_name
        
        # Фильтрация по regex-паттерну
        if self.name_pattern and not self.name_pattern.match(operation_name):
            return None
        
        # Извлечение префикса
        prefix = self._extract_prefix(operation_name)
        if not prefix:
            return None
        
        # Логика кластеризации по префиксу
        if prefix == self.current_prefix:
            return self.current_cluster_id
        else:
            # Новый кластер
            self.cluster_counter += 1
            self.current_prefix = prefix
            self.current_cluster_id = f"name_{prefix}_{self.cluster_counter}"
            return self.current_cluster_id
    
    def _extract_prefix(self, operation_name: str) -> Optional[str]:
        """Извлечение префикса из имени операции"""
        if not self.case_sensitive:
            operation_name = operation_name.upper()
        
        # Попытка извлечения по разделителю '_'
        parts = operation_name.split('_')
        if len(parts) > 1:
            return parts[0]
        
        # Альтернативно - по заданной длине
        if len(operation_name) >= self.prefix_length:
            return operation_name[:self.prefix_length]
        
        return None
    
    def get_meta_operation_description(self, meta_id: str, operations: list) -> str:
        """Генерация описания кластера по схожести имён"""
        if not operations:
            return f"Name similarity cluster: {meta_id}"
        
        prefix = self._extract_prefix(operations[0].operation_name)
        op_count = len(operations)
        
        if prefix:
            return f"'{prefix}_*' operations: {op_count} calls"
        else:
            return f"Similar operations: {op_count} calls"
```

### SequenceCountStrategy - Кластеризация последовательностей

```python
class SequenceCountStrategy(MetaOperationStrategy):
    """Стратегия группировки последовательных одинаковых операций"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.current_operation_name: Optional[str] = None
        self.current_sequence_count = 0
        self.current_cluster_id: Optional[str] = None
        self.cluster_counter = 0
    
    def validate_config(self) -> None:
        """Валидация конфигурации"""
        self.min_sequence = self.config.get("min_sequence", 3)
        self.operation_types = set(self.config.get("operation_types", []))
        self.status_filter = set(self.config.get("status_filter", ["OK", "Error"]))
        
        if self.min_sequence < 2:
            raise ValueError("min_sequence must be at least 2")
    
    @property
    def strategy_name(self) -> str:
        return "SequenceCount"
    
    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Детекция последовательностей операций
        
        Алгоритм:
        1. Отслеживание последовательности одинаковых операций
        2. При достижении min_sequence - начать группировку
        3. При изменении типа операции - завершить группу
        """
        operation_name = sub_op.operation_name
        status = sub_op.status
        
        # Фильтрация по типам операций и статусам
        if (self.operation_types and operation_name not in self.operation_types) or \
           (self.status_filter and status not in self.status_filter):
            return None
        
        # Логика последовательности
        if operation_name == self.current_operation_name:
            # Продолжение последовательности
            self.current_sequence_count += 1
            
            # Начало группировки при достижении порога
            if (self.current_sequence_count >= self.min_sequence and 
                self.current_cluster_id is None):
                
                self.cluster_counter += 1
                self.current_cluster_id = f"sequence_{operation_name}_{self.cluster_counter}"
            
            return self.current_cluster_id
            
        else:
            # Изменение типа операции - завершение последовательности
            self.current_operation_name = operation_name
            self.current_sequence_count = 1
            self.current_cluster_id = None
            return None
    
    def get_meta_operation_description(self, meta_id: str, operations: list) -> str:
        """Генерация описания последовательности"""
        if not operations:
            return f"Operation sequence: {meta_id}"
        
        operation_name = operations[0].operation_name
        count = len(operations)
        status = operations[0].status
        
        return f"Repeated {operation_name} ({status}): {count} times"
```

## Обработка конфликтов и приоритизация

### Политика разрешения конфликтов

```python
def _resolve_strategy_conflicts(self, 
                              sub_op: SubOperationLog,
                              strategy_results: List[Tuple[str, str]]) -> Optional[str]:
    """
    Разрешение конфликтов когда несколько стратегий предлагают группировку
    
    Args:
        sub_op: Анализируемая операция
        strategy_results: Список (strategy_name, meta_id) от сработавших стратегий
        
    Returns:
        Optional[str]: Финальный meta_id или None
    """
    if not strategy_results:
        return None
    
    if len(strategy_results) == 1:
        return strategy_results[0][1]  # Единственный результат
    
    # Политика приоритизации (порядок стратегий в конфигурации)
    strategy_priority = {
        strategy.strategy_name: i 
        for i, strategy in enumerate(self.strategies)
    }
    
    # Выбор стратегии с наивысшим приоритетом
    best_strategy = min(
        strategy_results,
        key=lambda x: strategy_priority.get(x[0], float('inf'))
    )
    
    if self.config.get("debug_mode", False):
        self.logger.debug(
            f"Conflict resolved for operation {sub_op.step_number}: "
            f"chosen {best_strategy[0]} over {[s[0] for s in strategy_results[1:]]}"
        )
    
    return best_strategy[1]
```

### Статистика и диагностика

```python
def _log_detection_statistics(self, 
                             operation_log: OperationLog,
                             all_meta_operations: Dict[str, MetaOperation]) -> None:
    """Логирование статистики обнаружения для отладки"""
    
    total_operations = len(operation_log.sub_operations)
    total_meta_operations = len(operation_log.meta_operations)
    grouped_operations = sum(len(mo.sub_operations) for mo in operation_log.meta_operations)
    ungrouped_operations = total_operations - grouped_operations
    
    # Статистика по стратегиям
    strategy_stats = {}
    for meta_op in operation_log.meta_operations:
        strategy = meta_op.strategy_name
        strategy_stats[strategy] = strategy_stats.get(strategy, 0) + 1
    
    self.logger.debug(
        f"Meta-operation detection complete:\n"
        f"  Total operations: {total_operations}\n"
        f"  Meta-operations created: {total_meta_operations}\n"
        f"  Operations grouped: {grouped_operations}\n"
        f"  Operations ungrouped: {ungrouped_operations}\n"
        f"  Strategy statistics: {strategy_stats}"
    )
```

## Следующий этап

**Этап 5**: Форматирование и визуализация метаопераций - проектирование системы вывода кластеризованных логов в читаемом формате.
