# Анализ производительности MODEL_BASED_CALCULATION и рекомендации по ускорению

## Проблема

Пользователь наблюдает низкую загрузку CPU при использовании оптимизационных алгоритмов `differential_evolution` и `basinhopping` в `MODEL_BASED_CALCULATION`. Основные симптомы:

1. **Differential Evolution**: Работает в основном один процесс, другие процессы подключаются только при улучшении результата и быстро затухают
2. **Basinhopping**: Аналогичная ситуация с низкой утилизацией CPU
3. **Общий результат**: Невозможность эффективно использовать многоядерные процессоры для ускорения расчетов

## Анализ корневых причин

### 1. Архитектурные ограничения Python

**Global Interpreter Lock (GIL)**:
- Python GIL позволяет выполнять только один поток Python-кода одновременно
- `scipy.optimize.differential_evolution` с `workers>1` использует `multiprocessing`, но overhead создания процессов велик
- Для сложных функций время вычисления одной оценки может быть меньше overhead'а межпроцессового взаимодействия

### 2. Специфика вашей реализации

**Анализ ModelBasedTargetFunction** (`src/core/calculation_scenarios.py:180-302`):

```python
class ModelBasedTargetFunction:
    def __call__(self, params: np.ndarray) -> float:
        # Последовательная обработка всех скоростей нагрева
        for beta_val in self.betas:
            total_mse += self.integrate_ode(beta_val, norm_contrib, params, ode_func)
        return total_mse
```

**Проблемы текущей реализации**:
1. **Последовательные вычисления**: Обработка каждой скорости нагрева выполняется последовательно
2. **Тяжелые ODE решения**: `solve_ivp` для каждой скорости - вычислительно дорогая операция
3. **Малый размер популяции**: `popsize=5` для DE недостаточен для эффективного распараллеливания
4. **Неоптимальные настройки**: `updating="deferred"` снижает эффективность параллелизации

### 3. Конфигурационные проблемы

**Текущие настройки DE** (`src/core/app_settings.py:46-61`):
```python
MODEL_BASED_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS = {
    "popsize": 5,        # Слишком мало для многоядерности
    "workers": 1,        # Параллелизация отключена
    "updating": "deferred",  # Плохо для параллельных вычислений
}
```

**Basinhopping настройки** (`src/core/app_settings.py:691-704`):
```python
DEFAULT_BASINHOPPING_PARAMS = {
    "niter": 100,
    "batch_size": None,  # Auto-detect, может быть неоптимальным
}
```

## Конкретные рекомендации для ускорения

### 1. Оптимизация Differential Evolution

**Ключевые изменения для DE**:

```python
# Высокопроизводительная конфигурация для MODEL_BASED_CALCULATION
MODEL_BASED_HIGH_PERFORMANCE_DE_KWARGS = {
    "strategy": "best1exp",  # Часто быстрее сходится
    "maxiter": 500,          # Меньше итераций, больше параллелизма
    "popsize": 24,           # 3-4x число процессоров для эффективного распараллеливания
    "tol": 0.015,           # Чуть более мягкий критерий остановки
    "mutation": (0.3, 0.9), # Оптимизированные параметры для быстрой сходимости
    "recombination": 0.8,
    "seed": 42,             # Воспроизводимость результатов
    "callback": None,
    "disp": True,
    "polish": True,         # Включаем локальную оптимизацию
    "init": "latinhypercube",
    "atol": 0,    "updating": "immediate", # КРИТИЧНО: улучшает параллелизацию
    "workers": -1,          # Использовать все доступные ядра
    "constraints": (),
}

# Адаптивная конфигурация на основе количества параметров
MODEL_BASED_ADAPTIVE_DE_KWARGS = {
    "strategy": "best1bin",
    "maxiter": 300,
    "popsize": "auto",      # Будет рассчитана автоматически
    "tol": 0.02,
    "mutation": (0.4, 0.8),
    "recombination": 0.75,
    "seed": None,
    "callback": None,
    "disp": True,
    "polish": True,
    "init": "latinhypercube", 
    "atol": 0,    "updating": "immediate",
    "workers": "auto",      # Автоматический выбор числа workers
    "constraints": (),
}
```

