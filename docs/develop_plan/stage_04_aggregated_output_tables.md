# Этап 4: Система агрегированного вывода таблиц

## Цель этапа
Создать систему автоматического формирования и отображения ASCII-таблиц с агрегированными метриками операций.

## Задачи этапа

### 4.1 Выбор и интеграция библиотеки форматирования таблиц
- Выбрать подходящую open source библиотеку (rich, tabulate, prettytable)
- Установить зависимость через poetry/pip
- Изучить возможности выбранной библиотеки
- Определить единый стиль таблиц для проекта

### 4.2 Разработка структуры метрик операций  
- Определить базовый набор метрик для всех операций
- Создать расширяемую систему пользовательских метрик
- Адаптировать форматирование под выбранную библиотеку
- Обеспечить локализацию и читаемость результатов

### 4.3 Интеграция с библиотекой Rich Console
```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

class OperationTableFormatter:
    def __init__(self):
        self.console = Console()
    
    def format_operation_summary(self, operation_data: dict) -> str:
        """Форматировать сводку операции используя Rich"""
        
    def format_with_rich_table(self, operation_data: dict) -> Table:
        """Создать Rich Table для операции"""
        
    def format_error_panel(self, error_info: dict) -> Panel:
        """Форматировать ошибку как Rich Panel"""
```

### 4.4 Реализация форматтера с Rich
```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from typing import Dict, Any

class RichOperationFormatter:
    """Форматтер операций используя библиотеку Rich"""
    
    def __init__(self):
        self.console = Console()
    
    def format_operation_summary(self, operation_data: Dict[str, Any]) -> None:
        """Вывести сводку операции используя Rich Console"""
        
        # Создать основную таблицу
        table = Table(
            title="🔄 OPERATION SUMMARY", 
            box=box.ROUNDED,
            show_header=False,
            title_style="bold blue"
        )
        
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="white", width=40)
        
        # Добавить строки с данными
        status_icon = "✅" if operation_data.get("status") == "SUCCESS" else "❌"
        table.add_row("Operation", operation_data.get("display_name", "Unknown"))
        table.add_row("Status", f"{status_icon} {operation_data.get('status', 'UNKNOWN')}")
        table.add_row("Duration", f"{operation_data.get('duration', 0):.3f}s")
        
        if operation_data.get("call_count", 0) > 1:
            nested_info = f"{operation_data['call_count']} (+ {operation_data.get('nested_operations', 0)} nested)"
            table.add_row("Calls", nested_info)
        
        if operation_data.get("files_modified", 0) > 0:
            table.add_row("Files Modified", str(operation_data["files_modified"]))
            
        if operation_data.get("thread_id"):
            table.add_row("Thread", operation_data["thread_id"])
            
        # Вывести таблицу
        self.console.print(table)
        
        # Если есть ошибка, показать панель с деталями
        if operation_data.get("status") == "ERROR":
            self._format_error_panel(operation_data.get("error_info", {}))
    
    def _format_error_panel(self, error_info: Dict[str, Any]) -> None:
        """Форматировать панель с информацией об ошибке"""
        
        error_text = Text()
        error_text.append("Error Type: ", style="bold red")
        error_text.append(error_info.get("type", "Unknown"), style="red")
        error_text.append("\nMessage: ", style="bold red") 
        error_text.append(error_info.get("message", "No message"), style="red")
        
        if error_info.get("recovery_attempted"):
            error_text.append("\n\n🔄 Recovery was attempted", style="yellow")
        
        panel = Panel(
            error_text,
            title="❌ Error Details",
            border_style="red",
            box=box.HEAVY
        )
        
        self.console.print(panel)
    
    def format_metrics_table(self, metrics: Dict[str, Any]) -> None:
        """Форматировать дополнительные метрики в отдельной таблице"""
        
        if not metrics:
            return
            
        table = Table(
            title="📊 Operation Metrics",
            box=box.SIMPLE,
            show_header=True
        )
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Сгруппировать метрики по типам
        for key, value in metrics.items():
            if isinstance(value, float):
                formatted_value = f"{value:.3f}"
            elif isinstance(value, int):
                formatted_value = str(value)
            else:
                formatted_value = str(value)
                
            table.add_row(key.replace("_", " ").title(), formatted_value)
        
        self.console.print(table)
```

## Альтернативные библиотеки для форматирования

### 4.5 Вариант 1: Rich (Рекомендуемый)
```python
# Установка: pip install rich

from rich.console import Console
from rich.table import Table

# Преимущества:
# - Богатые возможности форматирования
# - Поддержка цветов и стилей
# - Прогресс-бары и спиннеры
# - Панели и разметка
# - Активная разработка

console = Console()
table = Table(title="Operation Summary")
table.add_column("Property", style="cyan")
table.add_column("Value", style="magenta")
console.print(table)
```

### 4.6 Вариант 2: Tabulate
```python
# Установка: pip install tabulate

from tabulate import tabulate

# Преимущества:
# - Простота использования
# - Множество форматов вывода
# - Легковесная библиотека
# - Стабильная и надёжная

data = [["Operation", "Add Reaction"], ["Status", "✅ SUCCESS"]]
table = tabulate(data, tablefmt="grid")
print(table)
```

### 4.7 Вариант 3: PrettyTable  
```python
# Установка: pip install prettytable

from prettytable import PrettyTable

# Преимущества:
# - Классический ASCII стиль
# - Простое API
# - Лёгкая настройка

table = PrettyTable()
table.field_names = ["Property", "Value"]
table.add_row(["Operation", "Add Reaction"])
print(table)
```

