"""
Performance monitoring component for log aggregation system.

This module provides performance tracking and optimization for the aggregation pipeline,
including memory usage, processing time, and throughput metrics.
"""

import gc
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil


@dataclass
class PerformanceMetrics:
    """Performance metrics for aggregation system."""

    timestamp: datetime
    """When metrics were collected"""

    # Memory metrics
    memory_usage_mb: float
    """Current memory usage in MB"""

    memory_peak_mb: float
    """Peak memory usage in MB"""

    memory_available_mb: float
    """Available memory in MB"""

    # Processing metrics
    records_processed: int
    """Total records processed"""

    records_aggregated: int
    """Total records aggregated"""

    processing_time_ms: float
    """Total processing time in milliseconds"""

    avg_processing_time_ms: float
    """Average processing time per record in milliseconds"""

    # Throughput metrics
    records_per_second: float
    """Records processed per second"""

    aggregation_ratio: float
    """Ratio of aggregated to total records"""

    # Component performance
    buffer_size: int
    """Current buffer size"""

    pattern_detection_time_ms: float
    """Time spent in pattern detection"""

    aggregation_time_ms: float
    """Time spent in aggregation"""

    formatting_time_ms: float
    """Time spent in formatting"""

    # System metrics
    cpu_usage_percent: float
    """CPU usage percentage"""

    thread_count: int
    """Number of active threads"""

    gc_collections: int
    """Number of garbage collections"""


@dataclass
class PerformanceMonitoringConfig:
    """Configuration for performance monitoring."""

    enabled: bool = True
    """Whether performance monitoring is enabled"""

    collection_interval: float = 5.0
    """Interval in seconds between metric collection"""

    history_size: int = 1000
    """Number of metrics to keep in history"""

    memory_threshold_mb: float = 500.0
    """Memory threshold in MB for warnings"""

    processing_time_threshold_ms: float = 100.0
    """Processing time threshold in ms for warnings"""

    enable_detailed_profiling: bool = False
    """Whether to enable detailed profiling (impacts performance)"""

    enable_gc_monitoring: bool = True
    """Whether to monitor garbage collection"""

    log_warnings: bool = True
    """Whether to log performance warnings"""

    log_level: str = "INFO"
    """Log level for performance monitoring"""


