# Этап 6: Реализация и внедрение

## Задачи реализации

Данный этап включает непосредственную разработку стратегии **BaseSignalsMetaBurst** согласно всем определенным требованиям и спецификациям из предыдущих этапов.

## Структура реализации

### 1. Создание класса BaseSignalsBurstStrategy

#### Место размещения
- **Файл:** `src/core/log_aggregator/detection_strategies.py`
- **Пакет:** `src.core.log_aggregator`

#### Структура класса
```python
class BaseSignalsBurstStrategy(MetaOperationStrategy):
    """
    Стратегия детекции мета-операций для группировки 'всплесков' 
    подопераций из модуля base_signals в пределах временного окна.
    """
    
    def __init__(self, config: dict):
        """Инициализация стратегии с конфигурацией"""
        
    @property
    def strategy_name(self) -> str:
        """Возвращает уникальное имя стратегии"""
        
    def validate_config(self) -> None:
        """Валидация параметров конфигурации"""
        
    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """Основной метод детекции кластеров"""
        
    def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog], context: OperationLog) -> str:
        """Генерация описания мета-операции"""
```

### 2. Реализация основных методов

#### Метод `__init__`
```python
def __init__(self, config: dict):
    self.config = config
    self.window_ms = config.get("window_ms", 100)  # По умолчанию 100ms
    self.min_cluster_size = config.get("min_cluster_size", 2)  # По умолчанию 2
    self.validate_config()
```

#### Метод `validate_config`
```python
def validate_config(self) -> None:
    if not isinstance(self.window_ms, (int, float)) or self.window_ms <= 0:
        raise ValueError(f"window_ms должно быть положительным числом, получено: {self.window_ms}")
    
    if not isinstance(self.min_cluster_size, int) or self.min_cluster_size < 1:
        raise ValueError(f"min_cluster_size должно быть положительным целым числом, получено: {self.min_cluster_size}")
```

#### Метод `detect` (основная логика)
```python
def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
    # 1. Проверка принадлежности к base_signals
    if not self._is_base_signals_operation(sub_op):
        return None
    
    # 2. Поиск операций в временном окне
    cluster_ops = self._find_operations_in_window(sub_op, context)
    
    # 3. Проверка минимального размера кластера
    if len(cluster_ops) < self.min_cluster_size:
        return None
    
    # 4. Генерация meta_id
    cluster_start_time = min(op.start_time for op in cluster_ops)
    meta_id = f"base_signals_burst_{int(cluster_start_time * 1000)}"
    
    return meta_id
```

#### Вспомогательные методы
```python
def _is_base_signals_operation(self, sub_op: SubOperationLog) -> bool:
    """Проверяет, относится ли операция к base_signals"""
    # Логика определения может быть разной:
    # 1. По полю source_module (если есть)
    # 2. По имени операции
    # 3. По целевому модулю
    return hasattr(sub_op, 'source_module') and sub_op.source_module == "base_signals"

def _find_operations_in_window(self, base_op: SubOperationLog, context: OperationLog) -> List[SubOperationLog]:
    """Находит все base_signals операции в пределах временного окна"""
    window_seconds = self.window_ms / 1000.0
    window_start = base_op.start_time
    window_end = window_start + window_seconds
    
    cluster_ops = []
    for op in context.sub_operations:
        if (self._is_base_signals_operation(op) and 
            window_start <= op.start_time <= window_end):
            cluster_ops.append(op)
    
    return cluster_ops

def _find_noise_operations(self, cluster_ops: List[SubOperationLog], context: OperationLog) -> List[SubOperationLog]:
    """Находит шумовые операции в интервале кластера"""
    if not cluster_ops:
        return []
    
    cluster_start = min(op.start_time for op in cluster_ops)
    cluster_end = max(op.end_time for op in cluster_ops if op.end_time)
    
    noise_ops = []
    for op in context.sub_operations:
        if (not self._is_base_signals_operation(op) and
            cluster_start <= op.start_time <= cluster_end):
            noise_ops.append(op)
    
    return noise_ops
```

