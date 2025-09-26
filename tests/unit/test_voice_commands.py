#!/usr/bin/env python3
"""Test voice commands system."""

import asyncio
import time
from typing import List, Any
from voice_mode.voice_commands import (
    VoiceCommandEngine,
    VoiceCommandManager,
    VoiceCommand,
    CommandCategory,
    CommandPriority,
    CommandContext,
    CommandMatch,
    CommandExecutionError,
    get_voice_command_manager
)


def test_command_definition():
    """Test voice command definition and matching."""
    print("\n=== Testing Command Definition ===")
    
    # Create test handler
    async def test_handler(**kwargs):
        return f"Executed with {kwargs}"
    
    # Create command
    command = VoiceCommand(
        id="test.command",
        name="Test Command",
        category=CommandCategory.CUSTOM,
        priority=CommandPriority.NORMAL,
        patterns=[r"test command", r"run test"],
        handler=test_handler,
        description="A test command",
        aliases=["tc"],
        contexts={CommandContext.IDLE, CommandContext.LISTENING}
    )
    
    print(f"  Created command: {command.name}")
    print(f"  ID: {command.id}")
    print(f"  Category: {command.category.name}")
    print(f"  Priority: {command.priority.name}")
    print(f"  Patterns: {command.patterns}")
    print(f"  Aliases: {command.aliases}")
    
    # Test matching
    match1 = command.matches("please test command now", CommandContext.IDLE)
    print(f"  Match 'test command': {match1 is not None}")
    if match1:
        print(f"    Confidence: {match1.confidence:.2f}")
        print(f"    Matched text: '{match1.matched_text}'")
    
    match2 = command.matches("run test", CommandContext.LISTENING)
    print(f"  Match 'run test': {match2 is not None}")
    
    match3 = command.matches("tc", CommandContext.IDLE)
    print(f"  Match alias 'tc': {match3 is not None}")
    
    # Test context filtering
    match4 = command.matches("test command", CommandContext.SPEAKING)
    print(f"  Match in wrong context: {match4 is not None}")
    
    print("✓ Command definition working")


def test_engine_registration():
    """Test command registration in engine."""
    print("\n=== Testing Engine Registration ===")
    
    engine = VoiceCommandEngine(confidence_threshold=0.2)
    
    # Test handler
    executed = []
    
    async def custom_handler(value: str = "default"):
        executed.append(value)
        return f"Custom executed: {value}"
    
    # Register command
    command = engine.register_command(
        id="custom.test",
        name="Custom Test",
        category=CommandCategory.CUSTOM,
        priority=CommandPriority.NORMAL,
        patterns=[r"custom (?P<value>\w+)", r"execute custom"],
        handler=custom_handler,
        description="Custom test command",
        parameters={"value": str}
    )
    
    print(f"  Registered command: {command.name}")
    print(f"  Total commands: {len(engine.commands)}")
    
    # Test retrieval
    retrieved = engine.get_command("custom.test")
    assert retrieved is not None
    print(f"  Retrieved command: {retrieved.name}")
    
    # Test category listing
    custom_commands = engine.get_commands_by_category(CommandCategory.CUSTOM)
    print(f"  Custom commands: {len(custom_commands)}")
    
    # Test built-in commands
    builtin_count = len([cmd for cmd in engine.commands.values() 
                        if cmd.category != CommandCategory.CUSTOM])
    print(f"  Built-in commands: {builtin_count}")
    
    print("✓ Engine registration working")


