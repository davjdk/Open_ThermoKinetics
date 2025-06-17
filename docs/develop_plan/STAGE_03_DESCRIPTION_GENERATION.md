# Этап 3: Генерация описаний мета-операций и анализ контекста

## Цель этапа
Реализовать детальное формирование описаний кластеров BaseSignalsMetaBurst с анализом actor'ов, шумовых операций и временных характеристик.

## Задачи

### 3.1 Расширенный анализ мета-операции

**Полная реализация get_meta_operation_description():**

```python
def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
    """
    Генерирует человекочитаемое описание кластера BaseSignalsMetaBurst.
    
    Формат: "BaseSignalsBurst: {count} операций, {duration} мс, actor: {actor}, шум: {noise_status}"
    
    Args:
        meta_id: Идентификатор мета-операции
        operations: Список операций в кластере
    
    Returns:
        str: Описание кластера
    """
    if not operations:
        return "BaseSignalsBurst: 0 операций"
    
    # Основные метрики
    count = len(operations)
    duration_ms = self._calculate_duration_ms(operations)
    
    # Анализ actor'ов
    actor_info = self._analyze_actors(operations)
    
    # Анализ шумовых операций
    noise_info = self._analyze_noise_operations(operations)
    
    # Формирование итогового описания
    return f"BaseSignalsBurst: {count} операций, {duration_ms} мс, actor: {actor_info}, шум: {noise_info}"
```

### 3.2 Вычисление временных характеристик

```python
def _calculate_duration_ms(self, operations: List[SubOperationLog]) -> int:
    """
    Вычисляет общую длительность кластера в миллисекундах.
    
    Args:
        operations: Операции кластера
    
    Returns:
        int: Длительность в миллисекундах
    """
    if not operations:
        return 0
    
    # Фильтруем операции с валидным временем
    timed_operations = [op for op in operations if op.start_time is not None]
    if not timed_operations:
        return 0
    
    # Находим границы времени
    start_times = [op.start_time for op in timed_operations if op.start_time]
    end_times = []
    
    for op in timed_operations:
        if op.end_time:
            end_times.append(op.end_time)
        elif op.start_time and op.execution_time:
            end_times.append(op.start_time + op.execution_time)
        else:
            end_times.append(op.start_time)  # Fallback
    
    if not start_times or not end_times:
        return 0
    
    cluster_start = min(start_times)
    cluster_end = max(end_times)
    
    duration_seconds = cluster_end - cluster_start
    return int(duration_seconds * 1000)  # Конвертация в мс
```

### 3.3 Анализ actor'ов

```python
def _analyze_actors(self, operations: List[SubOperationLog]) -> str:
    """
    Анализирует actor'ов в кластере операций.
    
    Извлекает информацию об инициаторах операций из SubOperationLog.
    Поскольку прямого поля actor нет, анализируем доступные данные.
    
    Args:
        operations: Операции кластера
    
    Returns:
        str: Описание actor'ов ("не задан", конкретное имя, или "множественные")
    """
    # Попытка извлечь actor из request_kwargs (если они сохранены)
    actors = set()
    
    for op in operations:
        if hasattr(op, 'request_kwargs') and op.request_kwargs:
            # Из base_signals.py видим, что actor передается в запросе
            if 'actor' in op.request_kwargs:
                actor = op.request_kwargs['actor']
                if actor:
                    actors.add(str(actor))
        
        # Дополнительный анализ - можно попробовать извлечь из operation_name
        # если там есть паттерны вида "component_name_operation"
        if op.operation_name and '_' in op.operation_name:
            potential_actor = op.operation_name.split('_')[0]
            if potential_actor not in ['get', 'set', 'update', 'load', 'save']:  # Исключаем глаголы
                actors.add(potential_actor)
    
    # Формирование результата
    if not actors:
        return "не задан"
    elif len(actors) == 1:
        return list(actors)[0]
    else:
        # Множественные actor'ы - возвращаем первый + количество
        first_actor = sorted(list(actors))[0]
        return f"{first_actor} (+{len(actors)-1})"
```

### 3.4 Анализ шумовых операций