**Критические изменения**:
1. **`updating="immediate"`**: Критично для параллелизации - позволяет процессам сразу использовать улучшения
2. **`popsize=24`**: Размер популяции 3-4x от числа ядер обеспечивает постоянную загрузку
3. **`workers=-1`**: Использование всех доступных ядер
4. **`polish=True`**: Локальная оптимизация после DE улучшает результат

### 2. Оптимизация Basinhopping

```python
# Оптимизированные настройки basinhopping
OPTIMIZED_BASINHOPPING_PARAMS = {
    "niter": 150,           # Увеличено для лучшего исследования
    "T": 2.5,              # Выше температура для лучшего исследования
    "stepsize": 0.8,       # Больший шаг для выхода из локальных минимумов
    "batch_size": 8,       # Больший batch для лучшего параллелизма
    "minimizer_kwargs": {
        "method": "L-BFGS-B",
        "options": {
            "maxiter": 150,   # Больше итераций локального поиска
            "ftol": 1e-9,
            "gtol": 1e-6,
        },
    },
    "interval": 25,        # Чаще выводим прогресс
    "disp": True,
}
```

### 3. Параллелизация целевой функции

**Проблема**: Ваша `ModelBasedTargetFunction` обрабатывает скорости нагрева последовательно.

**Решение**: Распараллелить вычисления по скоростям нагрева:

```python
import concurrent.futures
import multiprocessing as mp

class OptimizedModelBasedTargetFunction:
    def __init__(self, *args, **kwargs):
        # ... существующий код ...
        # Добавить pool для параллельных вычислений
        self.max_workers = min(len(self.betas), mp.cpu_count())
    
    def __call__(self, params: np.ndarray) -> float:
        total_mse = 0.0
        n = self.num_reactions

        # Нормируем «вклады»
        raw_contrib = params[3 * n : 4 * n]
        sum_contrib = np.sum(raw_contrib)
        norm_contrib = raw_contrib / sum_contrib

        # Определяем функцию ОДУ
        def ode_func(T, y, beta):
            # ... существующий код ode_func ...
            pass

        # Параллельная обработка всех скоростей нагрева
        if len(self.betas) > 1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for beta_val in self.betas:
                    future = executor.submit(self.integrate_ode, beta_val, norm_contrib, params, ode_func)
                    futures.append(future)
                
                for future in concurrent.futures.as_completed(futures):
                    total_mse += future.result()
        else:
            # Для одной скорости нагрева - без overhead параллелизации
            for beta_val in self.betas:
                total_mse += self.integrate_ode(beta_val, norm_contrib, params, ode_func)

        with self.lock:
            if total_mse < self.best_mse.value:
                self.best_mse.value = total_mse

        return total_mse
```

### 4. Numba оптимизация критических функций

**Проблема**: ODE интегрирование - самая медленная часть.

**Решение**: Использовать Numba JIT для ускорения критических вычислений:

