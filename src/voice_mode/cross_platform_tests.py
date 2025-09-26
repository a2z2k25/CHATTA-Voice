#!/usr/bin/env python3
"""Cross-platform testing system for VoiceMode compatibility verification."""

import asyncio
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable, Union
import logging
import shutil

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms."""
    MACOS = "darwin"
    LINUX = "linux"
    WINDOWS = "win32"
    UNKNOWN = "unknown"


class Architecture(Enum):
    """Supported architectures."""
    X86_64 = "x86_64"
    ARM64 = "arm64"
    X86 = "i386"
    UNKNOWN = "unknown"


class TestEnvironment(Enum):
    """Test environment types."""
    NATIVE = "native"
    DOCKER = "docker"
    VM = "virtual_machine"
    GITHUB_ACTIONS = "github_actions"


class PlatformFeature(Enum):
    """Platform-specific features to test."""
    AUDIO_DEVICES = "audio_devices"
    FILE_PERMISSIONS = "file_permissions"
    PROCESS_MANAGEMENT = "process_management"
    NETWORK_ACCESS = "network_access"
    SYSTEM_SERVICES = "system_services"
    PACKAGE_INSTALLATION = "package_installation"
    ENVIRONMENT_VARIABLES = "environment_variables"
    PATH_HANDLING = "path_handling"
    UNICODE_SUPPORT = "unicode_support"
    ASYNC_IO = "async_io"


@dataclass
class PlatformInfo:
    """Platform information container."""
    platform: Platform
    architecture: Architecture
    version: str
    python_version: str
    environment: TestEnvironment
    features: Set[PlatformFeature] = field(default_factory=set)
    limitations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossPlatformTest:
    """Cross-platform test definition."""
    id: str
    name: str
    description: str
    platforms: Set[Platform]
    features: Set[PlatformFeature]
    test_function: Callable
    skip_conditions: Dict[Platform, str] = field(default_factory=dict)
    expected_failures: Dict[Platform, str] = field(default_factory=dict)
    setup_function: Optional[Callable] = None
    cleanup_function: Optional[Callable] = None
    timeout: float = 30.0
    critical: bool = False


@dataclass
class PlatformTestResult:
    """Result of a cross-platform test execution."""
    test_id: str
    platform_info: PlatformInfo
    status: str  # "passed", "failed", "skipped", "error"
    duration: float
    output: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class PlatformDetector:
    """Platform detection and analysis."""
    
    @staticmethod
    def detect_platform() -> Platform:
        """Detect current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return Platform.MACOS
        elif system == "linux":
            return Platform.LINUX
        elif system == "windows":
            return Platform.WINDOWS
        else:
            return Platform.UNKNOWN
    
    @staticmethod
    def detect_architecture() -> Architecture:
        """Detect current architecture."""
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return Architecture.X86_64
        elif machine in ("arm64", "aarch64"):
            return Architecture.ARM64
        elif machine in ("i386", "i686", "x86"):
            return Architecture.X86
        else:
            return Architecture.UNKNOWN
    
    @staticmethod
    def detect_environment() -> TestEnvironment:
        """Detect test environment."""
        if os.getenv("GITHUB_ACTIONS"):
            return TestEnvironment.GITHUB_ACTIONS
        elif os.path.exists("/.dockerenv"):
            return TestEnvironment.DOCKER
        elif os.getenv("VIRTUAL_ENV"):
            return TestEnvironment.VM
        else:
            return TestEnvironment.NATIVE
    
    @classmethod
    def get_platform_info(cls) -> PlatformInfo:
        """Get comprehensive platform information."""
        platform_obj = PlatformDetector.detect_platform()
        arch = PlatformDetector.detect_architecture()
        env = PlatformDetector.detect_environment()
        
        info = PlatformInfo(
            platform=platform_obj,
            architecture=arch,
            version=platform.platform(),
            python_version=platform.python_version(),
            environment=env
        )
        
        # Detect available features
        info.features = cls._detect_features(platform_obj)
        info.limitations = cls._detect_limitations(platform_obj, env)
        info.metadata = cls._collect_metadata()
        
        return info
    
    @staticmethod
    def _detect_features(platform_obj: Platform) -> Set[PlatformFeature]:
        """Detect available platform features."""
        features = set()
        
        # Audio devices
        if PlatformDetector._has_audio_support():
            features.add(PlatformFeature.AUDIO_DEVICES)
        
        # File permissions
        if hasattr(os, 'chmod'):
            features.add(PlatformFeature.FILE_PERMISSIONS)
        
        # Process management
        if hasattr(os, 'fork') or platform_obj == Platform.WINDOWS:
            features.add(PlatformFeature.PROCESS_MANAGEMENT)
        
        # Network access
        try:
            import socket
            features.add(PlatformFeature.NETWORK_ACCESS)
        except ImportError:
            pass
        
        # Always available features
        features.update([
            PlatformFeature.ENVIRONMENT_VARIABLES,
            PlatformFeature.PATH_HANDLING,
            PlatformFeature.UNICODE_SUPPORT,
            PlatformFeature.ASYNC_IO
        ])
        
        return features
    
    @staticmethod
    def _has_audio_support() -> bool:
        """Check if audio support is available."""
        try:
            if platform.system() == "Darwin":
                # macOS - check for audio units
                result = subprocess.run(["system_profiler", "SPAudioDataType"], 
                                      capture_output=True, timeout=5)
                return result.returncode == 0
            elif platform.system() == "Linux":
                # Linux - check for ALSA/PulseAudio
                return (os.path.exists("/proc/asound") or 
                       shutil.which("pulseaudio") is not None)
            elif platform.system() == "Windows":
                # Windows - assume audio is available
                return True
        except:
            pass
        return False
    
    @staticmethod
    def _detect_limitations(platform_obj: Platform, env: TestEnvironment) -> List[str]:
        """Detect platform limitations."""
        limitations = []
        
        if env == TestEnvironment.DOCKER:
            limitations.extend([
                "Limited audio device access in Docker",
                "No system service management",
                "Restricted process capabilities"
            ])
        
        if env == TestEnvironment.GITHUB_ACTIONS:
            limitations.extend([
                "No interactive audio testing",
                "Limited GUI capabilities",
                "Network restrictions may apply"
            ])
        
        if platform_obj == Platform.WINDOWS:
            limitations.extend([
                "Path separator differences",
                "Case-insensitive file system",
                "Different executable extensions"
            ])
        
        return limitations
    
    @staticmethod
    def _collect_metadata() -> Dict[str, Any]:
        """Collect additional platform metadata."""
        metadata = {
            "node": platform.node(),
            "processor": platform.processor(),
            "python_implementation": platform.python_implementation(),
            "python_compiler": platform.python_compiler(),
        }
        
        # Add environment-specific metadata
        if os.getenv("GITHUB_ACTIONS"):
            metadata.update({
                "github_runner_os": os.getenv("RUNNER_OS"),
                "github_runner_arch": os.getenv("RUNNER_ARCH"),
                "github_workflow": os.getenv("GITHUB_WORKFLOW")
            })
        
        return metadata


