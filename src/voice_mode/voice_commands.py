"""
Voice Commands System for CHATTA 1.0

This module provides comprehensive voice command recognition and execution,
enabling natural language control of the voice interaction system.
"""

import asyncio
import re
import time
import logging
from typing import Dict, List, Optional, Callable, Any, Set, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import threading
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class CommandCategory(Enum):
    """Voice command categories."""
    VOICE_CONTROL = auto()      # Start/stop voice, mute, etc.
    CONVERSATION = auto()       # Clear, save, export conversation
    PLAYBACK = auto()          # Play/pause/stop TTS
    NAVIGATION = auto()        # Next/previous, scroll, etc.
    SETTINGS = auto()          # Change preferences, volume, etc.
    SYSTEM = auto()            # Help, status, exit
    CUSTOM = auto()            # User-defined commands


class CommandPriority(Enum):
    """Command execution priority."""
    CRITICAL = auto()    # Emergency stop, exit
    HIGH = auto()        # Voice control, system commands  
    NORMAL = auto()      # Most commands
    LOW = auto()         # Non-essential commands


class CommandContext(Enum):
    """Execution context for commands."""
    IDLE = auto()        # No active conversation
    LISTENING = auto()   # Waiting for user input
    SPEAKING = auto()    # AI is speaking
    PROCESSING = auto()  # AI is processing request
    ANY = auto()         # Command works in any context


@dataclass
class CommandMatch:
    """Represents a matched voice command."""
    command_id: str
    confidence: float
    matched_text: str
    extracted_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class VoiceCommand:
    """Definition of a voice command."""
    id: str
    name: str
    category: CommandCategory
    priority: CommandPriority
    patterns: List[str]  # Regex patterns or keywords
    handler: Callable
    description: str = ""
    aliases: List[str] = field(default_factory=list)
    contexts: Set[CommandContext] = field(default_factory=lambda: {CommandContext.ANY})
    enabled: bool = True
    parameters: Dict[str, type] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    
    def matches(self, text: str, current_context: CommandContext) -> Optional[CommandMatch]:
        """Check if command matches the given text.
        
        Args:
            text: Input text to match
            current_context: Current system context
            
        Returns:
            CommandMatch if matched, None otherwise
        """
        if not self.enabled:
            return None
            
        # Check context compatibility
        if CommandContext.ANY not in self.contexts and current_context not in self.contexts:
            return None
            
        text_lower = text.lower().strip()
        
        # Try each pattern
        for pattern in self.patterns:
            pattern_lower = pattern.lower()
            
            # Direct keyword match
            if pattern_lower in text_lower:
                confidence = len(pattern_lower) / len(text_lower)
                return CommandMatch(
                    command_id=self.id,
                    confidence=confidence,
                    matched_text=pattern_lower
                )
                
            # Regex match
            try:
                regex_match = re.search(pattern_lower, text_lower)
                if regex_match:
                    # Extract parameters from named groups
                    params = regex_match.groupdict()
                    confidence = len(regex_match.group(0)) / len(text_lower)
                    
                    return CommandMatch(
                        command_id=self.id,
                        confidence=confidence,
                        matched_text=regex_match.group(0),
                        extracted_params=params
                    )
            except re.error:
                # Pattern is not a valid regex, skip
                continue
        
        # Try aliases
        for alias in self.aliases:
            if alias.lower() in text_lower:
                confidence = len(alias) / len(text_lower)
                return CommandMatch(
                    command_id=self.id,
                    confidence=confidence,
                    matched_text=alias.lower()
                )
        
        return None


class CommandExecutionError(Exception):
    """Error during command execution."""
    pass


