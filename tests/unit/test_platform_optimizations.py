#!/usr/bin/env python3
"""Test platform-specific optimizations."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.platform_optimizations import (
    Platform,
    AudioBackend,
    DisplayMode,
    PlatformCapabilities,
    PlatformDetector,
    PlatformOptimizer,
    AdaptiveOptimizer,
    get_optimizer
)


def test_platform_detection():
    """Test platform detection."""
    print("\n=== Testing Platform Detection ===")
    
    # Detect current platform
    platform = PlatformDetector.detect()
    print(f"Detected platform: {platform.name}")
    
    # Get capabilities
    capabilities = PlatformDetector.get_capabilities(platform)
    print(f"Has terminal: {capabilities.has_terminal}")
    print(f"Has direct audio: {capabilities.has_direct_audio}")
    print(f"Has rich UI: {capabilities.has_rich_ui}")
    print(f"Preferred audio: {capabilities.preferred_audio_backend.name}")
    print(f"Preferred display: {capabilities.preferred_display_mode.name}")
    
    # Test different platforms
    for p in [Platform.CLAUDE_DESKTOP, Platform.CLAUDE_CODE]:
        caps = PlatformDetector.get_capabilities(p)
        print(f"\n{p.name} capabilities:")
        print(f"  Terminal: {caps.has_terminal}")
        print(f"  Audio: {caps.has_direct_audio}")
        print(f"  Rich UI: {caps.has_rich_ui}")
        print(f"  Max message: {caps.max_message_size / 1024 / 1024:.1f}MB")


def test_audio_optimization():
    """Test audio pipeline optimization."""
    print("\n=== Testing Audio Optimization ===")
    
    optimizer = PlatformOptimizer()
    
    # Get audio configuration
    audio_config = optimizer.optimize_audio_pipeline()
    print(f"Audio backend: {audio_config['backend']}")
    print(f"Buffer size: {audio_config['buffer_size']}")
    print(f"Sample rate: {audio_config['sample_rate']}")
    print(f"Channels: {audio_config['channels']}")
    print(f"Format: {audio_config['format']}")
    
    # Get actual backend
    backend = optimizer.get_audio_backend()
    print(f"\nSelected backend: {backend.name}")


def test_display_optimization():
    """Test display output optimization."""
    print("\n=== Testing Display Optimization ===")
    
    optimizer = PlatformOptimizer()
    
    # Get display configuration
    display_config = optimizer.optimize_display_output()
    print(f"Display mode: {display_config['mode']}")
    print(f"Buffer lines: {display_config['buffer_lines']}")
    print(f"Update frequency: {display_config['update_frequency']}")
    
    # Get display handler
    handler = optimizer.get_display_handler()
    print(f"\nDisplay handler type: {type(handler).__name__}")
    
    # Test output
    print("\nTest output:")
    handler("  Hello from optimized display!")


def test_network_optimization():
    """Test network settings optimization."""
    print("\n=== Testing Network Optimization ===")
    
    optimizer = PlatformOptimizer()
    
    # Get network configuration
    network_config = optimizer.optimize_network_settings()
    print(f"Timeout: {network_config['timeout']}s")
    print(f"Retry count: {network_config['retry_count']}")
    print(f"Connection pool: {network_config['connection_pool_size']}")
    
    # Check additional settings
    for key, value in network_config.items():
        if key not in ['timeout', 'retry_count', 'connection_pool_size']:
            print(f"{key}: {value}")


def test_resource_optimization():
    """Test resource usage optimization."""
    print("\n=== Testing Resource Optimization ===")
    
    optimizer = PlatformOptimizer()
    
    # Get resource configuration
    resource_config = optimizer.optimize_resource_usage()
    print(f"Max memory: {resource_config['max_memory']}")
    print(f"Max threads: {resource_config['max_threads']}")
    print(f"Cache size: {resource_config['cache_size']}")
    
    # Check additional settings
    for key, value in resource_config.items():
        if key not in ['max_memory', 'max_threads', 'cache_size']:
            print(f"{key}: {value}")


def test_environment_application():
    """Test environment variable application."""
    print("\n=== Testing Environment Application ===")
    
    # Clear existing env vars
    for key in list(os.environ.keys()):
        if key.startswith("CHATTA_"):
            del os.environ[key]
    
    # Apply optimizations
    optimizer = PlatformOptimizer()
    optimizer.apply_optimizations()
    
    # Check environment variables
    env_vars = {k: v for k, v in os.environ.items() if k.startswith("CHATTA_")}
    
    print(f"Applied {len(env_vars)} environment variables:")
    for category in ["AUDIO", "DISPLAY", "NETWORK", "RESOURCE"]:
        category_vars = {k: v for k, v in env_vars.items() if f"CHATTA_{category}" in k}
        if category_vars:
            print(f"\n{category}:")
            for key, value in sorted(category_vars.items()):
                print(f"  {key}: {value}")


def test_adaptive_optimizer():
    """Test adaptive optimizer."""
    print("\n=== Testing Adaptive Optimizer ===")
    
    optimizer = PlatformOptimizer()
    adaptive = AdaptiveOptimizer(optimizer)
    
    print(f"Initial adjustments: {adaptive.adjustments_made}")
    print(f"Metrics tracked: {list(adaptive.metrics.keys())}")
    
    # Test metric collection (sync version for testing)
    try:
        import psutil
        process = psutil.Process()
        metrics = {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "thread_count": process.num_threads(),
        }
        print(f"\nCurrent metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value:.2f}")
    except ImportError:
        print("psutil not available for metrics")


def test_platform_comparison():
    """Compare settings across platforms."""
    print("\n=== Platform Comparison ===")
    
    configs = {}
    
    for platform in [Platform.CLAUDE_DESKTOP, Platform.CLAUDE_CODE]:
        # Mock platform detection
        optimizer = PlatformOptimizer()
        optimizer.platform = platform
        optimizer.capabilities = PlatformDetector.get_capabilities(platform)
        
        configs[platform.name] = {
            "audio": optimizer.optimize_audio_pipeline(),
            "display": optimizer.optimize_display_output(),
            "network": optimizer.optimize_network_settings(),
            "resource": optimizer.optimize_resource_usage()
        }
    
    # Compare configurations
    print("\nKey differences:")
    print("=" * 50)
    
    categories = ["audio", "display", "network", "resource"]
    for category in categories:
        print(f"\n{category.upper()}:")
        desktop = configs["CLAUDE_DESKTOP"][category]
        code = configs["CLAUDE_CODE"][category]
        
        # Find differences
        all_keys = set(desktop.keys()) | set(code.keys())
        for key in sorted(all_keys):
            desktop_val = desktop.get(key, "N/A")
            code_val = code.get(key, "N/A")
            if desktop_val != code_val:
                print(f"  {key}:")
                print(f"    Desktop: {desktop_val}")
                print(f"    Code: {code_val}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PLATFORM OPTIMIZATION TESTS")
    print("=" * 60)
    
    test_platform_detection()
    test_audio_optimization()
    test_display_optimization()
    test_network_optimization()
    test_resource_optimization()
    test_environment_application()
    test_adaptive_optimizer()
    test_platform_comparison()
    
    print("\n" + "=" * 60)
    print("✓ All platform optimization tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()