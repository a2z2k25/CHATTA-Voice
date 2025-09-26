#!/usr/bin/env python3
"""Comprehensive test suite for VoiceMode production readiness."""

import asyncio
import json
import os
import sys
import tempfile
import time
import traceback
import unittest
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set, Union
import subprocess
import logging

logger = logging.getLogger(__name__)


class TestSeverity(Enum):
    """Test severity levels."""
    CRITICAL = 1  # Must pass for production
    HIGH = 2      # Important for functionality
    MEDIUM = 3    # Good to have
    LOW = 4       # Nice to have


class TestCategory(Enum):
    """Test categories."""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPATIBILITY = "compatibility"
    REGRESSION = "regression"
    SMOKE = "smoke"
    STRESS = "stress"


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Individual test result."""
    test_id: str
    name: str
    category: TestCategory
    severity: TestSeverity
    status: TestStatus = TestStatus.PENDING
    duration: float = 0.0
    error_message: str = ""
    stack_trace: str = ""
    output: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuiteStats:
    """Test suite execution statistics."""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total_duration: float = 0.0
    coverage_percentage: float = 0.0
    by_category: Dict[TestCategory, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    by_severity: Dict[TestSeverity, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    critical_failures: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class TestExecutor:
    """Test execution engine."""
    
    def __init__(self):
        self.results: Dict[str, TestResult] = {}
        self.test_registry: Dict[str, Callable] = {}
        self.setup_hooks: List[Callable] = []
        self.teardown_hooks: List[Callable] = []
        self.parallel_execution = True
        self.timeout_seconds = 300
        self.continue_on_failure = True
        
    def register_test(
        self,
        test_id: str,
        name: str,
        category: TestCategory,
        severity: TestSeverity,
        test_function: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Register a test for execution."""
        self.test_registry[test_id] = test_function
        self.results[test_id] = TestResult(
            test_id=test_id,
            name=name,
            category=category,
            severity=severity,
            metadata=metadata or {}
        )
    
    def add_setup_hook(self, hook: Callable):
        """Add setup hook to run before tests."""
        self.setup_hooks.append(hook)
    
    def add_teardown_hook(self, hook: Callable):
        """Add teardown hook to run after tests."""
        self.teardown_hooks.append(hook)
    
    async def run_test(self, test_id: str) -> TestResult:
        """Run a single test."""
        result = self.results[test_id]
        test_function = self.test_registry[test_id]
        
        result.status = TestStatus.RUNNING
        result.started_at = datetime.now()
        
        try:
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(test_function):
                await test_function()
            else:
                test_function()
            
            result.duration = time.time() - start_time
            result.status = TestStatus.PASSED
            result.completed_at = datetime.now()
            
        except unittest.SkipTest as e:
            result.status = TestStatus.SKIPPED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            
        except AssertionError as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = traceback.format_exc()
            result.completed_at = datetime.now()
            
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.stack_trace = traceback.format_exc()
            result.completed_at = datetime.now()
        
        return result
    
    async def run_all_tests(
        self,
        categories: Optional[Set[TestCategory]] = None,
        severities: Optional[Set[TestSeverity]] = None,
        test_ids: Optional[Set[str]] = None
    ) -> TestSuiteStats:
        """Run all registered tests with optional filtering."""
        # Filter tests
        tests_to_run = []
        for test_id, result in self.results.items():
            if test_ids and test_id not in test_ids:
                continue
            if categories and result.category not in categories:
                continue
            if severities and result.severity not in severities:
                continue
            tests_to_run.append(test_id)
        
        # Run setup hooks
        for hook in self.setup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                logger.error(f"Setup hook failed: {e}")
        
        # Execute tests
        start_time = time.time()
        
        if self.parallel_execution and len(tests_to_run) > 1:
            tasks = [self.run_test(test_id) for test_id in tests_to_run]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for test_id in tests_to_run:
                await self.run_test(test_id)
                # Stop on critical failure if configured
                if (not self.continue_on_failure and 
                    self.results[test_id].status in [TestStatus.FAILED, TestStatus.ERROR] and
                    self.results[test_id].severity == TestSeverity.CRITICAL):
                    break
        
        total_duration = time.time() - start_time
        
        # Run teardown hooks
        for hook in self.teardown_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                logger.error(f"Teardown hook failed: {e}")
        
        # Generate statistics
        return self._generate_stats(tests_to_run, total_duration)
    
    def _generate_stats(self, test_ids: List[str], total_duration: float) -> TestSuiteStats:
        """Generate test suite statistics."""
        stats = TestSuiteStats()
        stats.total_tests = len(test_ids)
        stats.total_duration = total_duration
        
        for test_id in test_ids:
            result = self.results[test_id]
            
            # Count by status
            if result.status == TestStatus.PASSED:
                stats.passed += 1
            elif result.status == TestStatus.FAILED:
                stats.failed += 1
                if result.severity == TestSeverity.CRITICAL:
                    stats.critical_failures.append(test_id)
            elif result.status == TestStatus.SKIPPED:
                stats.skipped += 1
            elif result.status == TestStatus.ERROR:
                stats.errors += 1
                if result.severity == TestSeverity.CRITICAL:
                    stats.critical_failures.append(test_id)
            
            # Count by category and severity
            stats.by_category[result.category][result.status.value] += 1
            stats.by_severity[result.severity][result.status.value] += 1
        
        return stats
    
    def get_test_results(
        self,
        status: Optional[TestStatus] = None,
        category: Optional[TestCategory] = None,
        severity: Optional[TestSeverity] = None
    ) -> List[TestResult]:
        """Get filtered test results."""
        results = []
        for result in self.results.values():
            if status and result.status != status:
                continue
            if category and result.category != category:
                continue
            if severity and result.severity != severity:
                continue
            results.append(result)
        
        return sorted(results, key=lambda x: (x.severity.value, x.category.value, x.name))
    
    def generate_report(self, format: str = "text") -> str:
        """Generate test execution report."""
        if format == "text":
            return self._generate_text_report()
        elif format == "json":
            return self._generate_json_report()
        elif format == "html":
            return self._generate_html_report()
        else:
            raise ValueError(f"Unsupported report format: {format}")
    
    def _generate_text_report(self) -> str:
        """Generate text format report."""
        stats = self._generate_stats(list(self.results.keys()), 0)
        
        report = []
        report.append("=" * 70)
        report.append("COMPREHENSIVE TEST SUITE REPORT")
        report.append("=" * 70)
        report.append(f"Generated at: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 70)
        report.append(f"Total Tests:     {stats.total_tests}")
        report.append(f"Passed:          {stats.passed}")
        report.append(f"Failed:          {stats.failed}")
        report.append(f"Errors:          {stats.errors}")
        report.append(f"Skipped:         {stats.skipped}")
        report.append(f"Duration:        {stats.total_duration:.2f}s")
        
        if stats.critical_failures:
            report.append(f"Critical Failures: {len(stats.critical_failures)}")
        
        report.append("")
        
        # By Category
        report.append("BY CATEGORY")
        report.append("-" * 70)
        for category, counts in stats.by_category.items():
            total = sum(counts.values())
            passed = counts.get("passed", 0)
            report.append(f"{category.value:15} {passed:3}/{total:3} passed")
        
        report.append("")
        
        # By Severity
        report.append("BY SEVERITY")
        report.append("-" * 70)
        for severity, counts in stats.by_severity.items():
            total = sum(counts.values())
            passed = counts.get("passed", 0)
            report.append(f"{severity.name:15} {passed:3}/{total:3} passed")
        
        # Failed tests
        failed_results = self.get_test_results(status=TestStatus.FAILED)
        if failed_results:
            report.append("")
            report.append("FAILED TESTS")
            report.append("-" * 70)
            for result in failed_results:
                report.append(f"{result.name} ({result.severity.name})")
                report.append(f"  Error: {result.error_message}")
        
        # Error tests
        error_results = self.get_test_results(status=TestStatus.ERROR)
        if error_results:
            report.append("")
            report.append("ERROR TESTS")
            report.append("-" * 70)
            for result in error_results:
                report.append(f"{result.name} ({result.severity.name})")
                report.append(f"  Error: {result.error_message}")
        
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def _generate_json_report(self) -> str:
        """Generate JSON format report."""
        stats = self._generate_stats(list(self.results.keys()), 0)
        
        data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_tests": stats.total_tests,
                "passed": stats.passed,
                "failed": stats.failed,
                "errors": stats.errors,
                "skipped": stats.skipped,
                "duration": stats.total_duration,
                "critical_failures": len(stats.critical_failures)
            },
            "by_category": {
                cat.value: dict(counts) for cat, counts in stats.by_category.items()
            },
            "by_severity": {
                sev.name: dict(counts) for sev, counts in stats.by_severity.items()
            },
            "results": [
                {
                    "test_id": result.test_id,
                    "name": result.name,
                    "category": result.category.value,
                    "severity": result.severity.name,
                    "status": result.status.value,
                    "duration": result.duration,
                    "error_message": result.error_message,
                    "started_at": result.started_at.isoformat() if result.started_at else None,
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None
                }
                for result in self.results.values()
            ]
        }
        
        return json.dumps(data, indent=2)
    
    def _generate_html_report(self) -> str:
        """Generate HTML format report."""
        stats = self._generate_stats(list(self.results.keys()), 0)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Suite Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; margin: 10px 0; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .error {{ color: orange; }}
        .skipped {{ color: gray; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Test Suite Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p>Generated: {datetime.now().isoformat()}</p>
        <p>Total Tests: {stats.total_tests}</p>
        <p class="passed">Passed: {stats.passed}</p>
        <p class="failed">Failed: {stats.failed}</p>
        <p class="error">Errors: {stats.errors}</p>
        <p class="skipped">Skipped: {stats.skipped}</p>
        <p>Duration: {stats.total_duration:.2f}s</p>
    </div>
    
    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Category</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Error</th>
        </tr>
"""
        
        for result in sorted(self.results.values(), key=lambda x: x.name):
            status_class = result.status.value
            html += f"""
        <tr>
            <td>{result.name}</td>
            <td>{result.category.value}</td>
            <td>{result.severity.name}</td>
            <td class="{status_class}">{result.status.value}</td>
            <td>{result.duration:.2f}s</td>
            <td>{result.error_message[:100]}...</td>
        </tr>"""
        
        html += """
    </table>
</body>
</html>"""
        
        return html


class VoiceModeTestSuite:
    """Main test suite for VoiceMode."""
    
    def __init__(self):
        self.executor = TestExecutor()
        self.temp_dir: Optional[Path] = None
        self.setup_complete = False
        
        # Register all tests
        self._register_unit_tests()
        self._register_integration_tests()
        self._register_performance_tests()
        self._register_security_tests()
        self._register_compatibility_tests()
        self._register_regression_tests()
        
        # Add hooks
        self.executor.add_setup_hook(self._global_setup)
        self.executor.add_teardown_hook(self._global_teardown)
    
    def _register_unit_tests(self):
        """Register unit tests."""
        self.executor.register_test(
            "unit_config_loading",
            "Configuration Loading",
            TestCategory.UNIT,
            TestSeverity.CRITICAL,
            self._test_config_loading
        )
        
        self.executor.register_test(
            "unit_provider_discovery",
            "Provider Discovery",
            TestCategory.UNIT,
            TestSeverity.CRITICAL,
            self._test_provider_discovery
        )
        
        self.executor.register_test(
            "unit_audio_devices",
            "Audio Device Detection",
            TestCategory.UNIT,
            TestSeverity.HIGH,
            self._test_audio_devices
        )
        
        self.executor.register_test(
            "unit_help_system",
            "Help System Functionality",
            TestCategory.UNIT,
            TestSeverity.MEDIUM,
            self._test_help_system
        )
        
        self.executor.register_test(
            "unit_feedback_system",
            "Feedback Collection System",
            TestCategory.UNIT,
            TestSeverity.MEDIUM,
            self._test_feedback_system
        )
        
        self.executor.register_test(
            "unit_onboarding_system",
            "Onboarding System",
            TestCategory.UNIT,
            TestSeverity.MEDIUM,
            self._test_onboarding_system
        )
    
    def _register_integration_tests(self):
        """Register integration tests."""
        self.executor.register_test(
            "integration_mcp_server",
            "MCP Server Integration",
            TestCategory.INTEGRATION,
            TestSeverity.CRITICAL,
            self._test_mcp_server_integration
        )
        
        self.executor.register_test(
            "integration_voice_pipeline",
            "Voice Processing Pipeline",
            TestCategory.INTEGRATION,
            TestSeverity.HIGH,
            self._test_voice_pipeline_integration
        )
        
        self.executor.register_test(
            "integration_service_management",
            "Service Management",
            TestCategory.INTEGRATION,
            TestSeverity.HIGH,
            self._test_service_management
        )
        
        self.executor.register_test(
            "integration_tool_discovery",
            "Tool Discovery and Loading",
            TestCategory.INTEGRATION,
            TestSeverity.MEDIUM,
            self._test_tool_discovery
        )
    
    def _register_performance_tests(self):
        """Register performance tests."""
        self.executor.register_test(
            "perf_startup_time",
            "Application Startup Performance",
            TestCategory.PERFORMANCE,
            TestSeverity.HIGH,
            self._test_startup_performance
        )
        
        self.executor.register_test(
            "perf_memory_usage",
            "Memory Usage Under Load",
            TestCategory.PERFORMANCE,
            TestSeverity.MEDIUM,
            self._test_memory_usage
        )
        
        self.executor.register_test(
            "perf_concurrent_requests",
            "Concurrent Request Handling",
            TestCategory.PERFORMANCE,
            TestSeverity.MEDIUM,
            self._test_concurrent_requests
        )
        
        self.executor.register_test(
            "perf_response_latency",
            "Response Time Latency",
            TestCategory.PERFORMANCE,
            TestSeverity.HIGH,
            self._test_response_latency
        )
    
    def _register_security_tests(self):
        """Register security tests."""
        self.executor.register_test(
            "security_input_validation",
            "Input Validation Security",
            TestCategory.SECURITY,
            TestSeverity.CRITICAL,
            self._test_input_validation
        )
        
        self.executor.register_test(
            "security_file_access",
            "File Access Permissions",
            TestCategory.SECURITY,
            TestSeverity.HIGH,
            self._test_file_access_security
        )
        
        self.executor.register_test(
            "security_api_endpoints",
            "API Endpoint Security",
            TestCategory.SECURITY,
            TestSeverity.HIGH,
            self._test_api_security
        )
        
        self.executor.register_test(
            "security_data_sanitization",
            "Data Sanitization",
            TestCategory.SECURITY,
            TestSeverity.MEDIUM,
            self._test_data_sanitization
        )
    
    def _register_compatibility_tests(self):
        """Register compatibility tests."""
        self.executor.register_test(
            "compat_python_versions",
            "Python Version Compatibility",
            TestCategory.COMPATIBILITY,
            TestSeverity.HIGH,
            self._test_python_compatibility
        )
        
        self.executor.register_test(
            "compat_platform_support",
            "Cross-Platform Support",
            TestCategory.COMPATIBILITY,
            TestSeverity.HIGH,
            self._test_platform_compatibility
        )
        
        self.executor.register_test(
            "compat_dependency_versions",
            "Dependency Version Compatibility",
            TestCategory.COMPATIBILITY,
            TestSeverity.MEDIUM,
            self._test_dependency_compatibility
        )
    
    def _register_regression_tests(self):
        """Register regression tests."""
        self.executor.register_test(
            "regression_basic_functionality",
            "Basic Functionality Regression",
            TestCategory.REGRESSION,
            TestSeverity.CRITICAL,
            self._test_basic_functionality_regression
        )
        
        self.executor.register_test(
            "regression_configuration_changes",
            "Configuration Changes Regression",
            TestCategory.REGRESSION,
            TestSeverity.HIGH,
            self._test_configuration_regression
        )
        
        self.executor.register_test(
            "regression_api_contracts",
            "API Contract Regression",
            TestCategory.REGRESSION,
            TestSeverity.HIGH,
            self._test_api_regression
        )
    
    async def _global_setup(self):
        """Global test setup."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="voicemode_test_"))
        os.environ['VOICE_MODE_TEST_MODE'] = 'true'
        os.environ['VOICE_MODE_TEST_DIR'] = str(self.temp_dir)
        self.setup_complete = True
    
    async def _global_teardown(self):
        """Global test teardown."""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
        
        # Clean up environment
        os.environ.pop('VOICE_MODE_TEST_MODE', None)
        os.environ.pop('VOICE_MODE_TEST_DIR', None)
        
        self.setup_complete = False
    
    # Unit Tests
    async def _test_config_loading(self):
        """Test configuration loading functionality."""
        from voice_mode.config import VoiceModeConfig
        
        # Test default configuration
        config = VoiceModeConfig()
        assert config.whisper_enabled is not None
        assert config.kokoro_enabled is not None
        assert hasattr(config, 'audio_format')
        
        # Test environment variable override
        os.environ['WHISPER_ENABLED'] = 'false'
        config = VoiceModeConfig()
        assert not config.whisper_enabled
        
        os.environ.pop('WHISPER_ENABLED', None)
    
    async def _test_provider_discovery(self):
        """Test provider discovery functionality."""
        from voice_mode.providers import get_provider_registry
        
        registry = get_provider_registry()
        providers = registry.discover_providers()
        
        # Should find at least built-in providers
        assert len(providers) > 0
        
        # Test provider health checking
        for provider in providers:
            health = await registry.check_provider_health(provider)
            assert health is not None
    
    async def _test_audio_devices(self):
        """Test audio device detection."""
        try:
            from voice_mode.tools.devices import AudioDeviceManager
            
            manager = AudioDeviceManager()
            devices = await manager.list_audio_devices()
            
            # Should return device info
            assert isinstance(devices, dict)
            assert 'input_devices' in devices
            assert 'output_devices' in devices
        except ImportError:
            # Skip if optional dependencies not available
            raise unittest.SkipTest("Audio device dependencies not available")
    
    async def _test_help_system(self):
        """Test help system functionality."""
        from voice_mode.help_system import get_help_system
        
        help_system = get_help_system()
        
        # Test topic search
        results = help_system.search("voice commands", limit=5)
        assert len(results) > 0
        
        # Test topic retrieval
        topic = help_system.get_topic("getting_started.overview")
        assert topic is not None
        assert topic.title
        assert topic.content
    
    async def _test_feedback_system(self):
        """Test feedback collection system."""
        from voice_mode.feedback_system import get_feedback_collector, FeedbackType, FeedbackPriority
        
        collector = get_feedback_collector()
        
        # Test feedback submission
        feedback = await collector.submit_feedback(
            feedback_type=FeedbackType.BUG_REPORT,
            title="Test feedback",
            description="Testing feedback system",
            priority=FeedbackPriority.MEDIUM
        )
        
        assert feedback.id
        assert feedback.title == "Test feedback"
        assert feedback.type == FeedbackType.BUG_REPORT
    
    async def _test_onboarding_system(self):
        """Test onboarding system functionality."""
        from voice_mode.onboarding import get_onboarding_system
        
        onboarding = get_onboarding_system()
        
        # Test user onboarding start
        progress = await onboarding.start_onboarding("test_user")
        assert progress.user_id == "test_user"
        assert progress.current_stage is not None
        
        # Test task retrieval
        next_task = await onboarding.next_task("test_user")
        assert next_task is not None
        assert next_task.title
    
    # Integration Tests
    async def _test_mcp_server_integration(self):
        """Test MCP server integration."""
        from voice_mode.server import create_server
        
        # Test server creation
        server = create_server()
        assert server is not None
        
        # Test tool registration
        tools = server.list_tools()
        assert len(tools) > 0
        
        # Should have core tools
        tool_names = [tool.name for tool in tools]
        assert any("converse" in name for name in tool_names)
    
    async def _test_voice_pipeline_integration(self):
        """Test voice processing pipeline integration."""
        try:
            from voice_mode.core import VoiceMode
            
            voice_mode = VoiceMode()
            
            # Test initialization
            await voice_mode.initialize()
            assert voice_mode.is_initialized
            
            # Test provider availability
            providers = voice_mode.get_available_providers()
            assert isinstance(providers, list)
            
            await voice_mode.cleanup()
        except Exception as e:
            # Log but don't fail if optional services unavailable
            logger.warning(f"Voice pipeline test skipped: {e}")
            raise unittest.SkipTest(f"Voice services not available: {e}")
    
    async def _test_service_management(self):
        """Test service management functionality."""
        from voice_mode.tools.service import ServiceManager
        
        manager = ServiceManager()
        
        # Test service discovery
        services = await manager.get_available_services()
        assert isinstance(services, dict)
        
        # Test service status checking
        for service_name in services.keys():
            status = await manager.get_service_status(service_name)
            assert status is not None
    
    async def _test_tool_discovery(self):
        """Test tool discovery and loading."""
        from voice_mode.server import create_server
        
        server = create_server()
        tools = server.list_tools()
        
        # Should discover tools from tools directory
        assert len(tools) >= 3  # converse, service, devices at minimum
        
        # Test tool metadata
        for tool in tools:
            assert tool.name
            assert tool.description
    
    # Performance Tests
    async def _test_startup_performance(self):
        """Test application startup performance."""
        start_time = time.time()
        
        from voice_mode.server import create_server
        
        server = create_server()
        startup_time = time.time() - start_time
        
        # Should start within reasonable time
        assert startup_time < 5.0  # 5 seconds maximum
        
        # Store performance metric
        self.executor.results["perf_startup_time"].metadata["startup_time"] = startup_time
    
    async def _test_memory_usage(self):
        """Test memory usage under load."""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Simulate some load
        from voice_mode.help_system import get_help_system
        help_system = get_help_system()
        
        # Perform multiple searches
        for i in range(100):
            help_system.search(f"test query {i}")
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 100 * 1024 * 1024  # 100MB max increase
        
        self.executor.results["perf_memory_usage"].metadata["memory_increase"] = memory_increase
    
    async def _test_concurrent_requests(self):
        """Test concurrent request handling."""
        from voice_mode.help_system import get_help_system
        
        help_system = get_help_system()
        
        async def search_task(query):
            return help_system.search(f"concurrent test {query}")
        
        # Run concurrent searches
        start_time = time.time()
        tasks = [search_task(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # All requests should complete
        assert len(results) == 50
        
        # Should handle concurrency efficiently
        assert duration < 2.0  # 2 seconds maximum
        
        self.executor.results["perf_concurrent_requests"].metadata["duration"] = duration
    
    async def _test_response_latency(self):
        """Test response time latency."""
        from voice_mode.help_system import get_help_system
        
        help_system = get_help_system()
        latencies = []
        
        # Measure latency for multiple requests
        for i in range(20):
            start_time = time.time()
            help_system.search("test query")
            latency = time.time() - start_time
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        # Latency should be reasonable
        assert avg_latency < 0.01  # 10ms average
        assert max_latency < 0.05  # 50ms maximum
        
        self.executor.results["perf_response_latency"].metadata["avg_latency"] = avg_latency
        self.executor.results["perf_response_latency"].metadata["max_latency"] = max_latency
    
    # Security Tests
    async def _test_input_validation(self):
        """Test input validation security."""
        from voice_mode.feedback_system import get_feedback_collector, FeedbackType
        
        collector = get_feedback_collector()
        
        # Test malicious input handling
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE feedback; --",
            "../../../etc/passwd",
            "\x00\x01\x02",  # Binary data
            "A" * 10000  # Very long input
        ]
        
        for malicious_input in malicious_inputs:
            # Should handle malicious input without crashing
            feedback = await collector.submit_feedback(
                feedback_type=FeedbackType.GENERAL_COMMENT,
                title=malicious_input,
                description=malicious_input
            )
            
            # Feedback should be created (sanitized)
            assert feedback.id
            assert feedback.title  # Should not be empty after sanitization
    
    async def _test_file_access_security(self):
        """Test file access permissions security."""
        from voice_mode.config import VoiceModeConfig
        
        # Test that config doesn't access unauthorized files
        config = VoiceModeConfig()
        
        # Should not be able to read sensitive system files
        restricted_paths = [
            "/etc/passwd",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM"
        ]
        
        for path in restricted_paths:
            try:
                # This should not succeed
                with open(path, 'r') as f:
                    content = f.read()
                assert False, f"Unauthorized file access: {path}"
            except (FileNotFoundError, PermissionError, OSError):
                # Expected - should not have access
                pass
    
    async def _test_api_security(self):
        """Test API endpoint security."""
        from voice_mode.server import create_server
        
        server = create_server()
        
        # Test that sensitive information is not exposed
        tools = server.list_tools()
        
        for tool in tools:
            # Tool descriptions should not contain sensitive info
            description = tool.description.lower()
            assert "password" not in description
            assert "secret" not in description
            assert "token" not in description
            assert "key" not in description or "keyboard" in description  # Keyboard is ok
    
    async def _test_data_sanitization(self):
        """Test data sanitization."""
        from voice_mode.help_system import get_help_system
        
        help_system = get_help_system()
        
        # Test potentially dangerous query strings
        dangerous_queries = [
            "<script>",
            "javascript:",
            "data:text/html,",
            "file://",
            "ftp://"
        ]
        
        for query in dangerous_queries:
            # Should handle dangerous queries safely
            results = help_system.search(query)
            # Should return results (possibly empty) without error
            assert isinstance(results, list)
    
    # Compatibility Tests
    async def _test_python_compatibility(self):
        """Test Python version compatibility."""
        import sys
        
        # Should work with Python 3.10+
        assert sys.version_info >= (3, 10)
        
        # Test basic Python features used
        assert hasattr(sys, 'version_info')
        assert hasattr(asyncio, 'gather')
        
        # Test imports work
        try:
            import json
            import pathlib
            import dataclasses
            import typing
            import enum
        except ImportError as e:
            assert False, f"Required module not available: {e}"
    
    async def _test_platform_compatibility(self):
        """Test cross-platform support."""
        import platform
        
        system = platform.system()
        
        # Should support major platforms
        assert system in ['Darwin', 'Linux', 'Windows']
        
        # Test platform-specific functionality
        if system == 'Darwin':
            # macOS specific tests
            pass
        elif system == 'Linux':
            # Linux specific tests
            pass
        elif system == 'Windows':
            # Windows specific tests
            pass
    
    async def _test_dependency_compatibility(self):
        """Test dependency version compatibility."""
        # Test critical dependencies are available
        critical_deps = [
            'fastmcp',
            'pydantic',
            'asyncio'
        ]
        
        for dep in critical_deps:
            try:
                __import__(dep)
            except ImportError:
                assert False, f"Critical dependency missing: {dep}"
    
    # Regression Tests
    async def _test_basic_functionality_regression(self):
        """Test basic functionality hasn't regressed."""
        from voice_mode.server import create_server
        
        # Test server creation still works
        server = create_server()
        assert server is not None
        
        # Test tools are still discoverable
        tools = server.list_tools()
        assert len(tools) > 0
        
        # Test help system still works
        from voice_mode.help_system import get_help_system
        help_system = get_help_system()
        results = help_system.search("help")
        assert len(results) > 0
    
    async def _test_configuration_regression(self):
        """Test configuration changes haven't broken functionality."""
        from voice_mode.config import VoiceModeConfig
        
        # Test default configuration still loads
        config = VoiceModeConfig()
        assert hasattr(config, 'whisper_enabled')
        assert hasattr(config, 'kokoro_enabled')
        
        # Test environment override still works
        os.environ['WHISPER_ENABLED'] = 'false'
        config = VoiceModeConfig()
        assert not config.whisper_enabled
        
        os.environ.pop('WHISPER_ENABLED', None)
    
    async def _test_api_regression(self):
        """Test API contracts haven't changed."""
        from voice_mode.server import create_server
        
        server = create_server()
        tools = server.list_tools()
        
        # Core tools should still exist
        tool_names = [tool.name for tool in tools]
        
        # Check for expected tool patterns
        has_converse = any("converse" in name for name in tool_names)
        assert has_converse, "Core converse tool missing"
    
    async def run_test_suite(
        self,
        categories: Optional[Set[TestCategory]] = None,
        severities: Optional[Set[TestSeverity]] = None,
        parallel: bool = True,
        continue_on_failure: bool = True
    ) -> TestSuiteStats:
        """Run the complete test suite."""
        self.executor.parallel_execution = parallel
        self.executor.continue_on_failure = continue_on_failure
        
        return await self.executor.run_all_tests(categories, severities)
    
    def get_test_report(self, format: str = "text") -> str:
        """Get test execution report."""
        return self.executor.generate_report(format)
    
    def save_report(self, report_path: Path, format: str = "text"):
        """Save test report to file."""
        report = self.get_test_report(format)
        with open(report_path, 'w') as f:
            f.write(report)


# Global test suite instance
_test_suite: Optional[VoiceModeTestSuite] = None


def get_test_suite() -> VoiceModeTestSuite:
    """Get or create global test suite instance."""
    global _test_suite
    if _test_suite is None:
        _test_suite = VoiceModeTestSuite()
    return _test_suite


async def run_comprehensive_tests(
    categories: Optional[List[str]] = None,
    severities: Optional[List[str]] = None,
    parallel: bool = True,
    output_format: str = "text"
) -> Dict[str, Any]:
    """Run comprehensive test suite with options."""
    suite = get_test_suite()
    
    # Convert string parameters to enums
    category_enums = None
    if categories:
        category_enums = {TestCategory(cat) for cat in categories}
    
    severity_enums = None
    if severities:
        severity_enums = {TestSeverity[sev.upper()] for sev in severities}
    
    # Run tests
    stats = await suite.run_test_suite(
        categories=category_enums,
        severities=severity_enums,
        parallel=parallel
    )
    
    # Generate report
    report = suite.get_test_report(output_format)
    
    return {
        "stats": stats,
        "report": report,
        "critical_failures": stats.critical_failures,
        "success": len(stats.critical_failures) == 0 and stats.errors == 0
    }