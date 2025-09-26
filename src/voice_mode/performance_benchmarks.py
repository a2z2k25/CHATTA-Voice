#!/usr/bin/env python3
"""Performance benchmarking system for VoiceMode."""

import asyncio
import time
import psutil
import threading
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union, Tuple, Set
from enum import Enum
import logging
import json
from pathlib import Path
import tracemalloc
import gc
import sys
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkCategory(Enum):
    """Categories of performance benchmarks."""
    STARTUP = "startup"
    AUDIO_PROCESSING = "audio_processing"
    NETWORK = "network"
    MEMORY = "memory"
    CPU = "cpu"
    FILESYSTEM = "filesystem"
    CONCURRENCY = "concurrency"
    INTEGRATION = "integration"


class BenchmarkSeverity(Enum):
    """Severity levels for benchmarks."""
    CRITICAL = "critical"     # Must pass for production
    HIGH = "high"            # Important performance targets
    MEDIUM = "medium"        # Nice to have optimizations
    LOW = "low"              # Monitoring only


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    name: str
    value: float
    unit: str
    category: BenchmarkCategory
    severity: BenchmarkSeverity
    threshold: Optional[float] = None
    target: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def status(self) -> str:
        """Get performance status based on threshold."""
        if self.threshold is None:
            return "unknown"
        return "pass" if self.value <= self.threshold else "fail"
    
    @property
    def target_status(self) -> str:
        """Get target achievement status."""
        if self.target is None:
            return "unknown"
        return "achieved" if self.value <= self.target else "missed"


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    benchmark_id: str
    name: str
    category: BenchmarkCategory
    severity: BenchmarkSeverity
    status: str  # pass, fail, error, skipped
    duration: float
    metrics: List[PerformanceMetric] = field(default_factory=list)
    baseline: Optional[Dict[str, float]] = None
    improvement: Optional[Dict[str, float]] = None
    error: Optional[str] = None
    output: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_metric(self, metric: PerformanceMetric) -> None:
        """Add a performance metric."""
        self.metrics.append(metric)
    
    def get_metric(self, name: str) -> Optional[PerformanceMetric]:
        """Get metric by name."""
        return next((m for m in self.metrics if m.name == name), None)
    
    def calculate_improvement(self, baseline: Dict[str, float]) -> None:
        """Calculate improvement percentage vs baseline."""
        self.baseline = baseline.copy()
        self.improvement = {}
        
        for metric in self.metrics:
            if metric.name in baseline:
                baseline_val = baseline[metric.name]
                if baseline_val > 0:
                    improvement_pct = ((baseline_val - metric.value) / baseline_val) * 100
                    self.improvement[metric.name] = improvement_pct


class PerformanceBenchmark(ABC):
    """Abstract base class for performance benchmarks."""
    
    def __init__(self, benchmark_id: str, name: str, category: BenchmarkCategory, 
                 severity: BenchmarkSeverity = BenchmarkSeverity.MEDIUM):
        self.benchmark_id = benchmark_id
        self.name = name
        self.category = category
        self.severity = severity
    
    @abstractmethod
    async def run(self) -> BenchmarkResult:
        """Run the benchmark and return results."""
        pass
    
    def create_result(self, status: str = "pass", duration: float = 0.0, 
                     error: Optional[str] = None) -> BenchmarkResult:
        """Create a benchmark result."""
        return BenchmarkResult(
            benchmark_id=self.benchmark_id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            status=status,
            duration=duration,
            error=error
        )


class StartupBenchmark(PerformanceBenchmark):
    """Benchmark application startup performance."""
    
    def __init__(self):
        super().__init__(
            "startup.cold_start",
            "Cold Start Performance",
            BenchmarkCategory.STARTUP,
            BenchmarkSeverity.CRITICAL
        )
    
    async def run(self) -> BenchmarkResult:
        """Measure startup time."""
        start_time = time.perf_counter()
        
        try:
            # Simulate cold start by importing core modules
            import voice_mode.core
            import voice_mode.config
            import voice_mode.providers
            
            end_time = time.perf_counter()
            startup_time = (end_time - start_time) * 1000  # Convert to ms
            
            result = self.create_result("pass", startup_time / 1000)
            result.add_metric(PerformanceMetric(
                "startup_time",
                startup_time,
                "ms",
                self.category,
                self.severity,
                threshold=2000.0,  # 2 second threshold
                target=1000.0      # 1 second target
            ))
            
            return result
            
        except Exception as e:
            return self.create_result("error", 0.0, str(e))


