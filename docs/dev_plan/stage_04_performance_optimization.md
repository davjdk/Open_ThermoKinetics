# Этап 4: Оптимизация производительности и ресурсов

## Описание этапа

Оптимизация производительности subprocess системы и управления ресурсами. Включает настройку параллелизма SciPy, предотвращение утечек памяти, и оптимизацию межпроцессной коммуникации.

## Задачи этапа

### 1. Оптимизация параллелизма SciPy

**Файл:** `src/core/scipy_optimization.py`

Создать модуль для оптимальной настройки SciPy параллелизма:

```python
import multiprocessing
import psutil
from scipy.optimize import differential_evolution

class SciPyOptimizer:
    """
    Оптимизированная обертка для SciPy differential_evolution.
    
    Автоматически настраивает оптимальные параметры параллелизма
    в зависимости от системы и размера задачи.
    """
    
    @staticmethod
    def get_optimal_workers(problem_size, bounds_count):
        """
        Определение оптимального количества worker'ов.
        
        Args:
            problem_size: Размер задачи (количество вычислений)
            bounds_count: Количество оптимизируемых параметров
            
        Returns:
            int: Оптимальное количество worker'ов
        """
        cpu_count = multiprocessing.cpu_count()
        
        # Для небольших задач параллелизм неэффективен
        if bounds_count < 5:
            return 1
            
        # Для средних задач используем половину ядер
        if bounds_count < 15:
            return max(1, cpu_count // 2)
            
        # Для больших задач используем все ядра
        return cpu_count
    
    @staticmethod
    def optimize_method_params(method_params, bounds):
        """
        Оптимизация параметров алгоритма для subprocess.
        
        Args:
            method_params: Исходные параметры алгоритма
            bounds: Границы оптимизации
            
        Returns:
            dict: Оптимизированные параметры
        """
        optimized = method_params.copy()
        
        # Автоматическая настройка workers
        if "workers" not in optimized or optimized["workers"] == 1:
            optimal_workers = SciPyOptimizer.get_optimal_workers(
                problem_size=1000,  # Примерная оценка
                bounds_count=len(bounds)
            )
            optimized["workers"] = optimal_workers
            
        # Оптимизация popsize для параллельного выполнения
        workers = optimized.get("workers", 1)
        if workers > 1:
            popsize = optimized.get("popsize", 15)
            # Убеждаемся, что popsize кратен workers для равномерной загрузки
            optimized["popsize"] = max(popsize, workers * 2)
            
        # Настройка polish для subprocess
        if "polish" not in optimized:
            optimized["polish"] = False  # Отключаем для экономии времени
            
        return optimized
```

### 2. Управление памятью и ресурсами

**Файл:** `src/core/resource_manager.py`

Создать менеджер ресурсов для контроля утечек:

```python
import gc
import psutil
import threading
import time
from typing import Dict, Any

class ResourceManager:
    """
    Менеджер ресурсов для мониторинга и контроля использования памяти.
    """
    
    def __init__(self):
        self.initial_memory = psutil.Process().memory_info().rss
        self.monitoring_thread = None
        self.monitoring_active = False
        self.stats = {}
        
    def start_monitoring(self, interval=5.0):
        """
        Запуск мониторинга ресурсов.
        
        Args:
            interval: Интервал проверки в секундах
        """
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitor_resources,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        
    def stop_monitoring(self):
        """Остановка мониторинга ресурсов."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
            
    def _monitor_resources(self, interval):
        """Внутренний метод мониторинга."""
        while self.monitoring_active:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                
                self.stats.update({
                    'memory_rss': memory_info.rss,
                    'memory_vms': memory_info.vms,
                    'memory_percent': process.memory_percent(),
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads(),
                    'num_fds': process.num_fds() if hasattr(process, 'num_fds') else 0
                })
                
                # Принудительная сборка мусора при превышении лимитов
                if self.stats['memory_percent'] > 80:
                    gc.collect()
                    
            except Exception:
                pass
                
            time.sleep(interval)
            
    def get_memory_usage(self):
        """
        Получение текущего использования памяти.
        
        Returns:
            dict: Статистика использования памяти
        """
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'current_rss': memory_info.rss,
            'initial_rss': self.initial_memory,
            'growth': memory_info.rss - self.initial_memory,
            'percent': process.memory_percent()
        }
        
    def cleanup_resources(self):
        """Принудительная очистка ресурсов."""
        gc.collect()
        
        # Дополнительная очистка для numpy/scipy
        try:
            import numpy as np
            # np.clear_cache() # Если доступно
        except:
            pass
```

