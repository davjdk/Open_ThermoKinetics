# Руководство пользователя: Система кластеризации мета-операций

## Введение

Система кластеризации мета-операций автоматически группирует логически связанные подоперации в более крупные семантические блоки, что существенно улучшает читаемость логов и помогает выявлять паттерны для оптимизации.

## Основные возможности

### Автоматическое выявление паттернов
- **Временная группировка**: Операции, выполняющиеся в быстрой последовательности
- **Модульная группировка**: Операции, направленные на один компонент системы
- **Именная группировка**: Операции с похожими именами (GET_*, SET_*, UPDATE_*)
- **Последовательная группировка**: Цепочки однотипных операций

### Улучшенная читаемость логов
- Компактное представление множественных операций
- Семантические названия для групп операций
- Метрики производительности на уровне кластеров
- Возможность развертывания деталей по требованию

## Конфигурация

### Основные настройки

Конфигурация находится в `src/core/log_aggregator/meta_operation_config.py`:

```python
META_OPERATION_CONFIG = {
    "enabled": True,  # Включение/отключение всей системы
    "strategies": {
        # Группировка по времени
        "time_window": {
            "enabled": True,
            "time_window_ms": 50,     # Временное окно в миллисекундах
            "min_cluster_size": 2     # Минимальный размер кластера
        },
        
        # Группировка по целевому модулю
        "target_cluster": {
            "enabled": True,
            "min_cluster_size": 2
        },
        
        # Группировка по паттернам имен
        "name_similarity": {
            "enabled": True,
            "name_pattern": r"(GET_|SET_|UPDATE_).*",  # Regex паттерн
            "min_cluster_size": 2
        },
        
        # Группировка последовательностей
        "sequence_count": {
            "enabled": False,        # По умолчанию отключено
            "min_sequence_count": 3, # Минимальная длина последовательности
            "min_cluster_size": 3
        }
    },
    
    # Настройки форматирования
    "formatting": {
        "mode": "compact",                    # compact, detailed, table, json
        "show_individual_operations": True,   # Показывать отдельные операции
        "meta_operation_summary": True        # Показывать сводку мета-операций
    }
}
```

### Включение/отключение функциональности

**Полное отключение**:
```python
META_OPERATION_CONFIG["enabled"] = False
```

**Отключение конкретной стратегии**:
```python
META_OPERATION_CONFIG["strategies"]["time_window"]["enabled"] = False
```

**Настройка параметров временного окна**:
```python
# Для более агрессивной группировки
META_OPERATION_CONFIG["strategies"]["time_window"]["time_window_ms"] = 100

# Для более точной группировки
META_OPERATION_CONFIG["strategies"]["time_window"]["time_window_ms"] = 25
```

## Режимы форматирования

### Компактный режим (по умолчанию)
Показывает мета-операции в виде краткой сводки с возможностью развертывания деталей:

```
META-OPERATIONS DETECTED:
⚡ [time_window_cluster_1] File Data Operations (2 steps, 0.004s)
⚡ [target_cluster_calc] Calculation Updates (6 steps, 0.015s)
```

### Детальный режим
Показывает полную информацию о каждом кластере:

```python
META_OPERATION_CONFIG["formatting"]["mode"] = "detailed"
```

### Табличный режим
Интегрирует мета-операции прямо в основную таблицу операций:

```python
META_OPERATION_CONFIG["formatting"]["mode"] = "table"
```

### JSON режим
Выводит структурированные данные для программного анализа:

```python
META_OPERATION_CONFIG["formatting"]["mode"] = "json"
```

## Интерпретация результатов

### Типичные паттерны кластеризации

**1. Batch File Operations (Пакетные файловые операции)**
```
⚡ [time_window_cluster_1] File Data Operations (3 steps, 0.008s)
  → CHECK_EXPERIMENT_EXISTS, GET_DF_DATA, LOAD_FILE
```
**Интерпретация**: Последовательность загрузки и валидации файла

**2. Calculation Parameter Updates (Обновления параметров расчета)**
```
⚡ [target_cluster_calc] Calculation Updates (8 steps, 0.020s)
  → SET_VALUE, UPDATE_VALUE, SET_VALUE, UPDATE_VALUE...
```
**Интерпретация**: Пакетное обновление параметров реакции

**3. Series Data Processing (Обработка серийных данных)**
```
⚡ [name_similarity_get] Data Retrieval Operations (4 steps, 0.012s)
  → GET_SERIES_VALUE, GET_DF_DATA, GET_VALUE, GET_EXPERIMENTAL_DATA
```
**Интерпретация**: Сбор данных для анализа серии

