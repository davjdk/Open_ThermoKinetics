# Этап 5: Форматирование и отображение результатов

## Цель этапа
Реализовать поддержку кластеров BaseSignalsMetaBurst в системе форматирования вывода с корректным отображением шумовых операций и сводной информации.

## Задачи

### 5.1 Анализ существующей системы форматирования

**Изучение OperationTableFormatter:**
- Понимание текущих возможностей отображения мета-операций
- Анализ методов `format_meta_operations()` и `format_table_with_meta()`
- Определение точек расширения для BaseSignalsMetaBurst

**Изучение formatter_config.py:**
- Доступные опции форматирования
- Настройки отображения мета-операций
- Конфигурируемые параметры вывода

### 5.2 Расширение конфигурации форматирования

**Обновление FormatterConfig для поддержки BaseSignalsMetaBurst:**

```python
# В formatter_config.py
DEFAULT_FORMATTING_CONFIG = {
    # ...существующие опции...
    
    "base_signals_burst": {
        "show_in_table": True,                    # Показывать в основной таблице
        "collapsed_by_default": True,            # Свернутое отображение по умолчанию
        "show_noise_markers": True,              # Помечать шумовые операции
        "noise_marker": "[*]",                   # Маркер для шумовых операций
        "show_detailed_summary": True,           # Детальная сводка кластера
        "group_header_style": "enhanced",        # Стиль заголовка группы
        "indent_sub_operations": True,           # Отступы для подопераций
    },
    
    "meta_operation_display": {
        "show_cluster_boundaries": True,         # Показывать границы кластеров
        "highlight_base_signals": True,          # Выделять base_signals операции
        "summary_position": "after_operations",  # Позиция сводки (before/after/both)
    },
}
```

### 5.3 Специализированный форматтер для BaseSignalsMetaBurst

**Создание BaseSignalsBurstFormatter в table_formatter.py:**

```python
class BaseSignalsBurstFormatter:
    """
    Специализированный форматтер для отображения кластеров BaseSignalsMetaBurst.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.noise_marker = config.get("noise_marker", "[*]")
        self.show_noise_markers = config.get("show_noise_markers", True)
        
    def format_cluster(self, meta_operation: 'MetaOperation', 
                      table_formatter: 'OperationTableFormatter') -> List[str]:
        """
        Форматирует кластер BaseSignalsMetaBurst для вывода.
        
        Args:
            meta_operation: Мета-операция для форматирования
            table_formatter: Основной форматтер таблицы
            
        Returns:
            List[str]: Отформатированные строки кластера
        """
        lines = []
        
        # Заголовок кластера
        header = self._format_cluster_header(meta_operation)
        lines.append(header)
        
        # Детализированные операции (если не свернуто)
        if not self._is_collapsed(meta_operation):
            detail_lines = self._format_cluster_details(meta_operation, table_formatter)
            lines.extend(detail_lines)
        
        # Сводка кластера
        if self.config.get("show_detailed_summary", True):
            summary = self._format_cluster_summary(meta_operation)
            lines.append(summary)
            
        return lines
    
    def _format_cluster_header(self, meta_operation: 'MetaOperation') -> str:
        """Форматирует заголовок кластера."""
        # Используем описание из стратегии
        description = meta_operation.description or "BaseSignalsBurst"
        
        # Добавляем визуальные маркеры
        cluster_id = meta_operation.meta_id.split('_')[-1]  # Последняя часть ID
        header = f"⚡ [{cluster_id}] {description}"
        
        return header
    
    def _format_cluster_details(self, meta_operation: 'MetaOperation', 
                               table_formatter: 'OperationTableFormatter') -> List[str]:
        """Форматирует детальный список операций кластера."""
        lines = []
        
        # Сортировка операций по времени/шагу
        sorted_operations = sorted(meta_operation.sub_operations, 
                                 key=lambda x: x.step_number)
        
        for i, sub_op in enumerate(sorted_operations, 1):
            # Определяем, является ли операция шумовой
            is_noise = not self._is_base_signals_operation(sub_op)
            
            # Форматируем строку операции
            op_line = self._format_sub_operation(sub_op, i, is_noise, table_formatter)
            lines.append(op_line)
            
        return lines
    
    def _format_sub_operation(self, sub_op: 'SubOperationLog', index: int, 
                             is_noise: bool, table_formatter: 'OperationTableFormatter') -> str:
        """Форматирует отдельную подоперацию."""
        # Базовое форматирование через основной форматтер
        base_format = table_formatter._format_operation_row(sub_op)
        
        # Добавляем маркеры и отступы
        indent = "    "  # Отступ для подопераций
        
        if is_noise and self.show_noise_markers:
            # Добавляем маркер шума
            noise_marker = f"{self.noise_marker} "
            formatted_line = f"{indent}{index:2d}. {noise_marker}{base_format}"
        else:
            formatted_line = f"{indent}{index:2d}. {base_format}"
            
        return formatted_line
    
    def _format_cluster_summary(self, meta_operation: 'MetaOperation') -> str:
        """Форматирует сводку кластера."""
        operations = meta_operation.sub_operations
        
        # Подсчет статистики
        total_ops = len(operations)
        base_signals_ops = sum(1 for op in operations if self._is_base_signals_operation(op))
        noise_ops = total_ops - base_signals_ops
        
        # Вычисление времени
        if operations:
            start_time = min(op.start_time for op in operations if op.start_time)
            end_times = [op.end_time or op.start_time for op in operations if op.start_time]
            end_time = max(end_times) if end_times else start_time
            duration_ms = int((end_time - start_time) * 1000) if start_time and end_time else 0
        else:
            duration_ms = 0
        
        # Формирование сводки
        summary_parts = [
            f"Итого: {total_ops} операций",
            f"base_signals: {base_signals_ops}",
        ]
        
        if noise_ops > 0:
            summary_parts.append(f"шум: {noise_ops}")
            
        summary_parts.append(f"время: {duration_ms} мс")
        
        summary = f"    └─ {', '.join(summary_parts)}"
        return summary
    
    def _is_base_signals_operation(self, sub_op: 'SubOperationLog') -> bool:
        """Проверяет, является ли операция base_signals операцией."""
        # Используем ту же логику, что и в стратегии
        return (sub_op.target == "base_signals" or 
                "base_signals" in str(sub_op.target).lower() or
                "signal" in sub_op.operation_name.lower() if sub_op.operation_name else False)
    
    def _is_collapsed(self, meta_operation: 'MetaOperation') -> bool:
        """Определяет, должен ли кластер быть свернут."""
        return self.config.get("collapsed_by_default", True)
```

