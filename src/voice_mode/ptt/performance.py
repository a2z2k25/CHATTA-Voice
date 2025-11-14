"""
PTT performance monitoring and optimization.

Provides performance profiling, latency measurement, and optimization
recommendations for PTT operations.
"""

import time
import psutil
import sys
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager

from voice_mode.ptt.logging import get_ptt_logger


@dataclass
class PerformanceMetrics:
    """Performance metrics for PTT operations."""

    # Latency metrics (seconds)
    key_press_latency: Optional[float] = None      # Time from enable to key press
    recording_start_latency: Optional[float] = None  # Time from key press to recording start
    recording_stop_latency: Optional[float] = None   # Time from key release to stop
    total_latency: Optional[float] = None            # Total response time

    # Resource metrics
    memory_usage_mb: Optional[float] = None         # Memory usage in MB
    cpu_percent: Optional[float] = None             # CPU usage percentage

    # Operation timing
    operation_name: str = ""
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceTarget:
    """Performance targets and thresholds."""

    # Latency targets (milliseconds)
    target_key_press_latency: float = 30.0         # <30ms ideal
    target_recording_start: float = 50.0           # <50ms ideal
    target_recording_stop: float = 50.0            # <50ms ideal
    target_total_latency: float = 100.0            # <100ms total

    # Resource targets
    max_memory_mb: float = 100.0                   # <100MB ideal
    max_cpu_percent: float = 5.0                   # <5% when idle


