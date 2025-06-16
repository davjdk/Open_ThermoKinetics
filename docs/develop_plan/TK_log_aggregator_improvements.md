# Техническое задание: Корректировка системы агрегированного логирования операций

## Общая информация

**Проект:** Open ThermoKinetics - Анализ кинетики твердофазных реакций  
**Модуль:** `src/core/log_aggregator`  
**Версия:** v1.1  
**Дата создания:** 16 июня 2025  
**Приоритет:** Средний  

## Обзор задачи

Система агрегированного логирования операций требует доработки для улучшения читаемости выводимой информации и расширения функционала обработки ошибок. Необходимо реализовать два ключевых улучшения:

1. **Улучшение отображения названий операций** - убрать префикс `OperationType` из колонки Sub-operation
2. **Расширенная обработка ошибок** - детальное логирование ошибок подопераций с созданием специализированного класса

## Текущее состояние системы

### Архитектура модуля
```
src/core/log_aggregator/
├── __init__.py                      # Экспорт основных компонентов
├── operation_logger.py              # Декоратор @operation и proxy система
├── operation_log.py                 # Основная структура данных операции
├── sub_operation_log.py             # Структура данных подопераций
├── table_formatter.py               # Форматирование табличного вывода
├── aggregated_operation_logger.py   # Singleton менеджер логирования
└── LOG_AGGREGATOR_ARCHITECTURE.md   # Архитектурная документация
```

### Текущий формат вывода
```
================================================================================
Operation "ADD_REACTION" – STARTED (id=8, 2025-06-16 13:34:52)

+--------+----------------------+-----------------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target          | Result data type   |  Status  |   Time, s |
+========+======================+=================+====================+==========+===========+
|      1 | OperationType.CHE... | file_data       | bool               |    OK    |     0.001 |
|      2 | OperationType.GET... | file_data       | DataFrame          |    OK    |     0.003 |
|      3 | OperationType.SET... | calculations... | bool               |    OK    |     0.004 |
+--------+----------------------+-----------------+--------------------+----------+-----------+

SUMMARY: steps 3, successful 3, with errors 0, total time 0.063 s.
Operation "ADD_REACTION" – COMPLETED (status: successful)
================================================================================
```

### Проблемы текущей реализации

1. **Неинформативные названия операций**: 
   - Отображается `OperationType.CHE...` вместо читаемого `CHECK_FILE_EXISTS`
   - Обрезка через `_truncate_text()` скрывает полное название операции

2. **Недостаточная детализация ошибок**:
   - При статусе `Error` нет развернутой информации об ошибке
   - Отсутствует структурированная обработка различных типов ошибок
   - Нет системы для анализа причин ошибок подопераций

## Требования к доработке

### 1. Улучшение отображения названий операций

#### 1.1 Основные требования
- Убрать префикс `OperationType` из названий операций в колонке Sub-operation
- Отображать полное название операции без сокращений
- Сохранить совместимость с существующей системой логирования

#### 1.2 Техническая реализация
**Целевой файл:** `src/core/log_aggregator/table_formatter.py`

**Изменения в методе `_format_sub_operations_table()`:**
```python
# Текущая реализация (строка ~130):
self._truncate_text(sub_op.operation_name, 20)

# Требуемая реализация:
sub_op.clean_operation_name  # Новое свойство без OperationType префикса
```

**Дополнения в `SubOperationLog`:**
- Добавить свойство `clean_operation_name` для получения чистого названия операции
- Реализовать логику удаления префикса `OperationType.` из строки
- Обеспечить fallback для случаев, когда операция не является OperationType

#### 1.3 Ожидаемый результат
```
+--------+----------------------+-----------------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target          | Result data type   |  Status  |   Time, s |
+========+======================+=================+====================+==========+===========+
|      1 | CHECK_FILE_EXISTS    | file_data       | bool               |    OK    |     0.001 |
|      2 | GET_DF_DATA          | file_data       | DataFrame          |    OK    |     0.003 |
|      3 | SET_VALUE            | calculations... | bool               |    OK    |     0.004 |
+--------+----------------------+-----------------+--------------------+----------+-----------+
```

### 2. Расширенная система обработки ошибок

#### 2.1 Основные требования
- Создать специализированный класс для обработки ошибок подопераций
- Выводить развернутую информацию об ошибках при статусе `Error`
- Реализовать структурированную систему анализа типов ошибок
- Интегрировать расширенную обработку ошибок в существующий поток логирования

