# Этап 2: Условия и логика кластеризации BaseSignalsBurst

## Обновленная логика на основе архитектурного анализа

### Фундаментальные критерии идентификации

**Операции BaseSignals определяются через**:
```python
def is_base_signals_operation(sub_op: SubOperationLog) -> bool:
    """Критерии идентификации base_signals операций."""
    return (
        sub_op.caller_info.filename == "base_signals.py" and
        sub_op.caller_info.line_number == 51 and
        len(sub_op.sub_operations) == 0 and  # Атомарность
        sub_op.duration_ms <= 10.0  # Микрооперации
    )
```

**Целевые типы операций**:
- `SET_VALUE` - установка значений в структурах данных
- `GET_VALUE` - получение значений из модулей  
- `UPDATE_VALUE` - обновление существующих параметров
- `CHECK_*` - валидационные операции
- `LOAD_*` / `SAVE_*` - операции с данными

### Context-Aware временная группировка

**Принцип кластеризации**: операции группируются не только по временной близости, но и по принадлежности к одному thread-local контексту операции.

```python
def group_by_temporal_and_contextual_proximity(candidates: List[SubOperationLog], 
                                               context: OperationLog) -> List[List[SubOperationLog]]:
    """
    Группировка операций по временной близости И контекстной связанности.
    
    Args:
        candidates: Отфильтрованные base_signals операции
        context: Полный контекст родительской операции
    """
    # Все кандидаты уже принадлежат одному контексту (thread-local operation)
    # Поэтому группируем только по времени
    
    window_ms = config["time_window_ms"] / 1000.0  # 100ms default
    max_gap_ms = config.get("max_gap_ms", 50) / 1000.0  # 50ms max gap
    
    clusters = []
    current_cluster = []
    
    candidates.sort(key=lambda op: op.start_time)
    
    for op in candidates:
        if not current_cluster:
            current_cluster = [op]
        else:
            last_op = current_cluster[-1]
            gap = op.start_time - last_op.start_time
            
            if gap <= window_ms and gap <= max_gap_ms:
                current_cluster.append(op)
            else:
                # Завершить текущий кластер если он достаточно большой
                if len(current_cluster) >= config.get("min_burst_size", 2):
                    clusters.append(current_cluster)
                current_cluster = [op]
    
    # Финальный кластер
    if len(current_cluster) >= config.get("min_burst_size", 2):
        clusters.append(current_cluster)
    
    return clusters
```

## Реальные паттерны бурстов (из архитектурного анализа)

### Паттерн 1: Parameter Update Burst (UPDATE_VALUE операции)
```log
Временной ряд: t+0ms, t+15ms, t+32ms, t+45ms
base_signals.py:51 "GET_VALUE"      → calculations_data    # Получение текущего значения
base_signals.py:51 "CHECK_PATH"     → calculations_data    # Валидация path_keys
base_signals.py:51 "SET_VALUE"      → calculations_data    # Установка нового значения  
base_signals.py:51 "UPDATE_VALUE"   → calculations_data    # Обновление зависимых параметров

Реальный актор: main_window.py:456 "_handle_update_value"
Бурст создается: 4 операции, 45ms, 100% успешно
```

### Паттерн 2: Add Reaction Burst (ADD_REACTION операции)
```log
Временной ряд: t+0ms, t+8ms, t+12ms, t+18ms, t+25ms
base_signals.py:51 "SET_VALUE"      → calculations_data    # Создание структуры реакции
base_signals.py:51 "GET_VALUE"      → calculations_data    # Получение параметров
base_signals.py:51 "UPDATE_VALUE"   → calculations_data    # Обновление коэффициентов
base_signals.py:51 "SET_VALUE"      → calculations_data    # Установка границ оптимизации
base_signals.py:51 "UPDATE_VALUE"   → calculations_data    # Финальное обновление

Реальный актор: main_window.py:439 "_handle_add_reaction"  
Бурст создается: 5 операций, 25ms, 100% успешно
```

### Паттерн 3: Multi-target Burst (смешанные операции)
```log
Временной ряд: t+0ms, t+5ms, t+18ms
base_signals.py:51 "GET_DF_DATA"    → file_data           # Получение данных для визуализации
base_signals.py:51 "GET_VALUE"      → calculations_data    # Получение параметров реакции
base_signals.py:51 "HIGHLIGHT_*"    → calculations_data    # Активация подсветки

Реальный актор: main_window.py:446 "_handle_highlight_reaction"
Бурст создается: 3 операции, 18ms, смешанные targets
```

## Обновленный алгоритм кластеризации

### Основная функция detect()

