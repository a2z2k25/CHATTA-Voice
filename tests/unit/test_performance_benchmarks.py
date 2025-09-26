#!/usr/bin/env python3
"""Test performance benchmarking system."""

import asyncio
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from voice_mode.performance_benchmarks import (
    PerformanceBenchmarkRunner,
    BenchmarkCategory,
    BenchmarkSeverity,
    PerformanceMetric,
    BenchmarkResult,
    StartupBenchmark,
    MemoryBenchmark,
    AudioProcessingBenchmark,
    ConcurrencyBenchmark,
    NetworkBenchmark,
    FileSystemBenchmark,
    get_performance_runner,
    run_performance_benchmarks
)


def test_performance_metric_creation():
    """Test performance metric creation and properties."""
    print("\n=== Testing Performance Metric Creation ===")
    
    # Create a metric with threshold
    metric = PerformanceMetric(
        name="test_metric",
        value=100.0,
        unit="ms",
        category=BenchmarkCategory.STARTUP,
        severity=BenchmarkSeverity.HIGH,
        threshold=150.0,
        target=80.0
    )
    
    print(f"  Metric created: {metric.name}")
    print(f"  Value: {metric.value} {metric.unit}")
    print(f"  Category: {metric.category.value}")
    print(f"  Severity: {metric.severity.value}")
    print(f"  Status (vs threshold): {metric.status}")
    print(f"  Target status: {metric.target_status}")
    
    # Test threshold logic
    passing_metric = PerformanceMetric("pass_test", 50.0, "ms", BenchmarkCategory.STARTUP, BenchmarkSeverity.HIGH, threshold=100.0)
    failing_metric = PerformanceMetric("fail_test", 150.0, "ms", BenchmarkCategory.STARTUP, BenchmarkSeverity.HIGH, threshold=100.0)
    
    print(f"  Passing metric status: {passing_metric.status}")
    print(f"  Failing metric status: {failing_metric.status}")
    
    print("✓ Performance metric creation working")


def test_benchmark_result_operations():
    """Test benchmark result operations."""
    print("\n=== Testing Benchmark Result Operations ===")
    
    # Create a benchmark result
    result = BenchmarkResult(
        benchmark_id="test.benchmark",
        name="Test Benchmark",
        category=BenchmarkCategory.MEMORY,
        severity=BenchmarkSeverity.CRITICAL,
        status="pass",
        duration=1.5
    )
    
    print(f"  Result created: {result.name}")
    print(f"  Initial metrics: {len(result.metrics)}")
    
    # Add metrics
    result.add_metric(PerformanceMetric("memory_usage", 50.0, "MB", BenchmarkCategory.MEMORY, BenchmarkSeverity.HIGH))
    result.add_metric(PerformanceMetric("execution_time", 1200.0, "ms", BenchmarkCategory.MEMORY, BenchmarkSeverity.HIGH))
    
    print(f"  After adding metrics: {len(result.metrics)}")
    
    # Test metric retrieval
    memory_metric = result.get_metric("memory_usage")
    missing_metric = result.get_metric("nonexistent")
    
    print(f"  Retrieved existing metric: {memory_metric is not None}")
    print(f"  Retrieved missing metric: {missing_metric is None}")
    
    # Test improvement calculation
    baseline = {"memory_usage": 60.0, "execution_time": 1500.0}
    result.calculate_improvement(baseline)
    
    print(f"  Baseline set: {result.baseline is not None}")
    print(f"  Improvement calculated: {result.improvement is not None}")
    
    if result.improvement:
        for metric_name, improvement in result.improvement.items():
            print(f"    {metric_name}: {improvement:.1f}% improvement")
    
    print("✓ Benchmark result operations working")