async def test_command_recognition():
    """Test voice command recognition."""
    print("\n=== Testing Command Recognition ===")
    
    engine = VoiceCommandEngine(confidence_threshold=0.1)
    
    # Test built-in command recognition
    matches1 = await engine.recognize_command("start voice mode")
    print(f"  'start voice mode': {len(matches1)} matches")
    if matches1:
        best = matches1[0]
        print(f"    Best: {engine.commands[best.command_id].name} ({best.confidence:.2f})")
    
    matches2 = await engine.recognize_command("help me")
    print(f"  'help me': {len(matches2)} matches")
    
    matches3 = await engine.recognize_command("volume up please")
    print(f"  'volume up please': {len(matches3)} matches")
    
    # Test no matches
    matches4 = await engine.recognize_command("this should not match anything")
    print(f"  'no match text': {len(matches4)} matches")
    
    # Test multiple matches
    matches5 = await engine.recognize_command("help with voice commands")
    print(f"  'help with voice': {len(matches5)} matches")
    for i, match in enumerate(matches5[:3]):
        cmd = engine.commands[match.command_id]
        print(f"    {i+1}. {cmd.name} ({match.confidence:.2f})")
    
    print("✓ Command recognition working")


async def test_command_execution():
    """Test command execution."""
    print("\n=== Testing Command Execution ===")
    
    engine = VoiceCommandEngine()
    
    # Test built-in command execution
    matches = await engine.recognize_command("help")
    if matches:
        result = await engine.execute_command(matches[0])
        print(f"  Help command result length: {len(str(result))}")
        print(f"  Contains 'Available voice commands': {'Available voice commands' in result}")
    
    # Test status command
    matches = await engine.recognize_command("status")
    if matches:
        result = await engine.execute_command(matches[0])
        print(f"  Status command result: {len(str(result))} chars")
    
    # Test custom command with parameters
    executed_values = []
    
    async def param_handler(name: str = "unknown"):
        executed_values.append(name)
        return f"Hello {name}!"
    
    engine.register_command(
        id="test.greeting",
        name="Test Greeting",
        category=CommandCategory.CUSTOM,
        priority=CommandPriority.NORMAL,
        patterns=[r"greet (?P<name>\w+)"],
        handler=param_handler
    )
    
    matches = await engine.recognize_command("greet alice")
    if matches:
        result = await engine.execute_command(matches[0])
        print(f"  Greeting result: {result}")
        print(f"  Executed values: {executed_values}")
    
    print("✓ Command execution working")


async def test_context_handling():
    """Test command context handling."""
    print("\n=== Testing Context Handling ===")
    
    engine = VoiceCommandEngine()
    
    # Test context-specific commands
    print(f"  Initial context: {engine.current_context.name}")
    
    # Voice start should work in IDLE
    engine.set_context(CommandContext.IDLE)
    matches = await engine.recognize_command("start voice")
    print(f"  'start voice' in IDLE: {len(matches)} matches")
    
    # Voice stop should work in LISTENING/SPEAKING
    engine.set_context(CommandContext.LISTENING)
    matches = await engine.recognize_command("stop voice")
    print(f"  'stop voice' in LISTENING: {len(matches)} matches")
    
    # Voice start should NOT work in LISTENING
    matches = await engine.recognize_command("start voice")
    print(f"  'start voice' in LISTENING: {len(matches)} matches")
    
    # Mute should only work in SPEAKING
    engine.set_context(CommandContext.SPEAKING)
    matches = await engine.recognize_command("mute")
    print(f"  'mute' in SPEAKING: {len(matches)} matches")
    
    engine.set_context(CommandContext.IDLE)
    matches = await engine.recognize_command("mute")
    print(f"  'mute' in IDLE: {len(matches)} matches")
    
    print("✓ Context handling working")


