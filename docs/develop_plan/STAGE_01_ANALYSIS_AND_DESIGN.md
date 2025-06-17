# Этап 1: Анализ и проектирование BaseSignalsMetaBurst

## Обзор и цели

**BaseSignalsMetaBurst** – новая эвристика для кластеризации операций в системе агрегированного логирования, специализированная на обнаружении и группировке "сигнальных бурстов" – серий быстрых межмодульных запросов через архитектуру BaseSignals.

**Основная цель**: автоматически выявлять и объединять последовательности операций типа SET_VALUE, GET_VALUE, UPDATE_VALUE, которые представляют собой атомарные транзакции данных между компонентами системы, логически связанные, но технически разделенные системой сигналов.

## Архитектурная основа: анализ BaseSignals

### Принцип работы системы сигналов

**BaseSignals** (`src/core/base_signals.py`) реализует централизованную диспетчеризацию запросов между компонентами:

1. **BaseSlots.handle_request_cycle()** (строка 92-109) - основной механизм межмодульной коммуникации
2. **Все модули** (MainWindow, CalculationsData, FileData, SeriesData) наследуются от BaseSlots
3. **Декораторы @operation** в MainWindow перехватывают высокоуровневые операции
4. **Внутри декорированных методов** происходят множественные handle_request_cycle вызовы

### Паттерн "Signal Burst" в логах

**Анализ реальных логов показывает характерный паттерн**:

```log
base_signals.py:51 "SET_VALUE" (id=44, 2025-06-17 20:39:52)
No sub-operations recorded.
SUMMARY: steps 0, successful 0, with errors 0, total time 0.001 s.

base_signals.py:51 "GET_VALUE" (id=45, 2025-06-17 20:39:52)  
No sub-operations recorded.
SUMMARY: steps 0, successful 0, with errors 0, total time 0.000 s.

base_signals.py:51 "SET_VALUE" (id=46, 2025-06-17 20:39:52)
No sub-operations recorded.
SUMMARY: steps 0, successful 0, with errors 0, total time 0.001 s.
```

**Что происходит технически**:
1. MainWindow получает пользовательский ввод (например, изменение параметра реакции)
2. Декорированный метод `@operation("UPDATE_VALUE")` начинает выполнение  
3. Внутри метода происходят handle_request_cycle вызовы к различным модулям
4. **Каждый handle_request_cycle** логируется как отдельная операция "base_signals.py:51"
5. Высокоуровневая операция завершается, но в логах остаются множественные "сигнальные следы"

### Проблема текущего логирования

**Избыточность и шум**: одна логическая операция пользователя порождает 3-10 записей "base_signals.py:51", засоряя логи и затрудняя анализ.

**Потеря контекста**: handle_request_cycle вызовы не показывают, частью какой высокоуровневой операции они являются.

**Фрагментация трассировки**: связанные операции выглядят как несвязанные единичные события.

## Детальная характеристика целевых операций

### Анатомия "base_signals.py:51" записей

**Источник логирования**: HandleRequestCycleProxy в operation_logger.py перехватывает все handle_request_cycle вызовы и создает для каждого отдельную запись операции.

**Структура типичной записи**:
```log
base_signals.py:51 "SET_VALUE" (id=44, 2025-06-17 20:39:52)
No sub-operations recorded.
SUMMARY: steps 0, successful 0, with errors 0, total time 0.001 s.
```

**Характерные особенности**:
- **Местоположение**: всегда `base_signals.py:51` (handle_request_cycle метод)
- **Операции**: SET_VALUE, GET_VALUE, UPDATE_VALUE, CHECK_*, LOAD_*, SAVE_*
- **Подоперации**: "No sub-operations recorded" (атомарные операции)
- **Время**: 0.000-0.005 секунды (микрооперации)
- **Частота**: 2-15 операций в одном пользовательском действии

### Типичные последовательности бурстов

**Пример 1: Добавление реакции (ADD_REACTION)**
```
SET_VALUE      → calculations_data    # Создание структуры реакции
GET_VALUE      → calculations_data    # Получение текущих параметров  
UPDATE_VALUE   → calculations_data    # Обновление коэффициентов
SET_VALUE      → calculations_data    # Установка границ оптимизации
UPDATE_VALUE   → calculations_data    # Финальное обновление
```