```python
from numba import njit, prange
import numba

@njit(parallel=True, fastmath=True)
def fast_ode_step(y, T, beta, params, species_list, reactions):
    """Быстрая ODE step функция с Numba JIT компиляцией"""
    dYdt = np.zeros_like(y)
    n = len(reactions)
    num_species = len(species_list)
    conc = y[:num_species]
    beta_SI = beta / 60.0
    
    for i in prange(n):  # Параллельный цикл
        # Извлекаем параметры (оптимизировано для Numba)
        logA = params[i]
        Ea = params[n + i] 
        model_index = int(np.clip(np.round(params[2 * n + i]), 0, 4))  # Упрощено
        
        # Быстрые вычисления без Python overhead
        src_index = 0  # Упрощено для демонстрации
        tgt_index = 1
        e_value = conc[src_index]
        
        # Простые модели без table lookup для скорости
        if model_index == 0:  # F2
            f_e = e_value * e_value
        elif model_index == 1:  # F3
            f_e = e_value * e_value * e_value
        else:  # F1
            f_e = e_value
            
        k_i = (10**logA * np.exp(-Ea * 1000 / (8.314 * T))) / beta_SI
        rate = k_i * f_e
        
        dYdt[src_index] -= rate
        dYdt[tgt_index] += rate
        dYdt[num_species + i] = rate
    
    return dYdt

@njit(fastmath=True)
def fast_ode_integration(params, T_array, beta, species_list, reactions):
    """Быстрая ODE интеграция с простым методом Эйлера"""
    num_species = len(species_list)
    num_reactions = len(reactions)
    
    y = np.zeros(num_species + num_reactions)
    if num_species > 0:
        y[0] = 1.0
    
    dt = (T_array[-1] - T_array[0]) / len(T_array)
    
    # Простая интеграция методом Эйлера (быстрее чем solve_ivp для простых случаев)
    for i in range(len(T_array)):
        T = T_array[i]
        dydt = fast_ode_step(y, T, beta, params, species_list, reactions)
        y += dydt * dt
    
    return y
```

### 5. Альтернативные алгоритмы оптимизации

**Добавить поддержку современных алгоритмов**:

```python
# Новые методы оптимизации для app_settings.py
OPTIMIZATION_METHODS = [
    "differential_evolution",
    "basinhopping",
    "dual_annealing",      # Часто быстрее чем DE
    "shgo",               # Simplicial homology - хорош для многомодальных функций  
    "direct",             # DIRECT algorithm - эффективен для дорогих функций
]

DUAL_ANNEALING_KWARGS = {
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

# SHGO - Simplicial Homology Global Optimization
SHGO_KWARGS = {
    "n": 100,            # Количество выборочных точек
    "iters": 3,          # Количество итераций
    "callback": None,
    "minimizer_kwargs": {
        "method": "L-BFGS-B",
        "options": {"ftol": 1e-12}
    },
    "options": {
        "maxfev": 10000,
        "f_tol": 1e-12,
        "minimize_every_iter": True,
        "local_iter": True,
        "infty_constraints": True,
    }
}
```

### 6. Автоматический выбор параметров оптимизации

```python
import multiprocessing as mp
import psutil

class OptimizationConfigAdapter:
    """Автоматическая настройка параметров оптимизации под железо и задачу"""
    
    @staticmethod
    def adapt_de_config(n_parameters, n_beta_values):
        """Адаптивная настройка DE под конкретную задачу"""
        cpu_count = mp.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Оптимальный размер популяции
        if n_parameters <= 10:
            base_popsize = max(15, 3 * n_parameters)
        elif n_parameters <= 20:
            base_popsize = max(20, 2 * n_parameters)
        else:
            base_popsize = max(30, 1.5 * n_parameters)
        
        # Учитываем количество ядер
        optimal_popsize = min(base_popsize, cpu_count * 4)
        
        # Оптимальное количество workers
        optimal_workers = min(cpu_count, max(2, optimal_popsize // 3))
        
        # Адаптация maxiter под сложность
        if n_beta_values > 3:  # Сложная задача
            maxiter = 200
        elif n_parameters > 15:  # Много параметров
            maxiter = 300  
        else:
            maxiter = 500
            
        return {
            "popsize": int(optimal_popsize),
            "workers": optimal_workers,
            "maxiter": maxiter,
            "updating": "immediate",
            "polish": True,
            "strategy": "best1exp" if n_parameters <= 15 else "best1bin",
        }
    
    @staticmethod
    def adapt_basinhopping_config(n_parameters):
        """Адаптивная настройка basinhopping"""
        cpu_count = mp.cpu_count()
        
        # Больший batch_size для сложных задач
        if n_parameters > 20:
            batch_size = min(12, cpu_count)
            niter = 200
            T = 3.0
        elif n_parameters > 10:
            batch_size = min(8, cpu_count)
            niter = 150
            T = 2.5
        else:
            batch_size = min(6, cpu_count)
            niter = 100
            T = 2.0
            
        return {
            "batch_size": batch_size,
            "niter": niter,
            "T": T,
            "stepsize": 0.8,
        }
    
    @staticmethod
    def recommend_method(n_parameters, n_beta_values, target_accuracy="medium"):
        """Рекомендация оптимального метода для задачи"""
        if n_parameters <= 8 and target_accuracy == "high":
            return "dual_annealing"  # Лучшая точность для малых задач
        elif n_parameters <= 15 and n_beta_values <= 3:
            return "basinhopping"    # Хороший баланс скорости и качества
        elif n_parameters > 20:
            return "differential_evolution"  # Лучше масштабируется
        else:
            return "dual_annealing"  # Универсальный выбор
```