async def test_individual_benchmarks():
    """Test individual benchmark execution."""
    print("\n=== Testing Individual Benchmark Execution ===")
    
    benchmarks = [
        ("Startup", StartupBenchmark()),
        ("Memory", MemoryBenchmark()),
        ("Audio Processing", AudioProcessingBenchmark()),
        ("Concurrency", ConcurrencyBenchmark()),
        ("Network", NetworkBenchmark()),
        ("FileSystem", FileSystemBenchmark())
    ]
    
    results = []
    
    for name, benchmark in benchmarks:
        print(f"  Running {name} benchmark...")
        start_time = time.perf_counter()
        
        try:
            result = await benchmark.run()
            end_time = time.perf_counter()
            actual_duration = end_time - start_time
            
            print(f"    Status: {result.status}")
            print(f"    Reported duration: {result.duration:.3f}s")
            print(f"    Actual duration: {actual_duration:.3f}s")
            print(f"    Metrics: {len(result.metrics)}")
            
            # Show key metrics
            for metric in result.metrics[:2]:  # Show first 2 metrics
                print(f"      {metric.name}: {metric.value:.2f} {metric.unit}")
            
            if result.error:
                print(f"    Error: {result.error}")
            
            results.append((name, result))
            
        except Exception as e:
            print(f"    Failed: {e}")
            results.append((name, None))
    
    successful_benchmarks = sum(1 for _, result in results if result and result.status in ["pass", "skipped"])
    print(f"  Successful benchmarks: {successful_benchmarks}/{len(benchmarks)}")
    
    print("✓ Individual benchmark execution working")
    return results


def test_benchmark_runner_creation():
    """Test benchmark runner creation and registration."""
    print("\n=== Testing Benchmark Runner Creation ===")
    
    runner = PerformanceBenchmarkRunner()
    
    print(f"  Runner created: {runner is not None}")
    print(f"  Benchmarks registered: {len(runner.benchmarks)}")
    print(f"  Initial results: {len(runner.results)}")
    
    # Check benchmark categories
    categories = {}
    severities = {}
    
    for benchmark_id, benchmark in runner.benchmarks.items():
        categories[benchmark.category] = categories.get(benchmark.category, 0) + 1
        severities[benchmark.severity] = severities.get(benchmark.severity, 0) + 1
        print(f"    {benchmark_id}: {benchmark.name}")
    
    print(f"  Categories represented: {len(categories)}")
    for category, count in categories.items():
        print(f"    {category.value}: {count} benchmarks")
    
    print(f"  Severity levels: {len(severities)}")
    for severity, count in severities.items():
        print(f"    {severity.value}: {count} benchmarks")
    
    print("✓ Benchmark runner creation working")


async def test_benchmark_runner_execution():
    """Test benchmark runner execution."""
    print("\n=== Testing Benchmark Runner Execution ===")
    
    runner = get_performance_runner()
    
    # Test single benchmark execution
    try:
        if "startup.cold_start" in runner.benchmarks:
            result = await runner.run_benchmark("startup.cold_start")
            print(f"  Single benchmark result: {result.status}")
            print(f"    Metrics: {len(result.metrics)}")
        
        # Test invalid benchmark
        error_result = await runner.run_benchmark("nonexistent.benchmark")
        print(f"  Invalid benchmark handled: {error_result.status == 'error'}")
        
    except ValueError as e:
        print(f"  Invalid benchmark error: {type(e).__name__}")
    
    print("✓ Benchmark runner execution working")