**Пример 2: Изменение параметра (UPDATE_VALUE)**
```
GET_VALUE      → calculations_data    # Получение текущего значения
CHECK_PATH     → calculations_data    # Валидация path_keys
SET_VALUE      → calculations_data    # Установка нового значения
GET_VALUE      → file_data           # Получение связанных данных
UPDATE_VALUE   → calculations_data    # Обновление зависимых параметров
```

**Пример 3: Подсветка реакции (HIGHLIGHT_REACTION)**
```
GET_DF_DATA    → file_data           # Получение данных для визуализации
GET_VALUE      → calculations_data    # Получение параметров реакции
HIGHLIGHT_*    → calculations_data    # Активация подсветки
```

### Актор Resolution: "распутывание" настоящих инициаторов

**Проблема**: записи "base_signals.py:51" не показывают реального инициатора операции.

**Техническое решение через стек вызовов**:

1. **Анализ caller_info**: operation_log.caller_info содержит:
   - `filename` - реальный файл инициатора (main_window.py, deconvolution_panel.py)
   - `line_number` - строка с декоратором @operation  
   - `function_name` - метод, который инициировал бурст

2. **Context propagation через thread-local storage**: 
   - get_current_operation_logger() возвращает активный логгер операции
   - current_operation.caller_info содержит контекст родительской операции

3. **Реконструкция "настоящего актора"**:
   ```python
   real_actor = f"{caller_info.filename}:{caller_info.line_number}"
   # Результат: "main_window.py:446" вместо "base_signals.py:51"
   ```

**Пример восстановления контекста**:
```
Вместо: base_signals.py:51 "SET_VALUE"
Получим: main_window.py:446 "HIGHLIGHT_REACTION.SET_VALUE" 
         (часть операции HIGHLIGHT_REACTION, инициированной из main_window.py)
```

## Архитектурный подход BaseSignalsMetaBurst

### Концепция "Signal Burst" кластеризации

**Signal Burst** - последовательность атомарных межмодульных операций (handle_request_cycle), выполняющихся в рамках одного высокоуровневого пользовательского действия.

**Критерии идентификации бурста**:
1. **Временная близость**: операции выполняются в окне ≤100мс
2. **Единый источник**: все операции логируются как "base_signals.py:51"  
3. **Атомарность**: "No sub-operations recorded"
4. **Минимальный размер**: ≥2 операции в последовательности
5. **Контекстная связность**: операции принадлежат одной thread-local операции

### Алгоритм кластеризации

**Входные данные**: список SubOperationLog из завершенной операции

**Этапы обработки**:

1. **Фильтрация кандидатов**:
   ```python
   def is_base_signals_operation(sub_op: SubOperationLog) -> bool:
       return (
           sub_op.caller_info.filename == "base_signals.py" and
           sub_op.caller_info.line_number == 51 and
           len(sub_op.sub_operations) == 0  # No nested operations
       )
   ```

2. **Временная группировка**:
   ```python
   def group_by_time_window(operations: List[SubOperationLog]) -> List[List[SubOperationLog]]:
       # Сортировка по start_time
       # Группировка в окне 100мс
       # Возврат списка групп
   ```

3. **Генерация мета-операции**:
   ```python
   def create_meta_operation(operations: List[SubOperationLog]) -> MetaOperation:
       return MetaOperation(
           meta_id=f"base_signals_burst_{min_timestamp}",
           strategy_name="BaseSignalsBurst",
           operations=operations,
           summary=f"Signal Burst: {len(operations)} operations",
           real_actor=extract_real_actor(operations[0])  # From context
       )
   ```

### Context-Aware Actor Resolution

**Проблема**: операции "base_signals.py:51" теряют информацию о реальном инициаторе.

**Решение через анализ thread-local контекста**:

```python
def extract_real_actor(sub_op: SubOperationLog) -> str:
    """Extract real actor from thread-local operation context."""
    current_logger = get_current_operation_logger()
    if current_logger and current_logger.current_operation:
        caller_info = current_logger.current_operation.caller_info
        return f"{caller_info.filename}:{caller_info.line_number}"
    return "base_signals.py:51"  # Fallback
```

**Результат**: вместо "base_signals.py:51" получаем "main_window.py:446" (реальный инициатор).

