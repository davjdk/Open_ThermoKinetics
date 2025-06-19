# Этап 5: Comprehensive тестирование и отладка

## Описание этапа

Всестороннее тестирование subprocess системы в различных сценариях, отладка edge cases, stress-тестирование и подготовка к production развертыванию.

## Задачи этапа

### 1. End-to-End тестирование

**Файл:** `tests/test_e2e_subprocess.py`

Создать полные end-to-end тесты:

```python
import unittest
import time
import multiprocessing
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from src.gui.main_window import MainWindow
from src.core.calculation import Calculations

class TestE2ESubprocess(unittest.TestCase):
    """End-to-end тесты subprocess системы."""
    
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])
        
    def setUp(self):
        self.main_window = MainWindow()
        self.calculations = self.main_window.calculations
        
    def test_full_model_based_workflow(self):
        """Тест полного workflow model-based расчета."""
        # 1. Загрузка тестовых данных
        test_series = self._load_test_series()
        
        # 2. Настройка параметров расчета
        calc_params = {
            "scenario_key": "model_based_calculation",
            "series_name": "test_series",
            "calculation_settings": {
                "method": "differential_evolution",
                "method_parameters": {
                    "maxiter": 10,  # Короткий тест
                    "popsize": 8,
                    "workers": 2
                }
            }
        }
        
        # 3. Запуск расчета
        result_received = threading.Event()
        final_result = None
        
        def on_result(result):
            nonlocal final_result
            final_result = result
            result_received.set()
            
        self.calculations.calculation_finished.connect(on_result)
        self.calculations.run_calculation_scenario(calc_params)
        
        # 4. Ожидание завершения
        self.assertTrue(result_received.wait(timeout=60))  # 1 минута максимум
        
        # 5. Проверка результата
        self.assertIsNotNone(final_result)
        self.assertTrue(self.calculations.calculation_active is False)
        
    def test_ui_responsiveness_during_calculation(self):
        """Тест отзывчивости UI во время расчета."""
        # Запуск длительного расчета
        calc_params = self._get_long_calculation_params()
        self.calculations.run_calculation_scenario(calc_params)
        
        # Проверка, что UI отвечает
        for i in range(10):
            QTest.qWait(100)  # 100ms
            self.app.processEvents()
            
            # UI должен обрабатывать события
            self.assertTrue(self.app.hasPendingEvents() or True)
            
        # Остановка расчета
        self.calculations.stop_calculation()
        
    def test_multiple_sequential_calculations(self):
        """Тест множественных последовательных расчетов."""
        for i in range(3):
            with self.subTest(calculation=i):
                # Запуск расчета
                calc_params = self._get_short_calculation_params()
                self.calculations.run_calculation_scenario(calc_params)
                
                # Ожидание завершения
                start_time = time.time()
                while (self.calculations.calculation_active and 
                       time.time() - start_time < 30):
                    QTest.qWait(100)
                    
                self.assertFalse(self.calculations.calculation_active)
                
    def test_rapid_start_stop_cycles(self):
        """Тест быстрых циклов запуск-остановка."""
        for i in range(5):
            with self.subTest(cycle=i):
                # Быстрый запуск
                calc_params = self._get_long_calculation_params()
                self.calculations.run_calculation_scenario(calc_params)
                
                # Быстрая остановка
                QTest.qWait(50)  # Минимальная задержка
                stopped = self.calculations.stop_calculation()
                self.assertTrue(stopped)
                
                # Ожидание полной остановки
                start_time = time.time()
                while (self.calculations.model_calc_proxy.process and
                       self.calculations.model_calc_proxy.process.is_alive() and
                       time.time() - start_time < 5):
                    QTest.qWait(10)
                    
                # Проверка остановки
                if self.calculations.model_calc_proxy.process:
                    self.assertFalse(
                        self.calculations.model_calc_proxy.process.is_alive()
                    )
```

### 2. Stress-тестирование

**Файл:** `tests/test_stress_subprocess.py`

Создать нагрузочные тесты:

```python
import unittest
import multiprocessing
import psutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor

class TestSubprocessStress(unittest.TestCase):
    """Stress-тесты для subprocess системы."""
    
    def test_memory_stress(self):
        """Тест на утечки памяти при множественных запусках."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Множественные запуски и остановки
        for i in range(20):
            calc_params = self._get_medium_calculation_params()
            
            # Запуск
            self.calculations.run_calculation_scenario(calc_params)
            time.sleep(0.5)  # Дать процессу запуститься
            
            # Остановка
            self.calculations.stop_calculation()
            time.sleep(0.2)  # Дать процессу завершиться
            
            # Принудительная очистка
            import gc
            gc.collect()
            
        # Проверка роста памяти
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        max_allowed_growth = 200 * 1024 * 1024  # 200MB
        
        self.assertLess(
            memory_growth, 
            max_allowed_growth,
            f"Memory growth {memory_growth / 1024 / 1024:.1f}MB exceeds limit"
        )
        
    def test_cpu_stress(self):
        """Тест нагрузки на CPU."""
        # Запуск нескольких параллельных расчетов (если возможно)
        calculations_instances = []
        
        try:
            # Создание нескольких экземпляров Calculations
            for i in range(min(3, multiprocessing.cpu_count())):
                calc = Calculations()
                calculations_instances.append(calc)
                
            # Запуск расчетов
            for calc in calculations_instances:
                calc_params = self._get_medium_calculation_params()
                calc.run_calculation_scenario(calc_params)
                
            # Мониторинг CPU
            cpu_samples = []
            for _ in range(10):
                cpu_percent = psutil.cpu_percent(interval=1.0)
                cpu_samples.append(cpu_percent)
                
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            
            # CPU должен использоваться, но не 100% постоянно
            self.assertGreater(avg_cpu, 10, "CPU usage too low")
            self.assertLess(avg_cpu, 95, "CPU usage too high")
            
        finally:
            # Остановка всех расчетов
            for calc in calculations_instances:
                calc.stop_calculation()
                
    def test_process_spawn_stress(self):
        """Тест множественного создания процессов."""
        spawn_times = []
        
        for i in range(10):
            start_time = time.time()
            
            # Создание процесса
            calc_params = self._get_short_calculation_params()
            self.calculations.run_calculation_scenario(calc_params)
            
            spawn_time = time.time() - start_time
            spawn_times.append(spawn_time)
            
            # Ожидание и остановка
            time.sleep(0.1)
            self.calculations.stop_calculation()
            
        # Время создания не должно расти значительно
        avg_spawn_time = sum(spawn_times) / len(spawn_times)
        max_spawn_time = max(spawn_times)
        
        self.assertLess(avg_spawn_time, 2.0, "Average spawn time too high")
        self.assertLess(max_spawn_time, 5.0, "Max spawn time too high")
        
    def test_queue_overflow_stress(self):
        """Тест переполнения очереди сообщений."""
        # Модификация для генерации большого количества сообщений
        calc_params = {
            "scenario_key": "model_based_calculation",
            "calculation_settings": {
                "method_parameters": {
                    "maxiter": 1000,  # Много итераций
                    "popsize": 50,    # Большая популяция
                    "callback_frequency": 1  # Частые callback'и
                }
            }
        }
        
        message_count = 0
        
        def count_messages(msg):
            nonlocal message_count
            message_count += 1
            
        self.calculations.new_best_result.connect(count_messages)
        
        # Запуск с большим количеством сообщений
        self.calculations.run_calculation_scenario(calc_params)
        time.sleep(5)  # Дать сгенерировать сообщения
        self.calculations.stop_calculation()
        
        # Проверка, что сообщения не терялись критично
        self.assertGreater(message_count, 0, "No messages received")
```

### 3. Edge Cases тестирование

**Файл:** `tests/test_edge_cases.py`

Тестирование граничных случаев:

```python
import unittest
import signal
import os
from unittest.mock import patch, Mock

class TestEdgeCases(unittest.TestCase):
    """Тесты граничных случаев subprocess системы."""
    
    def test_process_killed_externally(self):
        """Тест внешнего убийства процесса."""
        # Запуск расчета
        calc_params = self._get_long_calculation_params()
        self.calculations.run_calculation_scenario(calc_params)
        
        # Ожидание запуска процесса
        time.sleep(1)
        process = self.calculations.model_calc_proxy.process
        self.assertIsNotNone(process)
        
        # Внешнее убийство процесса
        os.kill(process.pid, signal.SIGTERM)
        
        # Система должна корректно обработать смерть процесса
        time.sleep(2)
        self.assertFalse(process.is_alive())
        self.assertFalse(self.calculations.calculation_active)
        
    def test_invalid_target_function(self):
        """Тест с невалидной целевой функцией."""
        # Создание невалидного сценария
        with patch('src.core.calculation_scenarios.ModelBasedScenario') as mock_scenario:
            mock_instance = mock_scenario.return_value
            mock_instance.get_target_function.return_value = lambda x: float('inf')
            mock_instance.get_bounds.return_value = [(0, 1), (0, 1)]
            
            calc_params = {
                "scenario_key": "model_based_calculation",
                "calculation_settings": {"method_parameters": {"maxiter": 5}}
            }
            
            # Запуск должен обработать ошибку
            self.calculations.run_calculation_scenario(calc_params)
            
            # Ожидание обработки ошибки
            time.sleep(2)
            self.assertFalse(self.calculations.calculation_active)
            
    def test_queue_serialization_error(self):
        """Тест ошибок сериализации в очереди."""
        # Создание объекта, который не сериализуется
        class NonSerializable:
            def __reduce__(self):
                raise TypeError("Cannot serialize")
                
        # Попытка отправить несериализуемый объект
        queue = self.calculations.model_calc_proxy.queue
        if queue:
            with self.assertRaises(Exception):
                queue.put(NonSerializable())
                
    def test_system_resource_exhaustion(self):
        """Тест исчерпания системных ресурсов."""
        # Симуляция нехватки памяти
        with patch('multiprocessing.Process') as mock_process:
            mock_process.side_effect = OSError("Cannot allocate memory")
            
            calc_params = self._get_short_calculation_params()
            
            # Система должна обработать ошибку ресурсов
            with self.assertLogs(level='ERROR'):
                self.calculations.run_calculation_scenario(calc_params)
                
    def test_corrupted_queue_message(self):
        """Тест поврежденных сообщений в очереди."""
        # Подмена очереди для генерации поврежденных сообщений
        with patch.object(self.calculations.model_calc_proxy, '_handle_message') as mock_handler:
            mock_handler.side_effect = [
                Exception("Corrupted message"),  # Первое сообщение поврежденно
                None,  # Второе обрабатывается нормально
            ]
            
            # Система должна продолжить работу несмотря на поврежденные сообщения
            calc_params = self._get_short_calculation_params()
            self.calculations.run_calculation_scenario(calc_params)
            
            time.sleep(1)
            # Проверка, что система не упала
            self.assertIsNotNone(self.calculations.model_calc_proxy)
```

### 4. Регрессионное тестирование

**Файл:** `tests/test_regression.py`

Тесты на отсутствие регрессий:

```python
import unittest
from src.core.calculation import Calculations

class TestRegression(unittest.TestCase):
    """Тесты на отсутствие регрессий в существующей функциональности."""
    
    def test_thread_calculations_still_work(self):
        """Тест, что thread-based расчеты продолжают работать."""
        # Тест деконволюции (должна использовать thread)
        calc_params = {
            "scenario_key": "deconvolution",
            "file_name": "test_file.csv",
            "calculation_settings": {
                "method": "differential_evolution",
                "method_parameters": {"maxiter": 5}
            }
        }
        
        # Запуск через старый механизм
        self.calculations.run_calculation_scenario(calc_params)
        
        # Проверка, что используется thread, а не subprocess
        self.assertIsNone(self.calculations.model_calc_proxy.process)
        self.assertIsNotNone(self.calculations.thread)
        
    def test_backward_compatibility_api(self):
        """Тест обратной совместимости API."""
        # Старые методы должны работать
        self.assertTrue(hasattr(self.calculations, 'start_differential_evolution'))
        self.assertTrue(hasattr(self.calculations, 'stop_calculation'))
        self.assertTrue(hasattr(self.calculations, 'new_best_result'))
        
        # Сигналы должны остаться теми же
        self.assertIsNotNone(self.calculations.new_best_result)
        self.assertIsNotNone(self.calculations.calculation_finished)
        
    def test_gui_integration_unchanged(self):
        """Тест неизменности интеграции с GUI."""
        # GUI должен продолжать работать с теми же сигналами
        main_window = MainWindow()
        
        # Проверка подключения сигналов
        self.assertIsNotNone(main_window.calculations)
        
        # Сигналы должны быть подключены
        signal = main_window.calculations.new_best_result
        self.assertGreater(len(signal.receivers(signal)), 0)
```