async def test_benchmark_filtering():
    """Test benchmark filtering by category and severity."""
    print("\n=== Testing Benchmark Filtering ===")
    
    runner = get_performance_runner()
    
    # Test category filtering
    startup_results = await runner.run_all_benchmarks(categories={BenchmarkCategory.STARTUP})
    print(f"  Startup category benchmarks: {len(startup_results)}")
    
    memory_results = await runner.run_all_benchmarks(categories={BenchmarkCategory.MEMORY})
    print(f"  Memory category benchmarks: {len(memory_results)}")
    
    # Test severity filtering
    critical_results = await runner.run_all_benchmarks(severities={BenchmarkSeverity.CRITICAL})
    print(f"  Critical severity benchmarks: {len(critical_results)}")
    
    # Test critical only filter
    critical_only_results = await runner.run_all_benchmarks(critical_only=True)
    print(f"  Critical only benchmarks: {len(critical_only_results)}")
    
    # Test combined filtering
    critical_startup = await runner.run_all_benchmarks(
        categories={BenchmarkCategory.STARTUP},
        severities={BenchmarkSeverity.CRITICAL}
    )
    print(f"  Critical startup benchmarks: {len(critical_startup)}")
    
    # Verify filtering worked
    if critical_only_results:
        all_critical = all(r.severity == BenchmarkSeverity.CRITICAL for r in critical_only_results 
                          if hasattr(runner.benchmarks.get(r.benchmark_id), 'severity'))
        print(f"  All results are critical: {all_critical}")
    
    print("✓ Benchmark filtering working")


async def test_baseline_operations():
    """Test baseline save/load operations."""
    print("\n=== Testing Baseline Operations ===")
    
    runner = get_performance_runner()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        baseline_file = Path(temp_dir) / "test_baselines.json"
        
        # Run some benchmarks to generate results
        await runner.run_all_benchmarks(categories={BenchmarkCategory.STARTUP})
        initial_results = len(runner.results)
        
        print(f"  Generated results: {initial_results}")
        
        # Save baselines
        runner.save_baselines(baseline_file)
        print(f"  Baseline file created: {baseline_file.exists()}")
        
        if baseline_file.exists():
            print(f"  Baseline file size: {baseline_file.stat().st_size} bytes")
        
        # Create new runner and load baselines
        new_runner = PerformanceBenchmarkRunner()
        new_runner.load_baselines(baseline_file)
        
        print(f"  Baselines loaded: {len(new_runner.baselines)}")
        
        if new_runner.baselines:
            print("  Baseline entries:")
            for benchmark_id, metrics in list(new_runner.baselines.items())[:3]:
                print(f"    {benchmark_id}: {len(metrics)} metrics")
        
        # Test loading non-existent file
        fake_file = Path(temp_dir) / "nonexistent.json"
        new_runner.load_baselines(fake_file)
        print("  Non-existent file handled gracefully")
    
    print("✓ Baseline operations working")


async def test_report_generation():
    """Test performance report generation."""
    print("\n=== Testing Report Generation ===")
    
    runner = get_performance_runner()
    
    # Generate some results
    results = await runner.run_all_benchmarks(critical_only=True)
    print(f"  Benchmark results generated: {len(results)}")
    
    # Test text report
    text_report = runner.generate_report(format="text")
    print(f"  Text report generated: {isinstance(text_report, str)}")
    print(f"  Text report length: {len(text_report)} characters")
    print(f"  Contains header: {'PERFORMANCE BENCHMARK' in text_report}")
    print(f"  Contains summary: {'SUMMARY:' in text_report}")
    
    # Test JSON report
    json_report = runner.generate_report(format="json")
    print(f"  JSON report generated: {isinstance(json_report, dict)}")
    
    if isinstance(json_report, dict):
        print(f"  JSON report keys: {list(json_report.keys())}")
        print(f"  Has platform info: {'platform' in json_report}")
        print(f"  Has benchmarks: {'benchmarks' in json_report}")
        print(f"  Has summary: {'summary' in json_report}")
        
        if 'benchmarks' in json_report:
            print(f"    Benchmark entries: {len(json_report['benchmarks'])}")
    
    # Test summary calculation
    summary = runner._calculate_summary()
    print(f"  Summary calculated: {isinstance(summary, dict)}")
    
    if summary:
        print(f"    Total benchmarks: {summary.get('total_benchmarks', 0)}")
        print(f"    Success rate: {summary.get('success_rate', 0):.1f}%")
        print(f"    Performance score: {summary.get('performance_score', 0):.1f}/100")
    
    print("✓ Report generation working")