class PerformanceMonitor:
    """
    Monitor for tracking aggregation system performance.

    This component tracks memory usage, processing times, throughput,
    and system resource utilization to optimize aggregation performance.
    """

    def __init__(self, config: PerformanceMonitoringConfig):
        """Initialize performance monitor."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Metrics storage
        self._metrics_history: List[PerformanceMetrics] = []
        self._current_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            memory_usage_mb=0.0,
            memory_peak_mb=0.0,
            memory_available_mb=0.0,
            records_processed=0,
            records_aggregated=0,
            processing_time_ms=0.0,
            avg_processing_time_ms=0.0,
            records_per_second=0.0,
            aggregation_ratio=0.0,
            buffer_size=0,
            pattern_detection_time_ms=0.0,
            aggregation_time_ms=0.0,
            formatting_time_ms=0.0,
            cpu_usage_percent=0.0,
            thread_count=0,
            gc_collections=0,
        )

        # Performance tracking
        self._start_time = time.time()
        self._last_collection_time = time.time()
        self._total_records_processed = 0
        self._total_records_aggregated = 0
        self._total_processing_time = 0.0
        self._peak_memory_usage = 0.0  # Component timing
        self._component_timings: Dict[str, List[float]] = {
            "pattern_detection": [],
            "aggregation": [],
            "formatting": [],
            "error_expansion": [],
            "operation_aggregation": [],
            "value_aggregation": [],
        }

        # Monitoring thread
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._lock = threading.RLock()

        # System monitoring
        self._process = psutil.Process()
        self._last_gc_count = sum(gc.get_count()) if self.config.enable_gc_monitoring else 0

        if self.config.enabled:
            self._start_monitoring_thread()

    def record_processing_start(self) -> float:
        """Record start of processing operation."""
        return time.time()

    def record_processing_end(self, start_time: float, records_processed: int = 1, records_aggregated: int = 0) -> None:
        """Record end of processing operation."""
        if not self.config.enabled:
            return

        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        with self._lock:
            self._total_records_processed += records_processed
            self._total_records_aggregated += records_aggregated
            self._total_processing_time += processing_time

    def record_component_timing(self, component: str, timing_ms: float) -> None:
        """Record timing for specific component."""
        if not self.config.enabled:
            return

        with self._lock:
            if component in self._component_timings:
                self._component_timings[component].append(timing_ms)

                # Keep only recent timings
                if len(self._component_timings[component]) > 100:
                    self._component_timings[component] = self._component_timings[component][-50:]

    def record_buffer_size(self, size: int) -> None:
        """Record current buffer size."""
        if not self.config.enabled:
            return

        with self._lock:
            self._current_metrics.buffer_size = size

    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        with self._lock:
            return self._current_metrics

    def get_metrics_history(self) -> List[PerformanceMetrics]:
        """Get performance metrics history."""
        with self._lock:
            return self._metrics_history.copy()

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        with self._lock:
            current_time = time.time()
            uptime = current_time - self._start_time

            avg_processing_time = self._total_processing_time / max(1, self._total_records_processed)

            throughput = self._total_records_processed / max(1, uptime)

            aggregation_ratio = self._total_records_aggregated / max(1, self._total_records_processed)

            component_avg_timings = {}
            for component, timings in self._component_timings.items():
                if timings:
                    component_avg_timings[f"{component}_avg_ms"] = sum(timings) / len(timings)
                    component_avg_timings[f"{component}_max_ms"] = max(timings)
                else:
                    component_avg_timings[f"{component}_avg_ms"] = 0.0
                    component_avg_timings[f"{component}_max_ms"] = 0.0

            return {
                "uptime_seconds": uptime,
                "total_records_processed": self._total_records_processed,
                "total_records_aggregated": self._total_records_aggregated,
                "total_processing_time_ms": self._total_processing_time,
                "avg_processing_time_ms": avg_processing_time,
                "throughput_records_per_second": throughput,
                "aggregation_ratio": aggregation_ratio,
                "peak_memory_usage_mb": self._peak_memory_usage,
                "current_memory_usage_mb": self._current_metrics.memory_usage_mb,
                "monitoring_enabled": self.config.enabled,
                **component_avg_timings,
            }

    def _start_monitoring_thread(self) -> None:
        """Start the monitoring thread."""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True, name="PerformanceMonitor"
            )
            self._monitoring_thread.start()

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_monitoring.wait(self.config.collection_interval):
            try:
                self._collect_metrics()
                self._check_performance_warnings()
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")

    def _collect_metrics(self) -> None:
        """Collect current performance metrics."""
        current_time = time.time()

        # Collect system metrics
        memory_info = self._process.memory_info()
        memory_usage_mb = memory_info.rss / 1024 / 1024

        # Update peak memory usage
        if memory_usage_mb > self._peak_memory_usage:
            self._peak_memory_usage = memory_usage_mb

        # Get system memory info
        system_memory = psutil.virtual_memory()
        memory_available_mb = system_memory.available / 1024 / 1024

        # Get CPU usage
        cpu_usage = self._process.cpu_percent()

        # Get thread count
        thread_count = threading.active_count()

        # Get GC count
        gc_collections = 0
        if self.config.enable_gc_monitoring:
            current_gc_count = sum(gc.get_count())
            gc_collections = current_gc_count - self._last_gc_count
            self._last_gc_count = current_gc_count

        # Calculate processing metrics
        time_delta = current_time - self._last_collection_time
        records_per_second = 0.0

        if time_delta > 0:
            records_in_period = self._total_records_processed - getattr(
                self._current_metrics, "_last_total_processed", 0
            )
            records_per_second = records_in_period / time_delta

        avg_processing_time = self._total_processing_time / max(1, self._total_records_processed)

        aggregation_ratio = self._total_records_aggregated / max(
            1, self._total_records_processed
        )  # Calculate component timings
        pattern_detection_time = self._get_avg_component_timing("pattern_detection")
        aggregation_time = self._get_avg_component_timing("aggregation")
        formatting_time = self._get_avg_component_timing("formatting")

        # Create metrics object
        with self._lock:
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                memory_usage_mb=memory_usage_mb,
                memory_peak_mb=self._peak_memory_usage,
                memory_available_mb=memory_available_mb,
                records_processed=self._total_records_processed,
                records_aggregated=self._total_records_aggregated,
                processing_time_ms=self._total_processing_time,
                avg_processing_time_ms=avg_processing_time,
                records_per_second=records_per_second,
                aggregation_ratio=aggregation_ratio,
                buffer_size=self._current_metrics.buffer_size,
                pattern_detection_time_ms=pattern_detection_time,
                aggregation_time_ms=aggregation_time,
                formatting_time_ms=formatting_time,
                cpu_usage_percent=cpu_usage,
                thread_count=thread_count,
                gc_collections=gc_collections,
            )

            # Store for next calculation
            metrics._last_total_processed = self._total_records_processed

            self._current_metrics = metrics
            self._metrics_history.append(metrics)

            # Keep history within limits
            if len(self._metrics_history) > self.config.history_size:
                self._metrics_history = self._metrics_history[-self.config.history_size :]

        self._last_collection_time = current_time

    def _get_avg_component_timing(self, component: str) -> float:
        """Get average timing for component."""
        timings = self._component_timings.get(component, [])
        if timings:
            # Use recent timings for average
            recent_timings = timings[-10:]
            return sum(recent_timings) / len(recent_timings)
        return 0.0

    def _check_performance_warnings(self) -> None:
        """Check for performance issues and log warnings."""
        if not self.config.log_warnings:
            return

        metrics = self._current_metrics

        # Memory usage warning
        if metrics.memory_usage_mb > self.config.memory_threshold_mb:
            self.logger.warning(
                f"⚠️ PERFORMANCE WARNING: High memory usage: "
                f"{metrics.memory_usage_mb:.1f}MB (threshold: {self.config.memory_threshold_mb}MB)"
            )

        # Processing time warning
        if metrics.avg_processing_time_ms > self.config.processing_time_threshold_ms:
            self.logger.warning(
                f"⚠️ PERFORMANCE WARNING: Slow processing: "
                f"{metrics.avg_processing_time_ms:.2f}ms per record "
                f"(threshold: {self.config.processing_time_threshold_ms}ms)"
            )

        # Low throughput warning
        if metrics.records_per_second < 10 and self._total_records_processed > 100:
            self.logger.warning(
                f"⚠️ PERFORMANCE WARNING: Low throughput: " f"{metrics.records_per_second:.1f} records/sec"
            )

        # High buffer size warning
        if metrics.buffer_size > 500:
            self.logger.warning(f"⚠️ PERFORMANCE WARNING: Large buffer size: " f"{metrics.buffer_size} records")

        # Memory availability warning
        if metrics.memory_available_mb < 100:
            self.logger.warning(f"⚠️ PERFORMANCE WARNING: Low available memory: " f"{metrics.memory_available_mb:.1f}MB")

    def generate_performance_report(self) -> str:
        """Generate detailed performance report."""
        summary = self.get_performance_summary()
        metrics = self._current_metrics

        report_lines = [
            "📊 PERFORMANCE REPORT",
            "=" * 50,
            f"⏱️  Uptime: {summary['uptime_seconds']:.1f}s",
            f"📈 Total Records: {summary['total_records_processed']}",
            f"🔧 Aggregated: {summary['total_records_aggregated']} " f"({summary['aggregation_ratio']:.2%})",
            f"⚡ Throughput: {summary['throughput_records_per_second']:.1f} records/sec",
            f"📏 Avg Processing: {summary['avg_processing_time_ms']:.2f}ms/record",
            "",
            "💾 MEMORY USAGE",
            f"Current: {metrics.memory_usage_mb:.1f}MB",
            f"Peak: {summary['peak_memory_usage_mb']:.1f}MB",
            f"Available: {metrics.memory_available_mb:.1f}MB",
            "",
            "🔧 COMPONENT TIMINGS",
            f"Pattern Detection: {summary['pattern_detection_avg_ms']:.2f}ms avg, "
            f"{summary['pattern_detection_max_ms']:.2f}ms max",
            f"Aggregation: {summary['aggregation_avg_ms']:.2f}ms avg, " f"{summary['aggregation_max_ms']:.2f}ms max",
            f"Formatting: {summary['formatting_avg_ms']:.2f}ms avg, " f"{summary['formatting_max_ms']:.2f}ms max",
            "",
            "🖥️ SYSTEM METRICS",
            f"CPU Usage: {metrics.cpu_usage_percent:.1f}%",
            f"Thread Count: {metrics.thread_count}",
            f"Buffer Size: {metrics.buffer_size}",
            f"GC Collections: {metrics.gc_collections}",
            "=" * 50,
        ]

        return "\n".join(report_lines)

    def optimize_performance(self) -> Dict[str, str]:
        """Analyze performance and suggest optimizations."""
        summary = self.get_performance_summary()
        metrics = self._current_metrics
        suggestions = {}

        # Memory optimization suggestions
        if metrics.memory_usage_mb > self.config.memory_threshold_mb:
            suggestions["memory"] = (
                f"High memory usage ({metrics.memory_usage_mb:.1f}MB). "
                "Consider reducing buffer size or history limits."
            )  # Processing time optimization
        if summary["avg_processing_time_ms"] > self.config.processing_time_threshold_ms:
            suggestions["processing_time"] = (
                f"Slow processing ({summary['avg_processing_time_ms']:.2f}ms/record). "
                "Consider disabling detailed profiling or reducing pattern complexity."
            )

        # Throughput optimization
        if summary["throughput_records_per_second"] < 50:
            suggestions["throughput"] = (
                f"Low throughput ({summary['throughput_records_per_second']:.1f} rec/sec). "
                "Consider increasing buffer size or reducing aggregation frequency."
            )

        # Component-specific suggestions
        if summary["pattern_detection_avg_ms"] > 10:
            suggestions["pattern_detection"] = (
                "Pattern detection is slow. Consider reducing similarity threshold "
                "or disabling complex pattern types."
            )

        if summary["formatting_avg_ms"] > 5:
            suggestions["formatting"] = (
                "Formatting is slow. Consider disabling tabular formatting " "or reducing table complexity."
            )

        # Buffer optimization
        if metrics.buffer_size > 200:
            suggestions["buffer"] = (
                f"Large buffer size ({metrics.buffer_size}). " "Consider reducing flush interval or buffer limits."
            )

        return suggestions

    def shutdown(self) -> None:
        """Shutdown performance monitor."""
        self._stop_monitoring.set()
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=1.0)

        # Log final performance report
        if self.config.enabled:
            final_report = self.generate_performance_report()
            self.logger.info(f"📊 FINAL PERFORMANCE REPORT:\n{final_report}")