### 3. Генерация описаний мета-операций

#### Метод `get_meta_operation_description`
```python
def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog], context: OperationLog) -> str:
    """Генерирует человекочитаемое описание кластера"""
    ops_count = len(operations)
    
    # Вычисление длительности
    start_time = min(op.start_time for op in operations)
    end_time = max(op.end_time for op in operations if op.end_time)
    duration_ms = int((end_time - start_time) * 1000) if end_time else 0
    
    # Поиск шума
    noise_ops = self._find_noise_operations(operations, context)
    noise_count = len(noise_ops)
    
    # Актор (если есть в контексте)
    actor_info = ""
    if hasattr(context, 'actor') and context.actor:
        actor_info = f"actor: {context.actor}, "
    
    # Формирование описания
    description = f"BaseSignals Burst ({actor_info}{ops_count} ops, {duration_ms}ms"
    
    if noise_count > 0:
        description += f", noise: {noise_count}"
    
    description += ")"
    
    return description
```

### 4. Интеграция в MetaOperationDetector

#### Обновление регистрации стратегий
```python
# В MetaOperationDetector.__init__ или аналогичном методе

def _initialize_strategies(self, config):
    strategies = []
    
    # Существующие стратегии...
    
    # Новая стратегия BaseSignalsMetaBurst
    if config.strategies.get("base_signals_burst", {}).get("enabled", False):
        try:
            strategy_config = config.strategies["base_signals_burst"]
            strategies.append(BaseSignalsBurstStrategy(strategy_config))
            logger.debug("BaseSignalsMetaBurst strategy initialized")
        except Exception as e:
            logger.error(f"Failed to initialize BaseSignalsMetaBurst strategy: {e}")
    
    return strategies
```

### 5. Обновление конфигурации

#### Добавление в meta_operation_config.py
```python
META_OPERATION_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {
            "enabled": True,
            "window_ms": 50,
            "min_cluster_size": 2
        },
        "target_cluster": {
            "enabled": True,
            "min_cluster_size": 2
        },
        "name_similarity": {
            "enabled": True,
            "name_pattern": r"GET_.*|SET_.*|UPDATE_.*",
            "min_cluster_size": 2
        },
        "sequence_count": {
            "enabled": True,
            "min_sequence_count": 3
        },
        # Новая стратегия
        "base_signals_burst": {
            "enabled": True,
            "window_ms": 100,
            "min_cluster_size": 2
        }
    },
    "formatting": {
        "mode": "compact",
        "show_individual_operations": True,
        "meta_operation_summary": True
    }
}
```

### 6. Обновление форматтеров (если необходимо)

#### Поддержка в EnhancedTableFormatter
Если существующие форматтеры не поддерживают новые поля (актор, шум), может потребоваться их расширение:

```python
def _format_meta_operation_summary(self, meta_operation: MetaOperation) -> str:
    """Форматирование summary мета-операции с поддержкой новых полей"""
    
    base_summary = f"{meta_operation.name} ({len(meta_operation.sub_operations)} ops, {meta_operation.total_execution_time:.3f}s"
    
    # Для BaseSignalsMetaBurst добавляем специальную информацию
    if meta_operation.heuristic == "BaseSignalsMetaBurst":
        # Дополнительная логика для отображения шума и актора
        pass
    
    return base_summary
```

## Задачи внедрения

### 1. Создание unit тестов

#### Базовые тесты функциональности
```python
# tests/test_base_signals_burst_strategy.py

class TestBaseSignalsBurstStrategy:
    def test_basic_cluster_detection(self):
        """Тест базовой детекции кластера"""
        
    def test_config_validation(self):
        """Тест валидации конфигурации"""
        
    def test_time_window_boundaries(self):
        """Тест границ временного окна"""
        
    def test_min_cluster_size(self):
        """Тест минимального размера кластера"""
        
    def test_noise_detection(self):
        """Тест детекции шумовых операций"""
```

