# Этап 1: Создание базовой структуры стратегии BaseSignalsBurstStrategy

## Цель этапа
Создать базовую структуру класса `BaseSignalsBurstStrategy`, интегрировать его в систему конфигурации и реализовать каркас методов без полной логики кластеризации.

## Задачи

### 1.1 Создание класса стратегии
- Создать класс `BaseSignalsBurstStrategy` в `src/core/log_aggregator/detection_strategies.py`
- Наследовать от абстрактного класса `MetaOperationStrategy` 
- Реализовать обязательные методы интерфейса:
  - `strategy_name` (property) → возвращает `"BaseSignalsBurst"`
  - `validate_config()` → проверка конфигурационных параметров
  - `detect()` → заглушка с базовой логикой 
  - `get_meta_operation_description()` → генерация описания кластера

### 1.2 Анализ источников данных в base_signals.py
Из изучения `src/core/base_signals.py` извлекаем ключевые поля:

**Структура запроса в BaseSlots.create_and_emit_request():**
```python
request = {
    "actor": self.actor_name,          # Инициатор запроса
    "target": target,                  # Целевой модуль
    "operation": operation,            # Тип операции
    "request_id": request_id,          # UUID запроса
    **kwargs,                          # Дополнительные параметры
}
```

**Доступные поля для кластеризации:**
- `actor` - имя компонента-инициатора (self.actor_name из BaseSlots)
- `target` - целевой модуль обработки запроса
- `operation` - тип операции (из OperationType enum)
- `request_id` - уникальный идентификатор запроса

**Критерии идентификации base_signals операций:**
- `target == "base_signals"` - операции, направленные на диспетчер
- ИЛИ `actor` содержит "base_signals" - операции, инициированные диспетчером

### 1.3 Конфигурация стратегии
- Добавить `BaseSignalsBurstStrategy` в `STRATEGY_REGISTRY` в `meta_operation_config.py`
- Создать дефолтную конфигурацию в `DEFAULT_CONFIG`:
  ```python
  "base_signals_burst": {
      "window_ms": 100.0,           # Временное окно кластеризации
      "min_cluster_size": 2,        # Минимум base_signals операций в кластере  
      "include_noise": True,        # Включать промежуточные операции как шум
  }
  ```

### 1.4 Базовая структура методов

**validate_config():**
```python
def validate_config(self) -> None:
    required_params = ["window_ms", "min_cluster_size"]
    for param in required_params:
        if param not in self.config:
            raise ValueError(f"BaseSignalsBurstStrategy missing required parameter: {param}")
    
    if self.config["window_ms"] <= 0:
        raise ValueError("BaseSignalsBurstStrategy window_ms must be positive")
    
    if self.config["min_cluster_size"] < 1:
        raise ValueError("BaseSignalsBurstStrategy min_cluster_size must be >= 1")
```

**detect() - заглушка:**
```python
def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
    # Этап 1: Только базовая проверка принадлежности к base_signals
    if not self._is_base_signals_operation(sub_op):
        return None
    
    # TODO: Этап 2 - реализация логики кластеризации
    return None

def _is_base_signals_operation(self, sub_op: SubOperationLog) -> bool:
    """Проверка, относится ли операция к base_signals."""
    return (sub_op.target == "base_signals" or 
            "base_signals" in str(sub_op.target).lower())
```

**get_meta_operation_description() - заглушка:**
```python
def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
    count = len(operations)
    if not operations:
        return f"BaseSignalsBurst: {count} операций"
    
    duration_ms = int((operations[-1].end_time - operations[0].start_time) * 1000) if operations else 0
    # TODO: Этап 3 - добавить анализ actor и шума
    return f"BaseSignalsBurst: {count} операций, {duration_ms} мс"
```

## Результат этапа
- Интегрированный в систему класс `BaseSignalsBurstStrategy` 
- Рабочая конфигурация и валидация
- Базовые методы-заглушки готовые для развития на следующих этапах
- Понимание структуры данных из `base_signals.py`

## Файлы для изменения
- `src/core/log_aggregator/detection_strategies.py` - добавление класса
- `src/core/log_aggregator/meta_operation_config.py` - регистрация и конфигурация

## Критерии готовности
- [ ] Класс создан и наследует MetaOperationStrategy
- [ ] Все обязательные методы реализованы (хотя бы как заглушки)
- [ ] Стратегия зарегистрирована в STRATEGY_REGISTRY  
- [ ] Конфигурация добавлена в DEFAULT_CONFIG
- [ ] validate_config() проверяет все необходимые параметры
- [ ] Базовые тесты проходят без ошибок