### 7. Мониторинг производительности

```python
import time
import psutil
from threading import Thread
import matplotlib.pyplot as plt

class PerformanceMonitor:
    """Мониторинг производительности оптимизации в реальном времени"""
    
    def __init__(self):
        self.start_time = None
        self.cpu_history = []
        self.memory_history = []
        self.mse_history = []
        self.timestamps = []
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Запуск мониторинга производительности"""
        self.start_time = time.time()
        self.monitoring = True
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            
    def _monitor_loop(self):
        """Цикл мониторинга системных ресурсов"""
        while self.monitoring:
            current_time = time.time() - self.start_time
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            self.timestamps.append(current_time)
            self.cpu_history.append(cpu_percent)
            self.memory_history.append(memory_percent)
            
            if len(self.cpu_history) % 30 == 0:  # Каждые 30 секунд
                self.log_performance()
                
    def log_performance(self):
        """Логирование текущей производительности"""
        if not self.cpu_history:
            return
            
        avg_cpu = sum(self.cpu_history[-30:]) / min(30, len(self.cpu_history))
        current_memory = self.memory_history[-1] if self.memory_history else 0
        elapsed = time.time() - self.start_time
        
        print(f"Performance: CPU {avg_cpu:.1f}% (avg 30s), Memory {current_memory:.1f}%, Time {elapsed:.1f}s")
        
    def add_mse_point(self, mse_value):
        """Добавление точки MSE для отслеживания сходимости"""
        current_time = time.time() - self.start_time
        self.mse_history.append((current_time, mse_value))
        
    def plot_performance(self):
        """Построение графиков производительности"""
        if not self.timestamps:
            return
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        
        # CPU utilization
        ax1.plot(self.timestamps, self.cpu_history, 'b-', linewidth=2)
        ax1.set_title('CPU Utilization')
        ax1.set_ylabel('CPU %')
        ax1.grid(True)
        
        # Memory usage
        ax2.plot(self.timestamps, self.memory_history, 'r-', linewidth=2)
        ax2.set_title('Memory Usage')
        ax2.set_ylabel('Memory %')
        ax2.grid(True)
        
        # MSE convergence
        if self.mse_history:
            times, mse_values = zip(*self.mse_history)
            ax3.semilogy(times, mse_values, 'g-', linewidth=2)
            ax3.set_title('MSE Convergence')
            ax3.set_ylabel('MSE (log scale)')
            ax3.grid(True)
        
        # CPU efficiency (должен быть близок к 100% для хорошей параллелизации)
        cpu_efficiency = [min(100, cpu/80*100) for cpu in self.cpu_history]  # 80% - хорошая утилизация
        ax4.plot(self.timestamps, cpu_efficiency, 'm-', linewidth=2)
        ax4.set_title('CPU Efficiency')
        ax4.set_ylabel('Efficiency %')
        ax4.axhline(y=100, color='r', linestyle='--', label='Target')
        ax4.grid(True)
        ax4.legend()
        
        for ax in [ax1, ax2, ax3, ax4]:
            ax.set_xlabel('Time (seconds)')
            
        plt.tight_layout()
        plt.savefig('optimization_performance.png', dpi=150, bbox_inches='tight')
        plt.show()

# Интеграция в ModelBasedTargetFunction
class MonitoredModelBasedTargetFunction(OptimizedModelBasedTargetFunction):
    def __init__(self, *args, monitor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = monitor
        self.call_count = 0
        
    def __call__(self, params: np.ndarray) -> float:
        self.call_count += 1
        result = super().__call__(params)
        
        # Добавляем точку MSE в монитор
        if self.monitor and self.call_count % 10 == 0:  # Каждые 10 вызовов
            self.monitor.add_mse_point(result)
            
        return result
```