### 5.4 Интеграция в OperationTableFormatter

**Расширение основного форматтера:**

```python
# В классе OperationTableFormatter добавить:

def _format_base_signals_burst_meta_operation(self, meta_operation: 'MetaOperation') -> List[str]:
    """
    Специализированное форматирование для BaseSignalsMetaBurst.
    
    Args:
        meta_operation: Мета-операция типа BaseSignalsMetaBurst
        
    Returns:
        List[str]: Отформатированные строки
    """
    # Проверяем, что это действительно BaseSignalsMetaBurst
    if not meta_operation.meta_id.startswith("base_signals_burst_"):
        return self._format_generic_meta_operation(meta_operation)
    
    # Получаем конфигурацию для BaseSignalsMetaBurst
    config = self.config.get("base_signals_burst", {})
    
    # Создаем специализированный форматтер
    burst_formatter = BaseSignalsBurstFormatter(config)
    
    # Форматируем кластер
    return burst_formatter.format_cluster(meta_operation, self)

def _get_meta_operation_formatter(self, meta_operation: 'MetaOperation') -> callable:
    """
    Возвращает подходящий форматтер для мета-операции.
    
    Args:
        meta_operation: Мета-операция для форматирования
        
    Returns:
        callable: Метод форматирования
    """
    if meta_operation.meta_id.startswith("base_signals_burst_"):
        return self._format_base_signals_burst_meta_operation
    elif meta_operation.meta_id.startswith("time_window_"):
        return self._format_time_window_meta_operation
    else:
        return self._format_generic_meta_operation
```

### 5.5 Улучшение отображения в различных режимах

**Поддержка компактного режима:**

```python
def _format_compact_base_signals_burst(self, meta_operation: 'MetaOperation') -> str:
    """Компактное отображение BaseSignalsMetaBurst."""
    description = meta_operation.description or "BaseSignalsBurst"
    op_count = len(meta_operation.sub_operations)
    
    return f"⚡ {description} ({op_count} ops)"

def _format_json_base_signals_burst(self, meta_operation: 'MetaOperation') -> Dict[str, Any]:
    """JSON представление BaseSignalsMetaBurst."""
    operations = meta_operation.sub_operations
    
    return {
        "type": "BaseSignalsMetaBurst",
        "meta_id": meta_operation.meta_id,
        "description": meta_operation.description,
        "statistics": {
            "total_operations": len(operations),
            "base_signals_operations": sum(1 for op in operations 
                                         if self._is_base_signals_operation(op)),
            "noise_operations": sum(1 for op in operations 
                                  if not self._is_base_signals_operation(op)),
            "duration_ms": self._calculate_duration_ms(operations),
        },
        "operations": [self._operation_to_dict(op) for op in operations]
    }
```

### 5.6 Настройки отображения маркеров шума

**Конфигурируемые маркеры и стили:**

```python
NOISE_MARKER_STYLES = {
    "asterisk": "[*]",
    "warning": "[!]", 
    "tilde": "[~]",
    "arrow": "[→]",
    "dot": "[·]",
    "hash": "[#]",
}

def _apply_noise_styling(self, operation_text: str, is_noise: bool) -> str:
    """
    Применяет стилизацию для шумовых операций.
    
    Args:
        operation_text: Исходный текст операции
        is_noise: Является ли операция шумовой
        
    Returns:
        str: Стилизованный текст
    """
    if not is_noise or not self.config.get("show_noise_markers", True):
        return operation_text
    
    marker_style = self.config.get("noise_marker_style", "asterisk")
    marker = NOISE_MARKER_STYLES.get(marker_style, "[*]")
    
    # Дополнительная стилизация (цвет, курсив) если поддерживается терминалом
    if self.config.get("use_color", False):
        return f"\033[90m{marker}\033[0m {operation_text}"  # Серый цвет
    else:
        return f"{marker} {operation_text}"
```

## Результат этапа
- Специализированный форматтер для BaseSignalsMetaBurst кластеров
- Корректное отображение шумовых операций с маркерами
- Поддержка различных режимов вывода (детальный, компактный, JSON)
- Конфигурируемые стили и маркеры
- Интеграция в существующую систему форматирования
- Детальные сводки кластеров с статистикой

## Файлы для изменения
- `src/core/log_aggregator/table_formatter.py` - основные изменения форматирования
- `src/core/log_aggregator/formatter_config.py` - конфигурация отображения

## Критерии готовности
- [ ] BaseSignalsMetaBurst кластеры корректно отображаются в таблице
- [ ] Шумовые операции помечены маркерами
- [ ] Сводки кластеров содержат детальную статистику  
- [ ] Поддерживаются различные режимы отображения
- [ ] Конфигурация форматирования работает корректно
- [ ] Интеграция с существующим форматтером не ломает другие функции