```python
def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
    """
    Обнаружение принадлежности операции к BaseSignals burst.
    
    Args:
        sub_op: Анализируемая подоперация
        context: Полный контекст родительской операции
        
    Returns:
        meta_id если операция принадлежит бурсту, иначе None
    """
    # Фильтрация: только base_signals операции
    if not self._is_base_signals_operation(sub_op):
        return None
    
    # Поиск всех base_signals операций в контексте
    base_signals_ops = [
        op for op in context.sub_operations 
        if self._is_base_signals_operation(op)
    ]
    
    # Группировка по временной близости
    clusters = self._group_by_temporal_proximity(base_signals_ops)
    
    # Найти кластер, содержащий текущую операцию
    for i, cluster in enumerate(clusters):
        if sub_op in cluster:
            # Генерация стабильного meta_id на основе первой операции кластера
            first_op = min(cluster, key=lambda op: op.start_time)
            meta_id = f"base_signals_burst_{int(first_op.start_time * 1000)}_{i}"
            return meta_id
    
    return None
```

### Вспомогательные функции

```python
def _is_base_signals_operation(self, sub_op: SubOperationLog) -> bool:
    """Проверка является ли операция base_signals операцией."""
    return (
        sub_op.caller_info.filename == "base_signals.py" and
        sub_op.caller_info.line_number == 51 and
        len(sub_op.sub_operations) == 0 and
        sub_op.duration_ms <= self.config.get("max_duration_ms", 10.0)
    )

def _group_by_temporal_proximity(self, operations: List[SubOperationLog]) -> List[List[SubOperationLog]]:
    """Группировка операций по временной близости."""
    if not operations:
        return []
    
    operations.sort(key=lambda op: op.start_time)
    
    clusters = []
    current_cluster = [operations[0]]
    
    for op in operations[1:]:
        gap = op.start_time - current_cluster[-1].start_time
        window_sec = self.config["time_window_ms"] / 1000.0
        max_gap_sec = self.config.get("max_gap_ms", 50) / 1000.0
        
        if gap <= window_sec and gap <= max_gap_sec:
            current_cluster.append(op)
        else:
            if len(current_cluster) >= self.config.get("min_burst_size", 2):
                clusters.append(current_cluster)
            current_cluster = [op]
    
    # Финальный кластер
    if len(current_cluster) >= self.config.get("min_burst_size", 2):
        clusters.append(current_cluster)
    
    return clusters
```

## Конфигурация стратегии

### Параметры по умолчанию

```python
BASE_SIGNALS_BURST_CONFIG = {
    "enabled": True,
    "priority": 1,              # Наивысший приоритет среди стратегий
    "time_window_ms": 100,      # Временное окно группировки
    "min_burst_size": 2,        # Минимальное количество операций в бурсте
    "max_gap_ms": 50,          # Максимальный разрыв между операциями
    "max_duration_ms": 10.0,    # Максимальная длительность одной операции
    "include_cross_target": True # Включать операции с разными target
}
```

### Поведенческие особенности

**Приоритет 1**: BaseSignalsBurstStrategy выполняется первой, что позволяет ей "захватить" base_signals операции до обработки другими стратегиями.

**Cross-target группировка**: операции с разными targets (file_data, calculations_data) группируются в один бурст, если они происходят в рамках одного пользовательского действия.

**Контекстная принадлежность**: операции должны принадлежать одному thread-local контексту (одной родительской @operation).

## Результаты этапа 2

### ✅ Завершенные задачи

1. **✅ Обновлена логика идентификации**: критерии базируются на реальной архитектуре (filename, line_number, атомарность)

2. **✅ Усовершенствован алгоритм группировки**: добавлены max_gap_ms и контекстная проверка

3. **✅ Проанализированы реальные паттерны**: Parameter Update, Add Reaction, Multi-target бурсты

4. **✅ Определена конфигурация**: приоритет 1, временные окна, cross-target поддержка

5. **✅ Разработан detect() алгоритм**: с учетом существующей архитектуры MetaOperationStrategy

### 🎯 Ключевые улучшения

**Context-Aware группировка**: операции группируются не только по времени, но и по принадлежности к одному thread-local контексту.

**Реалистичные паттерны**: алгоритм основан на анализе реальных логов, а не гипотетических сценариев.

**Архитектурная совместимость**: полное соответствие интерфейсу MetaOperationStrategy без нарушения существующих принципов.

### 🚀 Готовность к этапу 3

Логика кластеризации проработана с учетом реальной архитектуры. Алгоритм готов к реализации в виде BaseSignalsBurstStrategy класса.

---

*Этап 2 завершён: 17 июня 2025*  
*Статус: Готов к формированию мета-операций*  
*Следующий этап: [STAGE_03_META_OPERATION_STRUCTURE.md](STAGE_03_META_OPERATION_STRUCTURE.md)*