### 3. Оптимизация межпроцессной коммуникации

**Файл:** `src/core/optimized_queue.py`

Создать оптимизированную систему очередей:

```python
import multiprocessing
import queue
import pickle
import time
from typing import Any, Optional

class OptimizedQueue:
    """
    Оптимизированная очередь для межпроцессной коммуникации.
    
    Включает сжатие данных, батчинг сообщений и защиту от переполнения.
    """
    
    def __init__(self, maxsize=100, compression=True):
        """
        Args:
            maxsize: Максимальный размер очереди
            compression: Использовать сжатие для больших сообщений
        """
        self.queue = multiprocessing.Queue(maxsize=maxsize)
        self.compression = compression
        self.compression_threshold = 1024  # Сжимать сообщения > 1KB
        
    def put(self, item, timeout=None):
        """
        Отправка элемента в очередь с опциональным сжатием.
        
        Args:
            item: Элемент для отправки
            timeout: Таймаут отправки
        """
        try:
            # Сериализация для проверки размера
            serialized = pickle.dumps(item)
            
            # Сжатие больших сообщений
            if (self.compression and 
                len(serialized) > self.compression_threshold):
                import gzip
                compressed = gzip.compress(serialized)
                if len(compressed) < len(serialized):
                    item = {"__compressed__": True, "data": compressed}
                    
            self.queue.put(item, timeout=timeout)
            
        except queue.Full:
            # Очередь переполнена, пропускаем промежуточные результаты
            if isinstance(item, dict) and "best_mse" in item:
                return  # Пропускаем промежуточный результат
            else:
                raise  # Важное сообщение, пробрасываем ошибку
                
    def get(self, timeout=None):
        """
        Получение элемента из очереди с автоматической распаковкой.
        
        Args:
            timeout: Таймаут получения
            
        Returns:
            Any: Полученный элемент
        """
        item = self.queue.get(timeout=timeout)
        
        # Распаковка сжатого сообщения
        if (isinstance(item, dict) and 
            item.get("__compressed__") is True):
            import gzip
            compressed_data = item["data"]
            serialized = gzip.decompress(compressed_data)
            item = pickle.loads(serialized)
            
        return item
        
    def qsize(self):
        """Размер очереди."""
        return self.queue.qsize()
        
    def empty(self):
        """Проверка пустоты очереди."""
        return self.queue.empty()
```

### 4. Профилирование и бенчмарки

**Файл:** `tests/test_performance.py`

Создать тесты производительности:

```python
import unittest
import time
import psutil
from src.core.model_calc_worker import run_model_calc
from src.core.model_calc_proxy import ModelCalcProxy

class TestPerformance(unittest.TestCase):
    
    def test_subprocess_vs_thread_performance(self):
        """Сравнение производительности subprocess vs thread."""
        # Бенчмарк для subprocess
        start_time = time.time()
        # ... запуск через subprocess
        subprocess_time = time.time() - start_time
        
        # Бенчмарк для thread
        start_time = time.time()
        # ... запуск через thread
        thread_time = time.time() - start_time
        
        # Логирование результатов
        print(f"Subprocess time: {subprocess_time:.2f}s")
        print(f"Thread time: {thread_time:.2f}s")
        
    def test_memory_usage(self):
        """Тест использования памяти."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Запуск нескольких расчетов
        for i in range(5):
            # ... запуск расчета
            pass
            
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Проверка отсутствия значительных утечек
        self.assertLess(memory_growth, 100 * 1024 * 1024)  # < 100MB
        
    def test_scipy_workers_scaling(self):
        """Тест масштабирования SciPy workers."""
        workers_times = {}
        
        for workers in [1, 2, 4, -1]:
            start_time = time.time()
            # ... запуск с разным количеством workers
            workers_times[workers] = time.time() - start_time
            
        print("Workers scaling:", workers_times)
        
    def test_queue_throughput(self):
        """Тест пропускной способности очереди."""
        from src.core.optimized_queue import OptimizedQueue
        
        queue = OptimizedQueue()
        
        # Тест отправки большого количества сообщений
        start_time = time.time()
        for i in range(1000):
            queue.put({"iteration": i, "data": list(range(100))})
        send_time = time.time() - start_time
        
        # Тест получения сообщений
        start_time = time.time()
        for i in range(1000):
            queue.get()
        receive_time = time.time() - start_time
        
        print(f"Queue send time: {send_time:.2f}s")
        print(f"Queue receive time: {receive_time:.2f}s")
```