### 4.8 Выбор библиотеки Rich как основной
**Обоснование выбора Rich:**
- **Современный дизайн:** Красивые таблицы с поддержкой Unicode и цветов
- **Расширенные возможности:** Панели для ошибок, прогресс-бары для долгих операций
- **Активная разработка:** Регулярные обновления и поддержка сообщества
- **Консольные приложения:** Идеально подходит для научных инструментов
- **Markdown поддержка:** Возможность экспорта в различные форматы

```python
# pyproject.toml - добавить зависимость
[tool.poetry.dependencies]
rich = "^13.0.0"
```

### Файловые метрики
```python
file_metrics = {
    "files_read": 2,                           # Количество прочитанных файлов
    "files_written": 1,                        # Количество записанных файлов
    "files_modified": 3,                       # Количество изменённых файлов
    "total_file_size": "1.2 MB",              # Общий размер обработанных файлов
}
```

### Доменные метрики (кинетический анализ)
```python
kinetics_metrics = {
    "reactions_found": 3,                      # Найдено реакций
    "coefficients_optimized": 15,              # Оптимизировано коэффициентов
    "convergence_iterations": 42,              # Итераций до сходимости
    "r_squared": 0.998,                        # Коэффициент детерминации
    "rmse": 0.0023,                           # Среднеквадратичная ошибка
}
```

### Метрики ошибок
```python
error_metrics = {
    "error_type": "ValueError",                # Тип исключения
    "error_message": "Invalid coefficient",   # Сообщение об ошибке
    "error_traceback": "...",                 # Сокращённый traceback
    "recovery_attempted": True,               # Была ли попытка восстановления
}
```

## Форматы вывода Rich таблиц

### Успешная операция с Rich
```python
# Результат форматирования через Rich
╭─────────────────── 🔄 OPERATION SUMMARY ───────────────────╮
│ Operation     │ Add Reaction                                │
│ Status        │ ✅ SUCCESS                                 │
│ Duration      │ 0.523s                                      │
│ Calls         │ 1 (+ 3 nested)                            │
│ Files Modified│ 2                                          │
│ Thread        │ MainThread                                 │
│ Timestamp     │ 2025-06-14 15:30:45                       │
╰─────────────────────────────────────────────────────────────╯

# Дополнительные метрики в отдельной таблице
┌─────────────────── 📊 Operation Metrics ───────────────────┐
│ Metric              │ Value                                │
├─────────────────────┼──────────────────────────────────────┤
│ Reactions Found     │ 3                                    │
│ R² Score           │ 0.998                                │
│ Convergence Iters  │ 42                                   │
│ Memory Used        │ 1.2 MB                               │
└─────────────────────┴──────────────────────────────────────┘
```

### Операция с ошибкой через Rich
```python
╭─────────────────── 🔄 OPERATION SUMMARY ───────────────────╮
│ Operation     │ Model Optimization                          │
│ Status        │ ❌ ERROR                                   │
│ Duration      │ 1.234s                                      │
│ Files Modified│ 0                                          │
│ Thread        │ MainThread                                 │
╰─────────────────────────────────────────────────────────────╯

╭───────────────────── ❌ Error Details ─────────────────────╮
│ Error Type: ValueError                                      │
│ Message: Invalid coefficient bounds                         │
│                                                             │
│ 🔄 Recovery was attempted                                  │
╰─────────────────────────────────────────────────────────────╯
```

## Настройки конфигурации для Rich

### Параметры Rich форматирования
```python
rich_config = {
    "enabled": True,                           # Включить Rich форматирование
    "force_terminal": False,                   # Принудительно использовать терминальный режим
    "width": None,                             # Ширина консоли (None = авто)
    "color_system": "auto",                    # auto/standard/256/truecolor/windows
    "theme": "default",                        # Тема оформления
    
    # Настройки таблиц
    "table_box": "ROUNDED",                    # ROUNDED/SQUARE/SIMPLE/HEAVY
    "show_header": True,                       # Показывать заголовки
    "header_style": "bold blue",               # Стиль заголовков
    "title_style": "bold cyan",                # Стиль заголовка таблицы
    
    # Настройки панелей ошибок
    "error_panel_style": "red",                # Стиль панели ошибок
    "error_box": "HEAVY",                      # Стиль рамки ошибок
    "show_error_panels": True,                 # Показывать панели ошибок
    
    # Экспорт
    "export_svg": False,                       # Экспорт в SVG
    "export_html": False,                      # Экспорт в HTML
    "record_mode": False,                      # Режим записи для экспорта
}
```

## Ожидаемые результаты
- Интеграция библиотеки Rich для профессионального форматирования таблиц
- Красивый консольный вывод с поддержкой цветов и Unicode
- Настраиваемые стили и темы оформления через конфигурацию
- Расширенные возможности: панели ошибок, экспорт, прогресс-бары

## Критерии готовности
- Rich библиотека интегрирована и настроена
- После каждой операции выводится отформатированная Rich таблица
- Ошибки отображаются в красивых панелях с деталями
- Форматирование настраивается через конфигурацию

## Тестирование
- Тест различных стилей Rich таблиц (ROUNDED, SQUARE, SIMPLE)
- Тест панелей ошибок и цветового оформления
- Тест производительности Rich форматирования
- Тест совместимости с различными терминалами
- Тест экспорта в HTML/SVG форматы

## Интеграция
- Автоматический вызов из `OperationLogger.end_operation()`
- Использование Rich Console для всего вывода
- Настройка Rich через глобальную конфигурацию
- Поддержка fallback на простой текст при необходимости
