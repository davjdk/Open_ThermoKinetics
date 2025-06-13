# Этап 3: Расширение OperationMonitor для сбора метрик

## Цель этапа
Расширить функциональность `OperationMonitor` для сбора детальных метрик операций и интеграции с системой явного логирования.

## Компоненты для модификации

### 3.1. OperationMonitor - расширение для метрик операций
Добавить в `src/log_aggregator/operation_monitor.py`:

#### Новые структуры данных:
```python
@dataclass
class OperationMetrics:
    """Метрики одной операции"""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    request_count: int = 0
    response_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    components_involved: Set[str] = field(default_factory=set)
    
    @property
    def duration(self) -> Optional[float]:
        """Длительность операции в секундах"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def status(self) -> str:
        """Статус операции на основе ошибок/предупреждений"""
        if self.error_count > 0:
            return "ERROR"
        elif self.warning_count > 0:
            return "WARNING"
        else:
            return "SUCCESS"
```

#### Расширение OperationMonitor:
```python
class OperationMonitor:
    def __init__(self):
        # Существующие поля...
        self.current_operation: Optional[OperationMetrics] = None
        self.completed_operations: List[OperationMetrics] = []
        self.operation_stack: List[OperationMetrics] = []  # Для вложенных операций
    
    def start_operation_tracking(self, name: str) -> None:
        """Начать отслеживание новой операции"""
        # Если есть текущая операция, сохранить её в стек
        if self.current_operation:
            self.operation_stack.append(self.current_operation)
        
        self.current_operation = OperationMetrics(
            operation_name=name,
            start_time=time.time()
        )
    
    def end_operation_tracking(self) -> Optional[OperationMetrics]:
        """Завершить отслеживание текущей операции"""
        if not self.current_operation:
            return None
        
        self.current_operation.end_time = time.time()
        completed = self.current_operation
        self.completed_operations.append(completed)
        
        # Восстановить предыдущую операцию из стека
        self.current_operation = self.operation_stack.pop() if self.operation_stack else None
        
        return completed
    
    def add_custom_metric(self, key: str, value: Any) -> None:
        """Добавить произвольную метрику к текущей операции"""
        if self.current_operation:
            self.current_operation.custom_metrics[key] = value
    
    def track_request(self, source: str, target: str, operation: str) -> None:
        """Отследить запрос в рамках операции"""
        if self.current_operation:
            self.current_operation.request_count += 1
            self.current_operation.components_involved.add(source)
            self.current_operation.components_involved.add(target)
        
        # Существующая логика...
    
    def track_response(self, source: str, target: str, operation: str) -> None:
        """Отследить ответ в рамках операции"""
        if self.current_operation:
            self.current_operation.response_count += 1
        
        # Существующая логика...
    
    def track_log_level(self, level: str) -> None:
        """Отследить уровень лога"""
        if not self.current_operation:
            return
        
        if level == "WARNING":
            self.current_operation.warning_count += 1
        elif level == "ERROR":
            self.current_operation.error_count += 1
```

### 3.2. Интеграция с существующими мониторами

#### Добавление метрик производительности:
```python
def add_performance_metrics(self) -> None:
    """Добавить метрики производительности к текущей операции"""
    if not self.current_operation:
        return
    
    # CPU и память (если доступен PerformanceMonitor)
    if hasattr(self, 'performance_monitor'):
        cpu_usage = self.performance_monitor.get_current_cpu()
        memory_usage = self.performance_monitor.get_current_memory()
        
        self.add_custom_metric("cpu_usage_avg", cpu_usage)
        self.add_custom_metric("memory_usage_mb", memory_usage)
```

#### Интеграция с OptimizationMonitor:
```python
def track_optimization_metrics(self, optimization_data: dict) -> None:
    """Отследить метрики оптимизации"""
    if not self.current_operation:
        return
    
    if "iteration_count" in optimization_data:
        self.add_custom_metric("iterations", optimization_data["iteration_count"])
    
    if "convergence_value" in optimization_data:
        self.add_custom_metric("convergence", optimization_data["convergence_value"])
    
    if "optimization_method" in optimization_data:
        self.add_custom_metric("method", optimization_data["optimization_method"])
```

### 3.3. Автоматическое обнаружение метрик в логах