class MemoryBenchmark(PerformanceBenchmark):
    """Benchmark memory usage patterns."""
    
    def __init__(self):
        super().__init__(
            "memory.baseline",
            "Memory Usage Baseline",
            BenchmarkCategory.MEMORY,
            BenchmarkSeverity.HIGH
        )
    
    async def run(self) -> BenchmarkResult:
        """Measure memory usage."""
        start_time = time.perf_counter()
        
        try:
            # Start tracing
            tracemalloc.start()
            
            # Get initial memory
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Import and initialize core components
            import voice_mode.core
            from voice_mode.config import VoiceModeConfig
            
            config = VoiceModeConfig()
            
            # Get peak memory
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            result = self.create_result("pass", duration)
            
            result.add_metric(PerformanceMetric(
                "initial_memory",
                initial_memory,
                "MB",
                self.category,
                self.severity
            ))
            
            result.add_metric(PerformanceMetric(
                "final_memory",
                final_memory,
                "MB",
                self.category,
                self.severity,
                threshold=200.0,  # 200MB threshold
                target=100.0      # 100MB target
            ))
            
            result.add_metric(PerformanceMetric(
                "memory_increase",
                memory_increase,
                "MB",
                self.category,
                self.severity,
                threshold=50.0,   # 50MB increase threshold
                target=25.0       # 25MB increase target
            ))
            
            result.add_metric(PerformanceMetric(
                "peak_traced_memory",
                peak / 1024 / 1024,  # Convert to MB
                "MB",
                self.category,
                self.severity
            ))
            
            return result
            
        except Exception as e:
            tracemalloc.stop()
            return self.create_result("error", 0.0, str(e))


class AudioProcessingBenchmark(PerformanceBenchmark):
    """Benchmark audio processing performance."""
    
    def __init__(self):
        super().__init__(
            "audio.processing",
            "Audio Processing Performance",
            BenchmarkCategory.AUDIO_PROCESSING,
            BenchmarkSeverity.CRITICAL
        )
    
    async def run(self) -> BenchmarkResult:
        """Measure audio processing performance."""
        start_time = time.perf_counter()
        
        try:
            # Simulate audio processing operations
            import numpy as np
            
            # Generate test audio data (16kHz, 5 seconds)
            sample_rate = 16000
            duration = 5.0
            samples = int(sample_rate * duration)
            
            # Generate sine wave test data
            test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, samples))
            
            # Measure processing time
            process_start = time.perf_counter()
            
            # Simulate common audio operations
            for _ in range(10):
                # Normalization
                normalized = test_audio / np.max(np.abs(test_audio))
                
                # Simple filtering (moving average)
                window_size = 100
                filtered = np.convolve(normalized, np.ones(window_size)/window_size, mode='same')
                
                # RMS calculation
                rms = np.sqrt(np.mean(filtered**2))
            
            process_end = time.perf_counter()
            processing_time = (process_end - process_start) * 1000
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            result = self.create_result("pass", total_duration)
            
            result.add_metric(PerformanceMetric(
                "processing_time",
                processing_time,
                "ms",
                self.category,
                self.severity,
                threshold=500.0,  # 500ms threshold
                target=100.0      # 100ms target
            ))
            
            result.add_metric(PerformanceMetric(
                "samples_per_second",
                (samples * 10) / (processing_time / 1000),
                "samples/s",
                self.category,
                self.severity,
                target=1000000.0  # 1M samples/s target
            ))
            
            return result
            
        except Exception as e:
            return self.create_result("error", 0.0, str(e))