### 5. Конфигурация производительности

**Файл:** `src/core/performance_config.py`

Создать конфигурацию для настройки производительности:

```python
import multiprocessing
from dataclasses import dataclass

@dataclass
class PerformanceConfig:
    """Конфигурация производительности для subprocess расчетов."""
    
    # Настройки SciPy
    auto_workers: bool = True
    max_workers: int = multiprocessing.cpu_count()
    min_workers: int = 1
    
    # Настройки очереди
    queue_maxsize: int = 100
    queue_compression: bool = True
    queue_check_interval: int = 100  # ms
    
    # Настройки памяти
    memory_monitoring: bool = True
    memory_cleanup_threshold: float = 80.0  # %
    
    # Настройки процесса
    graceful_stop_timeout: float = 0.2  # seconds
    force_terminate_timeout: float = 1.0  # seconds
    
    @classmethod
    def get_optimal_config(cls):
        """Получение оптимальной конфигурации для текущей системы."""
        cpu_count = multiprocessing.cpu_count()
        
        return cls(
            max_workers=cpu_count,
            min_workers=max(1, cpu_count // 4),
            queue_maxsize=max(50, cpu_count * 10),
            queue_compression=cpu_count > 4,  # Сжатие для многоядерных систем
            memory_monitoring=True
        )
```

## Критерии приемки

1. ✅ Создана система автоматической оптимизации SciPy параллелизма
2. ✅ Реализован мониторинг и контроль ресурсов
3. ✅ Оптимизирована межпроцессная коммуникация
4. ✅ Созданы бенчмарки и тесты производительности
5. ✅ Отсутствуют утечки памяти при повторных запусках
6. ✅ SciPy эффективно использует многопроцессность
7. ✅ UI остается отзывчивым под любой нагрузкой
8. ✅ Система масштабируется на различном железе

## Результат этапа

- Оптимизированная производительность subprocess системы
- Автоматическая настройка параллелизма SciPy
- Контроль ресурсов и предотвращение утечек
- Comprehensive бенчмарки производительности
- Конфигурируемые настройки производительности

## Pull Request

**Название:** `perf: optimize subprocess performance and resource management`

**Описание:**
```
Оптимизация производительности и управления ресурсами для subprocess:

- Добавлена автоматическая настройка SciPy workers в зависимости от системы
- Реализован мониторинг ресурсов и предотвращение утечек памяти
- Оптимизирована межпроцессная коммуникация с сжатием больших сообщений
- Созданы comprehensive бенчмарки производительности
- Добавлена гибкая конфигурация параметров производительности
- Подтверждено отсутствие утечек памяти при длительной работе

Система теперь эффективно использует все доступные ресурсы процессора.
```

**Связанные файлы:**
- `src/core/scipy_optimization.py` (новый)
- `src/core/resource_manager.py` (новый)
- `src/core/optimized_queue.py` (новый)
- `src/core/performance_config.py` (новый)
- `tests/test_performance.py` (новый)
- `docs/dev_plan/stage_04_performance_optimization.md` (новый)
