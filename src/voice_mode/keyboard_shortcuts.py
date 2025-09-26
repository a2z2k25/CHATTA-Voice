"""
Keyboard shortcuts and command system for voice mode.

This module provides a comprehensive keyboard control system with customizable
shortcuts, command palette, and help overlays for voice interactions.
"""

import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
import json
import os
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


class KeyModifier(Enum):
    """Keyboard modifiers."""
    NONE = auto()
    CTRL = auto()
    ALT = auto()
    SHIFT = auto()
    META = auto()  # Cmd on Mac, Win on Windows
    

class CommandCategory(Enum):
    """Command categories for organization."""
    VOICE = auto()
    PLAYBACK = auto()
    NAVIGATION = auto()
    EDITING = auto()
    SYSTEM = auto()
    HELP = auto()
    CUSTOM = auto()


@dataclass
class KeyBinding:
    """Single key binding definition."""
    key: str
    modifiers: Set[KeyModifier] = field(default_factory=set)
    description: str = ""
    
    def to_string(self) -> str:
        """Convert to human-readable string.
        
        Returns:
            String representation like "Ctrl+Shift+P"
        """
        parts = []
        if KeyModifier.CTRL in self.modifiers:
            parts.append("Ctrl")
        if KeyModifier.ALT in self.modifiers:
            parts.append("Alt")
        if KeyModifier.SHIFT in self.modifiers:
            parts.append("Shift")
        if KeyModifier.META in self.modifiers:
            parts.append("Cmd" if os.name == "darwin" else "Win")
        parts.append(self.key.upper())
        return "+".join(parts)
    
    @classmethod
    def from_string(cls, binding_str: str) -> "KeyBinding":
        """Parse from string representation.
        
        Args:
            binding_str: String like "Ctrl+Shift+P"
            
        Returns:
            KeyBinding instance
        """
        parts = binding_str.lower().split("+")
        modifiers = set()
        
        for part in parts[:-1]:
            if part in ["ctrl", "control"]:
                modifiers.add(KeyModifier.CTRL)
            elif part == "alt":
                modifiers.add(KeyModifier.ALT)
            elif part == "shift":
                modifiers.add(KeyModifier.SHIFT)
            elif part in ["cmd", "meta", "win", "windows"]:
                modifiers.add(KeyModifier.META)
        
        key = parts[-1] if parts else ""
        return cls(key=key, modifiers=modifiers)