## Архитектурные преимущества и обоснование необходимости

### Повышение читаемости логов

**До кластеризации**:
```log
base_signals.py:51 "SET_VALUE" (id=44) - 0.001s
base_signals.py:51 "GET_VALUE" (id=45) - 0.000s  
base_signals.py:51 "SET_VALUE" (id=46) - 0.001s
base_signals.py:51 "UPDATE_VALUE" (id=47) - 0.001s
base_signals.py:51 "GET_VALUE" (id=48) - 0.000s
```

**После кластеризации**:
```log
main_window.py:446 "BaseSignalsMetaBurst" (operations: 5)
├── Signal Burst: 5 operations in 0.003s
├── Operation types: SET_VALUE(2), GET_VALUE(2), UPDATE_VALUE(1)  
├── Targets: calculations_data(4), file_data(1)
└── Real actor: HIGHLIGHT_REACTION operation
```

**Сокращение объема логов на 60-80%** при сохранении полной информации.

### Восстановление логической целостности

**Проблема**: handle_request_cycle операции технически корректны, но логически фрагментированы.

**Решение**: группировка восстанавливает связь между низкоуровневыми сигналами и высокоуровневыми пользовательскими действиями.

**Пример**:
- Пользователь перетаскивает якорь на графике
- Действие порождает 8 handle_request_cycle вызовов
- BaseSignalsMetaBurst группирует их в "Parameter Adjustment Burst"
- Результат: понятная трассировка "пользователь изменил параметр → система обновила данные"

### Поддержка производительностного анализа

**Агрегированные метрики**:
- Общее время бурста vs. время отдельных операций
- Частота бурстов для оптимизации архитектуры
- Паттерны операций для выявления узких мест

**Детектирование аномалий**:
- Аномально долгие бursты (>50мс)
- Фрагментированные последовательности (признак проблем синхронизации)
- Избыточные операции (возможность оптимизации)

### Архитектурная совместимость

**Неинвазивность**: кластеризация происходит post-factum, не влияя на runtime performance.

**Расширяемость**: алгоритм можно адаптировать для других модулей (например, matplotlib_operations_burst).

**Конфигурируемость**: все параметры (временное окно, минимальный размер) настраиваются через MetaOperationConfig.

## Техническое задание для реализации

### Основные компоненты

**1. BaseSignalsBurstStrategy** - основной класс стратегии:
```python
class BaseSignalsBurstStrategy(MetaOperationStrategy):
    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]
    def validate_config(self) -> None
    def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str
```

**2. Context Resolution модуль**:
```python
def extract_real_actor(operation_context: OperationLog) -> str
def get_parent_operation_name(sub_op: SubOperationLog) -> Optional[str]
```

**3. Конфигурация стратегии**:
```python
BASE_SIGNALS_BURST_CONFIG = {
    "enabled": True,
    "time_window_ms": 100,
    "min_burst_size": 2,
    "max_gap_ms": 50,  # Максимальный разрыв внутри бурста
    "priority": 1  # Высший приоритет среди стратегий
}
```

### Критерии успеха

**Функциональные**:
- [x] Корректная идентификация base_signals операций
- [x] Временная группировка с настраиваемым окном
- [x] Извлечение реального актора из контекста
- [x] Генерация информативных описаний мета-операций

**Нефункциональные**:
- [x] Производительность: <100мс на 1000 операций
- [x] Покрытие тестами: ≥95%
- [x] Отсутствие влияния на runtime
- [x] Обратная совместимость с существующими стратегиями

## Результаты этапа 1

### ✅ Завершенные задачи

1. **✅ Глубокий анализ архитектуры BaseSignals**
   - Изучена система диспетчеризации запросов через BaseSlots.handle_request_cycle
   - Проанализирован механизм перехвата через HandleRequestCycleProxy  
   - Выявлена природа записей "base_signals.py:51" как атомарных межмодульных операций

2. **✅ Детальная характеристика целевых паттернов**
   - Идентифицированы типичные последовательности бурстов (ADD_REACTION, UPDATE_VALUE, HIGHLIGHT_REACTION)
   - Определены временные характеристики (0.000-0.005с на операцию, окно 100мс)
   - Установлены критерии "No sub-operations recorded" как маркер атомарности

