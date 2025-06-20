# Техническое задание: Этап 2 - Средние изменения для оптимизации производительности MODEL_BASED_CALCULATION

## Общая информация

**Документ:** Этап 2 реализации OPTIMIZATION_PERFORMANCE_ANALYSIS.md  
**Ожидаемые сроки:** 4-8 часов  
**Ожидаемый результат:** Ускорение в 4-8 раз, утилизация CPU 70-85%  
**Сложность:** Средняя  

## Цели и задачи

### Основная цель
Реализовать средний уровень оптимизации производительности MODEL_BASED_CALCULATION путем добавления новых алгоритмов оптимизации, автоматической адаптации параметров и системы мониторинга производительности.

### Ключевые задачи
1. **Интеграция dual_annealing** как третьего метода оптимизации
2. **Реализация OptimizationConfigAdapter** для автоматического выбора параметров
3. **Добавление PerformanceMonitor** для отслеживания эффективности
4. **Расширение UI** для поддержки новых возможностей
5. **Комплексное тестирование** новой функциональности

## Детальное описание задач

### Задача 1: Интеграция Dual Annealing алгоритма

#### 1.1 Добавление dual_annealing в core/app_settings.py

**Файл:** `src/core/app_settings.py`

**Действия:**
- Добавить "dual_annealing" в список OPTIMIZATION_METHODS
- Создать конфигурацию DUAL_ANNEALING_DEFAULT_KWARGS
- Добавить валидационные диапазоны DUAL_ANNEALING_PARAM_RANGES

**Конкретная реализация:**
```python
# После существующих OPTIMIZATION_METHODS добавить:
OPTIMIZATION_METHODS = [
    "differential_evolution",
    "basinhopping", 
    "dual_annealing",  # НОВЫЙ МЕТОД
]

# Новые константы:
DUAL_ANNEALING_DEFAULT_KWARGS = {
    "maxiter": 1000,
    "initial_temp": 5230.0,
    "restart_temp_ratio": 2e-05,
    "visit": 2.62,
    "accept": -5.0,
    "maxfun": 1000000,
    "seed": None,
    "no_local_search": False,  # Важно для точности
    "callback": None,
    "x0": None,
}

DUAL_ANNEALING_PARAM_RANGES = {
    "maxiter": (100, 5000),
    "initial_temp": (1000.0, 10000.0),
    "restart_temp_ratio": (1e-06, 1e-03),
    "visit": (2.0, 3.0),
    "accept": (-10.0, 0.0),
    "maxfun": (100000, 10000000),
}
```

#### 1.2 Обновление ModelBasedScenario для поддержки dual_annealing

**Файл:** `src/core/calculation_scenarios.py`

**Действия:**
- Добавить импорт `from scipy.optimize import dual_annealing`
- Расширить метод run_optimization() для обработки dual_annealing
- Адаптировать обработку результатов

**Критические моменты:**
- dual_annealing имеет другой интерфейс callbacks по сравнению с DE и basinhopping
- Нужна корректная обработка bounds для dual_annealing формата
- Результат возвращается как OptimizeResult объект

#### 1.3 Обновление GUI компонентов

**Файлы:** 
- `src/gui/main_tab/sub_sidebar/model_based/calculation_settings_dialogs.py`
- `src/gui/main_tab/sub_sidebar/model_based/calculation_controls.py`

**Действия:**
- Добавить dual_annealing в ComboBox выбора метода
- Создать CalculationSettingsDualAnnealingDialog
- Обновить обработчики событий для нового метода

### Задача 2: Реализация OptimizationConfigAdapter

#### 2.1 Создание модуля автоматической адаптации

**Файл:** `src/core/optimization_config_adapter.py` (новый файл)