@dataclass
class Command:
    """Command definition."""
    id: str
    name: str
    category: CommandCategory
    handler: Callable[..., Any]
    description: str = ""
    bindings: List[KeyBinding] = field(default_factory=list)
    enabled: bool = True
    visible: bool = True
    when: Optional[str] = None  # Condition expression
    
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the command.
        
        Args:
            *args: Command arguments
            **kwargs: Command keyword arguments
            
        Returns:
            Command result
        """
        if not self.enabled:
            logger.warning(f"Command {self.id} is disabled")
            return None
        
        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(*args, **kwargs)
        else:
            return self.handler(*args, **kwargs)


class KeyboardShortcutsManager:
    """Manages keyboard shortcuts and commands."""
    
    def __init__(self):
        """Initialize keyboard shortcuts manager."""
        self.commands: Dict[str, Command] = {}
        self.bindings: Dict[str, List[str]] = {}  # binding -> command IDs
        self.categories: Dict[CommandCategory, List[str]] = {
            cat: [] for cat in CommandCategory
        }
        self.custom_bindings: Dict[str, Dict[str, str]] = {}
        self.lock = threading.Lock()
        
        # Context for conditional commands
        self.context: Dict[str, Any] = {
            "voice_active": False,
            "recording": False,
            "playing": False,
            "connected": False,
            "mode": "normal"
        }
        
        # Register default commands
        self._register_default_commands()
    
    def _register_default_commands(self):
        """Register default voice mode commands."""
        
        # Voice commands
        self.register_command(
            id="voice.start",
            name="Start Voice Conversation",
            category=CommandCategory.VOICE,
            handler=self._start_voice,
            description="Start a new voice conversation",
            bindings=[KeyBinding(key="v", modifiers={KeyModifier.CTRL})]
        )
        
        self.register_command(
            id="voice.stop",
            name="Stop Voice Conversation",
            category=CommandCategory.VOICE,
            handler=self._stop_voice,
            description="Stop the current voice conversation",
            bindings=[KeyBinding(key="v", modifiers={KeyModifier.CTRL, KeyModifier.SHIFT})]
        )
        
        self.register_command(
            id="voice.toggle_mute",
            name="Toggle Mute",
            category=CommandCategory.VOICE,
            handler=self._toggle_mute,
            description="Toggle microphone mute",
            bindings=[KeyBinding(key="m", modifiers={KeyModifier.CTRL})]
        )
        
        # Playback commands
        self.register_command(
            id="playback.pause",
            name="Pause/Resume Playback",
            category=CommandCategory.PLAYBACK,
            handler=self._toggle_playback,
            description="Pause or resume audio playback",
            bindings=[KeyBinding(key="space", modifiers=set())]
        )
        
        self.register_command(
            id="playback.stop",
            name="Stop Playback",
            category=CommandCategory.PLAYBACK,
            handler=self._stop_playback,
            description="Stop audio playback",
            bindings=[KeyBinding(key="s", modifiers={KeyModifier.CTRL})]
        )
        
        self.register_command(
            id="playback.volume_up",
            name="Increase Volume",
            category=CommandCategory.PLAYBACK,
            handler=self._volume_up,
            description="Increase playback volume",
            bindings=[KeyBinding(key="+", modifiers=set())]
        )
        
        self.register_command(
            id="playback.volume_down",
            name="Decrease Volume",
            category=CommandCategory.PLAYBACK,
            handler=self._volume_down,
            description="Decrease playback volume",
            bindings=[KeyBinding(key="-", modifiers=set())]
        )
        
        # Navigation commands
        self.register_command(
            id="nav.transcript_up",
            name="Scroll Transcript Up",
            category=CommandCategory.NAVIGATION,
            handler=self._scroll_transcript_up,
            description="Scroll transcript up",
            bindings=[KeyBinding(key="up", modifiers={KeyModifier.CTRL})]
        )
        
        self.register_command(
            id="nav.transcript_down",
            name="Scroll Transcript Down",
            category=CommandCategory.NAVIGATION,
            handler=self._scroll_transcript_down,
            description="Scroll transcript down",
            bindings=[KeyBinding(key="down", modifiers={KeyModifier.CTRL})]
        )
        
        # System commands
        self.register_command(
            id="system.command_palette",
            name="Open Command Palette",
            category=CommandCategory.SYSTEM,
            handler=self._open_command_palette,
            description="Open the command palette",
            bindings=[
                KeyBinding(key="p", modifiers={KeyModifier.CTRL, KeyModifier.SHIFT}),
                KeyBinding(key="p", modifiers={KeyModifier.META, KeyModifier.SHIFT})
            ]
        )
        
        # Help commands
        self.register_command(
            id="help.show",
            name="Show Help",
            category=CommandCategory.HELP,
            handler=self._show_help,
            description="Show keyboard shortcuts help",
            bindings=[KeyBinding(key="?", modifiers={KeyModifier.SHIFT})]
        )
        
        self.register_command(
            id="help.search",
            name="Search Commands",
            category=CommandCategory.HELP,
            handler=self._search_commands,
            description="Search available commands",
            bindings=[KeyBinding(key="f", modifiers={KeyModifier.CTRL, KeyModifier.SHIFT})]
        )
    
    def register_command(
        self,
        id: str,
        name: str,
        category: CommandCategory,
        handler: Callable,
        description: str = "",
        bindings: Optional[List[KeyBinding]] = None,
        enabled: bool = True,
        visible: bool = True,
        when: Optional[str] = None
    ) -> Command:
        """Register a new command.
        
        Args:
            id: Unique command identifier
            name: Display name
            category: Command category
            handler: Command handler function
            description: Command description
            bindings: Key bindings
            enabled: Whether command is enabled
            visible: Whether command is visible
            when: Condition expression
            
        Returns:
            Registered command
        """
        command = Command(
            id=id,
            name=name,
            category=category,
            handler=handler,
            description=description,
            bindings=bindings or [],
            enabled=enabled,
            visible=visible,
            when=when
        )
        
        with self.lock:
            self.commands[id] = command
            self.categories[category].append(id)
            
            # Register bindings
            for binding in command.bindings:
                binding_key = binding.to_string()
                if binding_key not in self.bindings:
                    self.bindings[binding_key] = []
                self.bindings[binding_key].append(id)
        
        logger.info(f"Registered command: {id}")
        return command
    
    def unregister_command(self, command_id: str):
        """Unregister a command.
        
        Args:
            command_id: Command identifier
        """
        with self.lock:
            if command_id in self.commands:
                command = self.commands[command_id]
                
                # Remove from category
                self.categories[command.category].remove(command_id)
                
                # Remove bindings
                for binding in command.bindings:
                    binding_key = binding.to_string()
                    if binding_key in self.bindings:
                        self.bindings[binding_key].remove(command_id)
                        if not self.bindings[binding_key]:
                            del self.bindings[binding_key]
                
                del self.commands[command_id]
                logger.info(f"Unregistered command: {command_id}")
    
    def get_command(self, command_id: str) -> Optional[Command]:
        """Get command by ID.
        
        Args:
            command_id: Command identifier
            
        Returns:
            Command or None
        """
        return self.commands.get(command_id)
    
    def get_commands_for_binding(self, binding: Union[str, KeyBinding]) -> List[Command]:
        """Get commands for a key binding.
        
        Args:
            binding: Key binding string or object
            
        Returns:
            List of commands
        """
        if isinstance(binding, KeyBinding):
            binding_key = binding.to_string()
        else:
            binding_key = binding
        
        command_ids = self.bindings.get(binding_key, [])
        return [self.commands[id] for id in command_ids if id in self.commands]
    
    def handle_key_event(self, key: str, modifiers: Set[KeyModifier]) -> bool:
        """Handle keyboard event.
        
        Args:
            key: Key pressed
            modifiers: Active modifiers
            
        Returns:
            True if event was handled
        """
        binding = KeyBinding(key=key.lower(), modifiers=modifiers)
        binding_key = binding.to_string()
        
        commands = self.get_commands_for_binding(binding_key)
        
        # Filter by context conditions
        enabled_commands = []
        for command in commands:
            if not command.enabled:
                continue
            
            if command.when and not self._evaluate_condition(command.when):
                continue
            
            enabled_commands.append(command)
        
        if not enabled_commands:
            return False
        
        # Handle conflicts
        if len(enabled_commands) > 1:
            logger.warning(f"Multiple commands for binding {binding_key}")
            # Use first enabled command
        
        command = enabled_commands[0]
        
        # Execute command
        try:
            asyncio.create_task(command.execute())
            logger.info(f"Executed command: {command.id}")
            return True
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return False
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression.
        
        Args:
            condition: Condition expression
            
        Returns:
            True if condition is met
        """
        try:
            # Simple expression evaluation
            # In production, use a proper expression parser
            for key, value in self.context.items():
                condition = condition.replace(key, str(value))
            return eval(condition)
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return False
    
    def update_context(self, **kwargs):
        """Update context for conditional commands.
        
        Args:
            **kwargs: Context updates
        """
        self.context.update(kwargs)
    
    def customize_binding(self, command_id: str, new_binding: Union[str, KeyBinding]):
        """Customize a command's key binding.
        
        Args:
            command_id: Command identifier
            new_binding: New binding
        """
        if command_id not in self.commands:
            raise ValueError(f"Unknown command: {command_id}")
        
        command = self.commands[command_id]
        
        if isinstance(new_binding, str):
            new_binding = KeyBinding.from_string(new_binding)
        
        with self.lock:
            # Remove old bindings
            for binding in command.bindings:
                binding_key = binding.to_string()
                if binding_key in self.bindings:
                    self.bindings[binding_key].remove(command_id)
                    if not self.bindings[binding_key]:
                        del self.bindings[binding_key]
            
            # Add new binding
            command.bindings = [new_binding]
            binding_key = new_binding.to_string()
            if binding_key not in self.bindings:
                self.bindings[binding_key] = []
            self.bindings[binding_key].append(command_id)
            
            # Store customization
            if command_id not in self.custom_bindings:
                self.custom_bindings[command_id] = {}
            self.custom_bindings[command_id]["binding"] = binding_key
    
    def get_conflicts(self) -> List[Tuple[str, List[str]]]:
        """Get binding conflicts.
        
        Returns:
            List of (binding, [command_ids]) with conflicts
        """
        conflicts = []
        for binding_key, command_ids in self.bindings.items():
            if len(command_ids) > 1:
                conflicts.append((binding_key, command_ids))
        return conflicts
    
    def export_bindings(self) -> Dict[str, Any]:
        """Export key bindings configuration.
        
        Returns:
            Bindings configuration
        """
        config = {
            "version": "1.0",
            "bindings": {},
            "custom": self.custom_bindings
        }
        
        for command_id, command in self.commands.items():
            if command.bindings:
                config["bindings"][command_id] = [
                    b.to_string() for b in command.bindings
                ]
        
        return config
    
    def import_bindings(self, config: Dict[str, Any]):
        """Import key bindings configuration.
        
        Args:
            config: Bindings configuration
        """
        if config.get("version") != "1.0":
            raise ValueError("Unsupported configuration version")
        
        # Apply custom bindings
        for command_id, custom in config.get("custom", {}).items():
            if command_id in self.commands and "binding" in custom:
                self.customize_binding(command_id, custom["binding"])
    
    # Command handlers
    async def _start_voice(self):
        """Start voice conversation."""
        logger.info("Starting voice conversation")
        self.update_context(voice_active=True, recording=True)
    
    async def _stop_voice(self):
        """Stop voice conversation."""
        logger.info("Stopping voice conversation")
        self.update_context(voice_active=False, recording=False)
    
    async def _toggle_mute(self):
        """Toggle mute."""
        logger.info("Toggling mute")
    
    async def _toggle_playback(self):
        """Toggle playback."""
        logger.info("Toggling playback")
    
    async def _stop_playback(self):
        """Stop playback."""
        logger.info("Stopping playback")
        self.update_context(playing=False)
    
    async def _volume_up(self):
        """Increase volume."""
        logger.info("Increasing volume")
    
    async def _volume_down(self):
        """Decrease volume."""
        logger.info("Decreasing volume")
    
    async def _scroll_transcript_up(self):
        """Scroll transcript up."""
        logger.info("Scrolling transcript up")
    
    async def _scroll_transcript_down(self):
        """Scroll transcript down."""
        logger.info("Scrolling transcript down")
    
    async def _open_command_palette(self):
        """Open command palette."""
        logger.info("Opening command palette")
    
    async def _show_help(self):
        """Show help overlay."""
        logger.info("Showing help")
    
    async def _search_commands(self):
        """Search commands."""
        logger.info("Searching commands")


