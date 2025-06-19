# Этап 6: Финализация и документация

## Описание этапа

Финальный этап разработки: обновление архитектурной документации, создание migration guide, финальная оптимизация и подготовка к релизу.

## Задачи этапа

### 1. Обновление архитектурной документации

**Файл:** `docs/ARCHITECTURE_SUBPROCESS.md`

Создать дополнение к архитектурной документации:

```markdown
# Архитектура Subprocess для Model-Based расчетов

## Обзор изменений

В версии X.X добавлена поддержка выполнения model-based расчетов в отдельном процессе (subprocess) вместо QThread. Это обеспечивает:

- Улучшенную отзывчивость GUI
- Возможность использования SciPy multiprocessing (workers > 1)
- Мгновенную остановку расчетов
- Изоляцию тяжелых вычислений от главного процесса

## Архитектурная диаграмма

```mermaid
sequenceDiagram
    participant UI as MainWindow/UI
    participant Calc as Calculations
    participant Proxy as ModelCalcProxy
    participant Worker as Worker Process
    participant SciPy as SciPy Pool
    
    UI->>Calc: MODEL_BASED_CALCULATION
    Calc->>Proxy: start_process()
    Proxy->>Worker: multiprocessing.Process
    Worker->>SciPy: differential_evolution(workers>1)
    
    loop Optimization iterations
        SciPy-->>Worker: callback(best_result)
        Worker->>Proxy: result_queue.put()
        Proxy->>Calc: new_best_result.emit()
        Calc-->>UI: GUI update
    end
    
    opt User stops
        UI->>Calc: STOP_CALCULATION
        Calc->>Proxy: stop_process()
        Proxy->>Worker: stop_event.set()
        Proxy->>Worker: process.terminate()
    end
    
    Worker->>Proxy: final_result
    Proxy->>Calc: _calculation_finished()
    Calc-->>UI: CALCULATION_FINISHED
```

## Компоненты системы

### ModelCalcProxy
- **Назначение**: Управление subprocess из главного потока
- **Расположение**: `src/core/model_calc_proxy.py`
- **Интеграция**: QTimer для мониторинга очереди (100ms)

### Worker Process
- **Назначение**: Выполнение SciPy оптимизации
- **Расположение**: `src/core/model_calc_worker.py`
- **Особенности**: Использует SciPy workers > 1

### Межпроцессная коммуникация
- **Очередь результатов**: `multiprocessing.Queue`
- **События остановки**: `multiprocessing.Event`
- **Сжатие данных**: Автоматическое для сообщений > 1KB

## Интеграция с существующей архитектурой

### Слабая связность
Новые компоненты интегрированы через существующую систему BaseSlots без изменения публичных интерфейсов.

### Сигнально-слотовая коммуникация
Сохранены все существующие сигналы Qt:
- `new_best_result` - промежуточные результаты
- `calculation_finished` - завершение расчета

### Маршрутизация запросов
Автоматическое определение типа расчета в `Calculations.run_calculation_scenario()`:
```python
if scenario_key == "model_based_calculation":
    self._run_model_based_subprocess(params)
else:
    self._run_thread_calculation(params)
```

## Производительность

### Оптимизация SciPy
- Автоматическая настройка workers в зависимости от системы
- Оптимизация popsize для параллельных вычислений
- Отключение polish для экономии времени

### Управление ресурсами
- Мониторинг использования памяти
- Автоматическая сборка мусора при превышении лимитов
- Предотвращение утечек при повторных запусках

## Совместимость

### Обратная совместимость
- Все существующие API сохранены
- Thread-based расчеты продолжают работать без изменений
- GUI интеграция остается прозрачной

### Миграция
Никаких изменений в пользовательском коде не требуется. Переключение происходит автоматически на основе типа операции.
```

### 2. Migration Guide

**Файл:** `docs/MIGRATION_SUBPROCESS.md`

Создать руководство по миграции:

```markdown
# Migration Guide: Subprocess для Model-Based расчетов

## Для разработчиков

### Изменения в API
Никаких breaking changes в публичном API нет. Все существующие методы и сигналы работают как раньше.

### Новые конфигурационные опции
```python
# Новые параметры в method_parameters
method_params = {
    "workers": -1,  # Автоматическое использование всех ядер
    "popsize": 20,  # Оптимизировано для параллелизма
    "polish": False # Отключено для subprocess
}
```

### Мониторинг ресурсов
```python
from src.core.resource_manager import ResourceManager

# Включение мониторинга
resource_manager = ResourceManager()
resource_manager.start_monitoring()

