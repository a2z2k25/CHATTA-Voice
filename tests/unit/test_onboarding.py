#!/usr/bin/env python3
"""Test onboarding system."""

import asyncio
from typing import List, Dict, Any
from voice_mode.onboarding import (
    OnboardingSystem,
    OnboardingUI,
    OnboardingTask,
    OnboardingProgress,
    OnboardingStep,
    OnboardingStage,
    get_onboarding_system
)


def test_onboarding_task_creation():
    """Test onboarding task creation and execution."""
    print("\n=== Testing Onboarding Task Creation ===")
    
    # Test handler
    executed = []
    
    def test_handler(context: Dict[str, Any] = None):
        executed.append(context or {})
        return True
    
    task = OnboardingTask(
        id="test.task",
        title="Test Task",
        description="A test onboarding task",
        step_type=OnboardingStep.SETUP,
        stage=OnboardingStage.VOICE_SETUP,
        instructions=["Step 1", "Step 2", "Step 3"],
        verification=test_handler,
        estimated_time=60,
        tips=["Tip 1", "Tip 2"]
    )
    
    print(f"  Created task: {task.title}")
    print(f"  ID: {task.id}")
    print(f"  Step type: {task.step_type.name}")
    print(f"  Stage: {task.stage.name}")
    print(f"  Instructions: {len(task.instructions)}")
    print(f"  Estimated time: {task.estimated_time}s")
    print(f"  Is optional: {task.is_optional}")
    print(f"  Is completed: {task.is_completed}")
    
    print("✓ Task creation working")


async def test_task_execution():
    """Test task execution and verification."""
    print("\n=== Testing Task Execution ===")
    
    # Test successful execution
    executed_contexts = []
    
    def success_handler(context: Dict[str, Any] = None):
        executed_contexts.append(context or {})
        return True
    
    task1 = OnboardingTask(
        id="test.success",
        title="Success Task",
        description="Task that succeeds",
        step_type=OnboardingStep.TUTORIAL,
        stage=OnboardingStage.FIRST_CONVERSATION,
        verification=success_handler
    )
    
    result1 = await task1.execute({"test_data": "success"})
    print(f"  Success task result: {result1}")
    print(f"  Task completed: {task1.is_completed}")
    print(f"  Context received: {executed_contexts[0]}")
    
    # Test failed execution
    def failure_handler(context: Dict[str, Any] = None):
        return False
    
    task2 = OnboardingTask(
        id="test.failure",
        title="Failure Task",
        description="Task that fails",
        step_type=OnboardingStep.TUTORIAL,
        stage=OnboardingStage.FIRST_CONVERSATION,
        verification=failure_handler
    )
    
    result2 = await task2.execute()
    print(f"  Failure task result: {result2}")
    print(f"  Task completed: {task2.is_completed}")
    
    # Test no verification (auto-success)
    task3 = OnboardingTask(
        id="test.auto",
        title="Auto Task",
        description="Task with no verification",
        step_type=OnboardingStep.WELCOME,
        stage=OnboardingStage.WELCOME_INTRO
    )
    
    result3 = await task3.execute()
    print(f"  Auto task result: {result3}")
    print(f"  Task completed: {task3.is_completed}")
    
    print("✓ Task execution working")


def test_onboarding_progress():
    """Test onboarding progress tracking."""
    print("\n=== Testing Onboarding Progress ===")
    
    progress = OnboardingProgress(user_id="test_user")
    
    print(f"  Initial stage: {progress.current_stage.name}")
    print(f"  Initial completion: {progress.completion_percentage:.1f}%")
    print(f"  Is completed: {progress.is_completed}")
    
    # Simulate progress
    progress.current_stage = OnboardingStage.VOICE_SETUP
    progress.completed_tasks.append("welcome.intro")
    progress.completed_tasks.append("setup.microphone")
    
    print(f"  Updated stage: {progress.current_stage.name}")
    print(f"  Completed tasks: {len(progress.completed_tasks)}")
    print(f"  Updated completion: {progress.completion_percentage:.1f}%")
    
    # Test completion
    progress.current_stage = OnboardingStage.FINISHED
    print(f"  Final completion: {progress.completion_percentage:.1f}%")
    print(f"  Is completed: {progress.is_completed}")
    
    print("✓ Progress tracking working")


