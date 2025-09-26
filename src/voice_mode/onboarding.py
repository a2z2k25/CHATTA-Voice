"""
Onboarding system for new VoiceMode users.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class OnboardingStep(Enum):
    """Onboarding step types."""
    WELCOME = auto()
    SETUP = auto() 
    TUTORIAL = auto()
    PRACTICE = auto()
    COMPLETION = auto()


class OnboardingStage(Enum):
    """Current stage of onboarding."""
    NOT_STARTED = auto()
    WELCOME_INTRO = auto()
    VOICE_SETUP = auto()
    FIRST_CONVERSATION = auto()
    COMMANDS_TUTORIAL = auto()
    KEYBOARD_SHORTCUTS = auto()
    PREFERENCES_SETUP = auto()
    PRACTICE_SESSION = auto()
    COMPLETION = auto()
    FINISHED = auto()


@dataclass
class OnboardingTask:
    """Individual onboarding task."""
    id: str
    title: str
    description: str
    step_type: OnboardingStep
    stage: OnboardingStage
    instructions: List[str] = field(default_factory=list)
    verification: Optional[Callable] = None
    is_completed: bool = False
    is_optional: bool = False
    estimated_time: int = 30  # seconds
    prerequisites: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)
    
    async def execute(self, context: Dict[str, Any] = None) -> bool:
        """Execute the onboarding task."""
        logger.info(f"Executing onboarding task: {self.title}")
        
        if self.verification:
            try:
                if asyncio.iscoroutinefunction(self.verification):
                    result = await self.verification(context or {})
                else:
                    result = self.verification(context or {})
                
                self.is_completed = bool(result)
                return self.is_completed
            except Exception as e:
                logger.error(f"Task verification failed: {e}")
                return False
        else:
            # Mark as completed if no verification
            self.is_completed = True
            return True


@dataclass 
class OnboardingProgress:
    """Track onboarding progress."""
    user_id: str
    current_stage: OnboardingStage = OnboardingStage.NOT_STARTED
    completed_tasks: List[str] = field(default_factory=list)
    skipped_tasks: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    total_time_spent: int = 0  # seconds
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_completed(self) -> bool:
        """Check if onboarding is completed."""
        return self.current_stage == OnboardingStage.FINISHED
    
    @property
    def completion_percentage(self) -> float:
        """Get completion percentage."""
        total_stages = len([s for s in OnboardingStage if s not in [OnboardingStage.NOT_STARTED, OnboardingStage.FINISHED]])
        if total_stages == 0:
            return 0.0
        
        current_index = list(OnboardingStage).index(self.current_stage)
        return min(100.0, (current_index / total_stages) * 100)


class OnboardingSystem:
    """Comprehensive onboarding system."""
    
    def __init__(self):
        """Initialize onboarding system."""
        self.tasks: Dict[str, OnboardingTask] = {}
        self.stages: Dict[OnboardingStage, List[str]] = {
            stage: [] for stage in OnboardingStage
        }
        self.progress_data: Dict[str, OnboardingProgress] = {}
        self.listeners: List[Callable] = []
        
        self._create_default_tasks()
    
    def _create_default_tasks(self):
        """Create default onboarding tasks."""
        
        # Welcome tasks
        self.add_task(OnboardingTask(
            id="welcome.intro",
            title="Welcome to VoiceMode",
            description="Get introduced to VoiceMode's capabilities",
            step_type=OnboardingStep.WELCOME,
            stage=OnboardingStage.WELCOME_INTRO,
            instructions=[
                "Welcome to VoiceMode! This tool lets you have natural voice conversations with Claude Code.",
                "You'll learn how to start voice conversations, use commands, and customize your experience.",
                "The onboarding takes about 5-10 minutes and will guide you through all key features."
            ],
            estimated_time=60,
            tips=["You can skip any optional steps", "Press Escape to pause onboarding anytime"]
        ))
        
        # Voice setup tasks
        self.add_task(OnboardingTask(
            id="setup.microphone",
            title="Test Your Microphone",
            description="Ensure your microphone is working properly",
            step_type=OnboardingStep.SETUP,
            stage=OnboardingStage.VOICE_SETUP,
            instructions=[
                "We'll test your microphone to ensure voice conversations work properly.",
                "Please speak clearly: 'Testing microphone for VoiceMode'",
                "You should see your speech converted to text below."
            ],
            estimated_time=30,
            verification=self._verify_microphone,
            tips=["Speak clearly and avoid background noise", "Check your system audio settings if needed"]
        ))
        
        self.add_task(OnboardingTask(
            id="setup.speakers",
            title="Test Audio Output",
            description="Verify that you can hear VoiceMode's responses",
            step_type=OnboardingStep.SETUP,
            stage=OnboardingStage.VOICE_SETUP,
            instructions=[
                "Now we'll test audio output so you can hear VoiceMode's voice responses.",
                "You should hear a greeting message.",
                "Adjust your volume if needed."
            ],
            estimated_time=20,
            verification=self._verify_speakers,
            tips=["Check your system volume", "Use headphones if in a shared space"]
        ))
        
        # First conversation
        self.add_task(OnboardingTask(
            id="tutorial.first_conversation",
            title="Your First Voice Conversation",
            description="Start your first voice conversation with Claude",
            step_type=OnboardingStep.TUTORIAL,
            stage=OnboardingStage.FIRST_CONVERSATION,
            instructions=[
                "Let's start your first voice conversation!",
                "Say: 'start voice' or press Ctrl+Shift+V",
                "Then say: 'Hello Claude, how are you today?'",
                "End the conversation by saying 'stop voice'"
            ],
            estimated_time=60,
            verification=self._verify_first_conversation,
            prerequisites=["setup.microphone", "setup.speakers"],
            tips=["Speak naturally", "Wait for Claude to finish speaking before responding"]
        ))
        
        # Commands tutorial
        self.add_task(OnboardingTask(
            id="tutorial.voice_commands",
            title="Learn Voice Commands",
            description="Discover essential voice commands",
            step_type=OnboardingStep.TUTORIAL,
            stage=OnboardingStage.COMMANDS_TUTORIAL,
            instructions=[
                "VoiceMode has many built-in voice commands to control conversations.",
                "Try saying: 'help' to see available commands",
                "Try: 'volume up' and 'volume down'",
                "Try: 'repeat' to hear the last response again"
            ],
            estimated_time=90,
            verification=self._verify_voice_commands,
            prerequisites=["tutorial.first_conversation"],
            tips=["Commands work during voice conversations", "You can interrupt Claude anytime"]
        ))
        
        # Keyboard shortcuts
        self.add_task(OnboardingTask(
            id="tutorial.keyboard_shortcuts",
            title="Master Keyboard Shortcuts",
            description="Learn essential keyboard shortcuts",
            step_type=OnboardingStep.TUTORIAL,
            stage=OnboardingStage.KEYBOARD_SHORTCUTS,
            instructions=[
                "Keyboard shortcuts provide quick access to VoiceMode features:",
                "• Ctrl+Shift+V - Start/stop voice conversation",
                "• Ctrl+H - Show help",
                "• Ctrl+M - Mute/unmute",
                "• Space (during conversation) - Interrupt and stop",
                "Try using Ctrl+Shift+V to start a conversation!"
            ],
            estimated_time=45,
            verification=self._verify_keyboard_shortcuts,
            is_optional=True,
            tips=["Shortcuts work from anywhere in the application", "Memorize Ctrl+Shift+V for quick access"]
        ))
        
        # Preferences setup
        self.add_task(OnboardingTask(
            id="setup.preferences",
            title="Customize Your Preferences",
            description="Set up your preferred voice and settings",
            step_type=OnboardingStep.SETUP,
            stage=OnboardingStage.PREFERENCES_SETUP,
            instructions=[
                "Let's customize VoiceMode to your preferences.",
                "You can choose different voice models, adjust volume, and set wake words.",
                "Open preferences with Ctrl+, or say 'open preferences' during conversation",
                "Try different TTS voices and find one you like!"
            ],
            estimated_time=120,
            verification=self._verify_preferences_setup,
            is_optional=True,
            tips=["Save preferences to keep your settings", "You can change these anytime later"]
        ))
        
        # Practice session
        self.add_task(OnboardingTask(
            id="practice.conversation",
            title="Practice Session",
            description="Have a longer practice conversation",
            step_type=OnboardingStep.PRACTICE,
            stage=OnboardingStage.PRACTICE_SESSION,
            instructions=[
                "Time for a practice session! Have a 2-3 minute conversation with Claude.",
                "Try asking about code, getting help with a project, or casual conversation.",
                "Practice using voice commands and interruption.",
                "This helps you get comfortable with the natural flow."
            ],
            estimated_time=180,
            verification=self._verify_practice_session,
            prerequisites=["tutorial.first_conversation", "tutorial.voice_commands"],
            tips=["Be natural - treat Claude like a helpful colleague", "Try different types of questions"]
        ))
        
        # Completion
        self.add_task(OnboardingTask(
            id="completion.summary",
            title="Onboarding Complete!",
            description="Review what you've learned and next steps",
            step_type=OnboardingStep.COMPLETION,
            stage=OnboardingStage.COMPLETION,
            instructions=[
                "Congratulations! You've completed VoiceMode onboarding.",
                "You now know how to:",
                "• Start and stop voice conversations",
                "• Use voice commands and keyboard shortcuts", 
                "• Customize preferences",
                "• Have natural conversations with Claude",
                "Ready to boost your coding productivity with voice!"
            ],
            estimated_time=30,
            verification=lambda _: True,  # Always passes
            tips=["Use Ctrl+H anytime for help", "Check the documentation for advanced features"]
        ))
    
    def add_task(self, task: OnboardingTask):
        """Add onboarding task."""
        self.tasks[task.id] = task
        if task.stage not in self.stages:
            self.stages[task.stage] = []
        self.stages[task.stage].append(task.id)
    
    def get_progress(self, user_id: str) -> OnboardingProgress:
        """Get user's onboarding progress."""
        if user_id not in self.progress_data:
            self.progress_data[user_id] = OnboardingProgress(user_id=user_id)
        return self.progress_data[user_id]
    
    async def start_onboarding(self, user_id: str) -> OnboardingProgress:
        """Start onboarding for user."""
        progress = self.get_progress(user_id)
        progress.start_time = datetime.now()
        progress.current_stage = OnboardingStage.WELCOME_INTRO
        
        logger.info(f"Starting onboarding for user: {user_id}")
        await self._notify_listeners("onboarding_started", user_id, progress)
        
        return progress
    
    async def next_task(self, user_id: str) -> Optional[OnboardingTask]:
        """Get next task for user."""
        progress = self.get_progress(user_id)
        
        if progress.is_completed:
            return None
        
        # Get tasks for current stage
        stage_task_ids = self.stages.get(progress.current_stage, [])
        
        for task_id in stage_task_ids:
            task = self.tasks.get(task_id)
            if not task:
                continue
                
            # Check if task is completed
            if task.is_completed or task_id in progress.completed_tasks:
                continue
            
            # Check prerequisites
            if not self._check_prerequisites(task, progress.completed_tasks):
                continue
            
            return task
        
        # No more tasks in current stage, advance to next stage
        await self._advance_stage(user_id)
        
        # Try again with new stage
        if progress.current_stage != OnboardingStage.FINISHED:
            return await self.next_task(user_id)
        
        return None
    
    async def complete_task(self, user_id: str, task_id: str, success: bool = True) -> bool:
        """Mark task as completed."""
        progress = self.get_progress(user_id)
        task = self.tasks.get(task_id)
        
        if not task:
            return False
        
        if success:
            progress.completed_tasks.append(task_id)
            task.is_completed = True
            logger.info(f"Task completed: {task.title}")
        else:
            # Task failed, may retry or skip
            logger.warning(f"Task failed: {task.title}")
            return False
        
        await self._notify_listeners("task_completed", user_id, progress, task)
        
        # Check if stage is complete
        stage_tasks = self.stages.get(progress.current_stage, [])
        required_tasks = [tid for tid in stage_tasks if not self.tasks[tid].is_optional]
        completed_required = [tid for tid in required_tasks if tid in progress.completed_tasks]
        
        if len(completed_required) >= len(required_tasks):
            await self._advance_stage(user_id)
        
        return True
    
    async def skip_task(self, user_id: str, task_id: str) -> bool:
        """Skip an optional task."""
        progress = self.get_progress(user_id)
        task = self.tasks.get(task_id)
        
        if not task or not task.is_optional:
            return False
        
        progress.skipped_tasks.append(task_id)
        task.is_completed = True  # Mark as completed to move forward
        
        logger.info(f"Task skipped: {task.title}")
        await self._notify_listeners("task_skipped", user_id, progress, task)
        
        return True
    
    async def _advance_stage(self, user_id: str):
        """Advance to next onboarding stage."""
        progress = self.get_progress(user_id)
        
        stages = list(OnboardingStage)
        current_index = stages.index(progress.current_stage)
        
        if current_index < len(stages) - 1:
            progress.current_stage = stages[current_index + 1]
            logger.info(f"Advanced to stage: {progress.current_stage.name}")
            
            if progress.current_stage == OnboardingStage.FINISHED:
                await self._complete_onboarding(user_id)
        
        await self._notify_listeners("stage_advanced", user_id, progress)
    
    async def _complete_onboarding(self, user_id: str):
        """Complete onboarding process."""
        progress = self.get_progress(user_id)
        progress.completion_time = datetime.now()
        
        if progress.start_time:
            delta = progress.completion_time - progress.start_time
            progress.total_time_spent = int(delta.total_seconds())
        
        logger.info(f"Onboarding completed for user: {user_id}")
        await self._notify_listeners("onboarding_completed", user_id, progress)
    
    def _check_prerequisites(self, task: OnboardingTask, completed_tasks: List[str]) -> bool:
        """Check if task prerequisites are met."""
        return all(prereq in completed_tasks for prereq in task.prerequisites)
    
    async def _notify_listeners(self, event: str, user_id: str, progress: OnboardingProgress, task: OnboardingTask = None):
        """Notify event listeners."""
        for listener in self.listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event, user_id, progress, task)
                else:
                    listener(event, user_id, progress, task)
            except Exception as e:
                logger.error(f"Listener error: {e}")
    
    def add_listener(self, listener: Callable):
        """Add event listener."""
        self.listeners.append(listener)
    
    def remove_listener(self, listener: Callable):
        """Remove event listener."""
        if listener in self.listeners:
            self.listeners.remove(listener)
    
    # Verification methods for tasks
    async def _verify_microphone(self, context: Dict[str, Any]) -> bool:
        """Verify microphone is working."""
        # In real implementation, this would test actual microphone
        test_phrase = context.get("speech_input", "").lower()
        return "testing microphone" in test_phrase or len(test_phrase) > 10
    
    async def _verify_speakers(self, context: Dict[str, Any]) -> bool:
        """Verify speakers are working."""
        # In real implementation, this would play audio and ask for confirmation
        return context.get("audio_confirmed", False)
    
    async def _verify_first_conversation(self, context: Dict[str, Any]) -> bool:
        """Verify user had first conversation."""
        return (context.get("conversation_started", False) and 
                context.get("conversation_ended", False) and
                context.get("messages_exchanged", 0) >= 2)
    
    async def _verify_voice_commands(self, context: Dict[str, Any]) -> bool:
        """Verify user tried voice commands."""
        commands_used = context.get("commands_used", [])
        return len(commands_used) >= 2
    
    async def _verify_keyboard_shortcuts(self, context: Dict[str, Any]) -> bool:
        """Verify user tried keyboard shortcuts."""
        shortcuts_used = context.get("shortcuts_used", [])
        return "ctrl+shift+v" in [s.lower() for s in shortcuts_used]
    
    async def _verify_preferences_setup(self, context: Dict[str, Any]) -> bool:
        """Verify user opened and modified preferences."""
        return (context.get("preferences_opened", False) and
                context.get("preferences_modified", False))
    
    async def _verify_practice_session(self, context: Dict[str, Any]) -> bool:
        """Verify user had practice session."""
        return (context.get("conversation_duration", 0) >= 120 and
                context.get("messages_exchanged", 0) >= 8)
    
    def export_progress(self, user_id: str) -> Dict[str, Any]:
        """Export user progress data."""
        progress = self.get_progress(user_id)
        return {
            "user_id": progress.user_id,
            "current_stage": progress.current_stage.name,
            "completed_tasks": progress.completed_tasks,
            "skipped_tasks": progress.skipped_tasks,
            "completion_percentage": progress.completion_percentage,
            "is_completed": progress.is_completed,
            "total_time_spent": progress.total_time_spent,
            "preferences": progress.preferences,
            "start_time": progress.start_time.isoformat() if progress.start_time else None,
            "completion_time": progress.completion_time.isoformat() if progress.completion_time else None
        }
    
    def import_progress(self, data: Dict[str, Any]):
        """Import user progress data."""
        user_id = data["user_id"]
        progress = OnboardingProgress(
            user_id=user_id,
            current_stage=OnboardingStage[data["current_stage"]],
            completed_tasks=data["completed_tasks"],
            skipped_tasks=data["skipped_tasks"],
            total_time_spent=data["total_time_spent"],
            preferences=data["preferences"]
        )
        
        if data["start_time"]:
            progress.start_time = datetime.fromisoformat(data["start_time"])
        if data["completion_time"]:
            progress.completion_time = datetime.fromisoformat(data["completion_time"])
        
        self.progress_data[user_id] = progress
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get onboarding system statistics."""
        total_users = len(self.progress_data)
        completed_users = sum(1 for p in self.progress_data.values() if p.is_completed)
        
        stage_distribution = {}
        for progress in self.progress_data.values():
            stage = progress.current_stage.name
            stage_distribution[stage] = stage_distribution.get(stage, 0) + 1
        
        avg_completion_time = 0
        if completed_users > 0:
            total_time = sum(p.total_time_spent for p in self.progress_data.values() if p.is_completed)
            avg_completion_time = total_time / completed_users
        
        return {
            "total_tasks": len(self.tasks),
            "total_users": total_users,
            "completed_users": completed_users,
            "completion_rate": (completed_users / total_users * 100) if total_users > 0 else 0,
            "average_completion_time": avg_completion_time,
            "stage_distribution": stage_distribution,
            "tasks_by_type": {
                step_type.name: len([t for t in self.tasks.values() if t.step_type == step_type])
                for step_type in OnboardingStep
            }
        }


class OnboardingUI:
    """User interface for onboarding."""
    
    def __init__(self, onboarding_system: OnboardingSystem):
        """Initialize UI."""
        self.system = onboarding_system
        self.current_user = None
        self.ui_state = {}
    
    async def start_ui(self, user_id: str):
        """Start onboarding UI for user."""
        self.current_user = user_id
        progress = await self.system.start_onboarding(user_id)
        
        return {
            "message": "Welcome to VoiceMode onboarding!",
            "progress": progress.completion_percentage,
            "stage": progress.current_stage.name,
            "estimated_time": "5-10 minutes"
        }
    
    async def get_current_task(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get current task for UI display."""
        user_id = user_id or self.current_user
        if not user_id:
            return None
        
        task = await self.system.next_task(user_id)
        if not task:
            return None
        
        progress = self.system.get_progress(user_id)
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "instructions": task.instructions,
            "estimated_time": task.estimated_time,
            "is_optional": task.is_optional,
            "tips": task.tips,
            "progress_percentage": progress.completion_percentage,
            "stage": progress.current_stage.name,
            "can_skip": task.is_optional
        }
    
    async def submit_task_completion(self, user_id: str, task_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Submit task completion with context."""
        task = self.system.tasks.get(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}
        
        # Run verification if provided
        success = await task.execute(context)
        
        if success:
            await self.system.complete_task(user_id, task_id, True)
            next_task = await self.system.next_task(user_id)
            
            return {
                "success": True,
                "task_completed": task.title,
                "has_next_task": next_task is not None,
                "next_task": next_task.id if next_task else None,
                "progress": self.system.get_progress(user_id).completion_percentage
            }
        else:
            return {
                "success": False,
                "error": "Task verification failed",
                "can_retry": True
            }


# Global onboarding system instance
_onboarding_system: Optional[OnboardingSystem] = None

def get_onboarding_system() -> OnboardingSystem:
    """Get global onboarding system instance."""
    global _onboarding_system
    if _onboarding_system is None:
        _onboarding_system = OnboardingSystem()
    return _onboarding_system


if __name__ == "__main__":
    # Example usage
    async def demo():
        system = get_onboarding_system()
        user_id = "demo_user"
        
        # Start onboarding
        progress = await system.start_onboarding(user_id)
        print(f"Started onboarding: {progress.completion_percentage:.1f}% complete")
        
        # Get first task
        task = await system.next_task(user_id)
        if task:
            print(f"First task: {task.title}")
            
            # Complete task
            await system.complete_task(user_id, task.id)
            print(f"Task completed: {progress.completion_percentage:.1f}% complete")
    
    asyncio.run(demo())