**Функциональность:**
```python
import multiprocessing as mp
import psutil
from typing import Dict, Any, Tuple
from .app_settings import (
    MODEL_BASED_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS,
    DEFAULT_BASINHOPPING_PARAMS,
    DUAL_ANNEALING_DEFAULT_KWARGS
)

class OptimizationConfigAdapter:
    """Автоматическая настройка параметров оптимизации под железо и задачу"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Получение информации о системе"""
        return {
            "cpu_count": mp.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / (1024**3),
            "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 2000,
        }
    
    @staticmethod
    def adapt_de_config(n_parameters: int, n_beta_values: int) -> Dict[str, Any]:
        """Адаптивная настройка DE под конкретную задачу"""
        # Детальная реализация из OPTIMIZATION_PERFORMANCE_ANALYSIS.md
        
    @staticmethod
    def adapt_basinhopping_config(n_parameters: int) -> Dict[str, Any]:
        """Адаптивная настройка basinhopping"""
        # Детальная реализация из OPTIMIZATION_PERFORMANCE_ANALYSIS.md
        
    @staticmethod
    def adapt_dual_annealing_config(n_parameters: int, n_beta_values: int) -> Dict[str, Any]:
        """Адаптивная настройка dual_annealing"""
        system_info = OptimizationConfigAdapter.get_system_info()
        base_config = DUAL_ANNEALING_DEFAULT_KWARGS.copy()
        
        # Адаптация под сложность задачи
        if n_parameters > 20:
            base_config["maxiter"] = 1500
            base_config["initial_temp"] = 7000.0
        elif n_parameters > 10:
            base_config["maxiter"] = 1200
        
        # Адаптация под количество скоростей нагрева
        if n_beta_values > 3:
            base_config["maxfun"] = base_config["maxfun"] * 2
            
        return base_config
    
    @staticmethod
    def recommend_method(n_parameters: int, n_beta_values: int, 
                        target_accuracy: str = "medium") -> str:
        """Рекомендация оптимального метода для задачи"""
        # Логика выбора из OPTIMIZATION_PERFORMANCE_ANALYSIS.md
```

#### 2.2 Интеграция адаптера в ModelBasedScenario

**Файл:** `src/core/calculation_scenarios.py`

**Действия:**
- Добавить импорт OptimizationConfigAdapter
- Модифицировать методы для использования адаптивных конфигураций
- Добавить логику автоматического выбора метода

**Ключевые изменения:**
```python
# В методе setup_optimization_params()
def setup_optimization_params(self, method: str, **user_kwargs):
    """Setup optimization parameters with adaptive configuration"""
    n_params = len(self.initial_params)
    n_betas = len(self.series_data.experimental_data.columns) - 1
    
    if method == "auto":
        method = OptimizationConfigAdapter.recommend_method(
            n_params, n_betas, target_accuracy=user_kwargs.get("target_accuracy", "medium")
        )
    
    if method == "differential_evolution":
        base_config = OptimizationConfigAdapter.adapt_de_config(n_params, n_betas)
    elif method == "basinhopping":
        base_config = OptimizationConfigAdapter.adapt_basinhopping_config(n_params)
    elif method == "dual_annealing":
        base_config = OptimizationConfigAdapter.adapt_dual_annealing_config(n_params, n_betas)
    
    # Merge user overrides
    base_config.update(user_kwargs)
    return method, base_config
```

### Задача 3: Реализация PerformanceMonitor

#### 3.1 Создание модуля мониторинга производительности

**Файл:** `src/core/performance_monitor.py` (новый файл)

**Основной функционал:**
```python
import time
import psutil
import threading
from typing import List, Tuple, Optional
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal

@dataclass
class PerformanceMetrics:
    """Структура для хранения метрик производительности"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    active_threads: int
    mse_value: Optional[float] = None

class PerformanceMonitor(QObject):
    """Мониторинг производительности оптимизации в реальном времени"""
    
    # Qt сигналы для обновления UI
    metrics_updated = pyqtSignal(object)  # PerformanceMetrics
    performance_summary = pyqtSignal(str)  # Текстовая сводка
    
    def __init__(self, monitoring_interval: float = 1.0):
        super().__init__()
        self.monitoring_interval = monitoring_interval
        self.start_time = None
        self.metrics_history: List[PerformanceMetrics] = []
        self.monitoring = False
        self.monitor_thread = None
        self._lock = threading.Lock()
        
    def start_monitoring(self):
        """Запуск мониторинга производительности"""
        
    def stop_monitoring(self):
        """Остановка мониторинга"""
        
    def add_mse_point(self, mse_value: float):
        """Добавление точки MSE для отслеживания сходимости"""
        
    def get_performance_summary(self) -> str:
        """Получение текстовой сводки производительности"""
        
    def plot_performance(self, save_path: Optional[str] = None):
        """Построение графиков производительности"""
        
    def export_metrics(self, filename: str):
        """Экспорт метрик в CSV для детального анализа"""
```

