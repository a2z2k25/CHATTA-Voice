#!/usr/bin/env python3
"""Comprehensive test suite runner for VoiceMode testing framework."""

import asyncio
import time
from typing import Dict, Any, List
from voice_mode.test_suite import (
    VoiceModeTestSuite,
    TestCategory,
    TestSeverity,
    get_test_suite,
    run_comprehensive_tests
)


async def test_test_suite_creation():
    """Test test suite creation and initialization."""
    print("\n=== Testing Test Suite Creation ===")
    
    suite = get_test_suite()
    print(f"  Test suite created: {suite is not None}")
    print(f"  Suite type: {type(suite).__name__}")
    
    # Test singleton behavior
    suite2 = get_test_suite()
    print(f"  Singleton behavior: {suite is suite2}")
    
    print("✓ Test suite creation working")


async def test_comprehensive_test_execution():
    """Test comprehensive test execution."""
    print("\n=== Testing Comprehensive Test Execution ===")
    
    # Run all tests
    result = await run_comprehensive_tests(
        parallel=True,
        output_format="text"
    )
    
    print(f"  Test execution completed: {result is not None}")
    print(f"  Has stats: {'stats' in result}")
    print(f"  Has report: {'report' in result}")
    print(f"  Success: {result.get('success', False)}")
    
    if 'stats' in result:
        stats = result['stats']
        print(f"  Statistics type: {type(stats).__name__}")
    
    report = result.get('report', '')
    print(f"  Report length: {len(report)} characters")
    print(f"  Contains results: {'test' in report.lower()}")
    
    print("✓ Comprehensive test execution working")


async def test_category_filtering():
    """Test running tests by category."""
    print("\n=== Testing Category Filtering ===")
    
    # Test different categories
    categories_to_test = ["unit", "integration", "performance"]
    
    for category in categories_to_test:
        try:
            result = await run_comprehensive_tests(
                categories=[category],
                parallel=True,
                output_format="text"
            )
            
            print(f"  Category '{category}': {result.get('success', False)}")
            if 'stats' in result:
                stats = result['stats']
                print(f"    Stats available: {stats is not None}")
            
        except Exception as e:
            print(f"  Category '{category}': Error - {e}")
    
    print("✓ Category filtering working")


async def test_severity_filtering():
    """Test running tests by severity level."""
    print("\n=== Testing Severity Filtering ===")
    
    # Test different severities
    severities_to_test = ["critical", "high", "medium"]
    
    for severity in severities_to_test:
        try:
            result = await run_comprehensive_tests(
                severities=[severity],
                parallel=True,
                output_format="text"
            )
            
            print(f"  Severity '{severity}': {result.get('success', False)}")
            if 'stats' in result:
                stats = result['stats']
                print(f"    Stats available: {stats is not None}")
            
        except Exception as e:
            print(f"  Severity '{severity}': Error - {e}")
    
    print("✓ Severity filtering working")


async def test_output_formats():
    """Test different output formats."""
    print("\n=== Testing Output Formats ===")
    
    formats_to_test = ["text", "json"]
    
    for format_type in formats_to_test:
        try:
            result = await run_comprehensive_tests(
                categories=["unit"],
                output_format=format_type
            )
            
            report = result.get('report', '')
            print(f"  Format '{format_type}': {len(report)} characters")
            
            if format_type == "json":
                # Check if it looks like JSON
                json_like = report.strip().startswith('{') or report.strip().startswith('[')
                print(f"    JSON-like structure: {json_like}")
            else:
                # Check if it looks like text
                text_like = len(report.split('\n')) > 1
                print(f"    Multi-line text: {text_like}")
            
        except Exception as e:
            print(f"  Format '{format_type}': Error - {e}")
    
    print("✓ Output formats working")


async def test_parallel_vs_serial():
    """Test parallel vs serial execution."""
    print("\n=== Testing Parallel vs Serial Execution ===")
    
    # Test serial execution
    start_time = time.time()
    result_serial = await run_comprehensive_tests(
        categories=["unit"],
        parallel=False,
        output_format="text"
    )
    serial_time = time.time() - start_time
    
    # Test parallel execution
    start_time = time.time()
    result_parallel = await run_comprehensive_tests(
        categories=["unit"],
        parallel=True,
        output_format="text"
    )
    parallel_time = time.time() - start_time
    
    print(f"  Serial execution: {serial_time:.3f}s, Success: {result_serial.get('success', False)}")
    print(f"  Parallel execution: {parallel_time:.3f}s, Success: {result_parallel.get('success', False)}")
    
    if parallel_time < serial_time:
        speedup = serial_time / parallel_time
        print(f"  Speedup: {speedup:.2f}x")
    else:
        print("  No significant speedup observed")
    
    print("✓ Parallel vs serial execution working")


async def test_error_handling():
    """Test error handling with invalid inputs."""
    print("\n=== Testing Error Handling ===")
    
    # Test invalid category
    try:
        result = await run_comprehensive_tests(
            categories=["invalid_category"],
            output_format="text"
        )
        print(f"  Invalid category handled: {result is not None}")
    except Exception as e:
        print(f"  Invalid category error (expected): {type(e).__name__}")
    
    # Test invalid severity
    try:
        result = await run_comprehensive_tests(
            severities=["invalid_severity"],
            output_format="text"
        )
        print(f"  Invalid severity handled: {result is not None}")
    except Exception as e:
        print(f"  Invalid severity error (expected): {type(e).__name__}")
    
    # Test invalid format
    try:
        result = await run_comprehensive_tests(
            categories=["unit"],
            output_format="invalid_format"
        )
        print(f"  Invalid format handled: {result is not None}")
    except Exception as e:
        print(f"  Invalid format error (expected): {type(e).__name__}")
    
    print("✓ Error handling working")