#### Парсер метрик из лог-сообщений:
```python
class LogMetricsExtractor:
    """Извлечение метрик из лог-сообщений"""
    
    METRIC_PATTERNS = {
        r'handle_request_cycle.*OperationType\.(\w+)': 'sub_operation',
        r'operation.*completed.*(\d+\.?\d*)\s*(?:seconds|ms)': 'duration',
        r'processing (\d+) files': 'file_count',
        r'(\d+) reactions found': 'reaction_count',
        r'MSE:\s*(\d+\.?\d*)': 'mse_value',
        r'R²:\s*(\d+\.?\d*)': 'r_squared',
        r'heating rate:\s*(\d+\.?\d*)': 'heating_rate',
    }
    
    def extract_metrics(self, message: str) -> Dict[str, Any]:
        """Извлечь метрики из сообщения лога"""
        metrics = {}
        
        for pattern, metric_name in self.METRIC_PATTERNS.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                value = match.group(1)
                # Попытаться преобразовать в число
                try:
                    metrics[metric_name] = float(value) if '.' in value else int(value)
                except ValueError:
                    metrics[metric_name] = value
        
        return metrics
```

### 3.4. Специфичные метрики для solid-state-kinetics

#### Метрики для операций с данными:
```python
def track_data_operation_metrics(self, operation_type: str, data_info: dict) -> None:
    """Отследить метрики операций с данными"""
    if not self.current_operation:
        return
    
    # Метрики в зависимости от типа операции
    if operation_type == "ADD_NEW_SERIES":
        if "file_count" in data_info:
            self.add_custom_metric("files_processed", data_info["file_count"])
        if "heating_rates" in data_info:
            self.add_custom_metric("heating_rates", data_info["heating_rates"])
    
    elif operation_type == "DECONVOLUTION":
        if "reaction_count" in data_info:
            self.add_custom_metric("reactions_found", data_info["reaction_count"])
        if "mse" in data_info:
            self.add_custom_metric("final_mse", data_info["mse"])
    
    elif operation_type in ["MODEL_FIT_CALCULATION", "MODEL_FREE_CALCULATION"]:
        if "method" in data_info:
            self.add_custom_metric("calculation_method", data_info["method"])
        if "reaction_count" in data_info:
            self.add_custom_metric("reactions_analyzed", data_info["reaction_count"])
```

### 3.5. Интеграция с AggregationEngine

#### Передача метрик в агрегацию:
```python
def get_operation_metrics_for_aggregation(self) -> Dict[str, Any]:
    """Получить метрики операции для передачи в таблицу"""
    if not self.current_operation:
        return {}
    
    return {
        "duration": self.current_operation.duration,
        "request_count": self.current_operation.request_count,
        "response_count": self.current_operation.response_count,
        "warning_count": self.current_operation.warning_count,
        "error_count": self.current_operation.error_count,
        "status": self.current_operation.status,
        "components": list(self.current_operation.components_involved),
        **self.current_operation.custom_metrics
    }
```

## Автоматический сбор метрик

### Интеграция с основными операциями:
```python
# В MainWindow после интеграции с OperationLogger
def _handle_add_new_series(self, params):
    with log_operation("ADD_NEW_SERIES"):
        # Добавить метрики в начале
        operation_monitor.add_custom_metric("user_action", "add_series")
        
        df_copies = self.handle_request_cycle("file_data", OperationType.GET_ALL_DATA, file_name="all_files")
        
        # Метрики по ходу выполнения
        operation_monitor.add_custom_metric("file_count", len(selected_files))
        operation_monitor.add_custom_metric("heating_rates", [rate for _, rate, _ in selected_files])
        
        # Остальной код...
```

## Таймаут и автоматическое завершение

### Система таймаутов для операций:
```python
def check_operation_timeout(self, timeout_seconds: float = 30.0) -> None:
    """Проверить таймаут текущей операции"""
    if not self.current_operation:
        return
    
    current_time = time.time()
    if current_time - self.current_operation.start_time > timeout_seconds:
        logger.warning(f"Operation {self.current_operation.operation_name} timed out after {timeout_seconds}s")
        self.current_operation.custom_metrics["timeout"] = True
        self.end_operation_tracking()
```

## Критерии завершения этапа
1. ✅ Расширен `OperationMonitor` для сбора детальных метрик
2. ✅ Реализована структура `OperationMetrics` для хранения данных операции
3. ✅ Добавлен автоматический парсер метрик из лог-сообщений
4. ✅ Реализованы специфичные метрики для solid-state-kinetics операций
5. ✅ Добавлена система таймаутов и автоматического завершения операций
6. ✅ Интегрированы метрики производительности и оптимизации
7. ✅ Написаны unit-тесты для нового функционала
8. ✅ Проверена интеграция с `OperationAggregator`

## Ожидаемый результат
После завершения этапа система будет автоматически собирать богатый набор метрик для каждой операции, включая временные характеристики, количество запросов, статус выполнения и специфичные для домена метрики, что создаст основу для детального табличного представления операций.