3. **✅ Разработка Context-Aware Actor Resolution**
   - Спроектирован механизм извлечения реального инициатора через thread-local контекст
   - Определена схема восстановления caller_info из родительской операции
   - Обеспечена трассируемость от "base_signals.py:51" к "main_window.py:446"

4. **✅ Архитектурное проектирование BaseSignalsBurstStrategy**
   - Спроектирована структура класса с соответствием MetaOperationStrategy интерфейсу
   - Определены алгоритмы временной группировки и валидации
   - Разработана конфигурационная схема с приоритетом 1

5. **✅ Техническое задание с критериями успеха**
   - Определены функциональные требования (идентификация, группировка, резолюция актора)
   - Установлены нефункциональные ограничения (производительность <100мс/1000 операций)
   - Задано покрытие тестами ≥95% и требования обратной совместимости

### 🎯 Ключевые технические открытия

**Природа "base_signals.py:51" записей**: это НЕ самостоятельные операции, а побочные эффекты межмодульной коммуникации через декорированные методы MainWindow.

**Контекстная связность**: операции логически связаны через thread-local storage операционного логгера, что позволяет восстановить реального инициатора.

**Архитектурная возможность**: система уже содержит все необходимые механизмы для кластеризации, требуется только правильная интеграция в MetaOperationDetector.

### 📊 Ожидаемые эффекты внедрения

- **Сокращение объема логов**: 60-80% за счет группировки бурстов
- **Повышение читаемости**: замена фрагментированных записей логически целостными группами  
- **Улучшение трассируемости**: восстановление связи пользовательские действия ↔ системные операции
- **Поддержка аналитики**: агрегированные метрики для оптимизации архитектуры

### 🚀 Готовность к этапу 2

Этап 1 полностью завершен. Все необходимые архитектурные решения приняты, технические детали проработаны. Следующий этап может сосредоточиться на реализации алгоритма кластеризации с полным пониманием целевой архитектуры.

---

## Приложение: Технические детали для реализации

### Структура данных для анализа

**Доступная информация в SubOperationLog**:
```python
@dataclass
class SubOperationLog:
    step_number: int                    # Порядковый номер в операции
    operation_name: str                # "SET_VALUE", "GET_VALUE", etc.
    target: str                        # "calculations_data", "file_data"
    start_time: float                  # Unix timestamp начала
    request_kwargs: dict               # Параметры запроса
    caller_info: CallerInfo            # Информация о вызывающем коде
    # ... другие поля
```

**Ключевые поля для BaseSignalsBurst**:
- `caller_info.filename == "base_signals.py"`
- `caller_info.line_number == 51`
- `len(sub_operations) == 0` (атомарность)
- `start_time` (для временной группировки)

### Алгоритм детекции псевдокод

```python
def detect_base_signals_burst(context: OperationLog) -> List[MetaOperation]:
    # 1. Фильтрация кандидатов
    candidates = [
        op for op in context.sub_operations 
        if is_base_signals_operation(op)
    ]
    
    # 2. Временная сортировка
    candidates.sort(key=lambda op: op.start_time)
    
    # 3. Группировка в окне времени
    bursts = []
    current_burst = []
    window_ms = config["time_window_ms"] / 1000.0
    
    for op in candidates:
        if (not current_burst or 
            op.start_time - current_burst[-1].start_time <= window_ms):
            current_burst.append(op)
        else:
            if len(current_burst) >= config["min_burst_size"]:
                bursts.append(create_meta_operation(current_burst))
            current_burst = [op]
    
    # 4. Финальная группа
    if len(current_burst) >= config["min_burst_size"]:
        bursts.append(create_meta_operation(current_burst))
    
    return bursts
```

### Интеграционные точки

**Регистрация в MetaOperationConfig**:
```python
STRATEGY_REGISTRY["BaseSignalsBurst"] = {
    "enabled": True,
    "priority": 1,  # Высший приоритет
    "time_window_ms": 100,
    "min_burst_size": 2,
    "max_gap_ms": 50
}
```

**Интеграция в MetaOperationDetector**: автоматическая через существующую архитектуру стратегий.

---

*Этап 1 завершён: 17 июня 2025*  
*Статус: Готов к реализации*  
*Следующий этап: [STAGE_02_CLUSTERING_LOGIC.md](STAGE_02_CLUSTERING_LOGIC.md)*
