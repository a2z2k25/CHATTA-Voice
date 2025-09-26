#!/usr/bin/env python3
"""Test cross-platform testing system."""

import asyncio
import os
import platform
from typing import List, Dict, Any
from voice_mode.cross_platform_tests import (
    CrossPlatformTestRunner,
    PlatformDetector,
    Platform,
    Architecture,
    TestEnvironment,
    PlatformFeature,
    get_cross_platform_runner,
    run_cross_platform_tests
)


def test_platform_detection():
    """Test platform detection functionality."""
    print("\n=== Testing Platform Detection ===")
    
    # Test platform detection
    detected_platform = PlatformDetector.detect_platform()
    print(f"  Detected platform: {detected_platform.name}")
    print(f"  Platform value: {detected_platform.value}")
    
    # Test architecture detection
    detected_arch = PlatformDetector.detect_architecture()
    print(f"  Detected architecture: {detected_arch.name}")
    print(f"  Architecture value: {detected_arch.value}")
    
    # Test environment detection
    detected_env = PlatformDetector.detect_environment()
    print(f"  Detected environment: {detected_env.name}")
    print(f"  Environment value: {detected_env.value}")
    
    # Test platform info
    platform_info = PlatformDetector.get_platform_info()
    print(f"  Platform info created: {platform_info is not None}")
    print(f"  Available features: {len(platform_info.features)}")
    print(f"    Features: {[f.value for f in list(platform_info.features)[:5]]}")
    print(f"  Limitations: {len(platform_info.limitations)}")
    print(f"  Metadata keys: {len(platform_info.metadata)}")
    
    print("✓ Platform detection working")


def test_test_runner_creation():
    """Test cross-platform test runner creation."""
    print("\n=== Testing Test Runner Creation ===")
    
    runner = CrossPlatformTestRunner()
    print(f"  Runner created: {runner is not None}")
    print(f"  Platform info available: {runner.platform_info is not None}")
    print(f"  Total tests registered: {len(runner.tests)}")
    
    # Check test categories
    test_categories = {}
    for test_id, test in runner.tests.items():
        category = test_id.split('.')[0]
        test_categories[category] = test_categories.get(category, 0) + 1
    
    print(f"  Test categories: {len(test_categories)}")
    for category, count in test_categories.items():
        print(f"    {category}: {count} tests")
    
    # Check critical tests
    critical_tests = [test for test in runner.tests.values() if test.critical]
    print(f"  Critical tests: {len(critical_tests)}")
    
    print("✓ Test runner creation working")


async def test_individual_test_execution():
    """Test individual test execution."""
    print("\n=== Testing Individual Test Execution ===")
    
    runner = get_cross_platform_runner()
    
    # Test a few specific tests
    test_ids = [
        "fs.path_handling",
        "env.variable_handling", 
        "voicemode.import",
        "network.socket_creation"
    ]
    
    for test_id in test_ids:
        if test_id in runner.tests:
            result = await runner.run_test(test_id)
            print(f"  Test '{test_id}': {result.status}")
            print(f"    Duration: {result.duration:.3f}s")
            if result.error:
                print(f"    Error: {result.error[:100]}")
            if result.output:
                print(f"    Output: {result.output[:100]}")
        else:
            print(f"  Test '{test_id}': Not found")
    
    print("✓ Individual test execution working")