#### 2.2 Архитектура нового компонента

**Новый файл:** `src/core/log_aggregator/error_handler.py`

**Класс `SubOperationErrorHandler`:**
```python
class SubOperationErrorHandler:
    """
    Specialized handler for sub-operation error processing and detailed logging.
    
    Responsibilities:
    - Analyze different types of sub-operation errors
    - Extract detailed error information from response data
    - Format comprehensive error reports
    - Categorize errors by type and severity
    """
    
    def analyze_error(self, sub_operation: SubOperationLog) -> ErrorAnalysis
    def format_error_details(self, sub_operation: SubOperationLog) -> str
    def categorize_error_type(self, error_data: Any) -> ErrorCategory
    def extract_error_context(self, sub_operation: SubOperationLog) -> Dict[str, Any]
```

**Структура данных `ErrorAnalysis`:**
```python
@dataclass
class ErrorAnalysis:
    error_type: ErrorCategory
    error_message: str
    error_context: Dict[str, Any]
    severity: ErrorSeverity
    suggested_action: Optional[str] = None
    technical_details: Optional[str] = None
```

#### 2.3 Типы ошибок для обработки

**Перечисление `ErrorCategory`:**
- `COMMUNICATION_ERROR` - ошибки межмодульной коммуникации
- `DATA_VALIDATION_ERROR` - ошибки валидации данных
- `FILE_OPERATION_ERROR` - ошибки файловых операций
- `CALCULATION_ERROR` - ошибки вычислений
- `CONFIGURATION_ERROR` - ошибки конфигурации
- `UNKNOWN_ERROR` - неопределенные ошибки

**Перечисление `ErrorSeverity`:**
- `CRITICAL` - критические ошибки, блокирующие операцию
- `HIGH` - важные ошибки, влияющие на результат
- `MEDIUM` - умеренные ошибки с возможным workaround
- `LOW` - незначительные ошибки, не влияющие на функциональность

#### 2.4 Интеграция с форматированием

**Изменения в `OperationTableFormatter`:**
- Добавить метод `_format_error_details_block()` для вывода детальной информации об ошибках
- Модифицировать `format_operation_log()` для включения блока ошибок подопераций
- Добавить конфигурационный параметр `include_error_details: bool = True`

**Новая структура вывода при наличии ошибок:**
```
================================================================================
Operation "MODEL_FIT_CALCULATION" – STARTED (id=28, 2025-06-16 13:42:31)

+--------+----------------------+-----------------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target          | Result data type   |  Status  |   Time, s |
+========+======================+=================+====================+==========+===========+
|      1 | GET_SERIES_VALUE     | series_data     | dict               |  Error   |     0.033 |
|      2 | MODEL_FIT_CALC       | model_fit_ca... | dict               |  Error   |     0.498 |
|      3 | UPDATE_SERIES        | series_data     | bool               |    OK    |     0.026 |
+--------+----------------------+-----------------+--------------------+----------+-----------+

ERROR DETAILS:
─────────────────────────────────────────────────────────────────────────────────
Step 1: GET_SERIES_VALUE → series_data
  Error Type: DATA_VALIDATION_ERROR
  Severity: HIGH
  Message: Series data not found or invalid format
  Context: 
    - Target series: "test_series"
    - Expected path: ["test_series", "experimental_data"]
    - Actual data type: None
  Technical Details: KeyError in series_data.get_value() - missing experimental_data key
  
Step 2: MODEL_FIT_CALC → model_fit_calculation
  Error Type: CALCULATION_ERROR  
  Severity: CRITICAL
  Message: Insufficient data for model fitting calculation
  Context:
    - Required parameters: experimental_data, reaction_scheme
    - Missing parameters: experimental_data
    - Available data: deconvolution_results only
  Technical Details: ValueError: Cannot perform model fitting without experimental data
─────────────────────────────────────────────────────────────────────────────────

SUMMARY: steps 3, successful 1, with errors 2, total time 0.562 s.
Operation "MODEL_FIT_CALCULATION" – COMPLETED (status: successful)
================================================================================
```

#### 2.5 Расширение SubOperationLog