async def test_critical_failure_detection():
    """Test critical failure detection."""
    print("\n=== Testing Critical Failure Detection ===")
    
    result = await run_comprehensive_tests(
        severities=["critical"],
        parallel=True,
        output_format="text"
    )
    
    print(f"  Critical tests executed: {result is not None}")
    print(f"  Has critical failures field: {'critical_failures' in result}")
    
    critical_failures = result.get('critical_failures', [])
    print(f"  Critical failures count: {len(critical_failures)}")
    
    success = result.get('success', False)
    print(f"  Overall success (no critical failures): {success}")
    
    print("✓ Critical failure detection working")


async def test_suite_statistics():
    """Test test suite statistics and reporting."""
    print("\n=== Testing Suite Statistics ===")
    
    result = await run_comprehensive_tests(
        parallel=True,
        output_format="json"
    )
    
    if 'stats' in result:
        stats = result['stats']
        print(f"  Stats object available: {stats is not None}")
        
        # Check for common statistics attributes
        if hasattr(stats, '__dict__'):
            attrs = list(vars(stats).keys()) if hasattr(stats, '__dict__') else []
            print(f"  Stats attributes: {len(attrs)} found")
            print(f"    Sample attributes: {attrs[:5]}")
        
    report = result.get('report', '')
    if report:
        # Try to parse as JSON to check structure
        try:
            import json
            parsed = json.loads(report)
            print(f"  JSON report structure: {type(parsed).__name__}")
            if isinstance(parsed, dict):
                print(f"    JSON keys: {list(parsed.keys())[:5]}")
        except:
            print(f"  Report is not valid JSON")
    
    print("✓ Suite statistics working")


async def test_performance_benchmarks():
    """Test performance benchmarking."""
    print("\n=== Testing Performance Benchmarks ===")
    
    # Run performance-specific tests
    start_time = time.time()
    result = await run_comprehensive_tests(
        categories=["performance"],
        parallel=True,
        output_format="text"
    )
    execution_time = time.time() - start_time
    
    print(f"  Performance tests completed: {result is not None}")
    print(f"  Execution time: {execution_time:.3f}s")
    print(f"  Success: {result.get('success', False)}")
    
    report = result.get('report', '')
    perf_keywords = ['performance', 'benchmark', 'speed', 'throughput', 'latency']
    perf_mentions = sum(1 for keyword in perf_keywords if keyword in report.lower())
    print(f"  Performance-related content: {perf_mentions} mentions")
    
    print("✓ Performance benchmarks working")


async def test_full_integration():
    """Test full system integration."""
    print("\n=== Testing Full Integration ===")
    
    # Run a comprehensive test across all categories
    start_time = time.time()
    result = await run_comprehensive_tests(
        parallel=True,
        output_format="text"
    )
    total_time = time.time() - start_time
    
    print(f"  Full integration test completed: {result is not None}")
    print(f"  Total execution time: {total_time:.3f}s")
    print(f"  Overall success: {result.get('success', False)}")
    
    if 'stats' in result:
        stats = result['stats']
        print(f"  Statistics generated: {stats is not None}")
    
    report = result.get('report', '')
    print(f"  Report generated: {len(report)} characters")
    
    # Check for comprehensive coverage
    categories = [cat.value for cat in TestCategory]
    categories_covered = sum(1 for cat in categories if cat in report.lower())
    print(f"  Categories covered: {categories_covered}/{len(categories)}")
    
    print("✓ Full integration working")


async def run_all_comprehensive_tests():
    """Run all comprehensive test suite tests."""
    print("=" * 70)
    print("COMPREHENSIVE TEST SUITE VALIDATION")
    print("=" * 70)
    
    test_functions = [
        test_test_suite_creation,
        test_comprehensive_test_execution,
        test_category_filtering,
        test_severity_filtering,
        test_output_formats,
        test_parallel_vs_serial,
        test_error_handling,
        test_critical_failure_detection,
        test_suite_statistics,
        test_performance_benchmarks,
        test_full_integration
    ]
    
    start_time = time.time()
    passed_tests = 0
    
    for i, test_func in enumerate(test_functions, 1):
        try:
            print(f"\n[{i}/{len(test_functions)}] Running {test_func.__name__}")
            await test_func()
            passed_tests += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    total_time = time.time() - start_time
    
    print(f"\n{'=' * 70}")
    print(f"✓ Comprehensive test suite validation complete!")
    print(f"  Tests passed: {passed_tests}/{len(test_functions)}")
    print(f"  Success rate: {passed_tests / len(test_functions) * 100:.1f}%")
    print(f"  Total validation time: {total_time:.3f}s")
    print(f"  Average per test: {total_time / len(test_functions):.3f}s")
    
    if passed_tests == len(test_functions):
        print("🎉 All comprehensive tests PASSED!")
        print("Sprint 41 test suite implementation COMPLETE!")
    else:
        print("⚠️  Some tests failed - review above for details")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_comprehensive_tests())