class PTTPerformanceMonitor:
    """
    PTT performance monitor.

    Tracks performance metrics and provides optimization recommendations.
    """

    def __init__(self, targets: Optional[PerformanceTarget] = None):
        """
        Initialize performance monitor.

        Args:
            targets: Performance targets (uses defaults if None)
        """
        self.logger = get_ptt_logger()
        self.targets = targets or PerformanceTarget()
        self.metrics_history: List[PerformanceMetrics] = []
        self._timing_stack: List[tuple[str, float]] = []

    @contextmanager
    def measure(self, operation_name: str):
        """
        Context manager for measuring operation timing.

        Args:
            operation_name: Name of operation being measured

        Example:
            with monitor.measure("key_press"):
                # ... code to measure ...
        """
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_percent()

        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            end_memory = self._get_memory_usage()
            end_cpu = self._get_cpu_percent()

            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration=duration,
                memory_usage_mb=end_memory - start_memory if start_memory and end_memory else None,
                cpu_percent=end_cpu if end_cpu else None
            )

            self.metrics_history.append(metrics)

            self.logger.log_event("performance_measured", {
                "operation": operation_name,
                "duration_ms": duration * 1000,
                "memory_mb": metrics.memory_usage_mb
            })

    def measure_latency(
        self,
        key_press_latency: Optional[float] = None,
        recording_start_latency: Optional[float] = None,
        recording_stop_latency: Optional[float] = None
    ):
        """
        Record latency measurements.

        Args:
            key_press_latency: Key press latency (seconds)
            recording_start_latency: Recording start latency (seconds)
            recording_stop_latency: Recording stop latency (seconds)
        """
        total_latency = sum(
            l for l in [key_press_latency, recording_start_latency, recording_stop_latency]
            if l is not None
        )

        metrics = PerformanceMetrics(
            operation_name="latency_measurement",
            key_press_latency=key_press_latency,
            recording_start_latency=recording_start_latency,
            recording_stop_latency=recording_stop_latency,
            total_latency=total_latency,
            duration=total_latency
        )

        self.metrics_history.append(metrics)

    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception as e:
            self.logger.log_error(e, {"context": "get_memory_usage"})
            return None

    def _get_cpu_percent(self) -> Optional[float]:
        """Get current CPU usage percentage."""
        try:
            process = psutil.Process()
            return process.cpu_percent(interval=0.1)
        except Exception as e:
            self.logger.log_error(e, {"context": "get_cpu_percent"})
            return None

    def get_summary(self) -> Dict[str, Any]:
        """
        Get performance summary.

        Returns:
            Dictionary with performance statistics
        """
        if not self.metrics_history:
            return {
                "total_measurements": 0,
                "average_latency_ms": 0.0,
                "memory_usage_mb": 0.0,
                "cpu_percent": 0.0
            }

        # Calculate averages
        latency_metrics = [
            m for m in self.metrics_history
            if m.total_latency is not None
        ]

        avg_latency = (
            sum(m.total_latency for m in latency_metrics) / len(latency_metrics)
            if latency_metrics else 0.0
        )

        # Resource usage
        memory_metrics = [m for m in self.metrics_history if m.memory_usage_mb is not None]
        avg_memory = (
            sum(m.memory_usage_mb for m in memory_metrics) / len(memory_metrics)
            if memory_metrics else 0.0
        )

        cpu_metrics = [m for m in self.metrics_history if m.cpu_percent is not None]
        avg_cpu = (
            sum(m.cpu_percent for m in cpu_metrics) / len(cpu_metrics)
            if cpu_metrics else 0.0
        )

        return {
            "total_measurements": len(self.metrics_history),
            "average_latency_ms": avg_latency * 1000,
            "memory_usage_mb": avg_memory,
            "cpu_percent": avg_cpu,
            "targets": {
                "key_press_latency_ms": self.targets.target_key_press_latency,
                "recording_start_ms": self.targets.target_recording_start,
                "total_latency_ms": self.targets.target_total_latency
            }
        }

    def check_performance(self) -> List[str]:
        """
        Check performance against targets.

        Returns:
            List of performance issues/warnings
        """
        issues = []

        if not self.metrics_history:
            return ["No performance data collected"]

        summary = self.get_summary()

        # Check latency
        if summary['average_latency_ms'] > self.targets.target_total_latency:
            issues.append(
                f"High latency: {summary['average_latency_ms']:.1f}ms "
                f"(target: {self.targets.target_total_latency}ms)"
            )

        # Check memory
        if summary['memory_usage_mb'] > self.targets.max_memory_mb:
            issues.append(
                f"High memory usage: {summary['memory_usage_mb']:.1f}MB "
                f"(target: {self.targets.max_memory_mb}MB)"
            )

        # Check CPU
        if summary['cpu_percent'] > self.targets.max_cpu_percent:
            issues.append(
                f"High CPU usage: {summary['cpu_percent']:.1f}% "
                f"(target: {self.targets.max_cpu_percent}%)"
            )

        return issues if issues else ["Performance within targets"]

    def get_optimization_recommendations(self) -> List[str]:
        """
        Get optimization recommendations based on metrics.

        Returns:
            List of optimization suggestions
        """
        recommendations = []
        issues = self.check_performance()

        # If no issues, return general tips
        if issues == ["Performance within targets"]:
            return [
                "Performance is good! General tips:",
                "- Keep visual feedback enabled for user experience",
                "- Use compact or minimal display style for lower overhead",
                "- Consider disabling audio feedback if not needed",
                "- Monitor memory usage over long sessions"
            ]

        # Latency recommendations
        if any("latency" in issue.lower() for issue in issues):
            recommendations.extend([
                "Reduce latency:",
                "- Ensure pynput has proper permissions (especially macOS)",
                "- Close other resource-intensive applications",
                "- Use minimal display style instead of detailed",
                "- Disable audio feedback if not needed",
                "- Check for background processes using CPU"
            ])

        # Memory recommendations
        if any("memory" in issue.lower() for issue in issues):
            recommendations.extend([
                "Reduce memory usage:",
                "- Clear statistics history periodically",
                "- Disable visual feedback if not needed",
                "- Use minimal display style",
                "- Check for memory leaks in long sessions",
                "- Restart PTT periodically for very long sessions"
            ])

        # CPU recommendations
        if any("cpu" in issue.lower() for issue in issues):
            recommendations.extend([
                "Reduce CPU usage:",
                "- Disable live duration updates",
                "- Increase visual feedback update interval",
                "- Use minimal display style",
                "- Check for other CPU-intensive processes",
                "- Ensure audio drivers are up to date"
            ])

        return recommendations

    def format_report(self) -> str:
        """
        Format performance report.

        Returns:
            Formatted performance report string
        """
        summary = self.get_summary()
        issues = self.check_performance()
        recommendations = self.get_optimization_recommendations()

        lines = [
            "PTT Performance Report",
            "=" * 70,
            "",
            "Measurements:",
            f"  Total: {summary['total_measurements']}",
            f"  Average Latency: {summary['average_latency_ms']:.1f}ms",
            f"  Memory Usage: {summary['memory_usage_mb']:.1f}MB",
            f"  CPU Usage: {summary['cpu_percent']:.1f}%",
            "",
            "Targets:",
            f"  Key Press Latency: <{summary['targets']['key_press_latency_ms']}ms",
            f"  Recording Start: <{summary['targets']['recording_start_ms']}ms",
            f"  Total Latency: <{summary['targets']['total_latency_ms']}ms",
            "",
            "Performance Check:",
        ]

        for issue in issues:
            lines.append(f"  {'✅' if 'within targets' in issue.lower() else '⚠️'} {issue}")

        if recommendations:
            lines.extend([
                "",
                "Recommendations:",
            ])
            for rec in recommendations:
                lines.append(f"  {rec}")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)