class CommandPalette:
    """Command palette for discovering and executing commands."""
    
    def __init__(self, manager: KeyboardShortcutsManager):
        """Initialize command palette.
        
        Args:
            manager: Keyboard shortcuts manager
        """
        self.manager = manager
        self.search_query = ""
        self.filtered_commands: List[Command] = []
        self.selected_index = 0
    
    def search(self, query: str) -> List[Command]:
        """Search commands.
        
        Args:
            query: Search query
            
        Returns:
            Matching commands
        """
        self.search_query = query.lower()
        self.filtered_commands = []
        
        for command in self.manager.commands.values():
            if not command.visible:
                continue
            
            # Search in name, description, and category
            if (self.search_query in command.name.lower() or
                self.search_query in command.description.lower() or
                self.search_query in command.category.name.lower()):
                self.filtered_commands.append(command)
        
        # Sort by relevance
        self.filtered_commands.sort(key=lambda c: (
            not c.name.lower().startswith(self.search_query),
            c.name.lower()
        ))
        
        self.selected_index = 0
        return self.filtered_commands
    
    def select_next(self):
        """Select next command."""
        if self.filtered_commands:
            self.selected_index = (self.selected_index + 1) % len(self.filtered_commands)
    
    def select_previous(self):
        """Select previous command."""
        if self.filtered_commands:
            self.selected_index = (self.selected_index - 1) % len(self.filtered_commands)
    
    async def execute_selected(self):
        """Execute selected command."""
        if self.filtered_commands and 0 <= self.selected_index < len(self.filtered_commands):
            command = self.filtered_commands[self.selected_index]
            await command.execute()
    
    def get_display_items(self, max_items: int = 10) -> List[Dict[str, str]]:
        """Get display items for palette.
        
        Args:
            max_items: Maximum items to display
            
        Returns:
            List of display items
        """
        items = []
        
        for i, command in enumerate(self.filtered_commands[:max_items]):
            bindings_str = ", ".join(b.to_string() for b in command.bindings[:2])
            
            items.append({
                "name": command.name,
                "description": command.description,
                "category": command.category.name,
                "bindings": bindings_str,
                "selected": i == self.selected_index
            })
        
        return items