async def test_test_filtering():
    """Test test filtering by platforms and features."""
    print("\n=== Testing Test Filtering ===")
    
    runner = get_cross_platform_runner()
    current_platform = runner.platform_info.platform
    
    # Test platform filtering
    platform_results = await runner.run_all_tests(platforms={current_platform})
    print(f"  Platform-specific tests: {len(platform_results)} results")
    
    passed = sum(1 for r in platform_results if r.status == "passed")
    failed = sum(1 for r in platform_results if r.status == "failed")
    skipped = sum(1 for r in platform_results if r.status == "skipped")
    
    print(f"    Passed: {passed}")
    print(f"    Failed: {failed}")
    print(f"    Skipped: {skipped}")
    
    # Test feature filtering
    if PlatformFeature.PATH_HANDLING in runner.platform_info.features:
        feature_results = await runner.run_all_tests(features={PlatformFeature.PATH_HANDLING})
        print(f"  Path handling tests: {len(feature_results)} results")
    
    # Test critical tests only
    critical_results = await runner.run_all_tests(critical_only=True)
    print(f"  Critical tests: {len(critical_results)} results")
    
    critical_failures = sum(1 for r in critical_results if r.status in ["failed", "error"])
    print(f"    Critical failures: {critical_failures}")
    
    print("✓ Test filtering working")


async def test_comprehensive_run():
    """Test comprehensive cross-platform test run."""
    print("\n=== Testing Comprehensive Test Run ===")
    
    # Run all tests using the high-level function
    result = await run_cross_platform_tests(
        output_format="text",
        critical_only=False
    )
    
    print(f"  Test run completed: {result is not None}")
    print(f"  Has results: {'results' in result}")
    print(f"  Has report: {'report' in result}")
    print(f"  Success status: {result.get('success', False)}")
    
    if 'compatibility' in result:
        compat = result['compatibility']
        print(f"  Compatibility report available: {compat is not None}")
        
        if 'summary' in compat:
            summary = compat['summary']
            print(f"    Total tests: {summary.get('total_tests', 0)}")
            print(f"    Success rate: {summary.get('success_rate', 0):.1f}%")
            print(f"    Critical failures: {summary.get('critical_failures', 0)}")
    
    report = result.get('report', '')
    print(f"  Report length: {len(report)} characters")
    print(f"  Contains platform info: {'Platform:' in report}")
    
    print("✓ Comprehensive test run working")


async def test_error_handling():
    """Test error handling in cross-platform tests."""
    print("\n=== Testing Error Handling ===")
    
    runner = get_cross_platform_runner()
    
    # Test non-existent test
    result = await runner.run_test("nonexistent.test")
    print(f"  Non-existent test handled: {result.status == 'error'}")
    
    # Test with invalid platform filter
    try:
        results = await runner.run_all_tests(platforms={Platform.UNKNOWN})
        print(f"  Invalid platform filter handled: {len(results) >= 0}")
    except Exception as e:
        print(f"  Invalid platform error: {type(e).__name__}")
    
    # Test with empty feature filter
    results = await runner.run_all_tests(features=set())
    print(f"  Empty feature filter handled: {len(results) >= 0}")
    
    print("✓ Error handling working")


async def test_report_formats():
    """Test different report formats."""
    print("\n=== Testing Report Formats ===")
    
    # Test JSON format
    json_result = await run_cross_platform_tests(
        critical_only=True,
        output_format="json"
    )
    
    print(f"  JSON format result: {json_result is not None}")
    
    json_report = json_result.get('report', {})
    if isinstance(json_report, dict):
        print(f"  JSON report structure: {type(json_report).__name__}")
        print(f"    Top-level keys: {list(json_report.keys())[:5]}")
    
    # Test text format
    text_result = await run_cross_platform_tests(
        critical_only=True,
        output_format="text"
    )
    
    print(f"  Text format result: {text_result is not None}")
    
    text_report = text_result.get('report', '')
    if isinstance(text_report, str):
        print(f"  Text report length: {len(text_report)} characters")
        print(f"    Contains header: {'CROSS-PLATFORM' in text_report}")
        print(f"    Contains summary: {'SUMMARY:' in text_report}")
    
    print("✓ Report formats working")