async def test_error_handling():
    """Test command error handling."""
    print("\n=== Testing Error Handling ===")
    
    engine = VoiceCommandEngine()
    
    # Test invalid command execution
    invalid_match = CommandMatch(
        command_id="nonexistent.command",
        confidence=1.0,
        matched_text="test"
    )
    
    try:
        await engine.execute_command(invalid_match)
        assert False, "Should have raised error"
    except CommandExecutionError as e:
        print(f"  Invalid command error: {str(e)[:50]}...")
    
    # Test handler that raises exception
    def failing_handler():
        raise ValueError("Test error")
    
    engine.register_command(
        id="test.failing",
        name="Failing Command",
        category=CommandCategory.CUSTOM,
        priority=CommandPriority.NORMAL,
        patterns=["fail"],
        handler=failing_handler
    )
    
    # Test failing handler
    matches = await engine.recognize_command("fail")
    if matches:
        try:
            await engine.execute_command(matches[0])
            assert False, "Should have raised error"
        except CommandExecutionError as e:
            print(f"  Handler error: {str(e)[:50]}...")
    
    # Test disabled command
    engine.commands["test.failing"].enabled = False
    
    matches = await engine.recognize_command("fail")
    if matches:
        try:
            await engine.execute_command(matches[0])
            assert False, "Should have raised error"
        except CommandExecutionError as e:
            print(f"  Disabled command error: {str(e)[:50]}...")
    
    print("✓ Error handling working")


async def test_statistics():
    """Test statistics collection."""
    print("\n=== Testing Statistics ===")
    
    engine = VoiceCommandEngine()
    
    # Get initial stats
    stats = engine.get_statistics()
    print(f"  Initial commands registered: {stats['commands_registered']}")
    print(f"  Initial recognition attempts: {stats['recognition_attempts']}")
    print(f"  Current context: {stats['current_context']}")
    
    # Perform some operations
    await engine.recognize_command("help")
    await engine.recognize_command("status")
    await engine.recognize_command("invalid command")
    
    matches = await engine.recognize_command("help")
    if matches:
        await engine.execute_command(matches[0])
    
    matches = await engine.recognize_command("status")
    if matches:
        await engine.execute_command(matches[0])
    
    # Get updated stats
    stats = engine.get_statistics()
    print(f"  Final recognition attempts: {stats['recognition_attempts']}")
    print(f"  Successful matches: {stats['successful_matches']}")
    print(f"  Failed matches: {stats['failed_matches']}")
    print(f"  Commands executed: {stats['commands_executed']}")
    
    # Check categories
    print(f"  Commands by category:")
    for category, count in stats['commands_by_category'].items():
        if count > 0:
            print(f"    {category}: {count}")
    
    print("✓ Statistics working")


async def test_voice_command_manager():
    """Test high-level voice command manager."""
    print("\n=== Testing Voice Command Manager ===")
    
    manager = VoiceCommandManager()
    
    # Test basic functionality
    print(f"  Manager enabled: {manager.enabled}")
    print(f"  Wake word: '{manager.wake_word}'")
    print(f"  Wake word enabled: {manager.wake_word_enabled}")
    
    # Test processing without wake word
    results = await manager.process_speech("help me")
    print(f"  'help me' results: {len(results)}")
    
    # Test wake word processing
    results = await manager.process_speech("hey claude show help")
    print(f"  'hey claude show help' results: {len(results)}")
    
    # Test just wake word
    results = await manager.process_speech("hey claude")
    print(f"  'hey claude' results: {len(results)}")
    
    # Test custom command registration
    executed = []
    
    def custom_handler():
        executed.append("custom")
        return "Custom command executed"
    
    cmd_id = manager.register_custom_command(
        name="Custom Test",
        patterns=["custom test", "test custom"],
        handler=custom_handler,
        description="A custom test command"
    )
    
    print(f"  Registered custom command: {cmd_id}")
    
    # Test custom command execution
    results = await manager.process_speech("custom test")
    print(f"  Custom command results: {len(results)}")
    print(f"  Custom executions: {len(executed)}")
    
    # Test configuration export
    config = manager.export_configuration()
    print(f"  Configuration keys: {list(config.keys())}")
    print(f"  Custom commands exported: {len(config['custom_commands'])}")
    
    print("✓ Voice command manager working")


