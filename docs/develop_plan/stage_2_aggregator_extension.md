# Этап 2: Расширение OperationAggregator для поддержки явного режима

## Цель этапа
Модифицировать существующий `OperationAggregator` для поддержки явного режима операций и интеграции с новым API.

## Компоненты для модификации

### 2.1. OperationAggregator - добавление явного режима
Расширить класс `OperationAggregator` в `src/log_aggregator/operation_aggregator.py`:

#### Новые методы:
```python
def start_operation(self, name: str) -> None:
    """Начать новую группу операций в явном режиме"""
    # Закрыть текущую группу если открыта
    if self.current_group:
        self._close_current_group()
    
    # Создать новую группу
    self.current_group = OperationGroup(
        operation_name=name,
        start_time=time.time(),
        explicit_mode=True
    )

def end_operation(self) -> None:
    """Завершить текущую операцию в явном режиме"""
    if self.current_group and self.current_group.explicit_mode:
        self._close_current_group()
        self._generate_operation_table()

def is_explicit_mode(self) -> bool:
    """Проверить, находится ли агрегатор в явном режиме"""
    return self.current_group and self.current_group.explicit_mode
```

#### Модификация процесса обработки:
```python
def process_record(self, record: BufferedLogRecord) -> None:
    """Обработка записи с учетом явного режима"""
    # Если в явном режиме, все записи идут в текущую группу
    if self.is_explicit_mode():
        self.current_group.add_record(record)
        return
    
    # Иначе используем существующую логику автоматического режима
    self._process_automatic_mode(record)
```

### 2.2. OperationGroup - расширение структуры данных
Добавить поля в `OperationGroup` для поддержки явного режима:

```python
@dataclass
class OperationGroup:
    operation_name: str = None          # Явное имя операции
    explicit_mode: bool = False         # Флаг явного режима
    start_time: float = None           # Время начала операции
    end_time: float = None             # Время завершения операции
    request_count: int = 0             # Количество запросов в операции
    custom_metrics: Dict[str, Any] = field(default_factory=dict)  # Произвольные метрики
    sub_operations: List[str] = field(default_factory=list)       # Список подопераций
    
    # Существующие поля...
    records: List[BufferedLogRecord] = field(default_factory=list)
    actors: Set[str] = field(default_factory=set)
```

### 2.3. Интеграция с OperationLogger
Связать `OperationLogger` с `OperationAggregator`:

```python
class OperationLogger:
    def __init__(self, aggregator: OperationAggregator):
        self.aggregator = aggregator
    
    def start_operation(self, name: str) -> None:
        logger.info(f"OPERATION START: {name}")
        self.aggregator.start_operation(name)
    
    def end_operation(self) -> None:
        logger.info("OPERATION END")
        self.aggregator.end_operation()
```

## Места в коде для обнаружения подопераций

### Анализ каскадов в _handle_add_new_series:
```python
def _handle_add_new_series(self, params):
    with log_operation("ADD_NEW_SERIES"):
        # Подоперация 1: Получение данных файлов
        df_copies = self.handle_request_cycle("file_data", OperationType.GET_ALL_DATA, file_name="all_files")
        
        # Подоперация 2: Обработка данных и создание серии  
        merged_df = reduce(lambda left, right: pd.merge(left, right, on="temperature", how="outer"), df_with_rates.values())
        
        # Подоперация 3: Добавление серии в систему
        is_ok = self.handle_request_cycle("series_data", OperationType.ADD_NEW_SERIES, ...)
        
        # Подоперация 4: Получение схемы реакций
        series_entry = self.handle_request_cycle("series_data", OperationType.GET_SERIES, ...)
```

### Таблица подопераций для основных операций:

| Операция                   | Подоперации                                                                              | Запросы |
| -------------------------- | ---------------------------------------------------------------------------------------- | ------- |
| ADD_NEW_SERIES             | 1. GET_ALL_DATA<br/>2. Data Processing<br/>3. ADD_NEW_SERIES<br/>4. GET_SERIES           | 3       |
| MODEL_FREE_CALCULATION     | 1. GET_SERIES<br/>2. Data Preparation<br/>3. MODEL_FREE_CALCULATION<br/>4. UPDATE_SERIES | 3       |
| MODEL_FIT_CALCULATION      | 1. GET_SERIES<br/>2. Data Preparation<br/>3. MODEL_FIT_CALCULATION<br/>4. UPDATE_SERIES  | 3       |
| LOAD_DECONVOLUTION_RESULTS | 1. UPDATE_SERIES<br/>2. SELECT_SERIES                                                    | 2       |
| SELECT_SERIES              | 1. GET_SERIES<br/>2. UI Updates                                                          | 1       |
| DECONVOLUTION              | 1. DECONVOLUTION                                                                         | 1       |

### 2.4. Обнаружение подопераций
Реализовать автоматическое обнаружение подопераций через анализ handle_request_cycle:

```python
def _detect_sub_operations(self, record: BufferedLogRecord) -> Optional[str]:
    """Обнаружить подоперацию на основе содержимого записи"""
    message = record.getMessage()
    
    # Анализ паттернов вызовов
    if "handle_request_cycle" in message:
        # Извлечь OperationType из сообщения
        if "OperationType.GET_ALL_DATA" in message:
            return "GET_ALL_DATA"
        elif "OperationType.ADD_NEW_SERIES" in message:
            return "ADD_NEW_SERIES"
        # ... другие типы операций
    
    return None
```

## Конфигурация режимов
Добавить настройки для управления режимами:

```python
@dataclass
class OperationAggregationConfig:
    explicit_mode_enabled: bool = True          # Включить явный режим
    auto_mode_enabled: bool = True              # Включить автоматический режим  
    operation_timeout: float = 30.0             # Таймаут операции (секунды)
    detect_sub_operations: bool = True          # Обнаруживать подоперации
    merge_nested_operations: bool = True        # Объединять вложенные операции
```

## Критерии завершения этапа
1. ✅ Модифицирован `OperationAggregator` с поддержкой явного режима
2. ✅ Расширена структура `OperationGroup` для метрик операций
3. ✅ Реализована интеграция между `OperationLogger` и `OperationAggregator`
4. ✅ Добавлено автоматическое обнаружение подопераций
5. ✅ Написаны unit-тесты для нового функционала
6. ✅ Проверена совместимость с автоматическим режимом
7. ✅ Добавлена конфигурация для управления режимами

## Ожидаемый результат
После завершения этапа система сможет агрегировать логи в рамках явно обозначенных операций, автоматически обнаруживать подоперации и собирать базовые метрики для дальнейшего табличного представления.