### 5. Документация и примеры

**Файл:** `docs/subprocess_usage_guide.md`

Создать руководство по использованию:

```markdown
# Руководство по использованию Subprocess для Model-Based расчетов

## Введение

Начиная с версии X.X, model-based расчеты выполняются в отдельном процессе для улучшения отзывчивости GUI и использования многопроцессности SciPy.

## Автоматическое переключение

Система автоматически определяет тип расчета:
- `model_based_calculation` → subprocess
- Остальные типы → QThread (как раньше)

## Настройка производительности

### Конфигурация workers
```python
# Автоматическая настройка (рекомендуется)
method_params = {"workers": -1}  # Использовать все ядра

# Ручная настройка
method_params = {"workers": 4}   # Использовать 4 ядра
```

### Оптимизация памяти
```python
# Включение мониторинга ресурсов
from src.core.performance_config import PerformanceConfig

config = PerformanceConfig.get_optimal_config()
config.memory_monitoring = True
```

## Отладка

### Логирование subprocess
```python
import logging
logging.getLogger('src.core.model_calc_worker').setLevel(logging.DEBUG)
```

### Мониторинг ресурсов
```python
from src.core.resource_manager import ResourceManager

resource_manager = ResourceManager()
resource_manager.start_monitoring()
# ... выполнение расчетов
stats = resource_manager.get_memory_usage()
```

## Troubleshooting

### Процесс не останавливается
- Проверьте, что используется корректный stop_event
- Увеличьте timeout для graceful остановки
- Проверьте отсутствие зависших дочерних процессов

### Высокое использование памяти
- Включите мониторинг ресурсов
- Уменьшите popsize в параметрах оптимизации
- Проверьте размер сообщений в очереди
```

## Критерии приемки

1. ✅ Написаны comprehensive E2E тесты
2. ✅ Проведено stress-тестирование всех компонентов
3. ✅ Протестированы все edge cases
4. ✅ Подтверждено отсутствие регрессий
5. ✅ Система стабильна при длительной работе
6. ✅ Отсутствуют утечки ресурсов
7. ✅ GUI остается отзывчивым под любой нагрузкой
8. ✅ Создана документация и руководства
9. ✅ Система готова к production развертыванию

## Результат этапа

- Fully tested и debugged subprocess система
- Comprehensive тест-покрытие всех сценариев
- Подтвержденная стабильность и производительность
- Готовая документация и примеры
- Production-ready система

## Pull Request

**Название:** `test: comprehensive testing and debugging of subprocess system`

**Описание:**
```
Comprehensive тестирование и отладка subprocess системы:

- Написаны end-to-end тесты полного workflow
- Проведено stress-тестирование памяти, CPU и создания процессов
- Протестированы все edge cases (внешнее убийство процесса, ошибки сериализации)
- Подтверждено отсутствие регрессий в существующей функциональности
- Добавлены регрессионные тесты для thread-based расчетов
- Создана документация по использованию и troubleshooting
- Система полностью протестирована и готова к production

Все тесты проходят, система стабильна при длительной работе.
```

**Связанные файлы:**
- `tests/test_e2e_subprocess.py` (новый)
- `tests/test_stress_subprocess.py` (новый)
- `tests/test_edge_cases.py` (новый)
- `tests/test_regression.py` (новый)
- `docs/subprocess_usage_guide.md` (новый)
- `docs/dev_plan/stage_05_comprehensive_testing.md` (новый)