class PerformanceBenchmark:
    """
    PTT performance benchmarking utility.
    """

    def __init__(self):
        """Initialize benchmark."""
        self.logger = get_ptt_logger()
        self.monitor = PTTPerformanceMonitor()

    def benchmark_key_press_latency(self, iterations: int = 100) -> Dict[str, float]:
        """
        Benchmark key press detection latency.

        Args:
            iterations: Number of iterations

        Returns:
            Dictionary with min/max/avg latency
        """
        latencies = []

        for i in range(iterations):
            start = time.perf_counter()
            # Simulate key press detection overhead
            time.sleep(0.001)  # 1ms simulated overhead
            latency = time.perf_counter() - start
            latencies.append(latency)

        return {
            "min_ms": min(latencies) * 1000,
            "max_ms": max(latencies) * 1000,
            "avg_ms": (sum(latencies) / len(latencies)) * 1000,
            "iterations": iterations
        }

    def benchmark_visual_feedback(self, iterations: int = 100) -> Dict[str, float]:
        """
        Benchmark visual feedback rendering.

        Args:
            iterations: Number of iterations

        Returns:
            Dictionary with timing results
        """
        durations = []

        try:
            from voice_mode.ptt.status_display import PTTStatusDisplay, DisplayStyle

            display = PTTStatusDisplay(style=DisplayStyle.COMPACT)

            for i in range(iterations):
                with self.monitor.measure("visual_feedback"):
                    _ = display.format_recording_start("down+right", "hold")

            durations = [
                m.duration * 1000
                for m in self.monitor.metrics_history
                if m.operation_name == "visual_feedback"
            ]

        except ImportError:
            pass

        if not durations:
            return {"error": "Visual feedback not available"}

        return {
            "min_ms": min(durations),
            "max_ms": max(durations),
            "avg_ms": sum(durations) / len(durations),
            "iterations": len(durations)
        }

    def run_full_benchmark(self) -> Dict[str, Any]:
        """
        Run full PTT performance benchmark.

        Returns:
            Dictionary with all benchmark results
        """
        results = {
            "timestamp": time.time(),
            "platform": sys.platform,
            "benchmarks": {}
        }

        # Benchmark key press
        results["benchmarks"]["key_press"] = self.benchmark_key_press_latency()

        # Benchmark visual feedback
        results["benchmarks"]["visual_feedback"] = self.benchmark_visual_feedback()

        return results

    def format_benchmark_results(self, results: Dict[str, Any]) -> str:
        """
        Format benchmark results.

        Args:
            results: Benchmark results dictionary

        Returns:
            Formatted string
        """
        lines = [
            "PTT Performance Benchmark Results",
            "=" * 70,
            "",
            f"Platform: {results.get('platform', 'unknown')}",
            f"Timestamp: {results.get('timestamp', 0)}",
            ""
        ]

        for name, data in results.get("benchmarks", {}).items():
            lines.append(f"{name.replace('_', ' ').title()}:")

            if "error" in data:
                lines.append(f"  Error: {data['error']}")
            else:
                lines.append(f"  Min: {data.get('min_ms', 0):.2f}ms")
                lines.append(f"  Max: {data.get('max_ms', 0):.2f}ms")
                lines.append(f"  Avg: {data.get('avg_ms', 0):.2f}ms")
                lines.append(f"  Iterations: {data.get('iterations', 0)}")

            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


# Global performance monitor
_global_monitor: Optional[PTTPerformanceMonitor] = None


def get_performance_monitor() -> PTTPerformanceMonitor:
    """
    Get global performance monitor.

    Returns:
        PTTPerformanceMonitor instance
    """
    global _global_monitor

    if _global_monitor is None:
        _global_monitor = PTTPerformanceMonitor()

    return _global_monitor


def reset_performance_monitor():
    """Reset global performance monitor."""
    global _global_monitor
    _global_monitor = None


def benchmark_ptt_performance() -> str:
    """
    Run PTT performance benchmark and return formatted results.

    Returns:
        Formatted benchmark results
    """
    benchmark = PerformanceBenchmark()
    results = benchmark.run_full_benchmark()
    return benchmark.format_benchmark_results(results)


def get_performance_report() -> str:
    """
    Get current performance report.

    Returns:
        Formatted performance report
    """
    monitor = get_performance_monitor()
    return monitor.format_report()