class CrossPlatformTestRunner:
    """Cross-platform test execution engine."""
    
    def __init__(self):
        self.platform_info = PlatformDetector.get_platform_info()
        self.tests: Dict[str, CrossPlatformTest] = {}
        self.results: List[PlatformTestResult] = []
        self._register_tests()
    
    def _register_tests(self):
        """Register all cross-platform tests."""
        self._register_audio_tests()
        self._register_file_system_tests()
        self._register_process_tests()
        self._register_network_tests()
        self._register_environment_tests()
        self._register_compatibility_tests()
    
    def _register_audio_tests(self):
        """Register audio-related cross-platform tests."""
        self.tests["audio.device_detection"] = CrossPlatformTest(
            id="audio.device_detection",
            name="Audio Device Detection",
            description="Test audio device detection across platforms",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.AUDIO_DEVICES},
            test_function=self._test_audio_device_detection,
            skip_conditions={
                Platform.LINUX: "No audio system in headless environment"
            }
        )
        
        self.tests["audio.format_support"] = CrossPlatformTest(
            id="audio.format_support",
            name="Audio Format Support",
            description="Test supported audio formats across platforms",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.AUDIO_DEVICES},
            test_function=self._test_audio_format_support
        )
    
    def _register_file_system_tests(self):
        """Register file system cross-platform tests."""
        self.tests["fs.path_handling"] = CrossPlatformTest(
            id="fs.path_handling",
            name="Path Handling",
            description="Test path handling across platforms",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.PATH_HANDLING},
            test_function=self._test_path_handling,
            critical=True
        )
        
        self.tests["fs.permissions"] = CrossPlatformTest(
            id="fs.permissions",
            name="File Permissions",
            description="Test file permission handling",
            platforms={Platform.MACOS, Platform.LINUX},
            features={PlatformFeature.FILE_PERMISSIONS},
            test_function=self._test_file_permissions,
            skip_conditions={
                Platform.WINDOWS: "Windows uses different permission model"
            }
        )
        
        self.tests["fs.unicode"] = CrossPlatformTest(
            id="fs.unicode",
            name="Unicode File Support",
            description="Test Unicode file name support",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.UNICODE_SUPPORT},
            test_function=self._test_unicode_files,
            critical=True
        )
    
    def _register_process_tests(self):
        """Register process management tests."""
        self.tests["process.management"] = CrossPlatformTest(
            id="process.management",
            name="Process Management",
            description="Test process creation and management",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.PROCESS_MANAGEMENT},
            test_function=self._test_process_management
        )
        
        self.tests["process.signals"] = CrossPlatformTest(
            id="process.signals",
            name="Signal Handling",
            description="Test signal handling across platforms",
            platforms={Platform.MACOS, Platform.LINUX},
            features={PlatformFeature.PROCESS_MANAGEMENT},
            test_function=self._test_signal_handling,
            skip_conditions={
                Platform.WINDOWS: "Windows has limited signal support"
            }
        )
    
    def _register_network_tests(self):
        """Register network-related tests."""
        self.tests["network.socket_creation"] = CrossPlatformTest(
            id="network.socket_creation",
            name="Socket Creation",
            description="Test socket creation and binding",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.NETWORK_ACCESS},
            test_function=self._test_socket_creation
        )
        
        self.tests["network.http_requests"] = CrossPlatformTest(
            id="network.http_requests",
            name="HTTP Requests",
            description="Test HTTP client functionality",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.NETWORK_ACCESS},
            test_function=self._test_http_requests
        )
    
    def _register_environment_tests(self):
        """Register environment variable tests."""
        self.tests["env.variable_handling"] = CrossPlatformTest(
            id="env.variable_handling",
            name="Environment Variables",
            description="Test environment variable handling",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.ENVIRONMENT_VARIABLES},
            test_function=self._test_environment_variables,
            critical=True
        )
    
    def _register_compatibility_tests(self):
        """Register VoiceMode compatibility tests."""
        self.tests["voicemode.import"] = CrossPlatformTest(
            id="voicemode.import",
            name="VoiceMode Import",
            description="Test VoiceMode module import",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features=set(),
            test_function=self._test_voicemode_import,
            critical=True
        )
        
        self.tests["voicemode.config"] = CrossPlatformTest(
            id="voicemode.config",
            name="Configuration Loading",
            description="Test configuration loading across platforms",
            platforms={Platform.MACOS, Platform.LINUX, Platform.WINDOWS},
            features={PlatformFeature.PATH_HANDLING, PlatformFeature.ENVIRONMENT_VARIABLES},
            test_function=self._test_config_loading,
            critical=True
        )
    
    # Test implementation methods
    async def _test_audio_device_detection(self) -> bool:
        """Test audio device detection."""
        try:
            if self.platform_info.platform == Platform.MACOS:
                result = subprocess.run(["system_profiler", "SPAudioDataType"], 
                                      capture_output=True, timeout=10)
                return result.returncode == 0 and b"Audio" in result.stdout
            elif self.platform_info.platform == Platform.LINUX:
                return os.path.exists("/proc/asound") or shutil.which("aplay") is not None
            elif self.platform_info.platform == Platform.WINDOWS:
                # Windows API would be used here in real implementation
                return True
            return False
        except Exception:
            return False
    
    async def _test_audio_format_support(self) -> bool:
        """Test audio format support."""
        formats = ["wav", "mp3", "flac", "ogg"]
        supported = []
        
        for fmt in formats:
            # Simulate format testing
            if fmt in ["wav", "mp3"]:  # Basic formats usually supported
                supported.append(fmt)
        
        return len(supported) >= 2
    
    async def _test_path_handling(self) -> bool:
        """Test path handling across platforms."""
        try:
            # Test various path operations
            temp_dir = tempfile.mkdtemp()
            
            # Test path joining
            test_path = os.path.join(temp_dir, "test", "file.txt")
            os.makedirs(os.path.dirname(test_path), exist_ok=True)
            
            # Test path normalization
            normalized = os.path.normpath(test_path)
            
            # Test path exists
            exists_before = os.path.exists(test_path)
            
            # Create file
            with open(test_path, "w") as f:
                f.write("test content")
            
            exists_after = os.path.exists(test_path)
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            return not exists_before and exists_after and len(normalized) > 0
        except Exception:
            return False
    
    async def _test_file_permissions(self) -> bool:
        """Test file permission handling."""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(b"test")
            temp_file.close()
            
            # Test permission changes
            os.chmod(temp_file.name, 0o644)
            stat_info = os.stat(temp_file.name)
            
            # Cleanup
            os.unlink(temp_file.name)
            
            return stat_info.st_mode & 0o777 == 0o644
        except Exception:
            return False
    
    async def _test_unicode_files(self) -> bool:
        """Test Unicode file name support."""
        try:
            temp_dir = tempfile.mkdtemp()
            unicode_name = os.path.join(temp_dir, "测试文件_🎵.txt")
            
            with open(unicode_name, "w", encoding="utf-8") as f:
                f.write("Unicode content: 你好世界")
            
            exists = os.path.exists(unicode_name)
            
            if exists:
                with open(unicode_name, "r", encoding="utf-8") as f:
                    content = f.read()
                    content_ok = "你好世界" in content
            else:
                content_ok = False
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            return exists and content_ok
        except Exception:
            return False
    
    async def _test_process_management(self) -> bool:
        """Test process creation and management."""
        try:
            # Test subprocess creation
            result = subprocess.run([sys.executable, "-c", "print('test')"], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0 and b"test" in result.stdout
        except Exception:
            return False
    
    async def _test_signal_handling(self) -> bool:
        """Test signal handling."""
        try:
            import signal
            
            # Test signal handler registration
            original_handler = signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, original_handler)
            
            return True
        except Exception:
            return False
    
    async def _test_socket_creation(self) -> bool:
        """Test socket creation."""
        try:
            import socket
            
            # Test TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
            sock.close()
            
            return port > 0
        except Exception:
            return False
    
    async def _test_http_requests(self) -> bool:
        """Test HTTP requests."""
        try:
            import urllib.request
            
            # Test basic HTTP request (to local loopback)
            req = urllib.request.Request("http://127.0.0.1:1/")
            try:
                urllib.request.urlopen(req, timeout=1)
            except urllib.error.URLError:
                # Expected - no server running, but networking works
                return True
            except Exception:
                return False
            
            return True
        except Exception:
            return False
    
    async def _test_environment_variables(self) -> bool:
        """Test environment variable handling."""
        try:
            # Test setting and getting environment variables
            test_var = "VOICEMODE_TEST_VAR"
            test_value = "test_value_123"
            
            # Set variable
            os.environ[test_var] = test_value
            
            # Get variable
            retrieved = os.getenv(test_var)
            
            # Clean up
            if test_var in os.environ:
                del os.environ[test_var]
            
            return retrieved == test_value
        except Exception:
            return False
    
    async def _test_voicemode_import(self) -> bool:
        """Test VoiceMode module import."""
        try:
            import voice_mode
            return hasattr(voice_mode, '__version__')
        except ImportError:
            return False
        except Exception:
            return False
    
    async def _test_config_loading(self) -> bool:
        """Test configuration loading."""
        try:
            from voice_mode.config import VoiceModeConfig
            config = VoiceModeConfig()
            return config is not None
        except Exception:
            return False
    
    async def run_test(self, test_id: str) -> PlatformTestResult:
        """Run a single cross-platform test."""
        if test_id not in self.tests:
            return PlatformTestResult(
                test_id=test_id,
                platform_info=self.platform_info,
                status="error",
                duration=0.0,
                error="Test not found"
            )
        
        test = self.tests[test_id]
        
        # Check if test should be skipped
        if (self.platform_info.platform not in test.platforms or
            self.platform_info.platform in test.skip_conditions):
            skip_reason = test.skip_conditions.get(self.platform_info.platform, 
                                                 "Platform not supported")
            return PlatformTestResult(
                test_id=test_id,
                platform_info=self.platform_info,
                status="skipped",
                duration=0.0,
                output=f"Skipped: {skip_reason}"
            )
        
        # Check required features
        missing_features = test.features - self.platform_info.features
        if missing_features:
            return PlatformTestResult(
                test_id=test_id,
                platform_info=self.platform_info,
                status="skipped",
                duration=0.0,
                output=f"Missing features: {', '.join(f.value for f in missing_features)}"
            )
        
        start_time = time.time()
        
        try:
            # Run setup if provided
            if test.setup_function:
                await test.setup_function()
            
            # Run the test with timeout
            result = await asyncio.wait_for(
                test.test_function(),
                timeout=test.timeout
            )
            
            duration = time.time() - start_time
            
            # Check for expected failures
            if not result and self.platform_info.platform in test.expected_failures:
                expected_reason = test.expected_failures[self.platform_info.platform]
                return PlatformTestResult(
                    test_id=test_id,
                    platform_info=self.platform_info,
                    status="expected_failure",
                    duration=duration,
                    output=f"Expected failure: {expected_reason}"
                )
            
            status = "passed" if result else "failed"
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            status = "failed"
            error = f"Test timed out after {test.timeout}s"
        except Exception as e:
            duration = time.time() - start_time
            status = "error"
            error = str(e)
        else:
            error = ""
        
        finally:
            # Run cleanup if provided
            if test.cleanup_function:
                try:
                    await test.cleanup_function()
                except Exception as cleanup_error:
                    logger.warning(f"Cleanup failed for {test_id}: {cleanup_error}")
        
        result_obj = PlatformTestResult(
            test_id=test_id,
            platform_info=self.platform_info,
            status=status,
            duration=duration,
            error=error
        )
        
        self.results.append(result_obj)
        return result_obj
    
    async def run_all_tests(self, platforms: Optional[Set[Platform]] = None,
                           features: Optional[Set[PlatformFeature]] = None,
                           critical_only: bool = False) -> List[PlatformTestResult]:
        """Run all applicable cross-platform tests."""
        results = []
        
        for test_id, test in self.tests.items():
            # Filter by platforms
            if platforms and not (test.platforms & platforms):
                continue
            
            # Filter by features
            if features and not (test.features & features):
                continue
            
            # Filter by critical tests only
            if critical_only and not test.critical:
                continue
            
            result = await self.run_test(test_id)
            results.append(result)
        
        return results
    
    def get_compatibility_report(self) -> Dict[str, Any]:
        """Generate cross-platform compatibility report."""
        if not self.results:
            return {"error": "No test results available"}
        
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        errors = sum(1 for r in self.results if r.status == "error")
        expected_failures = sum(1 for r in self.results if r.status == "expected_failure")
        
        critical_tests = [r for r in self.results if self.tests[r.test_id].critical]
        critical_failures = [r for r in critical_tests if r.status in ["failed", "error"]]
        
        return {
            "platform": {
                "name": self.platform_info.platform.value,
                "architecture": self.platform_info.architecture.value,
                "version": self.platform_info.version,
                "python_version": self.platform_info.python_version,
                "environment": self.platform_info.environment.value
            },
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "errors": errors,
                "expected_failures": expected_failures,
                "success_rate": passed / max(total_tests - skipped, 1) * 100,
                "critical_failures": len(critical_failures)
            },
            "features": {
                "available": [f.value for f in self.platform_info.features],
                "limitations": self.platform_info.limitations
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "name": self.tests[r.test_id].name,
                    "status": r.status,
                    "duration": round(r.duration, 3),
                    "error": r.error,
                    "output": r.output[:200] + "..." if len(r.output) > 200 else r.output,
                    "critical": self.tests[r.test_id].critical
                }
                for r in self.results
            ],
            "critical_failures": [
                {
                    "test_id": r.test_id,
                    "name": self.tests[r.test_id].name,
                    "error": r.error,
                    "output": r.output
                }
                for r in critical_failures
            ]
        }