class HelpOverlay:
    """Help overlay showing keyboard shortcuts."""
    
    def __init__(self, manager: KeyboardShortcutsManager):
        """Initialize help overlay.
        
        Args:
            manager: Keyboard shortcuts manager
        """
        self.manager = manager
    
    def get_shortcuts_by_category(self) -> Dict[str, List[Dict[str, str]]]:
        """Get shortcuts organized by category.
        
        Returns:
            Shortcuts by category
        """
        shortcuts = {}
        
        for category in CommandCategory:
            category_commands = []
            
            for command_id in self.manager.categories[category]:
                command = self.manager.commands.get(command_id)
                if not command or not command.visible or not command.bindings:
                    continue
                
                category_commands.append({
                    "name": command.name,
                    "bindings": " / ".join(b.to_string() for b in command.bindings),
                    "description": command.description
                })
            
            if category_commands:
                shortcuts[category.name] = category_commands
        
        return shortcuts
    
    def format_text(self) -> str:
        """Format help as text.
        
        Returns:
            Formatted help text
        """
        lines = ["Keyboard Shortcuts", "=" * 40, ""]
        
        shortcuts = self.get_shortcuts_by_category()
        
        for category, commands in shortcuts.items():
            lines.append(f"{category}:")
            for cmd in commands:
                bindings = cmd["bindings"].ljust(20)
                name = cmd["name"]
                lines.append(f"  {bindings} {name}")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_markdown(self) -> str:
        """Format help as markdown.
        
        Returns:
            Formatted markdown
        """
        lines = ["# Keyboard Shortcuts\n"]
        
        shortcuts = self.get_shortcuts_by_category()
        
        for category, commands in shortcuts.items():
            lines.append(f"## {category}\n")
            lines.append("| Shortcut | Command | Description |")
            lines.append("|----------|---------|-------------|")
            
            for cmd in commands:
                bindings = cmd["bindings"]
                name = cmd["name"]
                desc = cmd["description"]
                lines.append(f"| `{bindings}` | {name} | {desc} |")
            
            lines.append("")
        
        return "\n".join(lines)


# Global instance
_shortcuts_manager: Optional[KeyboardShortcutsManager] = None


def get_shortcuts_manager() -> KeyboardShortcutsManager:
    """Get global shortcuts manager.
    
    Returns:
        Shortcuts manager instance
    """
    global _shortcuts_manager
    if _shortcuts_manager is None:
        _shortcuts_manager = KeyboardShortcutsManager()
    return _shortcuts_manager


# Example usage
if __name__ == "__main__":
    # Create manager
    manager = get_shortcuts_manager()
    
    # Show current bindings
    help_overlay = HelpOverlay(manager)
    print(help_overlay.format_text())
    
    # Test command palette
    palette = CommandPalette(manager)
    results = palette.search("voice")
    print(f"\nSearch results for 'voice': {len(results)} commands")
    for cmd in results:
        print(f"  - {cmd.name}")
    
    # Check for conflicts
    conflicts = manager.get_conflicts()
    if conflicts:
        print("\nBinding conflicts:")
        for binding, commands in conflicts:
            print(f"  {binding}: {commands}")
    
    # Export configuration
    config = manager.export_bindings()
    print(f"\nExported {len(config['bindings'])} bindings")