### 2. Создание integration тестов

#### Тесты интеграции с системой
```python
# tests/integration/test_meta_operation_integration.py

class TestMetaOperationIntegration:
    def test_base_signals_burst_end_to_end(self):
        """Сквозной тест стратегии BaseSignalsMetaBurst"""
        
    def test_multiple_strategies_compatibility(self):
        """Тест совместимости с другими стратегиями"""
        
    def test_formatter_integration(self):
        """Тест интеграции с форматтерами"""
```

### 3. Документирование

#### Обновление документации
- Добавить описание новой стратегии в LOG_AGGREGATOR_ARCHITECTURE.md
- Обновить примеры конфигурации
- Создать примеры использования

#### Комментарии в коде
- Добавить подробные docstring для всех методов
- Документировать алгоритмы и бизнес-логику
- Добавить примеры использования в комментариях

### 4. Валидация и тестирование

#### Ручное тестирование
1. Создать тестовые сценарии с реальными данными
2. Проверить работу в разных режимах конфигурации
3. Валидировать вывод в различных форматах

#### Автоматизированное тестирование
1. Запуск всех unit тестов
2. Запуск integration тестов
3. Performance тестирование
4. Проверка покрытия кода

### 5. Развертывание

#### Этапы развертывания
1. **Код review** - проверка кода коллегами
2. **Merge в main branch** - интеграция в основную ветку
3. **Обновление конфигурации** - включение стратегии в продакшн-конфиге
4. **Мониторинг** - отслеживание работы в production

#### Rollback план
1. Отключение стратегии через конфигурацию
2. Возврат к предыдущей версии кода при критических проблемах
3. План восстановления данных (если необходимо)

## Критерии завершения этапа

### Функциональные критерии
- [ ] Класс BaseSignalsBurstStrategy реализован и интегрирован
- [ ] Все unit тесты проходят успешно
- [ ] Integration тесты показывают корректную работу с системой
- [ ] Конфигурация обновлена и документирована

### Качественные критерии
- [ ] Код соответствует стандартам проекта
- [ ] Документация обновлена и полна
- [ ] Производительность находится в допустимых пределах
- [ ] Нет регрессий в существующей функциональности

### Операционные критерии
- [ ] Стратегия успешно развернута в продакшн
- [ ] Мониторинг показывает стабильную работу
- [ ] Логи генерируются в ожидаемом формате
- [ ] Конфигурация может быть изменена без перезапуска

## Риски и митигация

### Технические риски
- **Производительность:** Возможное замедление логирования
  - *Митигация:* Performance тестирование и оптимизация алгоритмов
- **Конфликты со стратегиями:** Пересечение с существующими стратегиями
  - *Митигация:* Тщательное тестирование совместной работы
- **Ошибки в детекции:** Неправильная группировка операций
  - *Митигация:* Исчерпывающее unit тестирование

### Операционные риски
- **Увеличение размера логов:** Дополнительная информация в логах
  - *Митигация:* Мониторинг размера логов и ротация
- **Сложность отладки:** Усложнение анализа логов
  - *Митигация:* Детальная документация и примеры

## Следующие шаги

После завершения реализации и внедрения BaseSignalsMetaBurst стратегии:

1. **Мониторинг и оптимизация** - отслеживание производительности в продакшн
2. **Сбор обратной связи** - получение feedback от пользователей системы
3. **Итеративные улучшения** - доработка на основе реального использования
4. **Документирование best practices** - создание руководств по использованию

## Заключение

Этап реализации и внедрения завершает разработку стратегии BaseSignalsMetaBurst. Успешное выполнение всех задач этого этапа обеспечит появление в системе логирования нового мощного инструмента для анализа паттернов работы base_signals модуля, что значительно улучшит observability приложения.