**Дополнительные поля:**
```python
@dataclass
class SubOperationLog:
    # ...существующие поля...
    
    # Новые поля для расширенной обработки ошибок
    error_details: Optional[ErrorAnalysis] = None
    exception_traceback: Optional[str] = None
    response_data_raw: Optional[Any] = None  # Для анализа ошибок
```

**Новые методы:**
```python
def analyze_error_details(self) -> Optional[ErrorAnalysis]:
    """Анализ ошибки с помощью ErrorHandler."""
    
def has_detailed_error(self) -> bool:
    """Проверка наличия детальной информации об ошибке."""
    
def get_error_summary(self) -> str:
    """Краткое описание ошибки для таблицы."""
```

## План реализации

Реализация разбита на 4 последовательных этапа с детальными планами в отдельных файлах:

### 📋 [Этап 1: Улучшение отображения операций](stage_1_operation_display_improvement.md) (1-2 дня)

**Цель:** Убрать префикс `OperationType` из названий операций в колонке Sub-operation

**Ключевые задачи:**
- Добавить свойство `clean_operation_name` в `SubOperationLog`
- Обновить `OperationTableFormatter` для использования чистых названий операций
- Создать unit тесты для нового функционала

### 🔧 [Этап 2: Создание системы обработки ошибок](stage_2_error_handling_system.md) (3-4 дня)

**Цель:** Создать специализированную систему анализа ошибок подопераций

**Ключевые задачи:**
- Создать файл `error_handler.py` с классами обработки ошибок
- Определить перечисления `ErrorCategory` и `ErrorSeverity`
- Расширить `SubOperationLog` полями для детальной обработки ошибок
- Реализовать автоматический анализ ошибок

### 🎨 [Этап 3: Интеграция с форматированием](stage_3_formatting_integration.md) (2-3 дня)

**Цель:** Интегрировать систему обработки ошибок с выводом логов

**Ключевые задачи:**
- Добавить методы форматирования детальных ошибок в `OperationTableFormatter`
- Реализовать конфигурируемость детализации ошибок
- Обновить систему логирования для сохранения данных ошибок
- Создать комплексные тесты интеграции

### 📚 [Этап 4: Документация и финализация](stage_4_documentation_finalization.md) (1 день)

**Цель:** Завершить проект с полной документацией и финальными тестами

**Ключевые задачи:**
- Обновить архитектурную документацию с описанием системы ошибок
- Создать руководство пользователя и migration guide
- Провести финальное комплексное тестирование
- Создать демонстрационные примеры

### 📋 [Сводка всех этапов](stages_overview.md)

Детальный обзор всех этапов с структурой файлов и примерами результатов.

## Критерии качества

### Функциональные требования
- ✅ Названия операций отображаются без префикса `OperationType`
- ✅ При статусе `Error` выводится детальная информация об ошибке
- ✅ Система совместима с существующим кодом
- ✅ Производительность логирования не ухудшается значительно

### Нефункциональные требования
- ✅ Код соответствует существующим стилевым стандартам
- ✅ Покрытие тестами новой функциональности не менее 80%
- ✅ Документация обновлена и соответствует изменениям
- ✅ Backward compatibility с существующими логами

## Риски и митигации

### Технические риски
1. **Производительность:** Дополнительная обработка ошибок может замедлить логирование
   - **Митигация:** Lazy evaluation и optional детальный анализ ошибок

2. **Совместимость:** Изменения могут нарушить существующие интеграции
   - **Митигация:** Тщательное тестирование и поэтапное внедрение

3. **Сложность:** Расширенная обработка ошибок может усложнить поддержку
   - **Митигация:** Четкая архитектура и comprehensive документация

### Операционные риски
1. **Размер логов:** Детальная информация об ошибках увеличит размер файлов
   - **Митигация:** Конфигурируемые уровни детализации и ротация логов

2. **Отладка:** Более сложная система может затруднить диагностику проблем
   - **Митигация:** Подробная документация и инструменты отладки

## Заключение

Предлагаемые улучшения системы агрегированного логирования операций значительно повысят информативность и удобство использования логов для диагностики и отладки приложения Open ThermoKinetics. Реализация планируется в течение 7-9 рабочих дней с сохранением архитектурных принципов и обеспечением высокого качества кода.

---

**Ответственный:** GitHub Copilot  
**Согласовано:** Техническая команда проекта  
**Статус:** К реализации