#### 3.2 Интеграция мониторинга в ModelBasedTargetFunction

**Файл:** `src/core/calculation_scenarios.py`

**Действия:**
- Добавить поддержку PerformanceMonitor в ModelBasedTargetFunction
- Интегрировать отслеживание MSE значений
- Добавить callback для обновления метрик

**Реализация:**
```python
class ModelBasedTargetFunction:
    def __init__(self, *args, performance_monitor: Optional[PerformanceMonitor] = None, **kwargs):
        # ...existing code...
        self.performance_monitor = performance_monitor
        self.call_count = 0
        
    def __call__(self, params: np.ndarray) -> float:
        self.call_count += 1
        start_time = time.time()
        
        # ...existing calculation logic...
        
        if self.performance_monitor and self.call_count % 10 == 0:
            self.performance_monitor.add_mse_point(total_mse)
            
        return total_mse
```

### Задача 4: Расширение пользовательского интерфейса

#### 4.1 Добавление мониторинга в ModelBasedPanel

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/model_based_panel.py`

**Действия:**
- Добавить виджет отображения производительности
- Интегрировать PerformanceMonitor в панель
- Добавить кнопки управления мониторингом

**Компоненты:**
```python
class PerformanceWidget(QWidget):
    """Виджет отображения метрик производительности в реальном времени"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Labels для отображения метрик
        self.cpu_label = QLabel("CPU: ---%")
        self.memory_label = QLabel("Memory: ---%") 
        self.time_label = QLabel("Time: ---s")
        self.mse_label = QLabel("Current MSE: ---")
        
        # Progress bar для CPU утилизации
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setMaximum(100)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        self.start_monitoring_btn = QPushButton("Start Monitoring")
        self.stop_monitoring_btn = QPushButton("Stop Monitoring")
        self.export_metrics_btn = QPushButton("Export Metrics")
        
        # Layout assembly
        layout.addWidget(QLabel("Performance Monitor"))
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.cpu_progress)
        layout.addWidget(self.memory_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.mse_label)
        
        button_layout.addWidget(self.start_monitoring_btn)
        button_layout.addWidget(self.stop_monitoring_btn)
        button_layout.addWidget(self.export_metrics_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
```

#### 4.2 Обновление CalculationControls

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/calculation_controls.py`

**Действия:**
- Добавить опцию "Auto-select method" 
- Интегрировать адаптивную конфигурацию
- Добавить отображение рекомендованного метода

#### 4.3 Создание DualAnnealingSettingsDialog

**Файл:** `src/gui/main_tab/sub_sidebar/model_based/calculation_settings_dialogs.py`

**Действия:**
- Создать диалог настроек для dual_annealing
- Добавить валидацию параметров
- Интегрировать с адаптивной конфигурацией

### Задача 5: Комплексное тестирование

#### 5.1 Модульные тесты

**Файл:** `tests/test_optimization_stage2.py` (новый файл)

**Тестовые случаи:**
- Тестирование OptimizationConfigAdapter для различных конфигураций
- Проверка корректности dual_annealing интеграции
- Валидация PerformanceMonitor метрик
- Тестирование UI компонентов

```python
import pytest
import multiprocessing as mp
from src.core.optimization_config_adapter import OptimizationConfigAdapter
from src.core.performance_monitor import PerformanceMonitor

class TestOptimizationConfigAdapter:
    """Тесты адаптера конфигурации оптимизации"""
    
    def test_system_info_collection(self):
        """Тест сбора информации о системе"""
        info = OptimizationConfigAdapter.get_system_info()
        assert "cpu_count" in info
        assert info["cpu_count"] == mp.cpu_count()
        assert "memory_gb" in info
        assert info["memory_gb"] > 0
        
    def test_de_config_adaptation(self):
        """Тест адаптации DE конфигурации"""
        # Тест для малых задач
        config = OptimizationConfigAdapter.adapt_de_config(5, 2)
        assert config["popsize"] >= 15
        assert config["workers"] > 0
        
        # Тест для больших задач
        config_large = OptimizationConfigAdapter.adapt_de_config(25, 4)
        assert config_large["maxiter"] <= config["maxiter"]  # Меньше итераций для больших задач
        
    def test_method_recommendation(self):
        """Тест рекомендации метода оптимизации"""
        # Малые задачи высокой точности
        method = OptimizationConfigAdapter.recommend_method(5, 2, "high")
        assert method == "dual_annealing"
        
        # Большие задачи
        method_large = OptimizationConfigAdapter.recommend_method(25, 4, "medium")
        assert method_large == "differential_evolution"

class TestPerformanceMonitor:
    """Тесты монитора производительности"""
    
    def test_monitoring_lifecycle(self):
        """Тест жизненного цикла мониторинга"""
        monitor = PerformanceMonitor(monitoring_interval=0.1)
        
        # Запуск мониторинга
        monitor.start_monitoring()
        assert monitor.monitoring is True
        
        # Ожидание нескольких метрик
        time.sleep(0.3)
        assert len(monitor.metrics_history) > 0
        
        # Остановка мониторинга
        monitor.stop_monitoring()
        assert monitor.monitoring is False
        
    def test_mse_tracking(self):
        """Тест отслеживания MSE значений"""
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        # Добавление MSE точек
        monitor.add_mse_point(1.5)
        monitor.add_mse_point(1.2)
        monitor.add_mse_point(0.8)
        
        monitor.stop_monitoring()
        
        # Проверка наличия MSE данных
        mse_points = [m for m in monitor.metrics_history if m.mse_value is not None]
        assert len(mse_points) == 3
        assert mse_points[-1].mse_value == 0.8
```

#### 5.2 Интеграционные тесты

**Файл:** `tests/test_model_based_integration_stage2.py` (новый файл)

**Тестовые сценарии:**
- Полный цикл оптимизации с dual_annealing
- Интеграция PerformanceMonitor с ModelBasedScenario
- Тестирование адаптивной конфигурации в реальных условиях

#### 5.3 Тесты производительности

**Файл:** `tests/test_performance_benchmarks.py` (новый файл)

**Бенчмарки:**
- Сравнение времени выполнения до и после оптимизации
- Измерение утилизации CPU для разных методов
- Валидация ускорения в 4-8 раз

## Технические требования

### Требования к производительности
- **Утилизация CPU:** 70-85% при использовании всех доступных ядер
- **Ускорение:** В 4-8 раз по сравнению с первоначальной реализацией
- **Память:** Не более 2 GB дополнительного использования памяти
- **Отзывчивость UI:** GUI должен оставаться отзывчивым во время оптимизации

### Требования к совместимости
- **Python версии:** 3.8+
- **Зависимости:** Все новые зависимости должны быть добавлены в pyproject.toml
- **ОС:** Windows, Linux, macOS
- **Обратная совместимость:** Существующие конфигурации должны продолжать работать

### Требования к качеству кода
- **Покрытие тестами:** Минимум 85% для новых модулей
- **Документация:** Полное покрытие docstrings в стиле Google
- **Типизация:** Использование type hints для всех публичных API
- **Линтинг:** Соответствие правилам black, isort, flake8

## Структура файлов

### Новые файлы
```
src/
  core/
    optimization_config_adapter.py     # Адаптивная конфигурация
    performance_monitor.py             # Мониторинг производительности
  gui/
    main_tab/sub_sidebar/model_based/
      performance_widget.py            # UI для мониторинга

tests/
  test_optimization_stage2.py         # Модульные тесты
  test_model_based_integration_stage2.py  # Интеграционные тесты
  test_performance_benchmarks.py      # Бенчмарки производительности

docs/
  develop_plan/
    optimization_stage2_results.md    # Отчет о результатах
```

### Модифицируемые файлы
```
src/
  core/
    app_settings.py                   # Новые константы и конфигурации
    calculation_scenarios.py          # Интеграция новых возможностей
  gui/
    main_tab/sub_sidebar/model_based/
      model_based_panel.py           # Интеграция мониторинга
      calculation_controls.py        # Поддержка auto-select
      calculation_settings_dialogs.py # Новый диалог dual_annealing
```

## План выполнения

### Этап 2.1: Подготовка инфраструктуры (1-2 часа)
1. Создание новых модулей:
   - `optimization_config_adapter.py`
   - `performance_monitor.py` 
2. Обновление `app_settings.py` с новыми константами
3. Настройка базовой структуры тестов

### Этап 2.2: Реализация основного функционала (2-3 часа)
1. Реализация OptimizationConfigAdapter
2. Интеграция dual_annealing в ModelBasedScenario
3. Реализация PerformanceMonitor
4. Обновление ModelBasedTargetFunction

### Этап 2.3: Интеграция с UI (1-2 часа)
1. Создание PerformanceWidget
2. Обновление ModelBasedPanel
3. Создание DualAnnealingSettingsDialog
4. Обновление CalculationControls

### Этап 2.4: Тестирование и отладка (1-2 часа)
1. Написание и запуск модульных тестов
2. Интеграционное тестирование
3. Бенчмарки производительности
4. Исправление найденных проблем

### Этап 2.5: Документация и финализация (30 минут)
1. Обновление документации API
2. Создание отчета о результатах
3. Подготовка к следующему этапу

## Критерии успеха

### Функциональные критерии
- ✅ dual_annealing успешно интегрирован и работает
- ✅ OptimizationConfigAdapter корректно адаптирует параметры
- ✅ PerformanceMonitor отслеживает метрики в реальном времени
- ✅ GUI поддерживает все новые возможности
- ✅ Все тесты проходят успешно

### Критерии производительности
- ✅ Утилизация CPU 70-85% (по сравнению с 20-30% до оптимизации)
- ✅ Ускорение в 4-8 раз по времени выполнения
- ✅ Автоматический выбор оптимального метода работает корректно
- ✅ Мониторинг не влияет существенно на производительность (overhead < 5%)

### Критерии качества
- ✅ Покрытие тестами >= 85%
- ✅ Все новые модули имеют полную документацию
- ✅ Код соответствует стандартам проекта
- ✅ Обратная совместимость сохранена

## Риски и их митигация

### Риск 1: Производительность dual_annealing ниже ожидаемой
**Митигация:** Тщательная настройка параметров и сравнительное тестирование с DE и basinhopping

### Риск 2: Overhead мониторинга влияет на производительность
**Митигация:** Асинхронный мониторинг в отдельном потоке, настраиваемая частота сбора метрик

### Риск 3: Сложность автоматической адаптации параметров
**Митигация:** Начать с простых эвристик, постепенно усложнять, обширное тестирование

### Риск 4: Проблемы интеграции с существующим UI
**Митигация:** Тщательное планирование изменений, поэтапная интеграция, тестирование на каждом шаге

## Заключение

Этап 2 представляет собой сбалансированное расширение функциональности, которое должно дать существенное ускорение производительности при умеренной сложности реализации. Ключевые преимущества:

1. **Новый алгоритм оптимизации** (dual_annealing) для лучшего качества решений
2. **Автоматическая адаптация** под характеристики задачи и железа
3. **Мониторинг производительности** для контроля эффективности
4. **Улучшенный UX** с автоматическим выбором методов

После успешной реализации этапа 2 система будет готова к более глубоким оптимизациям этапа 3, включающим параллелизацию целевой функции и Numba оптимизации.
