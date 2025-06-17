# Этап 2: Реализация логики кластеризации подопераций

## Цель этапа  
Реализовать основную логику кластеризации операций `base_signals` по временным окнам, включая обработку промежуточных "шумовых" операций.

## Задачи

### 2.1 Алгоритм временной кластеризации

**Основная логика в методе detect():**

```python
def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
    """
    Обнаружение принадлежности операции к base_signals кластеру.
    
    Логика:
    1. Проверяем, является ли sub_op операцией base_signals
    2. Находим все близкие операции base_signals в временном окне
    3. Включаем промежуточные операции как шум
    4. Генерируем meta_id для кластера
    """
    if not self._is_base_signals_operation(sub_op):
        return None
    
    # Поиск операций base_signals в окне времени
    window_seconds = self.config["window_ms"] / 1000.0
    cluster_operations = self._find_time_window_cluster(sub_op, context, window_seconds)
    
    # Проверка минимального размера кластера
    min_size = self.config.get("min_cluster_size", 2)
    base_signals_count = sum(1 for op in cluster_operations 
                            if self._is_base_signals_operation(op))
    
    if base_signals_count < min_size:
        return None
    
    # Генерация уникального ID кластера
    return self._generate_cluster_id(cluster_operations[0])
```

### 2.2 Поиск операций в временном окне

```python
def _find_time_window_cluster(self, sub_op: SubOperationLog, 
                             context: OperationLog, 
                             window_seconds: float) -> List[SubOperationLog]:
    """
    Находит все операции в временном окне, включая промежуточные.
    
    Args:
        sub_op: Текущая операция base_signals
        context: Полный лог операции
        window_seconds: Размер временного окна в секундах
    
    Returns:
        List[SubOperationLog]: Операции в кластере (base_signals + шум)
    """
    if not sub_op.start_time:
        return [sub_op]
    
    cluster_ops = []
    base_signals_times = []
    
    # Сбор всех операций base_signals в окне
    for op in context.sub_operations:
        if not op.start_time:
            continue
            
        if self._is_base_signals_operation(op):
            time_diff = abs(op.start_time - sub_op.start_time)
            if time_diff <= window_seconds:
                base_signals_times.append(op.start_time)
                cluster_ops.append(op)
    
    # Если нашли только одну операцию base_signals - не кластер
    if len([op for op in cluster_ops if self._is_base_signals_operation(op)]) < 2:
        return []
    
    # Определение временных границ кластера
    min_time = min(base_signals_times)
    max_time = max(base_signals_times)
    
    # Добавление промежуточных операций (шум) 
    if self.config.get("include_noise", True):
        noise_ops = self._collect_noise_operations(context, min_time, max_time)
        cluster_ops.extend(noise_ops)
    
    # Сортировка по времени выполнения
    cluster_ops.sort(key=lambda x: x.start_time or 0)
    return cluster_ops
```

### 2.3 Сбор промежуточных операций (шум)

```python  
def _collect_noise_operations(self, context: OperationLog, 
                             min_time: float, max_time: float) -> List[SubOperationLog]:
    """
    Собирает операции других модулей между base_signals операциями.
    
    Args:
        context: Полный лог операции
        min_time: Начало временного интервала кластера
        max_time: Конец временного интервала кластера
    
    Returns:
        List[SubOperationLog]: Промежуточные операции (шум)
    """
    noise_operations = []
    
    for op in context.sub_operations:
        if not op.start_time:
            continue
            
        # Операция в временных границах кластера
        if min_time <= op.start_time <= max_time:
            # Но не является операцией base_signals
            if not self._is_base_signals_operation(op):
                noise_operations.append(op)
    
    return noise_operations
```

### 2.4 Генерация идентификаторов кластеров

```python
def _generate_cluster_id(self, first_operation: SubOperationLog) -> str:
    """
    Генерирует уникальный идентификатор для кластера.
    
    Args:
        first_operation: Первая операция кластера по времени
    
    Returns:
        str: Уникальный ID кластера
    """
    # Используем timestamp первой операции для уникальности
    timestamp = int(first_operation.start_time * 1000) if first_operation.start_time else 0
    return f"base_signals_burst_{timestamp}_{first_operation.step_number}"
```

### 2.5 Улучшенная проверка base_signals операций

```python
def _is_base_signals_operation(self, sub_op: SubOperationLog) -> bool:
    """
    Проверяет, относится ли операция к модулю base_signals.
    
    Анализирует поля target и operation_name для определения принадлежности.
    
    Args:
        sub_op: Подоперация для анализа
    
    Returns:
        bool: True если операция относится к base_signals
    """
    # Прямая проверка по target
    if sub_op.target == "base_signals":
        return True
    
    # Проверка по названию операции (может содержать базовые сигнальные операции)
    operation_lower = sub_op.operation_name.lower() if sub_op.operation_name else ""
    if "signal" in operation_lower or "request" in operation_lower:
        return True
    
    # Проверка по target (может быть составное имя)  
    target_lower = str(sub_op.target).lower() if sub_op.target else ""
    if "base_signals" in target_lower or "signals" in target_lower:
        return True
    
    return False
```

### 2.6 Предотвращение дублирования кластеров

```python
def _is_already_clustered(self, sub_op: SubOperationLog, context: OperationLog) -> bool:
    """
    Проверяет, не была ли операция уже включена в другой кластер.
    
    Предотвращает создание пересекающихся кластеров.
    """
    # Проверяем существующие мета-операции в контексте
    for meta_op in getattr(context, 'meta_operations', []):
        if any(op.step_number == sub_op.step_number for op in meta_op.sub_operations):
            return True
    return False
```

## Результат этапа
- Полная логика кластеризации операций base_signals  
- Обработка временных окон и пороговых значений
- Сбор и маркировка промежуточных операций как шума
- Предотвращение дублирования кластеров
- Уникальная генерация идентификаторов кластеров

## Файлы для изменения
- `src/core/log_aggregator/detection_strategies.py` - реализация методов

## Критерии готовности
- [ ] detect() возвращает валидные meta_id для операций base_signals
- [ ] Временное окно корректно обрабатывается (window_ms → секунды)
- [ ] Минимальный размер кластера проверяется
- [ ] Промежуточные операции собираются как шум
- [ ] Кластеры не пересекаются
- [ ] Идентификаторы кластеров уникальны