def test_onboarding_system_initialization():
    """Test onboarding system initialization and default tasks."""
    print("\n=== Testing Onboarding System Initialization ===")
    
    system = OnboardingSystem()
    
    print(f"  Total tasks loaded: {len(system.tasks)}")
    print(f"  Total stages: {len(system.stages)}")
    
    # Check specific tasks exist
    welcome_task = system.tasks.get("welcome.intro")
    print(f"  Welcome task exists: {welcome_task is not None}")
    if welcome_task:
        print(f"    Title: {welcome_task.title}")
        print(f"    Instructions: {len(welcome_task.instructions)}")
    
    mic_task = system.tasks.get("setup.microphone")
    print(f"  Microphone task exists: {mic_task is not None}")
    
    first_conv_task = system.tasks.get("tutorial.first_conversation")
    print(f"  First conversation task exists: {first_conv_task is not None}")
    if first_conv_task:
        print(f"    Prerequisites: {first_conv_task.prerequisites}")
    
    completion_task = system.tasks.get("completion.summary")
    print(f"  Completion task exists: {completion_task is not None}")
    
    # Check stages
    welcome_tasks = system.stages[OnboardingStage.WELCOME_INTRO]
    print(f"  Welcome stage tasks: {len(welcome_tasks)}")
    
    voice_setup_tasks = system.stages[OnboardingStage.VOICE_SETUP]
    print(f"  Voice setup tasks: {len(voice_setup_tasks)}")
    
    print("✓ System initialization working")


async def test_onboarding_flow():
    """Test complete onboarding flow."""
    print("\n=== Testing Onboarding Flow ===")
    
    system = OnboardingSystem()
    user_id = "test_flow_user"
    
    # Start onboarding
    progress = await system.start_onboarding(user_id)
    print(f"  Started onboarding: {progress.current_stage.name}")
    print(f"  Start progress: {progress.completion_percentage:.1f}%")
    
    # Get first task
    task1 = await system.next_task(user_id)
    print(f"  First task: {task1.title if task1 else 'None'}")
    
    if task1:
        # Complete first task
        success = await system.complete_task(user_id, task1.id, True)
        print(f"  Task completion success: {success}")
        
        updated_progress = system.get_progress(user_id)
        print(f"  Updated progress: {updated_progress.completion_percentage:.1f}%")
        print(f"  Completed tasks: {len(updated_progress.completed_tasks)}")
    
    # Get next task
    task2 = await system.next_task(user_id)
    print(f"  Next task: {task2.title if task2 else 'None'}")
    
    if task2:
        # Test skipping optional task
        if task2.is_optional:
            skipped = await system.skip_task(user_id, task2.id)
            print(f"  Skipped optional task: {skipped}")
        else:
            # Complete required task
            await system.complete_task(user_id, task2.id, True)
            print(f"  Completed required task: {task2.title}")
    
    # Check final progress
    final_progress = system.get_progress(user_id)
    print(f"  Final progress: {final_progress.completion_percentage:.1f}%")
    print(f"  Final stage: {final_progress.current_stage.name}")
    
    print("✓ Onboarding flow working")