### Метрики производительности

**Время выполнения кластера**: Общее время всех операций в группе
**Количество шагов**: Число операций в кластере
**Эффективность группировки**: Процент операций, попавших в кластеры

## Диагностика и отладка

### Включение debug-режима

Для получения детальной информации о работе системы кластеризации:

```python
import logging
logging.getLogger("solid_state_kinetics.operations").setLevel(logging.DEBUG)
```

### Проверка работы стратегий

**Временная стратегия не работает**:
- Проверьте настройку `time_window_ms` - возможно, операции выполняются слишком медленно
- Убедитесь, что `min_cluster_size` не слишком большой

**Целевая стратегия группирует слишком много**:
- Проверьте, что операции действительно должны быть сгруппированы
- Рассмотрите увеличение `min_cluster_size`

**Именная стратегия не находит паттерны**:
- Проверьте корректность regex в `name_pattern`
- Убедитесь, что имена операций соответствуют ожидаемому формату

### Просмотр статистики группировки

После выполнения операций можно проанализировать эффективность:

```python
# В debug логах будет информация вида:
# DEBUG: TimeWindowStrategy: Clustered 6/8 operations into 2 groups
# DEBUG: TargetClusterStrategy: Clustered 4/8 operations into 1 group
# DEBUG: Total clustering efficiency: 75% (6/8 operations)
```

## Рекомендации по использованию

### Начальная настройка
1. Начните с включения только `time_window` стратегии
2. Проанализируйте результаты на реальных операциях
3. Постепенно включайте другие стратегии
4. Настройте параметры под специфику вашего workflow

### Оптимизация производительности
- Для высоконагруженных систем рассмотрите отключение детального форматирования
- Используйте JSON режим для автоматического анализа логов
- Отключите неиспользуемые стратегии

### Анализ паттернов
- Ищите кластеры с большим количеством операций - возможные места для оптимизации
- Обращайте внимание на временные характеристики кластеров
- Анализируйте повторяющиеся паттерны для выявления workflow проблем

## Примеры реальных сценариев

### Сценарий 1: Загрузка эксперимента
```
Operation "LOAD_EXPERIMENT" – STARTED

META-OPERATIONS DETECTED:
⚡ [time_window_cluster_1] File Validation (3 steps, 0.005s)
⚡ [target_cluster_file] Data Loading (2 steps, 0.125s)

SUMMARY: steps 5, meta-operations 2, total time 0.130s
```

### Сценарий 2: Деконволюция пиков
```
Operation "DECONVOLUTION" – STARTED

META-OPERATIONS DETECTED:
⚡ [target_cluster_calc] Parameter Setup (12 steps, 0.008s)
⚡ [sequence_cluster_1] Iterative Optimization (24 steps, 2.450s)
⚡ [target_cluster_calc] Result Storage (6 steps, 0.003s)

SUMMARY: steps 42, meta-operations 3, total time 2.461s
```

### Сценарий 3: Model-based анализ
```
Operation "MODEL_BASED_CALCULATION" – STARTED

META-OPERATIONS DETECTED:
⚡ [name_similarity_get] Data Collection (8 steps, 0.015s)
⚡ [time_window_cluster_1] Scheme Validation (4 steps, 0.002s)
⚡ [sequence_cluster_1] Differential Evolution (156 steps, 45.230s)
⚡ [target_cluster_series] Result Integration (3 steps, 0.008s)

SUMMARY: steps 171, meta-operations 4, total time 45.255s
```

## Поддержка и решение проблем

### Часто встречающиеся проблемы

**Проблема**: Мета-операции не создаются
**Решение**: 
1. Проверьте, что `enabled: True` в конфигурации
2. Убедитесь, что операции соответствуют критериям группировки
3. Проверьте значения `min_cluster_size`

**Проблема**: Слишком агрессивная группировка
**Решение**:
1. Уменьшите `time_window_ms`
2. Увеличьте `min_cluster_size`
3. Отключите неподходящие стратегии

**Проблема**: Логи стали слишком подробными
**Решение**:
1. Переключитесь на компактный режим: `"mode": "compact"`
2. Отключите детали: `"show_individual_operations": False`

### Техническая поддержка

При обнаружении проблем:
1. Включите debug логирование
2. Соберите примеры проблемных операций
3. Проверьте конфигурацию стратегий
4. Обратитесь к разработчикам с подробным описанием

---

Система кластеризации мета-операций - мощный инструмент для анализа и оптимизации workflow приложения. Правильная настройка позволяет значительно улучшить читаемость логов и выявить возможности для повышения производительности.