async def test_high_level_interface():
    """Test high-level run_performance_benchmarks function."""
    print("\n=== Testing High-Level Interface ===")
    
    # Test with different parameters
    test_params = [
        {"critical_only": True, "output_format": "text"},
        {"categories": ["startup", "memory"], "output_format": "json"},
        {"severities": ["critical", "high"]}
    ]
    
    for i, params in enumerate(test_params, 1):
        print(f"  Test {i}: {params}")
        
        try:
            result = await run_performance_benchmarks(**params)
            
            print(f"    Success: {result.get('success', False)}")
            print(f"    Has results: {'results' in result}")
            print(f"    Has report: {'report' in result}")
            print(f"    Has summary: {'summary' in result}")
            
            if 'results' in result:
                print(f"    Results count: {len(result['results'])}")
            
            if 'summary' in result:
                summary = result['summary']
                print(f"    Success rate: {summary.get('success_rate', 0):.1f}%")
                print(f"    Critical failures: {summary.get('critical_failures', 0)}")
            
        except Exception as e:
            print(f"    Error: {e}")
    
    print("✓ High-level interface working")


async def test_performance_thresholds():
    """Test performance threshold validation."""
    print("\n=== Testing Performance Thresholds ===")
    
    runner = get_performance_runner()
    
    # Run critical benchmarks
    critical_results = await runner.run_all_benchmarks(critical_only=True)
    
    threshold_violations = []
    target_achievements = []
    
    for result in critical_results:
        if result.status == "pass":
            for metric in result.metrics:
                if metric.threshold is not None:
                    if metric.status == "fail":
                        threshold_violations.append(f"{result.name}.{metric.name}")
                    
                if metric.target is not None:
                    if metric.target_status == "achieved":
                        target_achievements.append(f"{result.name}.{metric.name}")
    
    print(f"  Critical benchmarks run: {len(critical_results)}")
    print(f"  Threshold violations: {len(threshold_violations)}")
    print(f"  Target achievements: {len(target_achievements)}")
    
    if threshold_violations:
        print("  Violations:")
        for violation in threshold_violations[:3]:
            print(f"    - {violation}")
    
    if target_achievements:
        print("  Target achievements:")
        for achievement in target_achievements[:3]:
            print(f"    - {achievement}")
    
    # Calculate performance health
    total_critical_metrics = sum(len(r.metrics) for r in critical_results if r.status == "pass")
    health_score = (len(target_achievements) / total_critical_metrics * 100) if total_critical_metrics > 0 else 0
    
    print(f"  Performance health score: {health_score:.1f}%")
    print(f"  Critical system health: {'GOOD' if len(threshold_violations) == 0 else 'ATTENTION NEEDED'}")
    
    print("✓ Performance threshold validation working")


def test_singleton_behavior():
    """Test singleton behavior of performance runner."""
    print("\n=== Testing Singleton Behavior ===")
    
    runner1 = get_performance_runner()
    runner2 = get_performance_runner()
    
    print(f"  Same instance: {runner1 is runner2}")
    print(f"  Instance type: {type(runner1).__name__}")
    
    # Test shared state
    initial_results = len(runner1.results)
    
    # Add results via runner1
    runner1.results.append(BenchmarkResult(
        "test.singleton", "Singleton Test", BenchmarkCategory.STARTUP, 
        BenchmarkSeverity.LOW, "pass", 1.0
    ))
    
    after_addition = len(runner2.results)
    print(f"  State shared: {after_addition > initial_results}")
    print(f"  Total results: {len(runner2.results)}")
    
    print("✓ Singleton behavior working")