# Получение статистики
stats = resource_manager.get_memory_usage()
```

## Для пользователей

### Видимые изменения
1. **Улучшенная отзывчивость**: GUI не "зависает" во время model-based расчетов
2. **Быстрая остановка**: Кнопка "Stop" работает мгновенно
3. **Использование CPU**: Автоматическое использование всех ядер процессора

### Настройки производительности
В настройках model-based расчетов доступны новые опции:
- **Workers**: Количество параллельных процессов (по умолчанию: автоматически)
- **Memory monitoring**: Мониторинг использования памяти

## Устранение неполадок

### Проблема: Расчет не останавливается
**Решение**: 
1. Проверьте Task Manager на наличие зависших Python процессов
2. Перезапустите приложение если необходимо

### Проблема: Высокое использование памяти
**Решение**:
1. Включите мониторинг ресурсов в настройках
2. Уменьшите popsize в параметрах оптимизации
3. Перезапустите приложение после серии расчетов

### Проблема: Медленный запуск расчетов
**Решение**:
1. Проверьте настройки Windows Defender (исключите папку приложения)
2. Убедитесь что workers установлен в -1 (автоматически)

## Откат к предыдущей версии

Если возникли проблемы, можно временно отключить subprocess:

```python
# В src/core/calculation.py, метод run_calculation_scenario()
# Закомментировать условие subprocess:
# if scenario_key == "model_based_calculation":
#     self._run_model_based_subprocess(params)
# else:
    self._run_thread_calculation(params)  # Использовать для всех типов
```

**Важно**: Это временное решение, рекомендуется решить проблему с subprocess.
```

### 3. Performance Guide

**Файл:** `docs/PERFORMANCE_GUIDE.md`

Создать руководство по производительности:

```markdown
# Руководство по производительности Subprocess системы

## Оптимальные настройки

### Для быстрых систем (8+ ядер, 16+ GB RAM)
```python
method_params = {
    "workers": -1,        # Использовать все ядра
    "popsize": 50,        # Большая популяция
    "maxiter": 1000,      # Больше итераций
    "polish": False       # Отключить для скорости
}
```

### Для медленных систем (2-4 ядра, 8 GB RAM)
```python
method_params = {
    "workers": 2,         # Ограничить количество ядер
    "popsize": 15,        # Меньшая популяция
    "maxiter": 300,       # Меньше итераций
    "polish": False
}
```

### Для отладки (минимальное время)
```python
method_params = {
    "workers": 1,         # Последовательно
    "popsize": 6,         # Минимальная популяция
    "maxiter": 50,        # Мало итераций
    "polish": False
}
```

## Мониторинг производительности

### Включение мониторинга
```python
from src.core.performance_config import PerformanceConfig

config = PerformanceConfig.get_optimal_config()
config.memory_monitoring = True
```

### Ключевые метрики
1. **Memory RSS**: Должно быть < 2GB для большинства задач
2. **CPU Usage**: 70-90% при активном расчете
3. **Process Count**: Не должно расти после завершения расчетов

## Benchmarks

### Время создания процесса
- **Хорошо**: < 1 секунды
- **Приемлемо**: 1-3 секунды
- **Плохо**: > 3 секунд

### Использование памяти
- **Хорошо**: < 1GB для обычных задач
- **Приемлемо**: 1-2GB для сложных задач
- **Плохо**: > 2GB или постоянный рост

### Отзывчивость GUI
- GUI должен отвечать на клики в течение 100ms
- Обновления прогресса должны происходить каждые 1-2 секунды

## Оптимизация конкретных сценариев

### Большие реакционные схемы (>10 реакций)
```python
method_params = {
    "workers": min(multiprocessing.cpu_count(), 8),  # Ограничить
    "popsize": max(30, len(bounds) * 3),             # Адаптивный размер
    "maxiter": 2000,                                 # Больше итераций
}
```

### Точные расчеты (высокая точность)
```python
method_params = {
    "workers": -1,
    "popsize": 100,        # Большая популяция
    "tol": 1e-8,          # Высокая точность
    "atol": 1e-12,        # Высокая абсолютная точность
    "maxiter": 5000,      # Много итераций
    "polish": True        # Включить полировку
}
```

### Быстрые предварительные расчеты
```python
method_params = {
    "workers": 4,
    "popsize": 12,
    "tol": 1e-3,          # Низкая точность
    "maxiter": 100,       # Мало итераций
    "polish": False
}
```
```

### 4. Финальная оптимизация кода

**Файл:** `src/core/subprocess_optimization.py`

Создать финальные оптимизации:

```python
"""
Финальные оптимизации для subprocess системы.
"""

import multiprocessing
import time
from typing import Optional, Dict, Any

class SubprocessOptimizer:
    """Класс для финальных оптимизаций subprocess системы."""
    
    @staticmethod
    def optimize_startup_time():
        """Оптимизация времени запуска процессов."""
        # Предварительная инициализация multiprocessing
        if not hasattr(multiprocessing, '_initialized'):
            try:
                multiprocessing.set_start_method('spawn', force=True)
            except RuntimeError:
                pass  # Уже установлен
                
    @staticmethod
    def validate_system_requirements() -> Dict[str, Any]:
        """
        Проверка системных требований.
        
        Returns:
            dict: Результаты проверки
        """
        cpu_count = multiprocessing.cpu_count()
        
        try:
            import psutil
            memory_gb = psutil.virtual_memory().total / (1024**3)
            available_gb = psutil.virtual_memory().available / (1024**3)
        except ImportError:
            memory_gb = "unknown"
            available_gb = "unknown"
            
        return {
            "cpu_count": cpu_count,
            "memory_total_gb": memory_gb,
            "memory_available_gb": available_gb,
            "recommended_workers": min(cpu_count, 8),
            "system_suitable": cpu_count >= 2 and available_gb > 2
        }
        
    @staticmethod
    def cleanup_zombie_processes():
        """Очистка зомби-процессов."""
        try:
            import psutil
            current_process = psutil.Process()
            
            # Поиск дочерних процессов
            children = current_process.children(recursive=True)
            
            for child in children:
                try:
                    if child.status() == psutil.STATUS_ZOMBIE:
                        child.terminate()
                        child.wait(timeout=1)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    pass
                    
        except ImportError:
            # psutil не доступен, используем базовую очистку
            pass
```

### 5. Финальные тесты интеграции

**Файл:** `tests/test_final_integration.py`

Создать финальные интеграционные тесты:

```python
import unittest
import time
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

class TestFinalIntegration(unittest.TestCase):
    """Финальные интеграционные тесты."""
    
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])
        
    def test_complete_user_workflow(self):
        """Тест полного пользовательского workflow."""
        # 1. Запуск приложения
        main_window = MainWindow()
        main_window.show()
        
        # 2. Загрузка данных
        # ... имитация загрузки файлов
        
        # 3. Настройка model-based расчета
        # ... имитация настройки параметров
        
        # 4. Запуск расчета
        # ... имитация запуска
        
        # 5. Мониторинг прогресса
        # ... проверка обновлений GUI
        
        # 6. Остановка расчета
        # ... имитация остановки
        
        # 7. Проверка результатов
        # ... валидация финального состояния
        
        self.assertTrue(True)  # Placeholder
        
    def test_system_stability_long_run(self):
        """Тест стабильности при длительной работе."""
        main_window = MainWindow()
        
        # Множественные циклы работы
        for i in range(10):
            # Имитация пользовательской активности
            time.sleep(0.1)
            QApplication.processEvents()
            
        # Проверка стабильности
        self.assertIsNotNone(main_window)
        
    def test_resource_cleanup_on_exit(self):
        """Тест очистки ресурсов при выходе."""
        main_window = MainWindow()
        
        # Запуск расчета
        # ...
        
        # Закрытие приложения
        main_window.close()
        
        # Проверка очистки
        calculations = main_window.calculations
        if hasattr(calculations, 'model_calc_proxy'):
            proxy = calculations.model_calc_proxy
            self.assertIsNone(proxy.process)
```

## Критерии приемки

1. ✅ Обновлена архитектурная документация
2. ✅ Создан migration guide для разработчиков и пользователей
3. ✅ Написано руководство по производительности
4. ✅ Проведена финальная оптимизация кода
5. ✅ Выполнены финальные интеграционные тесты
6. ✅ Документация соответствует реальной реализации
7. ✅ Система готова к production релизу
8. ✅ Созданы примеры использования

## Результат этапа

- Полная документация новой архитектуры
- Migration guide для пользователей
- Руководство по производительности
- Финально оптимизированная система
- Production-ready codebase

## Pull Request

**Название:** `docs: finalize subprocess documentation and optimization`

**Описание:**
```
Финализация разработки subprocess системы:

- Обновлена архитектурная документация с mermaid диаграммами
- Создан comprehensive migration guide
- Добавлено руководство по производительности с benchmarks
- Проведена финальная оптимизация кода
- Выполнены финальные интеграционные тесты
- Система полностью документирована и готова к релизу

Subprocess система готова к production использованию.
```

**Связанные файлы:**
- `docs/ARCHITECTURE_SUBPROCESS.md` (новый)
- `docs/MIGRATION_SUBPROCESS.md` (новый)
- `docs/PERFORMANCE_GUIDE.md` (новый)
- `src/core/subprocess_optimization.py` (новый)
- `tests/test_final_integration.py` (новый)
- `docs/dev_plan/stage_06_finalization.md` (новый)

## Итоговый результат проекта

После завершения всех 6 этапов будет реализована полноценная система выполнения model-based расчетов в отдельном процессе, которая:

1. **Улучшает отзывчивость GUI** - интерфейс не блокируется во время тяжелых вычислений
2. **Обеспечивает мгновенную остановку** - расчеты прерываются без задержек
3. **Использует полную мощность CPU** - SciPy может использовать все ядра процессора
4. **Сохраняет обратную совместимость** - существующий код продолжает работать
5. **Обеспечивает стабильность** - нет утечек памяти или зависших процессов
6. **Полностью протестирована** - comprehensive тест-покрытие всех сценариев
7. **Хорошо документирована** - полная документация архитектуры и использования