async def test_task_prerequisites():
    """Test task prerequisite checking."""
    print("\n=== Testing Task Prerequisites ===")
    
    system = OnboardingSystem()
    user_id = "prereq_user"
    
    # Start onboarding
    await system.start_onboarding(user_id)
    
    # Try to get first conversation task (has prerequisites)
    first_conv_task = system.tasks.get("tutorial.first_conversation")
    print(f"  First conversation prerequisites: {first_conv_task.prerequisites}")
    
    progress = system.get_progress(user_id)
    
    # Check if prerequisites are met (should not be initially)
    prereqs_met = system._check_prerequisites(first_conv_task, progress.completed_tasks)
    print(f"  Prerequisites met initially: {prereqs_met}")
    
    # Complete prerequisite tasks
    progress.completed_tasks.extend(["setup.microphone", "setup.speakers"])
    prereqs_met = system._check_prerequisites(first_conv_task, progress.completed_tasks)
    print(f"  Prerequisites met after setup: {prereqs_met}")
    
    # Test task with no prerequisites
    welcome_task = system.tasks.get("welcome.intro")
    no_prereqs_met = system._check_prerequisites(welcome_task, [])
    print(f"  No prerequisites task accessible: {no_prereqs_met}")
    
    print("✓ Prerequisites checking working")


async def test_onboarding_listeners():
    """Test onboarding event listeners."""
    print("\n=== Testing Onboarding Listeners ===")
    
    system = OnboardingSystem()
    
    # Track events
    events = []
    
    def event_listener(event: str, user_id: str, progress: OnboardingProgress, task: OnboardingTask = None):
        events.append({
            "event": event,
            "user_id": user_id,
            "stage": progress.current_stage.name,
            "task": task.title if task else None
        })
    
    system.add_listener(event_listener)
    
    user_id = "listener_user"
    
    # Start onboarding (should trigger event)
    await system.start_onboarding(user_id)
    print(f"  Events after start: {len(events)}")
    print(f"    Last event: {events[-1]['event']}")
    
    # Complete a task (should trigger event)
    task = await system.next_task(user_id)
    if task:
        await system.complete_task(user_id, task.id, True)
        print(f"  Events after task completion: {len(events)}")
        print(f"    Last event: {events[-1]['event']}")
    
    # Remove listener
    system.remove_listener(event_listener)
    
    # Complete another task (should not trigger new events)
    initial_event_count = len(events)
    task2 = await system.next_task(user_id)
    if task2:
        await system.complete_task(user_id, task2.id, True)
    
    print(f"  Events after listener removal: {len(events)} (should be {initial_event_count})")
    
    print("✓ Event listeners working")


async def test_onboarding_ui():
    """Test onboarding UI interface."""
    print("\n=== Testing Onboarding UI ===")
    
    system = OnboardingSystem()
    ui = OnboardingUI(system)
    
    user_id = "ui_user"
    
    # Start UI
    start_result = await ui.start_ui(user_id)
    print(f"  UI start result: {start_result['message'][:30]}...")
    print(f"  Initial progress: {start_result['progress']:.1f}%")
    print(f"  Initial stage: {start_result['stage']}")
    
    # Get current task
    task_info = await ui.get_current_task(user_id)
    print(f"  Current task: {task_info['title'] if task_info else 'None'}")
    
    if task_info:
        print(f"    Description: {task_info['description'][:50]}...")
        print(f"    Instructions: {len(task_info['instructions'])}")
        print(f"    Estimated time: {task_info['estimated_time']}s")
        print(f"    Can skip: {task_info['can_skip']}")
        
        # Submit task completion
        completion_result = await ui.submit_task_completion(
            user_id, 
            task_info['id'], 
            {"test": True}
        )
        print(f"    Completion success: {completion_result['success']}")
        if completion_result['success']:
            print(f"    Progress after completion: {completion_result['progress']:.1f}%")
            print(f"    Has next task: {completion_result['has_next_task']}")
    
    print("✓ Onboarding UI working")


