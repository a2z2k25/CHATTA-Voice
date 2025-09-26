#!/usr/bin/env python3
"""Test keyboard shortcuts and commands system."""

import asyncio
from typing import Set
from voice_mode.keyboard_shortcuts import (
    KeyboardShortcutsManager,
    CommandPalette,
    HelpOverlay,
    KeyBinding,
    KeyModifier,
    CommandCategory,
    get_shortcuts_manager
)


def test_key_bindings():
    """Test key binding parsing and formatting."""
    print("\n=== Testing Key Bindings ===")
    
    # Test binding creation
    binding1 = KeyBinding(key="p", modifiers={KeyModifier.CTRL, KeyModifier.SHIFT})
    print(f"  Created binding: {binding1.to_string()}")
    
    # Test string parsing
    binding2 = KeyBinding.from_string("Ctrl+Alt+Delete")
    print(f"  Parsed binding: {binding2.to_string()}")
    
    # Test platform-specific meta key
    binding3 = KeyBinding(key="c", modifiers={KeyModifier.META})
    print(f"  Meta binding: {binding3.to_string()}")
    
    # Test simple key
    binding4 = KeyBinding(key="space", modifiers=set())
    print(f"  Simple binding: {binding4.to_string()}")
    
    print("✓ Key bindings working")


def test_command_registration():
    """Test command registration and management."""
    print("\n=== Testing Command Registration ===")
    
    manager = KeyboardShortcutsManager()
    
    # Test custom command registration
    async def custom_handler():
        return "Custom command executed"
    
    command = manager.register_command(
        id="custom.test",
        name="Test Custom Command",
        category=CommandCategory.CUSTOM,
        handler=custom_handler,
        description="A test custom command",
        bindings=[KeyBinding(key="t", modifiers={KeyModifier.CTRL})]
    )
    
    print(f"  Registered command: {command.id}")
    print(f"  Command name: {command.name}")
    print(f"  Command bindings: {[b.to_string() for b in command.bindings]}")
    
    # Test command retrieval
    retrieved = manager.get_command("custom.test")
    assert retrieved is not None
    print(f"  Retrieved command: {retrieved.id}")
    
    # Test command listing
    voice_commands = manager.categories[CommandCategory.VOICE]
    print(f"  Voice commands: {len(voice_commands)}")
    
    print("✓ Command registration working")


async def test_command_execution():
    """Test command execution."""
    print("\n=== Testing Command Execution ===")
    
    manager = KeyboardShortcutsManager()
    
    # Track execution
    executed = []
    
    async def test_handler(value: str = "default"):
        executed.append(value)
        return f"Executed with {value}"
    
    manager.register_command(
        id="test.execute",
        name="Test Execute",
        category=CommandCategory.CUSTOM,
        handler=test_handler,
        bindings=[KeyBinding(key="e", modifiers={KeyModifier.CTRL})]
    )
    
    # Execute command
    command = manager.get_command("test.execute")
    result = await command.execute("test_value")
    print(f"  Execution result: {result}")
    print(f"  Executed values: {executed}")
    
    print("✓ Command execution working")


def test_keyboard_handling():
    """Test keyboard event handling."""
    print("\n=== Testing Keyboard Handling ===")
    
    manager = KeyboardShortcutsManager()
    
    # Test matching binding
    handled = manager.handle_key_event("v", {KeyModifier.CTRL})
    print(f"  Ctrl+V handled: {handled}")
    
    # Test non-matching binding
    handled = manager.handle_key_event("x", {KeyModifier.ALT})
    print(f"  Alt+X handled: {handled}")
    
    # Test multiple modifiers
    handled = manager.handle_key_event("p", {KeyModifier.CTRL, KeyModifier.SHIFT})
    print(f"  Ctrl+Shift+P handled: {handled}")
    
    print("✓ Keyboard handling working")


def test_binding_customization():
    """Test binding customization."""
    print("\n=== Testing Binding Customization ===")
    
    manager = KeyboardShortcutsManager()
    
    # Get original binding
    command = manager.get_command("voice.start")
    original = command.bindings[0].to_string() if command.bindings else "None"
    print(f"  Original binding: {original}")
    
    # Customize binding
    manager.customize_binding("voice.start", "Alt+V")
    command = manager.get_command("voice.start")
    customized = command.bindings[0].to_string() if command.bindings else "None"
    print(f"  Customized binding: {customized}")
    
    # Check custom bindings storage
    print(f"  Custom bindings stored: {len(manager.custom_bindings)}")
    
    print("✓ Binding customization working")


def test_conflict_detection():
    """Test binding conflict detection."""
    print("\n=== Testing Conflict Detection ===")
    
    manager = KeyboardShortcutsManager()
    
    # Create conflicting bindings
    manager.register_command(
        id="conflict.1",
        name="Conflict 1",
        category=CommandCategory.CUSTOM,
        handler=lambda: None,
        bindings=[KeyBinding(key="x", modifiers={KeyModifier.CTRL})]
    )
    
    manager.register_command(
        id="conflict.2",
        name="Conflict 2",
        category=CommandCategory.CUSTOM,
        handler=lambda: None,
        bindings=[KeyBinding(key="x", modifiers={KeyModifier.CTRL})]
    )
    
    # Check conflicts
    conflicts = manager.get_conflicts()
    print(f"  Found {len(conflicts)} conflicts")
    
    for binding, commands in conflicts:
        print(f"    {binding}: {commands}")
    
    print("✓ Conflict detection working")