class ConcurrencyBenchmark(PerformanceBenchmark):
    """Benchmark concurrent operation performance."""
    
    def __init__(self):
        super().__init__(
            "concurrency.parallel",
            "Parallel Processing Performance",
            BenchmarkCategory.CONCURRENCY,
            BenchmarkSeverity.HIGH
        )
    
    async def run(self) -> BenchmarkResult:
        """Measure concurrent processing performance."""
        start_time = time.perf_counter()
        
        try:
            # Test async operations
            async def worker(task_id: int) -> Tuple[int, float]:
                work_start = time.perf_counter()
                
                # Simulate work
                await asyncio.sleep(0.1)
                
                # CPU-intensive task
                result = sum(i * i for i in range(1000))
                
                work_end = time.perf_counter()
                return task_id, (work_end - work_start) * 1000
            
            # Run tasks concurrently
            num_tasks = 10
            concurrent_start = time.perf_counter()
            
            tasks = [worker(i) for i in range(num_tasks)]
            results = await asyncio.gather(*tasks)
            
            concurrent_end = time.perf_counter()
            concurrent_time = (concurrent_end - concurrent_start) * 1000
            
            # Calculate individual task times
            task_times = [time for _, time in results]
            avg_task_time = statistics.mean(task_times)
            max_task_time = max(task_times)
            min_task_time = min(task_times)
            
            # Test thread pool performance
            thread_start = time.perf_counter()
            
            def cpu_bound_work(n: int) -> int:
                return sum(i * i for i in range(n * 1000))
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(cpu_bound_work, i) for i in range(num_tasks)]
                thread_results = [f.result() for f in as_completed(futures)]
            
            thread_end = time.perf_counter()
            thread_time = (thread_end - thread_start) * 1000
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            result = self.create_result("pass", total_duration)
            
            result.add_metric(PerformanceMetric(
                "concurrent_execution_time",
                concurrent_time,
                "ms",
                self.category,
                self.severity,
                threshold=1500.0,  # 1.5s threshold for 10 concurrent tasks
                target=500.0       # 500ms target
            ))
            
            result.add_metric(PerformanceMetric(
                "avg_task_time",
                avg_task_time,
                "ms",
                self.category,
                self.severity,
                threshold=200.0,   # 200ms per task threshold
                target=120.0       # 120ms per task target
            ))
            
            result.add_metric(PerformanceMetric(
                "thread_pool_time",
                thread_time,
                "ms",
                self.category,
                self.severity,
                threshold=1000.0,  # 1s threshold
                target=300.0       # 300ms target
            ))
            
            result.add_metric(PerformanceMetric(
                "task_time_variance",
                statistics.variance(task_times),
                "ms²",
                self.category,
                self.severity,
                threshold=100.0    # Low variance target
            ))
            
            return result
            
        except Exception as e:
            return self.create_result("error", 0.0, str(e))


class NetworkBenchmark(PerformanceBenchmark):
    """Benchmark network operations."""
    
    def __init__(self):
        super().__init__(
            "network.requests",
            "Network Request Performance",
            BenchmarkCategory.NETWORK,
            BenchmarkSeverity.MEDIUM
        )
    
    async def run(self) -> BenchmarkResult:
        """Measure network request performance."""
        start_time = time.perf_counter()
        
        try:
            import aiohttp
            import asyncio
            
            async def make_request(session: aiohttp.ClientSession, url: str) -> float:
                request_start = time.perf_counter()
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        await response.text()
                        request_end = time.perf_counter()
                        return (request_end - request_start) * 1000
                except Exception:
                    return -1  # Error indicator
            
            # Test URLs (using httpbin for reliable testing)
            test_urls = [
                "https://httpbin.org/delay/0.1",
                "https://httpbin.org/json",
                "https://httpbin.org/uuid"
            ]
            
            async with aiohttp.ClientSession() as session:
                # Single requests
                single_times = []
                for url in test_urls:
                    request_time = await make_request(session, url)
                    if request_time > 0:
                        single_times.append(request_time)
                
                # Concurrent requests
                concurrent_start = time.perf_counter()
                concurrent_tasks = [make_request(session, url) for url in test_urls * 3]
                concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                concurrent_end = time.perf_counter()
                
                concurrent_times = [r for r in concurrent_results if isinstance(r, (int, float)) and r > 0]
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            result = self.create_result("pass", total_duration)
            
            if single_times:
                result.add_metric(PerformanceMetric(
                    "avg_request_time",
                    statistics.mean(single_times),
                    "ms",
                    self.category,
                    self.severity,
                    threshold=2000.0,  # 2s threshold
                    target=500.0       # 500ms target
                ))
                
                result.add_metric(PerformanceMetric(
                    "max_request_time",
                    max(single_times),
                    "ms",
                    self.category,
                    self.severity,
                    threshold=5000.0   # 5s threshold
                ))
            
            if concurrent_times:
                result.add_metric(PerformanceMetric(
                    "concurrent_avg_time",
                    statistics.mean(concurrent_times),
                    "ms",
                    self.category,
                    self.severity,
                    threshold=3000.0,  # 3s threshold for concurrent
                    target=1000.0      # 1s target
                ))
                
                concurrent_total = (concurrent_end - concurrent_start) * 1000
                result.add_metric(PerformanceMetric(
                    "concurrent_total_time",
                    concurrent_total,
                    "ms",
                    self.category,
                    self.severity,
                    threshold=10000.0,  # 10s threshold
                    target=3000.0       # 3s target
                ))
            
            return result
            
        except ImportError:
            return self.create_result("skipped", 0.0, "aiohttp not available")
        except Exception as e:
            return self.create_result("error", 0.0, str(e))