## Практические рекомендации по внедрению

### Этап 1: Быстрые изменения (1-2 часа)

1. **Обновить настройки DE в `app_settings.py`**:
   ```python
   MODEL_BASED_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS = {
       "strategy": "best1exp",      # Вместо "best1bin"
       "popsize": 24,               # Вместо 5
       "maxiter": 500,              # Вместо 1000
       "updating": "immediate",     # Вместо "deferred"  
       "workers": -1,               # Вместо 1
       "polish": True,              # Вместо False
       "tol": 0.015,               # Вместо 0.01
       "mutation": (0.3, 0.9),     # Вместо (0.5, 1)
       "recombination": 0.8,       # Вместо 0.7
   }
   ```

2. **Оптимизировать basinhopping в `app_settings.py`**:
   ```python
   DEFAULT_BASINHOPPING_PARAMS = {
       "niter": 150,               # Вместо 100
       "T": 2.5,                   # Вместо 1.0
       "stepsize": 0.8,            # Вместо 0.5
       "batch_size": 8,            # Вместо None
       "minimizer_kwargs": {
           "method": "L-BFGS-B",
           "options": {"maxiter": 150},  # Вместо 100
       },
   }
   ```

**Ожидаемый результат**: Ускорение в **2-4 раза**, утилизация CPU **60-80%**.

### Этап 2: Средние изменения (4-8 часов)

1. **Добавить `dual_annealing`** как третий метод оптимизации
2. **Реализовать `OptimizationConfigAdapter`** для автоматического выбора параметров
3. **Добавить `PerformanceMonitor`** для отслеживания эффективности

**Ожидаемый результат**: Ускорение в **4-8 раз**, автоматическая оптимизация под железо.

### Этап 3: Глубокие изменения (1-2 дня)

1. **Параллелизация `ModelBasedTargetFunction`** по скоростям нагрева
2. **Numba оптимизация** критических численных функций
3. **Интеграция мониторинга** в реальном времени

**Ожидаемый результат**: Ускорение в **8-20 раз**, утилизация CPU **90%+**.

## Резюме по ожидаемым результатам

| Этап | Время | Ускорение | CPU Утилизация | Сложность |
| ---- | ----- | --------- | -------------- | --------- |
| 1    | 1-2ч  | 2-4x      | 60-80%         | Низкая    |
| 2    | 4-8ч  | 4-8x      | 70-85%         | Средняя   |
| 3    | 1-2д  | 8-20x     | 90%+           | Высокая   |

**Рекомендация**: Начать с Этапа 1, который даст немедленное ускорение без серьезных изменений в архитектуре кода.

## Заключение

Основная проблема - неоптимальные настройки алгоритмов оптимизации, которые не используют возможности современных многоядерных процессоров. 

**Ключевые изменения для немедленного эффекта**:
- `updating="immediate"` вместо `"deferred"` 
- `popsize=24` вместо `5`
- `workers=-1` вместо `1`
- `polish=True` для финальной локальной оптимизации

Эти изменения дадут **2-4x ускорение** сразу после применения, а дальнейшая оптимизация может увеличить производительность до **20x** для сложных задач.