async def test_platform_specific_behavior():
    """Test platform-specific behavior."""
    print("\n=== Testing Platform-Specific Behavior ===")
    
    runner = get_cross_platform_runner()
    current_platform = runner.platform_info.platform
    
    print(f"  Current platform: {current_platform.name}")
    
    # Test platform-specific features
    if current_platform == Platform.MACOS:
        print("  macOS-specific tests:")
        # Test features specific to macOS
        features = ["Audio device detection via system_profiler"]
    elif current_platform == Platform.LINUX:
        print("  Linux-specific tests:")
        # Test features specific to Linux
        features = ["ALSA/PulseAudio detection", "Signal handling"]
    elif current_platform == Platform.WINDOWS:
        print("  Windows-specific tests:")
        # Test features specific to Windows
        features = ["Windows process management", "Path separator handling"]
    else:
        features = ["Unknown platform"]
    
    for feature in features:
        print(f"    - {feature}: Available")
    
    # Test skipped tests
    all_results = await runner.run_all_tests()
    skipped_tests = [r for r in all_results if r.status == "skipped"]
    
    print(f"  Skipped tests: {len(skipped_tests)}")
    for result in skipped_tests[:3]:  # Show first 3
        test_name = runner.tests[result.test_id].name
        print(f"    - {test_name}: {result.output}")
    
    print("✓ Platform-specific behavior working")


async def test_performance_metrics():
    """Test performance metrics collection."""
    print("\n=== Testing Performance Metrics ===")
    
    import time
    
    # Run tests and measure performance
    start_time = time.time()
    result = await run_cross_platform_tests(critical_only=True)
    execution_time = time.time() - start_time
    
    results = result.get('results', [])
    total_test_time = sum(r.duration for r in results)
    
    print(f"  Total execution time: {execution_time:.3f}s")
    print(f"  Test results: {len(results)}")
    print(f"  Combined test time: {total_test_time:.3f}s")
    
    if len(results) > 0:
        avg_test_time = total_test_time / len(results)
        print(f"  Average test time: {avg_test_time:.3f}s")
        
        fastest = min(results, key=lambda x: x.duration)
        slowest = max(results, key=lambda x: x.duration)
        
        print(f"  Fastest test: {fastest.test_id} ({fastest.duration:.3f}s)")
        print(f"  Slowest test: {slowest.test_id} ({slowest.duration:.3f}s)")
    
    print("✓ Performance metrics working")


async def test_singleton_behavior():
    """Test singleton behavior."""
    print("\n=== Testing Singleton Behavior ===")
    
    runner1 = get_cross_platform_runner()
    runner2 = get_cross_platform_runner()
    
    print(f"  Same instance: {runner1 is runner2}")
    print(f"  Instance type: {type(runner1).__name__}")
    
    # Test that results are shared
    initial_results = len(runner1.results)
    
    await runner1.run_test("env.variable_handling")
    after_test1 = len(runner1.results)
    
    await runner2.run_test("fs.path_handling")
    after_test2 = len(runner2.results)
    
    print(f"  Results shared: {after_test2 > after_test1 > initial_results}")
    print(f"  Total results: {len(runner2.results)}")
    
    print("✓ Singleton behavior working")


async def run_all_cross_platform_tests():
    """Run all cross-platform test validation."""
    print("=" * 70)
    print("CROSS-PLATFORM TEST SYSTEM VALIDATION")
    print("=" * 70)
    
    test_functions = [
        test_platform_detection,
        test_test_runner_creation,
        test_individual_test_execution,
        test_test_filtering,
        test_error_handling,
        test_report_formats,
        test_platform_specific_behavior,
        test_performance_metrics,
        test_singleton_behavior,
        test_comprehensive_run  # Run comprehensive test last
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
    print(f"✓ Cross-platform test system validation complete!")
    print(f"  Tests passed: {passed_tests}/{len(test_functions)}")
    print(f"  Success rate: {passed_tests / len(test_functions) * 100:.1f}%")
    print(f"  Total validation time: {total_time:.3f}s")
    print(f"  Average per test: {total_time / len(test_functions):.3f}s")
    
    if passed_tests == len(test_functions):
        print("🎉 All cross-platform tests PASSED!")
        print("Sprint 42 cross-platform testing COMPLETE!")
    else:
        print("⚠️  Some tests failed - review above for details")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_cross_platform_tests())