class FileSystemBenchmark(PerformanceBenchmark):
    """Benchmark filesystem operations."""
    
    def __init__(self):
        super().__init__(
            "filesystem.io",
            "Filesystem I/O Performance",
            BenchmarkCategory.FILESYSTEM,
            BenchmarkSeverity.MEDIUM
        )
    
    async def run(self) -> BenchmarkResult:
        """Measure filesystem performance."""
        start_time = time.perf_counter()
        
        try:
            import tempfile
            import os
            import shutil
            
            test_data = "x" * 1024 * 100  # 100KB test data
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Write performance
                write_start = time.perf_counter()
                test_files = []
                for i in range(50):
                    file_path = temp_path / f"test_{i}.txt"
                    with open(file_path, 'w') as f:
                        f.write(test_data)
                    test_files.append(file_path)
                write_end = time.perf_counter()
                write_time = (write_end - write_start) * 1000
                
                # Read performance
                read_start = time.perf_counter()
                for file_path in test_files:
                    with open(file_path, 'r') as f:
                        content = f.read()
                read_end = time.perf_counter()
                read_time = (read_end - read_start) * 1000
                
                # Directory operations
                dir_start = time.perf_counter()
                for i in range(10):
                    dir_path = temp_path / f"subdir_{i}"
                    dir_path.mkdir()
                    
                    # Create nested structure
                    nested_path = dir_path / "nested"
                    nested_path.mkdir()
                    
                    # List directory
                    list(dir_path.iterdir())
                dir_end = time.perf_counter()
                dir_time = (dir_end - dir_start) * 1000
                
                # Cleanup performance (delete files)
                cleanup_start = time.perf_counter()
                for file_path in test_files:
                    file_path.unlink()
                cleanup_end = time.perf_counter()
                cleanup_time = (cleanup_end - cleanup_start) * 1000
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            result = self.create_result("pass", total_duration)
            
            # Calculate throughput
            total_data_mb = (len(test_data) * len(test_files)) / 1024 / 1024
            
            result.add_metric(PerformanceMetric(
                "write_time",
                write_time,
                "ms",
                self.category,
                self.severity,
                threshold=2000.0,  # 2s threshold
                target=500.0       # 500ms target
            ))
            
            result.add_metric(PerformanceMetric(
                "read_time",
                read_time,
                "ms",
                self.category,
                self.severity,
                threshold=1000.0,  # 1s threshold
                target=200.0       # 200ms target
            ))
            
            result.add_metric(PerformanceMetric(
                "write_throughput",
                total_data_mb / (write_time / 1000),
                "MB/s",
                self.category,
                self.severity,
                target=10.0        # 10 MB/s target
            ))
            
            result.add_metric(PerformanceMetric(
                "read_throughput",
                total_data_mb / (read_time / 1000),
                "MB/s",
                self.category,
                self.severity,
                target=50.0        # 50 MB/s target
            ))
            
            result.add_metric(PerformanceMetric(
                "directory_operations_time",
                dir_time,
                "ms",
                self.category,
                self.severity,
                threshold=1000.0,  # 1s threshold
                target=200.0       # 200ms target
            ))
            
            return result
            
        except Exception as e:
            return self.create_result("error", 0.0, str(e))