class VoiceCommandEngine:
    """Core voice command recognition and execution engine."""
    
    def __init__(self, confidence_threshold: float = 0.3):
        """Initialize command engine.
        
        Args:
            confidence_threshold: Minimum confidence for command execution
        """
        self.commands: Dict[str, VoiceCommand] = {}
        self.categories: Dict[CommandCategory, List[VoiceCommand]] = {
            category: [] for category in CommandCategory
        }
        self.confidence_threshold = confidence_threshold
        self.current_context = CommandContext.IDLE
        self.execution_history: List[CommandMatch] = []
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'commands_registered': 0,
            'commands_executed': 0,
            'recognition_attempts': 0,
            'successful_matches': 0,
            'failed_matches': 0,
            'execution_errors': 0
        }
        
        # Built-in command handlers
        self._register_builtin_commands()
    
    def register_command(
        self,
        id: str,
        name: str,
        category: CommandCategory,
        priority: CommandPriority,
        patterns: List[str],
        handler: Callable,
        description: str = "",
        aliases: Optional[List[str]] = None,
        contexts: Optional[Set[CommandContext]] = None,
        parameters: Optional[Dict[str, type]] = None,
        examples: Optional[List[str]] = None
    ) -> VoiceCommand:
        """Register a new voice command.
        
        Args:
            id: Unique command identifier
            name: Human-readable name
            category: Command category
            priority: Execution priority
            patterns: List of matching patterns (regex or keywords)
            handler: Function to execute when command matches
            description: Command description
            aliases: Alternative triggers
            contexts: Valid execution contexts
            parameters: Expected parameters and their types
            examples: Usage examples
            
        Returns:
            Created VoiceCommand
        """
        command = VoiceCommand(
            id=id,
            name=name,
            category=category,
            priority=priority,
            patterns=patterns,
            handler=handler,
            description=description,
            aliases=aliases or [],
            contexts=contexts or {CommandContext.ANY},
            parameters=parameters or {},
            examples=examples or []
        )
        
        with self.lock:
            self.commands[id] = command
            self.categories[category].append(command)
            self.stats['commands_registered'] += 1
        
        logger.info(f"Registered voice command: {id} ({category.name})")
        return command
    
    def unregister_command(self, command_id: str) -> bool:
        """Unregister a voice command.
        
        Args:
            command_id: Command to remove
            
        Returns:
            True if command was removed
        """
        with self.lock:
            if command_id in self.commands:
                command = self.commands[command_id]
                del self.commands[command_id]
                self.categories[command.category].remove(command)
                self.stats['commands_registered'] -= 1
                logger.info(f"Unregistered voice command: {command_id}")
                return True
        return False
    
    def get_command(self, command_id: str) -> Optional[VoiceCommand]:
        """Get command by ID.
        
        Args:
            command_id: Command identifier
            
        Returns:
            VoiceCommand if found
        """
        return self.commands.get(command_id)
    
    def get_commands_by_category(self, category: CommandCategory) -> List[VoiceCommand]:
        """Get all commands in a category.
        
        Args:
            category: Command category
            
        Returns:
            List of commands
        """
        return self.categories.get(category, []).copy()
    
    def set_context(self, context: CommandContext):
        """Update current execution context.
        
        Args:
            context: New context
        """
        old_context = self.current_context
        self.current_context = context
        logger.debug(f"Context changed: {old_context.name} -> {context.name}")
    
    async def recognize_command(self, text: str) -> List[CommandMatch]:
        """Recognize voice commands in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of matched commands sorted by confidence
        """
        if not text or not text.strip():
            return []
        
        self.stats['recognition_attempts'] += 1
        matches = []
        
        with self.lock:
            commands_to_check = list(self.commands.values())
        
        # Find all matches
        for command in commands_to_check:
            match = command.matches(text, self.current_context)
            if match and match.confidence >= self.confidence_threshold:
                matches.append(match)
        
        # Sort by confidence and priority
        def sort_key(match):
            command = self.commands[match.command_id]
            priority_weight = {
                CommandPriority.CRITICAL: 1000,
                CommandPriority.HIGH: 100,
                CommandPriority.NORMAL: 10,
                CommandPriority.LOW: 1
            }[command.priority]
            return match.confidence + (priority_weight * 0.001)
        
        matches.sort(key=sort_key, reverse=True)
        
        if matches:
            self.stats['successful_matches'] += 1
            logger.info(f"Found {len(matches)} command matches for: '{text}'")
        else:
            self.stats['failed_matches'] += 1
            logger.debug(f"No command matches for: '{text}'")
        
        return matches
    
    async def execute_command(
        self,
        match: CommandMatch,
        **kwargs
    ) -> Any:
        """Execute a matched command.
        
        Args:
            match: Matched command to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Command execution result
        """
        command = self.commands.get(match.command_id)
        if not command:
            raise CommandExecutionError(f"Command not found: {match.command_id}")
        
        if not command.enabled:
            raise CommandExecutionError(f"Command disabled: {match.command_id}")
        
        logger.info(f"Executing command: {command.name} (confidence: {match.confidence:.2f})")
        
        try:
            # Prepare parameters
            params = {**match.extracted_params, **kwargs}
            
            # Execute command
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(command.handler):
                result = await command.handler(**params)
            else:
                result = command.handler(**params)
            
            execution_time = time.time() - start_time
            
            # Update statistics
            self.stats['commands_executed'] += 1
            
            # Record in history
            with self.lock:
                self.execution_history.append(match)
                # Keep only recent history
                if len(self.execution_history) > 1000:
                    self.execution_history = self.execution_history[-500:]
            
            logger.info(f"Command executed successfully in {execution_time:.3f}s: {command.name}")
            return result
            
        except Exception as e:
            self.stats['execution_errors'] += 1
            error_msg = f"Command execution failed: {command.name} - {str(e)}"
            logger.error(error_msg)
            raise CommandExecutionError(error_msg) from e
    
    async def process_voice_input(self, text: str) -> List[Any]:
        """Process voice input and execute matching commands.
        
        Args:
            text: Voice input text
            
        Returns:
            List of execution results
        """
        matches = await self.recognize_command(text)
        results = []
        
        for match in matches:
            try:
                result = await self.execute_command(match)
                results.append(result)
                
                # Only execute highest priority match for most categories
                command = self.commands[match.command_id]
                if command.priority in [CommandPriority.CRITICAL, CommandPriority.HIGH]:
                    break
                    
            except CommandExecutionError as e:
                logger.error(f"Command execution error: {e}")
                results.append(None)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.lock:
            history_by_command = {}
            for match in self.execution_history[-100:]:  # Recent history
                cmd_id = match.command_id
                if cmd_id not in history_by_command:
                    history_by_command[cmd_id] = 0
                history_by_command[cmd_id] += 1
        
        return {
            **self.stats.copy(),
            'current_context': self.current_context.name,
            'confidence_threshold': self.confidence_threshold,
            'recent_commands': history_by_command,
            'commands_by_category': {
                cat.name: len(commands) 
                for cat, commands in self.categories.items()
            }
        }
    
    def _register_builtin_commands(self):
        """Register built-in voice commands."""
        
        # Voice Control Commands
        self.register_command(
            id="voice.start",
            name="Start Voice Mode",
            category=CommandCategory.VOICE_CONTROL,
            priority=CommandPriority.HIGH,
            patterns=[r"start voice", r"begin voice", r"voice on"],
            handler=self._handle_voice_start,
            description="Start voice interaction mode",
            contexts={CommandContext.IDLE},
            examples=["start voice", "begin voice mode", "turn voice on"]
        )
        
        self.register_command(
            id="voice.stop",
            name="Stop Voice Mode", 
            category=CommandCategory.VOICE_CONTROL,
            priority=CommandPriority.HIGH,
            patterns=[r"stop voice", r"end voice", r"voice off", r"quiet"],
            handler=self._handle_voice_stop,
            description="Stop voice interaction mode",
            contexts={CommandContext.LISTENING, CommandContext.SPEAKING},
            examples=["stop voice", "end voice mode", "turn voice off", "quiet"]
        )
        
        self.register_command(
            id="voice.mute",
            name="Mute Audio",
            category=CommandCategory.VOICE_CONTROL,
            priority=CommandPriority.HIGH,
            patterns=[r"mute", r"silence", r"shut up"],
            handler=self._handle_mute,
            description="Mute audio output",
            contexts={CommandContext.SPEAKING},
            examples=["mute", "silence", "shut up"]
        )
        
        # Conversation Commands
        self.register_command(
            id="conversation.clear",
            name="Clear Conversation",
            category=CommandCategory.CONVERSATION,
            priority=CommandPriority.NORMAL,
            patterns=[r"clear conversation", r"clear chat", r"new conversation"],
            handler=self._handle_clear_conversation,
            description="Clear current conversation history",
            examples=["clear conversation", "clear chat", "new conversation"]
        )
        
        self.register_command(
            id="conversation.save",
            name="Save Conversation",
            category=CommandCategory.CONVERSATION,
            priority=CommandPriority.NORMAL,
            patterns=[r"save conversation", r"export chat"],
            handler=self._handle_save_conversation,
            description="Save conversation to file",
            examples=["save conversation", "export chat"]
        )
        
        # Playback Commands
        self.register_command(
            id="playback.pause",
            name="Pause Playback",
            category=CommandCategory.PLAYBACK,
            priority=CommandPriority.HIGH,
            patterns=[r"pause", r"hold on", r"wait"],
            handler=self._handle_pause,
            description="Pause TTS playback",
            contexts={CommandContext.SPEAKING},
            examples=["pause", "hold on", "wait"]
        )
        
        self.register_command(
            id="playback.resume",
            name="Resume Playback",
            category=CommandCategory.PLAYBACK,
            priority=CommandPriority.HIGH,
            patterns=[r"resume", r"continue", r"go on"],
            handler=self._handle_resume,
            description="Resume TTS playback",
            contexts={CommandContext.IDLE},
            examples=["resume", "continue", "go on"]
        )
        
        # Settings Commands
        self.register_command(
            id="settings.volume_up",
            name="Volume Up",
            category=CommandCategory.SETTINGS,
            priority=CommandPriority.NORMAL,
            patterns=[r"volume up", r"louder", r"increase volume"],
            handler=self._handle_volume_up,
            description="Increase audio volume",
            examples=["volume up", "louder", "increase volume"]
        )
        
        self.register_command(
            id="settings.volume_down",
            name="Volume Down",
            category=CommandCategory.SETTINGS,
            priority=CommandPriority.NORMAL,
            patterns=[r"volume down", r"quieter", r"decrease volume"],
            handler=self._handle_volume_down,
            description="Decrease audio volume",
            examples=["volume down", "quieter", "decrease volume"]
        )
        
        # System Commands
        self.register_command(
            id="system.help",
            name="Show Help",
            category=CommandCategory.SYSTEM,
            priority=CommandPriority.NORMAL,
            patterns=[r"help", r"commands", r"what can you do"],
            handler=self._handle_help,
            description="Show available voice commands",
            examples=["help", "show commands", "what can you do"]
        )
        
        self.register_command(
            id="system.status",
            name="System Status",
            category=CommandCategory.SYSTEM,
            priority=CommandPriority.NORMAL,
            patterns=[r"status", r"how are you", r"system status"],
            handler=self._handle_status,
            description="Show system status",
            examples=["status", "how are you", "system status"]
        )
        
        logger.info("Built-in voice commands registered")
    
    # Built-in command handlers
    async def _handle_voice_start(self) -> str:
        """Handle voice start command."""
        self.set_context(CommandContext.LISTENING)
        return "Voice mode started"
    
    async def _handle_voice_stop(self) -> str:
        """Handle voice stop command."""
        self.set_context(CommandContext.IDLE)
        return "Voice mode stopped"
    
    async def _handle_mute(self) -> str:
        """Handle mute command."""
        return "Audio muted"
    
    async def _handle_clear_conversation(self) -> str:
        """Handle clear conversation command."""
        return "Conversation cleared"
    
    async def _handle_save_conversation(self) -> str:
        """Handle save conversation command."""
        return "Conversation saved"
    
    async def _handle_pause(self) -> str:
        """Handle pause command."""
        return "Playback paused"
    
    async def _handle_resume(self) -> str:
        """Handle resume command."""
        return "Playback resumed"
    
    async def _handle_volume_up(self) -> str:
        """Handle volume up command."""
        return "Volume increased"
    
    async def _handle_volume_down(self) -> str:
        """Handle volume down command."""
        return "Volume decreased"
    
    async def _handle_help(self) -> str:
        """Handle help command."""
        commands_by_cat = {}
        for category, commands in self.categories.items():
            if commands:
                commands_by_cat[category.name] = [
                    f"• {cmd.name}: {cmd.description}" 
                    for cmd in commands if cmd.enabled
                ]
        
        help_text = "Available voice commands:\n"
        for category, command_list in commands_by_cat.items():
            if command_list:
                help_text += f"\n{category}:\n" + "\n".join(command_list) + "\n"
        
        return help_text
    
    async def _handle_status(self) -> str:
        """Handle status command."""
        stats = self.get_statistics()
        return (
            f"System Status:\n"
            f"• Context: {stats['current_context']}\n"
            f"• Commands registered: {stats['commands_registered']}\n"
            f"• Commands executed: {stats['commands_executed']}\n"
            f"• Recognition attempts: {stats['recognition_attempts']}\n"
            f"• Success rate: {stats['successful_matches'] / max(1, stats['recognition_attempts']) * 100:.1f}%"
        )