```python
def _analyze_noise_operations(self, operations: List[SubOperationLog]) -> str:
    """
    Анализирует наличие шумовых операций в кластере.
    
    Args:
        operations: Операции кластера
    
    Returns:
        str: Статус шума ("нет", "есть", "есть (X ops)")
    """
    base_signals_count = 0
    noise_count = 0
    noise_targets = set()
    
    for op in operations:
        if self._is_base_signals_operation(op):
            base_signals_count += 1
        else:
            noise_count += 1
            if op.target:
                noise_targets.add(str(op.target))
    
    if noise_count == 0:
        return "нет"
    elif noise_count == 1:
        return "есть"
    else:
        # Детальная информация для множественного шума
        targets_info = ""
        if len(noise_targets) <= 2:
            targets_info = f" ({', '.join(sorted(noise_targets))})"
        elif len(noise_targets) > 2:
            targets_list = sorted(list(noise_targets))
            targets_info = f" ({targets_list[0]}, {targets_list[1]}, +{len(noise_targets)-2})"
        
        return f"есть ({noise_count} ops{targets_info})"
```

### 3.5 Дополнительные методы анализа

```python
def _get_cluster_statistics(self, operations: List[SubOperationLog]) -> Dict[str, Any]:
    """
    Собирает детальную статистику кластера для отладки и расширенного анализа.
    
    Args:
        operations: Операции кластера
    
    Returns:
        Dict[str, Any]: Статистика кластера
    """
    base_signals_ops = [op for op in operations if self._is_base_signals_operation(op)]
    noise_ops = [op for op in operations if not self._is_base_signals_operation(op)]
    
    stats = {
        'total_operations': len(operations),
        'base_signals_operations': len(base_signals_ops),
        'noise_operations': len(noise_ops),
        'duration_ms': self._calculate_duration_ms(operations),
        'actors': self._get_all_actors(operations),
        'noise_targets': list(set(op.target for op in noise_ops if op.target)),
        'time_span': {
            'start': min(op.start_time for op in operations if op.start_time),
            'end': max(op.end_time or op.start_time for op in operations if op.start_time),
        } if any(op.start_time for op in operations) else None
    }
    
    return stats

def _get_all_actors(self, operations: List[SubOperationLog]) -> List[str]:
    """Извлекает всех уникальных actor'ов из операций."""
    actors = set()
    for op in operations:
        if hasattr(op, 'request_kwargs') and op.request_kwargs:
            if 'actor' in op.request_kwargs and op.request_kwargs['actor']:
                actors.add(str(op.request_kwargs['actor']))
    return sorted(list(actors))
```

### 3.6 Обработка граничных случаев

```python
def _handle_edge_cases(self, operations: List[SubOperationLog]) -> Dict[str, str]:
    """
    Обрабатывает специальные случаи в кластере.
    
    Returns:
        Dict[str, str]: Словарь с предупреждениями или особенностями кластера
    """
    warnings = {}
    
    # Проверка на операции без времени
    no_time_ops = [op for op in operations if not op.start_time]
    if no_time_ops:
        warnings['timing'] = f"{len(no_time_ops)} операций без времени"
    
    # Проверка на операции с ошибками
    error_ops = [op for op in operations if op.status == "Error"]
    if error_ops:
        warnings['errors'] = f"{len(error_ops)} операций с ошибками"
    
    # Проверка на подозрительно длинные кластеры (>1 секунды)
    duration_ms = self._calculate_duration_ms(operations)
    if duration_ms > 1000:
        warnings['duration'] = f"длинный кластер ({duration_ms}мс)"
    
    return warnings
```

## Результат этапа
- Детальные человекочитаемые описания кластеров
- Анализ actor'ов из доступных данных операций  
- Точная классификация шумовых операций с детализацией
- Корректное вычисление временных метрик
- Обработка граничных случаев и ошибок

## Файлы для изменения
- `src/core/log_aggregator/detection_strategies.py` - реализация методов анализа

## Критерии готовности
- [ ] get_meta_operation_description() возвращает детальные описания
- [ ] Длительность кластера вычисляется корректно
- [ ] Actor'ы извлекаются из доступных данных операций
- [ ] Шумовые операции правильно классифицируются и подсчитываются
- [ ] Обрабатываются граничные случаи (нет времени, ошибки)
- [ ] Описания соответствуют формату из технического задания