class PerformanceBenchmarkRunner:
    """Runner for performance benchmarks."""
    
    def __init__(self):
        self.benchmarks: Dict[str, PerformanceBenchmark] = {}
        self.results: List[BenchmarkResult] = []
        self.baselines: Dict[str, Dict[str, float]] = {}
        self._register_benchmarks()
    
    def _register_benchmarks(self) -> None:
        """Register all available benchmarks."""
        benchmarks = [
            StartupBenchmark(),
            MemoryBenchmark(),
            AudioProcessingBenchmark(),
            ConcurrencyBenchmark(),
            NetworkBenchmark(),
            FileSystemBenchmark()
        ]
        
        for benchmark in benchmarks:
            self.benchmarks[benchmark.benchmark_id] = benchmark
    
    async def run_benchmark(self, benchmark_id: str) -> BenchmarkResult:
        """Run a specific benchmark."""
        if benchmark_id not in self.benchmarks:
            raise ValueError(f"Benchmark '{benchmark_id}' not found")
        
        benchmark = self.benchmarks[benchmark_id]
        logger.info(f"Running benchmark: {benchmark.name}")
        
        try:
            result = await benchmark.run()
            
            # Calculate improvement if baseline exists
            if benchmark_id in self.baselines:
                baseline_metrics = self.baselines[benchmark_id]
                result.calculate_improvement(baseline_metrics)
            
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Benchmark {benchmark_id} failed: {e}")
            error_result = benchmark.create_result("error", 0.0, str(e))
            self.results.append(error_result)
            return error_result
    
    async def run_all_benchmarks(
        self,
        categories: Optional[Set[BenchmarkCategory]] = None,
        severities: Optional[Set[BenchmarkSeverity]] = None,
        critical_only: bool = False
    ) -> List[BenchmarkResult]:
        """Run all benchmarks with optional filtering."""
        
        # Filter benchmarks
        benchmarks_to_run = []
        for benchmark_id, benchmark in self.benchmarks.items():
            
            # Category filter
            if categories and benchmark.category not in categories:
                continue
                
            # Severity filter
            if severities and benchmark.severity not in severities:
                continue
                
            # Critical only filter
            if critical_only and benchmark.severity != BenchmarkSeverity.CRITICAL:
                continue
            
            benchmarks_to_run.append(benchmark_id)
        
        logger.info(f"Running {len(benchmarks_to_run)} benchmarks")
        
        # Run benchmarks
        results = []
        for benchmark_id in benchmarks_to_run:
            result = await self.run_benchmark(benchmark_id)
            results.append(result)
        
        return results
    
    def load_baselines(self, baseline_file: Union[str, Path]) -> None:
        """Load baseline performance data."""
        baseline_path = Path(baseline_file)
        if baseline_path.exists():
            try:
                with open(baseline_path, 'r') as f:
                    self.baselines = json.load(f)
                logger.info(f"Loaded baselines for {len(self.baselines)} benchmarks")
            except Exception as e:
                logger.warning(f"Failed to load baselines: {e}")
    
    def save_baselines(self, baseline_file: Union[str, Path]) -> None:
        """Save current results as baseline."""
        baseline_data = {}
        
        for result in self.results:
            if result.status == "pass":
                baseline_data[result.benchmark_id] = {
                    metric.name: metric.value 
                    for metric in result.metrics
                }
        
        baseline_path = Path(baseline_file)
        with open(baseline_path, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        logger.info(f"Saved baselines for {len(baseline_data)} benchmarks")
    
    def generate_report(self, format: str = "text") -> Union[str, Dict[str, Any]]:
        """Generate performance report."""
        if format == "json":
            return self._generate_json_report()
        else:
            return self._generate_text_report()
    
    def _generate_json_report(self) -> Dict[str, Any]:
        """Generate JSON format report."""
        return {
            "timestamp": time.time(),
            "platform": {
                "system": platform.system(),
                "machine": platform.machine(),
                "python_version": platform.python_version()
            },
            "summary": self._calculate_summary(),
            "benchmarks": [
                {
                    "id": r.benchmark_id,
                    "name": r.name,
                    "category": r.category.value,
                    "severity": r.severity.value,
                    "status": r.status,
                    "duration": r.duration,
                    "metrics": [
                        {
                            "name": m.name,
                            "value": m.value,
                            "unit": m.unit,
                            "status": m.status,
                            "target_status": m.target_status,
                            "threshold": m.threshold,
                            "target": m.target
                        }
                        for m in r.metrics
                    ],
                    "improvement": r.improvement,
                    "error": r.error
                }
                for r in self.results
            ]
        }
    
    def _generate_text_report(self) -> str:
        """Generate text format report."""
        lines = [
            "=" * 70,
            "PERFORMANCE BENCHMARK REPORT",
            "=" * 70,
            "",
            f"Platform: {platform.system()} {platform.machine()}",
            f"Python: {platform.python_version()}",
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "SUMMARY:",
            "--------"
        ]
        
        summary = self._calculate_summary()
        lines.extend([
            f"  Total Benchmarks: {summary['total_benchmarks']}",
            f"  Passed: {summary['passed']}",
            f"  Failed: {summary['failed']}",
            f"  Errors: {summary['errors']}",
            f"  Skipped: {summary['skipped']}",
            f"  Success Rate: {summary['success_rate']:.1f}%",
            f"  Critical Failures: {summary['critical_failures']}",
            f"  Performance Score: {summary['performance_score']:.1f}/100",
            ""
        ])
        
        # Benchmark details
        lines.append("BENCHMARK DETAILS:")
        lines.append("-" * 50)
        
        for result in sorted(self.results, key=lambda x: (x.category.value, x.severity.value)):
            status_icon = {"pass": "✅", "fail": "❌", "error": "💥", "skipped": "⏭️"}.get(result.status, "❓")
            
            lines.append(f"{status_icon} {result.name}")
            lines.append(f"   Category: {result.category.value}")
            lines.append(f"   Severity: {result.severity.value}")
            lines.append(f"   Duration: {result.duration:.3f}s")
            
            if result.error:
                lines.append(f"   Error: {result.error}")
            
            for metric in result.metrics:
                status_text = f"[{metric.status.upper()}]" if metric.threshold else "[INFO]"
                improvement_text = ""
                
                if result.improvement and metric.name in result.improvement:
                    improvement = result.improvement[metric.name]
                    if improvement > 0:
                        improvement_text = f" (+{improvement:.1f}% better)"
                    else:
                        improvement_text = f" ({improvement:.1f}% worse)"
                
                lines.append(f"   {metric.name}: {metric.value:.2f} {metric.unit} {status_text}{improvement_text}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate performance summary statistics."""
        total_benchmarks = len(self.results)
        
        if total_benchmarks == 0:
            return {
                "total_benchmarks": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "success_rate": 0.0,
                "critical_failures": 0,
                "performance_score": 0.0
            }
        
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail")
        errors = sum(1 for r in self.results if r.status == "error")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        
        success_rate = (passed / total_benchmarks) * 100 if total_benchmarks > 0 else 0
        
        critical_failures = sum(1 for r in self.results 
                              if r.severity == BenchmarkSeverity.CRITICAL and r.status in ["fail", "error"])
        
        # Calculate performance score based on metrics meeting targets
        total_metrics = sum(len(r.metrics) for r in self.results)
        target_achieved = 0
        
        for result in self.results:
            for metric in result.metrics:
                if metric.target_status == "achieved":
                    target_achieved += 1
        
        performance_score = (target_achieved / total_metrics) * 100 if total_metrics > 0 else 0
        
        return {
            "total_benchmarks": total_benchmarks,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "success_rate": success_rate,
            "critical_failures": critical_failures,
            "performance_score": performance_score
        }


# Global runner instance
_performance_runner = None


def get_performance_runner() -> PerformanceBenchmarkRunner:
    """Get the global performance benchmark runner."""
    global _performance_runner
    if _performance_runner is None:
        _performance_runner = PerformanceBenchmarkRunner()
    return _performance_runner


async def run_performance_benchmarks(
    categories: Optional[List[str]] = None,
    severities: Optional[List[str]] = None,
    critical_only: bool = False,
    baseline_file: Optional[str] = None,
    save_baseline: bool = False,
    output_format: str = "text"
) -> Dict[str, Any]:
    """Run performance benchmarks with specified parameters."""
    
    runner = get_performance_runner()
    
    # Load baseline if specified
    if baseline_file:
        runner.load_baselines(baseline_file)
    
    # Convert string parameters to enums
    category_enums = None
    if categories:
        category_enums = {BenchmarkCategory(cat) for cat in categories if cat in [c.value for c in BenchmarkCategory]}
    
    severity_enums = None
    if severities:
        severity_enums = {BenchmarkSeverity(sev) for sev in severities if sev in [s.value for s in BenchmarkSeverity]}
    
    # Run benchmarks
    results = await runner.run_all_benchmarks(
        categories=category_enums,
        severities=severity_enums,
        critical_only=critical_only
    )
    
    # Save baseline if requested
    if save_baseline and baseline_file:
        runner.save_baselines(baseline_file)
    
    # Generate report
    report = runner.generate_report(format=output_format)
    
    # Calculate success status
    summary = runner._calculate_summary()
    success = (summary["critical_failures"] == 0 and 
              summary["errors"] == 0 and
              summary["success_rate"] >= 80.0)
    
    return {
        "success": success,
        "results": results,
        "report": report,
        "summary": summary,
        "runner": runner
    }


if __name__ == "__main__":
    async def main():
        result = await run_performance_benchmarks()
        print(result["report"])
    
    asyncio.run(main())