class VoiceCommandManager:
    """High-level voice command management interface."""
    
    def __init__(self, engine: Optional[VoiceCommandEngine] = None):
        """Initialize command manager.
        
        Args:
            engine: Optional existing engine instance
        """
        self.engine = engine or VoiceCommandEngine()
        self.enabled = True
        self.wake_word = "hey claude"
        self.wake_word_enabled = True
        
    def enable(self):
        """Enable voice commands."""
        self.enabled = True
        logger.info("Voice commands enabled")
    
    def disable(self):
        """Disable voice commands."""
        self.enabled = False
        logger.info("Voice commands disabled")
    
    async def process_speech(self, text: str) -> List[Any]:
        """Process speech input for commands.
        
        Args:
            text: Speech-to-text result
            
        Returns:
            List of command execution results
        """
        if not self.enabled:
            return []
        
        # Check for wake word if enabled
        if self.wake_word_enabled:
            text_lower = text.lower()
            if self.wake_word in text_lower:
                # Remove wake word and process remainder
                wake_idx = text_lower.find(self.wake_word)
                remaining_text = text[wake_idx + len(self.wake_word):].strip()
                if remaining_text:
                    text = remaining_text
                else:
                    # Just wake word, activate listening
                    self.engine.set_context(CommandContext.LISTENING)
                    return ["Voice activated"]
        
        return await self.engine.process_voice_input(text)
    
    def set_wake_word(self, wake_word: str):
        """Set wake word for command activation.
        
        Args:
            wake_word: New wake word phrase
        """
        self.wake_word = wake_word.lower()
        logger.info(f"Wake word set to: {wake_word}")
    
    def register_custom_command(
        self,
        name: str,
        patterns: List[str],
        handler: Callable,
        description: str = "",
        priority: CommandPriority = CommandPriority.NORMAL
    ) -> str:
        """Register a custom voice command.
        
        Args:
            name: Command name
            patterns: Trigger patterns
            handler: Execution handler
            description: Command description
            priority: Execution priority
            
        Returns:
            Command ID
        """
        command_id = f"custom.{name.lower().replace(' ', '_')}"
        
        self.engine.register_command(
            id=command_id,
            name=name,
            category=CommandCategory.CUSTOM,
            priority=priority,
            patterns=patterns,
            handler=handler,
            description=description
        )
        
        return command_id
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export command configuration.
        
        Returns:
            Configuration dictionary
        """
        config = {
            'enabled': self.enabled,
            'wake_word': self.wake_word,
            'wake_word_enabled': self.wake_word_enabled,
            'confidence_threshold': self.engine.confidence_threshold,
            'statistics': self.engine.get_statistics(),
            'custom_commands': []
        }
        
        # Export custom commands only
        for command in self.engine.get_commands_by_category(CommandCategory.CUSTOM):
            config['custom_commands'].append({
                'id': command.id,
                'name': command.name,
                'patterns': command.patterns,
                'description': command.description,
                'enabled': command.enabled
            })
        
        return config


# Global instance
_voice_command_manager: Optional[VoiceCommandManager] = None

def get_voice_command_manager() -> VoiceCommandManager:
    """Get global voice command manager instance.
    
    Returns:
        VoiceCommandManager instance
    """
    global _voice_command_manager
    if _voice_command_manager is None:
        _voice_command_manager = VoiceCommandManager()
    return _voice_command_manager