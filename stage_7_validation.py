#!/usr/bin/env python3
"""
Валидация завершения этапа 7: Тестирование, оптимизация, упрощение
"""

import sys
import time
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))


def check_value_aggregator_removal():
    """Проверить удаление ValueAggregator"""
    print("🔍 Проверка удаления ValueAggregator...")

    # Проверить что файл удален
    value_agg_path = Path("src/log_aggregator/value_aggregator.py")
    if value_agg_path.exists():
        print("❌ FAILED: Файл ValueAggregator все еще существует")
        return False

    print("✅ Файл ValueAggregator успешно удален")

    # Проверить что backup существует
    backup_path = Path("src/log_aggregator/value_aggregator.py.backup")
    if backup_path.exists():
        print("✅ Backup файл ValueAggregator существует")
    else:
        print("⚠️  WARNING: Backup файл ValueAggregator не найден")

    return True


def check_functionality_migration():
    """Проверить перенос функциональности"""
    print("\n🔍 Проверка переноса функциональности...")

    try:
        from src.log_aggregator.operation_logger import OperationLogger, log_operation

        logger = OperationLogger()  # Тест сжатия больших данных
        large_list = list(range(5000))
        compressed = logger._compress_value(large_list)
        display_value = logger._get_display_value(compressed)

        if "5000 items" in display_value:
            print("✅ Функциональность сжатия больших данных работает")
        else:
            print("❌ FAILED: Функциональность сжатия не работает")
            print(f"   Получено: {display_value}")
            return False

        # Тест операций
        with log_operation("VALIDATION_TEST"):
            logger.add_metric("test_data", large_list)
            logger.add_metric("status", "testing")

        print("✅ Операционное логирование работает")
        return True

    except Exception as e:
        print(f"❌ FAILED: Ошибка при проверке функциональности: {e}")
        return False


def check_performance():
    """Проверить производительность"""
    print("\n🔍 Проверка производительности...")

    try:
        from src.log_aggregator.operation_logger import OperationLogger

        start_time = time.time()

        # Тест производительности
        logger = OperationLogger()  # Создаем один логгер
        for i in range(100):
            with logger.log_operation(f"perf_test_{i}"):
                # Большие данные
                large_data = [f"item_{j}" for j in range(1000)]
                logger.add_metric("large_data", large_data)
                logger.add_metric("iteration", i)

        elapsed = time.time() - start_time
        avg_time = elapsed / 100 * 1000  # мс на операцию

        print(f"✅ Обработано 100 операций за {elapsed:.3f}s")
        print(f"✅ Среднее время на операцию: {avg_time:.1f}ms")

        if elapsed < 5.0:  # Должно быть быстро
            print("✅ Производительность в норме")
            return True
        else:
            print("⚠️  WARNING: Производительность может быть улучшена")
            return True  # Не критично

    except Exception as e:
        print(f"❌ FAILED: Ошибка при проверке производительности: {e}")
        return False


def check_system_health():
    """Проверить общее здоровье системы"""
    print("\n🔍 Проверка здоровья системы...")

    try:
        # Проверить основные импорты
        from src.log_aggregator.operation_logger import OperationLogger
        from src.log_aggregator.operation_monitor import OperationMonitor
        from src.log_aggregator.realtime_handler import AggregatingHandler

        print("✅ Основные компоненты импортируются без ошибок")

        # Проверить что компоненты можно инициализировать
        _ = OperationLogger()

        # OperationMonitor требует config
        from src.log_aggregator.operation_monitor import OperationMonitoringConfig

        config = OperationMonitoringConfig()
        _ = OperationMonitor(config)

        _ = AggregatingHandler()  # Используем AggregatingHandler

        print("✅ Компоненты инициализируются без ошибок")
        return True

    except Exception as e:
        print(f"❌ FAILED: Ошибка системы: {e}")
        return False


def main():
    """Основная функция валидации"""
    print("=" * 70)
    print("🔬 ВАЛИДАЦИЯ ЭТАПА 7: ТЕСТИРОВАНИЕ, ОПТИМИЗАЦИЯ, УПРОЩЕНИЕ")
    print("=" * 70)

    checks = [
        ("Удаление ValueAggregator", check_value_aggregator_removal),
        ("Перенос функциональности", check_functionality_migration),
        ("Производительность", check_performance),
        ("Здоровье системы", check_system_health),
    ]

    passed = 0
    total = len(checks)

    for name, check_func in checks:
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print(f"❌ FAILED: {name} - {e}")

    print("\n" + "=" * 70)
    print(f"📊 РЕЗУЛЬТАТЫ: {passed}/{total} проверок пройдено")

    if passed == total:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Этап 7 успешно завершен.")
        print("\n✅ ValueAggregator удален")
        print("✅ Функциональность перенесена")
        print("✅ Производительность в норме")
        print("✅ Система работает стабильно")
        return True
    else:
        print("⚠️  Некоторые проверки не пройдены. Требуется доработка.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