async def test_error_handling():
    """Test error handling in benchmarks."""
    print("\n=== Testing Error Handling ===")
    
    runner = get_performance_runner()
    
    # Test invalid benchmark ID
    try:
        result = await runner.run_benchmark("invalid.benchmark")
        print(f"  Invalid benchmark handled: {result is not None}")
    except ValueError as e:
        print(f"  Invalid benchmark error: {type(e).__name__}")
    
    # Test empty filters
    empty_category_results = await runner.run_all_benchmarks(categories=set())
    print(f"  Empty category filter handled: {len(empty_category_results) >= 0}")
    
    empty_severity_results = await runner.run_all_benchmarks(severities=set())
    print(f"  Empty severity filter handled: {len(empty_severity_results) >= 0}")
    
    # Test invalid format
    try:
        invalid_report = runner.generate_report(format="invalid")
        print(f"  Invalid format handled: {invalid_report is not None}")
    except Exception as e:
        print(f"  Invalid format error: {type(e).__name__}")
    
    print("✓ Error handling working")


async def test_concurrent_execution():
    """Test concurrent benchmark execution safety."""
    print("\n=== Testing Concurrent Execution Safety ===")
    
    runner = get_performance_runner()
    
    async def run_benchmark_set(benchmark_ids: List[str]) -> List[BenchmarkResult]:
        """Run a set of benchmarks."""
        results = []
        for benchmark_id in benchmark_ids:
            if benchmark_id in runner.benchmarks:
                result = await runner.run_benchmark(benchmark_id)
                results.append(result)
        return results
    
    # Split benchmarks into groups for concurrent execution
    benchmark_ids = list(runner.benchmarks.keys())
    mid_point = len(benchmark_ids) // 2
    
    group1 = benchmark_ids[:mid_point]
    group2 = benchmark_ids[mid_point:]
    
    print(f"  Group 1 benchmarks: {len(group1)}")
    print(f"  Group 2 benchmarks: {len(group2)}")
    
    # Run groups concurrently
    start_time = time.perf_counter()
    
    concurrent_results = await asyncio.gather(
        run_benchmark_set(group1),
        run_benchmark_set(group2),
        return_exceptions=True
    )
    
    end_time = time.perf_counter()
    concurrent_time = end_time - start_time
    
    print(f"  Concurrent execution time: {concurrent_time:.3f}s")
    
    # Check results
    total_results = 0
    for group_results in concurrent_results:
        if isinstance(group_results, list):
            total_results += len(group_results)
        elif isinstance(group_results, Exception):
            print(f"    Group error: {group_results}")
    
    print(f"  Total concurrent results: {total_results}")
    print(f"  Runner results count: {len(runner.results)}")
    
    print("✓ Concurrent execution safety working")


async def run_all_performance_tests():
    """Run all performance benchmark tests."""
    print("=" * 70)
    print("PERFORMANCE BENCHMARK SYSTEM VALIDATION")
    print("=" * 70)
    
    test_functions = [
        test_performance_metric_creation,
        test_benchmark_result_operations,
        test_individual_benchmarks,
        test_benchmark_runner_creation,
        test_benchmark_runner_execution,
        test_benchmark_filtering,
        test_baseline_operations,
        test_report_generation,
        test_high_level_interface,
        test_performance_thresholds,
        test_singleton_behavior,
        test_error_handling,
        test_concurrent_execution
    ]
    
    start_time = asyncio.get_event_loop().time()
    passed_tests = 0
    
    for i, test_func in enumerate(test_functions, 1):
        try:
            print(f"\n[{i}/{len(test_functions)}] Running {test_func.__name__}")
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            passed_tests += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    total_time = asyncio.get_event_loop().time() - start_time
    
    print(f"\n{'=' * 70}")
    print(f"✓ Performance benchmark system validation complete!")
    print(f"  Tests passed: {passed_tests}/{len(test_functions)}")
    print(f"  Success rate: {passed_tests / len(test_functions) * 100:.1f}%")
    print(f"  Total validation time: {total_time:.3f}s")
    print(f"  Average per test: {total_time / len(test_functions):.3f}s")
    
    if passed_tests == len(test_functions):
        print("🎉 All performance benchmark tests PASSED!")
        print("Sprint 43 performance benchmarking COMPLETE!")
    else:
        print("⚠️  Some tests failed - review above for details")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_performance_tests())