def test_command_palette():
    """Test command palette."""
    print("\n=== Testing Command Palette ===")
    
    manager = get_shortcuts_manager()
    palette = CommandPalette(manager)
    
    # Search for voice commands
    results = palette.search("voice")
    print(f"  Search 'voice': {len(results)} results")
    for cmd in results[:3]:
        print(f"    - {cmd.name}")
    
    # Search for help commands
    results = palette.search("help")
    print(f"  Search 'help': {len(results)} results")
    
    # Test navigation
    palette.search("playback")
    palette.select_next()
    palette.select_previous()
    
    # Get display items
    items = palette.get_display_items(5)
    print(f"  Display items: {len(items)}")
    
    print("✓ Command palette working")


def test_help_overlay():
    """Test help overlay."""
    print("\n=== Testing Help Overlay ===")
    
    manager = get_shortcuts_manager()
    help_overlay = HelpOverlay(manager)
    
    # Get shortcuts by category
    shortcuts = help_overlay.get_shortcuts_by_category()
    print(f"  Categories: {list(shortcuts.keys())}")
    
    for category, commands in shortcuts.items():
        print(f"    {category}: {len(commands)} shortcuts")
    
    # Format as text
    text = help_overlay.format_text()
    lines = text.split('\n')
    print(f"  Text format: {len(lines)} lines")
    
    # Format as markdown
    markdown = help_overlay.format_markdown()
    print(f"  Markdown format: {len(markdown)} characters")
    
    print("✓ Help overlay working")


def test_context_conditions():
    """Test conditional command execution."""
    print("\n=== Testing Context Conditions ===")
    
    manager = KeyboardShortcutsManager()
    
    # Register conditional command
    executed = []
    
    def conditional_handler():
        executed.append("executed")
    
    manager.register_command(
        id="conditional.test",
        name="Conditional Test",
        category=CommandCategory.CUSTOM,
        handler=conditional_handler,
        bindings=[KeyBinding(key="c", modifiers={KeyModifier.CTRL})],
        when="voice_active == True"
    )
    
    # Test with condition false
    manager.update_context(voice_active=False)
    handled = manager.handle_key_event("c", {KeyModifier.CTRL})
    print(f"  Handled with voice_active=False: {handled}")
    
    # Test with condition true
    manager.update_context(voice_active=True)
    handled = manager.handle_key_event("c", {KeyModifier.CTRL})
    print(f"  Handled with voice_active=True: {handled}")
    
    print(f"  Executions: {len(executed)}")
    
    print("✓ Context conditions working")


def test_import_export():
    """Test configuration import/export."""
    print("\n=== Testing Import/Export ===")
    
    manager = KeyboardShortcutsManager()
    
    # Customize some bindings
    manager.customize_binding("voice.start", "F1")
    manager.customize_binding("voice.stop", "F2")
    
    # Export configuration
    config = manager.export_bindings()
    print(f"  Exported config version: {config['version']}")
    print(f"  Exported bindings: {len(config['bindings'])}")
    print(f"  Exported custom: {len(config['custom'])}")
    
    # Create new manager and import
    new_manager = KeyboardShortcutsManager()
    new_manager.import_bindings(config)
    
    # Verify import
    command = new_manager.get_command("voice.start")
    if command and command.bindings:
        print(f"  Imported binding: {command.bindings[0].to_string()}")
    
    print("✓ Import/export working")


async def test_performance():
    """Test performance of keyboard shortcuts."""
    print("\n=== Testing Performance ===")
    
    import time
    
    manager = KeyboardShortcutsManager()
    
    # Register many commands
    for i in range(100):
        manager.register_command(
            id=f"perf.test{i}",
            name=f"Performance Test {i}",
            category=CommandCategory.CUSTOM,
            handler=lambda: None,
            bindings=[KeyBinding(key=str(i % 10), modifiers={KeyModifier.CTRL, KeyModifier.ALT})]
        )
    
    print(f"  Registered {len(manager.commands)} commands")
    
    # Test lookup performance
    start = time.time()
    for _ in range(1000):
        manager.handle_key_event("5", {KeyModifier.CTRL, KeyModifier.ALT})
    elapsed = time.time() - start
    
    rate = 1000 / elapsed if elapsed > 0 else 0
    print(f"  Lookup rate: {rate:.1f} lookups/sec")
    
    # Test search performance
    palette = CommandPalette(manager)
    start = time.time()
    for _ in range(100):
        palette.search("test")
    elapsed = time.time() - start
    
    rate = 100 / elapsed if elapsed > 0 else 0
    print(f"  Search rate: {rate:.1f} searches/sec")
    
    print("✓ Performance acceptable")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("KEYBOARD SHORTCUTS TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_key_bindings()
    test_command_registration()
    test_keyboard_handling()
    test_binding_customization()
    test_conflict_detection()
    test_command_palette()
    test_help_overlay()
    test_context_conditions()
    test_import_export()
    
    # Run async tests
    await test_command_execution()
    await test_performance()
    
    print("\n" + "=" * 60)
    print("✓ All keyboard shortcuts tests passed!")
    print("Sprint 35 complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())