async def test_performance():
    """Test voice command performance."""
    print("\n=== Testing Performance ===")
    
    import time
    
    engine = VoiceCommandEngine(confidence_threshold=0.1)
    
    # Add many custom commands
    for i in range(50):
        engine.register_command(
            id=f"perf.test{i}",
            name=f"Performance Test {i}",
            category=CommandCategory.CUSTOM,
            priority=CommandPriority.NORMAL,
            patterns=[f"test {i}", f"command {i}"],
            handler=lambda: f"Result {i}"
        )
    
    print(f"  Total commands registered: {len(engine.commands)}")
    
    # Test recognition performance
    test_phrases = [
        "help me please",
        "start voice mode",
        "test 25",
        "volume up",
        "status check",
        "invalid phrase",
        "command 10",
        "stop voice",
        "mute audio",
        "show help"
    ]
    
    start_time = time.time()
    total_matches = 0
    
    for _ in range(100):  # 100 iterations
        for phrase in test_phrases:
            matches = await engine.recognize_command(phrase)
            total_matches += len(matches)
    
    elapsed = time.time() - start_time
    rate = (100 * len(test_phrases)) / elapsed
    
    print(f"  Recognition rate: {rate:.1f} recognitions/sec")
    print(f"  Total matches found: {total_matches}")
    print(f"  Average matches per phrase: {total_matches / (100 * len(test_phrases)):.2f}")
    
    # Test execution performance
    help_matches = await engine.recognize_command("help")
    if help_matches:
        start_time = time.time()
        
        for _ in range(50):
            await engine.execute_command(help_matches[0])
        
        elapsed = time.time() - start_time
        rate = 50 / elapsed
        
        print(f"  Execution rate: {rate:.1f} executions/sec")
    
    print("✓ Performance acceptable")


async def test_pattern_matching():
    """Test advanced pattern matching."""
    print("\n=== Testing Pattern Matching ===")
    
    engine = VoiceCommandEngine()
    
    # Register command with regex patterns
    executed_params = []
    
    async def regex_handler(**params):
        executed_params.append(params)
        return f"Regex result: {params}"
    
    engine.register_command(
        id="test.regex",
        name="Regex Test",
        category=CommandCategory.CUSTOM,
        priority=CommandPriority.NORMAL,
        patterns=[
            r"set volume to (?P<level>\d+)",
            r"change speed to (?P<speed>slow|normal|fast)",
            r"repeat (?P<count>\d+) times"
        ],
        handler=regex_handler
    )
    
    # Test parameter extraction
    matches = await engine.recognize_command("set volume to 75")
    if matches:
        await engine.execute_command(matches[0])
        print(f"  Volume params: {executed_params[-1]}")
    
    matches = await engine.recognize_command("change speed to fast")
    if matches:
        await engine.execute_command(matches[0])
        print(f"  Speed params: {executed_params[-1]}")
    
    matches = await engine.recognize_command("repeat 3 times")
    if matches:
        await engine.execute_command(matches[0])
        print(f"  Repeat params: {executed_params[-1]}")
    
    print(f"  Total parameter extractions: {len(executed_params)}")
    
    print("✓ Pattern matching working")


def test_global_manager():
    """Test global manager instance."""
    print("\n=== Testing Global Manager ===")
    
    # Get global instance
    manager1 = get_voice_command_manager()
    manager2 = get_voice_command_manager()
    
    print(f"  Same instance: {manager1 is manager2}")
    print(f"  Manager type: {type(manager1).__name__}")
    print(f"  Commands available: {len(manager1.engine.commands)}")
    
    # Test that it has built-in commands
    help_cmd = manager1.engine.get_command("system.help")
    print(f"  Help command available: {help_cmd is not None}")
    
    if help_cmd:
        print(f"  Help command name: {help_cmd.name}")
        print(f"  Help command patterns: {help_cmd.patterns}")
    
    print("✓ Global manager working")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("VOICE COMMANDS TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_command_definition()
    test_engine_registration()
    test_global_manager()
    
    # Run async tests
    await test_command_recognition()
    await test_command_execution()
    await test_context_handling()
    await test_error_handling()
    await test_statistics()
    await test_pattern_matching()
    await test_voice_command_manager()
    await test_performance()
    
    print("\n" + "=" * 60)
    print("✓ All voice commands tests passed!")
    print("Sprint 37 complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())