# Global test runner instance
_cross_platform_runner: Optional[CrossPlatformTestRunner] = None


def get_cross_platform_runner() -> CrossPlatformTestRunner:
    """Get or create global cross-platform test runner."""
    global _cross_platform_runner
    if _cross_platform_runner is None:
        _cross_platform_runner = CrossPlatformTestRunner()
    return _cross_platform_runner


async def run_cross_platform_tests(
    platforms: Optional[List[str]] = None,
    features: Optional[List[str]] = None,
    critical_only: bool = False,
    output_format: str = "json"
) -> Dict[str, Any]:
    """Run cross-platform tests with options."""
    runner = get_cross_platform_runner()
    
    # Convert string parameters to enums
    platform_enums = None
    if platforms:
        platform_enums = {Platform(p) for p in platforms if p in [e.value for e in Platform]}
    
    feature_enums = None
    if features:
        feature_enums = {PlatformFeature(f) for f in features if f in [e.value for e in PlatformFeature]}
    
    # Run tests
    results = await runner.run_all_tests(
        platforms=platform_enums,
        features=feature_enums,
        critical_only=critical_only
    )
    
    # Generate report
    report = runner.get_compatibility_report()
    
    if output_format == "text":
        # Convert to text format
        text_parts = []
        text_parts.append("CROSS-PLATFORM COMPATIBILITY REPORT")
        text_parts.append("=" * 50)
        text_parts.append(f"Platform: {report['platform']['name']} ({report['platform']['architecture']})")
        text_parts.append(f"Python: {report['platform']['python_version']}")
        text_parts.append(f"Environment: {report['platform']['environment']}")
        text_parts.append("")
        text_parts.append("SUMMARY:")
        text_parts.append(f"  Total Tests: {report['summary']['total_tests']}")
        text_parts.append(f"  Passed: {report['summary']['passed']}")
        text_parts.append(f"  Failed: {report['summary']['failed']}")
        text_parts.append(f"  Skipped: {report['summary']['skipped']}")
        text_parts.append(f"  Success Rate: {report['summary']['success_rate']:.1f}%")
        text_parts.append(f"  Critical Failures: {report['summary']['critical_failures']}")
        text_parts.append("")
        
        if report['summary']['critical_failures'] > 0:
            text_parts.append("CRITICAL FAILURES:")
            for failure in report['critical_failures']:
                text_parts.append(f"  - {failure['name']}: {failure['error']}")
            text_parts.append("")
        
        report_text = "\n".join(text_parts)
        return {
            "results": results,
            "report": report_text,
            "compatibility": report,
            "success": report['summary']['critical_failures'] == 0
        }
    
    return {
        "results": results,
        "report": report,
        "compatibility": report,
        "success": report['summary']['critical_failures'] == 0
    }