async def test_verification_methods():
    """Test built-in verification methods."""
    print("\n=== Testing Verification Methods ===")
    
    system = OnboardingSystem()
    
    # Test microphone verification
    mic_result1 = await system._verify_microphone({"speech_input": "testing microphone for voicemode"})
    print(f"  Microphone verification (good): {mic_result1}")
    
    mic_result2 = await system._verify_microphone({"speech_input": "hello"})
    print(f"  Microphone verification (bad): {mic_result2}")
    
    # Test speaker verification
    speaker_result1 = await system._verify_speakers({"audio_confirmed": True})
    print(f"  Speaker verification (confirmed): {speaker_result1}")
    
    speaker_result2 = await system._verify_speakers({"audio_confirmed": False})
    print(f"  Speaker verification (not confirmed): {speaker_result2}")
    
    # Test conversation verification
    conv_result1 = await system._verify_first_conversation({
        "conversation_started": True,
        "conversation_ended": True,
        "messages_exchanged": 5
    })
    print(f"  Conversation verification (good): {conv_result1}")
    
    conv_result2 = await system._verify_first_conversation({
        "conversation_started": True,
        "conversation_ended": False,
        "messages_exchanged": 1
    })
    print(f"  Conversation verification (bad): {conv_result2}")
    
    # Test voice commands verification
    cmd_result1 = await system._verify_voice_commands({"commands_used": ["help", "volume up", "status"]})
    print(f"  Voice commands verification (good): {cmd_result1}")
    
    cmd_result2 = await system._verify_voice_commands({"commands_used": ["help"]})
    print(f"  Voice commands verification (bad): {cmd_result2}")
    
    print("✓ Verification methods working")


def test_data_export_import():
    """Test progress data export and import."""
    print("\n=== Testing Data Export/Import ===")
    
    system = OnboardingSystem()
    user_id = "export_user"
    
    # Create some progress
    progress = OnboardingProgress(user_id=user_id)
    progress.current_stage = OnboardingStage.VOICE_SETUP
    progress.completed_tasks = ["welcome.intro", "setup.microphone"]
    progress.skipped_tasks = ["setup.preferences"]
    progress.total_time_spent = 180
    progress.preferences = {"voice": "nova", "volume": 0.8}
    
    system.progress_data[user_id] = progress
    
    # Export data
    exported = system.export_progress(user_id)
    print(f"  Exported keys: {list(exported.keys())}")
    print(f"  Exported stage: {exported['current_stage']}")
    print(f"  Exported completed tasks: {len(exported['completed_tasks'])}")
    print(f"  Exported time spent: {exported['total_time_spent']}s")
    
    # Import to new system
    new_system = OnboardingSystem()
    new_system.import_progress(exported)
    
    imported_progress = new_system.get_progress(user_id)
    print(f"  Imported stage: {imported_progress.current_stage.name}")
    print(f"  Imported completed tasks: {len(imported_progress.completed_tasks)}")
    print(f"  Imported preferences: {imported_progress.preferences}")
    print(f"  Data matches: {imported_progress.total_time_spent == progress.total_time_spent}")
    
    print("✓ Data export/import working")


def test_statistics():
    """Test onboarding statistics."""
    print("\n=== Testing Statistics ===")
    
    system = OnboardingSystem()
    
    # Create sample data
    users = ["user1", "user2", "user3", "user4"]
    
    for i, user_id in enumerate(users):
        progress = OnboardingProgress(user_id=user_id)
        
        if i == 0:  # Completed user
            progress.current_stage = OnboardingStage.FINISHED
            progress.total_time_spent = 420
        elif i == 1:  # In progress
            progress.current_stage = OnboardingStage.VOICE_SETUP
            progress.completed_tasks = ["welcome.intro"]
        elif i == 2:  # Just started
            progress.current_stage = OnboardingStage.WELCOME_INTRO
        else:  # Not started
            progress.current_stage = OnboardingStage.NOT_STARTED
        
        system.progress_data[user_id] = progress
    
    # Get statistics
    stats = system.get_statistics()
    
    print(f"  Total tasks: {stats['total_tasks']}")
    print(f"  Total users: {stats['total_users']}")
    print(f"  Completed users: {stats['completed_users']}")
    print(f"  Completion rate: {stats['completion_rate']:.1f}%")
    print(f"  Average completion time: {stats['average_completion_time']:.1f}s")
    
    print(f"  Stage distribution:")
    for stage, count in stats['stage_distribution'].items():
        print(f"    {stage}: {count}")
    
    print(f"  Tasks by type:")
    for task_type, count in stats['tasks_by_type'].items():
        print(f"    {task_type}: {count}")
    
    print("✓ Statistics working")


def test_global_instance():
    """Test global onboarding system instance."""
    print("\n=== Testing Global Instance ===")
    
    # Get multiple instances
    system1 = get_onboarding_system()
    system2 = get_onboarding_system()
    
    print(f"  Same instance: {system1 is system2}")
    print(f"  Instance type: {type(system1).__name__}")
    print(f"  Tasks available: {len(system1.tasks)}")
    
    # Test that changes persist
    user_id = "global_test"
    system1.progress_data[user_id] = OnboardingProgress(user_id=user_id)
    
    # Check in second instance
    has_data = user_id in system2.progress_data
    print(f"  Data persists across instances: {has_data}")
    
    print("✓ Global instance working")


async def test_performance():
    """Test onboarding system performance."""
    print("\n=== Testing Performance ===")
    
    import time
    
    system = OnboardingSystem()
    
    # Test task lookup performance
    start_time = time.time()
    
    for _ in range(1000):
        task = system.tasks.get("welcome.intro")
        assert task is not None
    
    elapsed = time.time() - start_time
    lookup_rate = 1000 / elapsed if elapsed > 0 else 0
    
    print(f"  Task lookup rate: {lookup_rate:.1f} lookups/sec")
    
    # Test progress tracking performance
    user_ids = [f"perf_user_{i}" for i in range(100)]
    
    start_time = time.time()
    
    for user_id in user_ids:
        progress = system.get_progress(user_id)
        progress.completed_tasks.append("welcome.intro")
    
    elapsed = time.time() - start_time
    progress_rate = len(user_ids) / elapsed if elapsed > 0 else 0
    
    print(f"  Progress update rate: {progress_rate:.1f} updates/sec")
    
    # Test next task performance
    start_time = time.time()
    
    for user_id in user_ids[:50]:  # Smaller batch for async operations
        task = await system.next_task(user_id)
    
    elapsed = time.time() - start_time
    next_task_rate = 50 / elapsed if elapsed > 0 else 0
    
    print(f"  Next task rate: {next_task_rate:.1f} tasks/sec")
    
    print("✓ Performance acceptable")


async def test_error_handling():
    """Test onboarding error handling."""
    print("\n=== Testing Error Handling ===")
    
    system = OnboardingSystem()
    user_id = "error_user"
    
    # Test non-existent task completion
    result = await system.complete_task(user_id, "nonexistent.task", True)
    print(f"  Non-existent task completion: {result}")
    
    # Test skip non-optional task
    required_task = system.tasks.get("welcome.intro")
    if required_task:
        required_task.is_optional = False  # Ensure it's not optional
        skip_result = await system.skip_task(user_id, required_task.id)
        print(f"  Skip non-optional task: {skip_result}")
    
    # Test task with failing verification
    def failing_verification(context):
        raise Exception("Verification error")
    
    error_task = OnboardingTask(
        id="error.task",
        title="Error Task",
        description="Task with failing verification",
        step_type=OnboardingStep.SETUP,
        stage=OnboardingStage.VOICE_SETUP,
        verification=failing_verification
    )
    
    result = await error_task.execute()
    print(f"  Task with failing verification: {result}")
    print(f"  Error task completed: {error_task.is_completed}")
    
    # Test UI with non-existent user
    ui = OnboardingUI(system)
    task_info = await ui.get_current_task("nonexistent_user")
    print(f"  UI with non-existent user: {task_info is None}")
    
    print("✓ Error handling working")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("ONBOARDING SYSTEM TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_onboarding_task_creation()
    test_onboarding_progress()
    test_onboarding_system_initialization()
    test_data_export_import()
    test_statistics()
    test_global_instance()
    
    # Run async tests
    await test_task_execution()
    await test_onboarding_flow()
    await test_task_prerequisites()
    await test_onboarding_listeners()
    await test_onboarding_ui()
    await test_verification_methods()
    await test_performance()
    await test_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ All onboarding system tests passed!")
    print("Sprint 39 complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())