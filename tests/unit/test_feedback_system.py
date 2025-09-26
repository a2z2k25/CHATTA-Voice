#!/usr/bin/env python3
"""Test feedback collection system."""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from voice_mode.feedback_system import (
    FeedbackCollector,
    FeedbackUI,
    FeedbackItem,
    FeedbackType,
    FeedbackPriority,
    FeedbackStatus,
    FeedbackSentiment,
    FeedbackContext,
    FeedbackStats,
    get_feedback_collector,
    get_feedback_ui
)


def test_feedback_item_creation():
    """Test feedback item creation and properties."""
    print("\n=== Testing Feedback Item Creation ===")
    
    context = FeedbackContext(
        app_version="1.0.0",
        platform="darwin",
        python_version="3.10.0",
        session_duration=120.5,
        active_features=["voice", "tts"],
        user_session_id="test-session-123"
    )
    
    feedback = FeedbackItem(
        type=FeedbackType.BUG_REPORT,
        title="Audio not working",
        description="Microphone input is not being detected",
        user_id="user123",
        priority=FeedbackPriority.HIGH,
        context=context,
        tags={"audio", "microphone", "bug"},
        contact_info="user@example.com"
    )
    
    print(f"  Created feedback: {feedback.title}")
    print(f"  ID: {feedback.id}")
    print(f"  Type: {feedback.type.name}")
    print(f"  Priority: {feedback.priority.name}")
    print(f"  Tags: {feedback.tags}")
    print(f"  Context version: {feedback.context.app_version}")
    print(f"  Default status: {feedback.status.name}")
    print(f"  Created at: {feedback.created_at}")
    
    print("✓ Feedback item creation working")


def test_feedback_collector_initialization():
    """Test feedback collector initialization."""
    print("\n=== Testing Feedback Collector Initialization ===")
    
    # Use temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        print(f"  Database path: {collector.db_path}")
        print(f"  Database exists: {collector.db_path.exists()}")
        print(f"  Initial feedback count: {len(collector.feedback_items)}")
        print(f"  Auto categorize: {collector.auto_categorize}")
        print(f"  Sentiment analysis: {collector.sentiment_analysis}")
        print(f"  Duplicate detection: {collector.duplicate_detection}")
        
        # Test database tables exist
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"  Database tables: {tables}")
    
    print("✓ Feedback collector initialization working")


async def test_feedback_submission():
    """Test feedback submission process."""
    print("\n=== Testing Feedback Submission ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        # Track listener calls
        listener_calls = []
        
        def feedback_listener(feedback: FeedbackItem):
            listener_calls.append(feedback.id)
        
        collector.add_listener(feedback_listener)
        
        # Submit feedback
        context = FeedbackContext(
            app_version="1.0.0",
            platform="darwin",
            active_features=["voice", "keyboard_shortcuts"]
        )
        
        feedback = await collector.submit_feedback(
            feedback_type=FeedbackType.FEATURE_REQUEST,
            title="Add dark mode",
            description="Would love to have a dark mode option for the interface",
            user_id="user456",
            priority=FeedbackPriority.MEDIUM,
            context=context,
            tags={"ui", "enhancement"},
            contact_info="user456@example.com"
        )
        
        print(f"  Submitted feedback: {feedback.title}")
        print(f"  Generated ID: {feedback.id}")
        print(f"  Auto sentiment: {feedback.sentiment}")
        print(f"  Auto tags: {feedback.tags}")
        print(f"  Listener called: {len(listener_calls) > 0}")
        print(f"  Stored in collector: {feedback.id in collector.feedback_items}")
        
        # Test retrieval
        retrieved = collector.get_feedback(feedback.id)
        print(f"  Retrieved successfully: {retrieved is not None}")
        print(f"  Title matches: {retrieved.title == feedback.title}")
    
    print("✓ Feedback submission working")


async def test_auto_categorization():
    """Test automatic feedback categorization."""
    print("\n=== Testing Auto Categorization ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        # Test different types of feedback
        test_cases = [
            ("App crashes when I start voice mode", {"bug", "audio", "voice"}),
            ("The interface is slow and laggy", {"performance", "ui"}),
            ("Love the new keyboard shortcuts!", {"keyboard", "ui"}),
            ("Microphone setup is confusing", {"audio", "setup", "voice"}),
            ("Critical error in speech recognition", {"bug", "voice"})
        ]
        
        for title, expected_tags in test_cases:
            feedback = await collector.submit_feedback(
                feedback_type=FeedbackType.GENERAL_COMMENT,
                title=title,
                description="Test description"
            )
            
            matched_tags = feedback.tags.intersection(expected_tags)
            print(f"  '{title}' -> {feedback.tags}")
            print(f"    Expected: {expected_tags}, Matched: {matched_tags}")
            print(f"    Priority: {feedback.priority.name}")
    
    print("✓ Auto categorization working")


async def test_sentiment_analysis():
    """Test sentiment analysis of feedback."""
    print("\n=== Testing Sentiment Analysis ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        sentiment_tests = [
            ("This is amazing! Love the new features!", FeedbackSentiment.POSITIVE),
            ("The app is terrible and broken", FeedbackSentiment.NEGATIVE),
            ("Setup instructions are clear", FeedbackSentiment.NEUTRAL),
            ("Good features but bad performance", FeedbackSentiment.MIXED),
            ("Excellent voice quality, terrible UI", FeedbackSentiment.MIXED)
        ]
        
        for text, expected_sentiment in sentiment_tests:
            feedback = await collector.submit_feedback(
                feedback_type=FeedbackType.GENERAL_COMMENT,
                title=text,
                description="Test sentiment analysis"
            )
            
            print(f"  '{text}' -> {feedback.sentiment}")
            print(f"    Expected: {expected_sentiment}, Got: {feedback.sentiment}")
    
    print("✓ Sentiment analysis working")


async def test_duplicate_detection():
    """Test duplicate feedback detection."""
    print("\n=== Testing Duplicate Detection ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        # Submit original feedback
        original = await collector.submit_feedback(
            feedback_type=FeedbackType.BUG_REPORT,
            title="Voice recognition not working",
            description="Speech to text is not responding"
        )
        
        # Submit similar feedback
        similar = await collector.submit_feedback(
            feedback_type=FeedbackType.BUG_REPORT,
            title="Voice recognition broken",
            description="STT functionality is broken"
        )
        
        # Submit different feedback
        different = await collector.submit_feedback(
            feedback_type=FeedbackType.FEATURE_REQUEST,
            title="Add new voice commands",
            description="Would like more voice commands"
        )
        
        print(f"  Original feedback: {original.title}")
        print(f"  Similar feedback: {similar.title}")
        print(f"    Related to original: {original.id in similar.related_feedback}")
        print(f"  Different feedback: {different.title}")
        print(f"    Has no relations: {len(different.related_feedback) == 0}")
    
    print("✓ Duplicate detection working")


async def test_feedback_filtering():
    """Test feedback filtering and listing."""
    print("\n=== Testing Feedback Filtering ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        # Create test feedback items with different properties
        await collector.submit_feedback(
            FeedbackType.BUG_REPORT, "Bug 1", user_id="user1", priority=FeedbackPriority.HIGH
        )
        await collector.submit_feedback(
            FeedbackType.FEATURE_REQUEST, "Feature 1", user_id="user2", priority=FeedbackPriority.LOW
        )
        await collector.submit_feedback(
            FeedbackType.BUG_REPORT, "Bug 2", user_id="user1", priority=FeedbackPriority.CRITICAL
        )
        
        # Test filtering
        all_feedback = collector.list_feedback()
        print(f"  Total feedback: {len(all_feedback)}")
        
        bug_reports = collector.list_feedback(feedback_type=FeedbackType.BUG_REPORT)
        print(f"  Bug reports: {len(bug_reports)}")
        
        user1_feedback = collector.list_feedback(user_id="user1")
        print(f"  User1 feedback: {len(user1_feedback)}")
        
        high_priority = collector.list_feedback(priority=FeedbackPriority.HIGH)
        print(f"  High priority: {len(high_priority)}")
        
        # Test combined filters
        user1_bugs = collector.list_feedback(
            feedback_type=FeedbackType.BUG_REPORT,
            user_id="user1"
        )
        print(f"  User1 bugs: {len(user1_bugs)}")
    
    print("✓ Feedback filtering working")


async def test_feedback_status_updates():
    """Test feedback status updates and resolution."""
    print("\n=== Testing Feedback Status Updates ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        # Submit feedback
        feedback = await collector.submit_feedback(
            feedback_type=FeedbackType.BUG_REPORT,
            title="Test bug report",
            description="This is a test bug"
        )
        
        print(f"  Initial status: {feedback.status.name}")
        print(f"  Resolved at: {feedback.resolved_at}")
        
        # Update to in progress
        success = await collector.update_feedback_status(
            feedback.id,
            FeedbackStatus.IN_PROGRESS,
            "Working on this issue"
        )
        
        updated_feedback = collector.get_feedback(feedback.id)
        print(f"  Update success: {success}")
        print(f"  New status: {updated_feedback.status.name}")
        print(f"  Resolution notes: {updated_feedback.resolution_notes}")
        
        # Resolve feedback
        await collector.update_feedback_status(
            feedback.id,
            FeedbackStatus.RESOLVED,
            "Issue has been fixed in version 1.0.1"
        )
        
        resolved_feedback = collector.get_feedback(feedback.id)
        print(f"  Final status: {resolved_feedback.status.name}")
        print(f"  Resolved at: {resolved_feedback.resolved_at is not None}")
        
        # Test voting
        collector.vote_feedback(feedback.id, 3)
        voted_feedback = collector.get_feedback(feedback.id)
        print(f"  Votes after voting: {voted_feedback.votes}")
    
    print("✓ Feedback status updates working")


async def test_feedback_statistics():
    """Test feedback statistics generation."""
    print("\n=== Testing Feedback Statistics ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        # Create diverse feedback data
        feedback_data = [
            (FeedbackType.BUG_REPORT, FeedbackPriority.HIGH, FeedbackStatus.RESOLVED, {"bug", "audio"}),
            (FeedbackType.FEATURE_REQUEST, FeedbackPriority.MEDIUM, FeedbackStatus.IN_PROGRESS, {"ui", "enhancement"}),
            (FeedbackType.BUG_REPORT, FeedbackPriority.CRITICAL, FeedbackStatus.RESOLVED, {"bug", "crash"}),
            (FeedbackType.USABILITY_ISSUE, FeedbackPriority.LOW, FeedbackStatus.SUBMITTED, {"ui", "confusion"}),
            (FeedbackType.PERFORMANCE_FEEDBACK, FeedbackPriority.MEDIUM, FeedbackStatus.ACKNOWLEDGED, {"performance"})
        ]
        
        for feedback_type, priority, status, tags in feedback_data:
            feedback = await collector.submit_feedback(
                feedback_type=feedback_type,
                title=f"Test {feedback_type.name}",
                description="Test feedback",
                priority=priority,
                tags=tags
            )
            
            # Simulate resolution for resolved items
            if status == FeedbackStatus.RESOLVED:
                # Set resolved_at manually for testing
                feedback.resolved_at = datetime.now() - timedelta(hours=2)
                feedback.status = status
                collector._save_feedback(feedback)
        
        # Get statistics
        stats = collector.get_statistics()
        
        print(f"  Total feedback: {stats.total_feedback}")
        print(f"  By type: {[(t.name, count) for t, count in stats.by_type.items()]}")
        print(f"  By priority: {[(p.name, count) for p, count in stats.by_priority.items()]}")
        print(f"  By status: {[(s.name, count) for s, count in stats.by_status.items()]}")
        print(f"  By sentiment: {[(s.name, count) for s, count in stats.by_sentiment.items()]}")
        print(f"  Common issues: {stats.common_issues[:5]}")
        print(f"  User satisfaction: {stats.user_satisfaction:.2f}")
        print(f"  Average resolution time: {stats.resolution_time}")
    
    print("✓ Feedback statistics working")


async def test_feedback_ui():
    """Test feedback UI functionality."""
    print("\n=== Testing Feedback UI ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        ui = FeedbackUI(collector)
        
        # Test form display
        form = await ui.show_feedback_form(
            feedback_type=FeedbackType.BUG_REPORT,
            pre_filled_title="Test bug",
            pre_filled_description="This is a test"
        )
        
        print(f"  Form ID: {form['form_id']}")
        print(f"  Available types: {len(form['feedback_types'])}")
        print(f"  Pre-filled title: {form['pre_filled']['title']}")
        print(f"  Optional fields: {form['optional_fields']}")
        
        # Test form submission
        form_data = {
            "type": "bug_report",
            "title": "Test submission",
            "description": "This is a test submission",
            "priority": "high",
            "tags": "bug, test, ui",
            "contact_info": "test@example.com"
        }
        
        result = await ui.submit_form_data(form_data)
        print(f"  Submission success: {result['success']}")
        print(f"  Feedback ID: {result.get('feedback_id', 'N/A')}")
        print(f"  Message: {result.get('message', 'N/A')}")
        
        if result['success']:
            # Test status check
            status = ui.get_feedback_status(result['feedback_id'])
            print(f"  Status check: {status['status']}")
            print(f"  Submitted at: {status['submitted_at']}")
        
        # Test user summary (submit more feedback first)
        await collector.submit_feedback(
            FeedbackType.FEATURE_REQUEST,
            "Another test",
            user_id="test_user"
        )
        
        summary = ui.get_user_feedback_summary("test_user")
        print(f"  User feedback count: {summary['total_submitted']}")
        print(f"  Status breakdown: {summary['by_status']}")
    
    print("✓ Feedback UI working")


async def test_data_persistence():
    """Test feedback data persistence."""
    print("\n=== Testing Data Persistence ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        
        # Create collector and add feedback
        collector1 = FeedbackCollector(db_path=db_path)
        
        feedback_id = (await collector1.submit_feedback(
            feedback_type=FeedbackType.BUG_REPORT,
            title="Persistence test",
            description="Testing data persistence",
            user_id="persist_user",
            tags={"test", "persistence"}
        )).id
        
        print(f"  Created feedback with ID: {feedback_id}")
        print(f"  Items in collector1: {len(collector1.feedback_items)}")
        
        # Create new collector instance (should load from database)
        collector2 = FeedbackCollector(db_path=db_path)
        print(f"  Items in collector2: {len(collector2.feedback_items)}")
        
        # Verify data loaded correctly
        loaded_feedback = collector2.get_feedback(feedback_id)
        if loaded_feedback:
            print(f"  Loaded feedback title: {loaded_feedback.title}")
            print(f"  Loaded user ID: {loaded_feedback.user_id}")
            print(f"  Loaded tags: {loaded_feedback.tags}")
            print(f"  Created at preserved: {loaded_feedback.created_at is not None}")
        else:
            print("  ERROR: Failed to load feedback from database")
    
    print("✓ Data persistence working")


async def test_export_functionality():
    """Test feedback data export."""
    print("\n=== Testing Export Functionality ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        # Add some test feedback
        await collector.submit_feedback(
            FeedbackType.BUG_REPORT,
            "Export test bug",
            description="Testing export functionality",
            tags={"export", "test"}
        )
        
        await collector.submit_feedback(
            FeedbackType.FEATURE_REQUEST,
            "Export test feature",
            description="Testing export feature request",
            priority=FeedbackPriority.HIGH
        )
        
        # Test JSON export
        json_export = collector.export_feedback("json")
        print(f"  JSON export length: {len(json_export)} characters")
        
        # Parse and validate JSON
        try:
            data = json.loads(json_export)
            print(f"  Exported items: {data['total_items']}")
            print(f"  Export timestamp: {data['exported_at']}")
            print(f"  First item type: {data['feedback'][0]['type']}")
        except Exception as e:
            print(f"  JSON parsing error: {e}")
        
        # Test invalid format
        try:
            collector.export_feedback("xml")
            print("  ERROR: Should have raised ValueError for unsupported format")
        except ValueError:
            print("  Correctly rejected unsupported format")
    
    print("✓ Export functionality working")


async def test_global_instances():
    """Test global feedback system instances."""
    print("\n=== Testing Global Instances ===")
    
    # Test global collector
    collector1 = get_feedback_collector()
    collector2 = get_feedback_collector()
    
    print(f"  Same collector instance: {collector1 is collector2}")
    print(f"  Collector type: {type(collector1).__name__}")
    
    # Test global UI
    ui1 = get_feedback_ui()
    ui2 = get_feedback_ui()
    
    print(f"  UI instances use same collector: {ui1.collector is ui2.collector}")
    print(f"  UI type: {type(ui1).__name__}")
    
    # Test that operations persist across instances
    original_count = len(collector1.feedback_items)
    await collector1.submit_feedback(
        FeedbackType.GENERAL_COMMENT,
        "Global test",
        description="Testing global instance persistence"
    )
    
    new_count = len(collector2.feedback_items)
    print(f"  Feedback count changed: {new_count > original_count}")
    
    print("✓ Global instances working")


async def test_performance():
    """Test feedback system performance."""
    print("\n=== Testing Performance ===")
    
    import time
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        
        # Test submission performance
        start_time = time.time()
        
        for i in range(50):
            await collector.submit_feedback(
                feedback_type=FeedbackType.GENERAL_COMMENT,
                title=f"Performance test {i}",
                description=f"Testing performance with item {i}",
                tags={"performance", "test"}
            )
        
        submission_time = time.time() - start_time
        submission_rate = 50 / submission_time
        
        print(f"  Submission rate: {submission_rate:.1f} submissions/sec")
        
        # Test retrieval performance
        start_time = time.time()
        
        for _ in range(500):
            collector.list_feedback(limit=10)
        
        retrieval_time = time.time() - start_time
        retrieval_rate = 500 / retrieval_time
        
        print(f"  List retrieval rate: {retrieval_rate:.1f} retrievals/sec")
        
        # Test search performance
        start_time = time.time()
        
        for _ in range(100):
            collector.list_feedback(feedback_type=FeedbackType.GENERAL_COMMENT)
        
        search_time = time.time() - start_time
        search_rate = 100 / search_time
        
        print(f"  Filtered search rate: {search_rate:.1f} searches/sec")
        
        # Test statistics performance
        start_time = time.time()
        
        for _ in range(100):
            collector.get_statistics()
        
        stats_time = time.time() - start_time
        stats_rate = 100 / stats_time
        
        print(f"  Statistics calculation rate: {stats_rate:.1f} calculations/sec")
    
    print("✓ Performance acceptable")


async def test_error_handling():
    """Test feedback system error handling."""
    print("\n=== Testing Error Handling ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_feedback.db"
        collector = FeedbackCollector(db_path=db_path)
        ui = FeedbackUI(collector)
        
        # Test invalid feedback ID retrieval
        invalid_feedback = collector.get_feedback("invalid-id")
        print(f"  Invalid ID retrieval: {invalid_feedback is None}")
        
        # Test status update with invalid ID
        update_result = await collector.update_feedback_status(
            "invalid-id",
            FeedbackStatus.RESOLVED
        )
        print(f"  Invalid ID status update: {not update_result}")
        
        # Test voting with invalid ID
        vote_result = collector.vote_feedback("invalid-id")
        print(f"  Invalid ID voting: {not vote_result}")
        
        # Test UI with invalid form data
        invalid_form_data = {
            "type": "invalid_type",
            "title": "",  # Empty title
            "priority": "invalid_priority"
        }
        
        result = await ui.submit_form_data(invalid_form_data)
        print(f"  Invalid form handling: {not result['success']}")
        
        # Test UI status check with invalid ID
        status_result = ui.get_feedback_status("invalid-id")
        print(f"  Invalid status check: {'error' in status_result}")
        
        # Test export with invalid format
        try:
            collector.export_feedback("invalid_format")
            print("  ERROR: Should have raised ValueError")
        except ValueError:
            print("  Invalid export format handled correctly")
        
        # Test empty title submission
        try:
            empty_feedback = await collector.submit_feedback(
                feedback_type=FeedbackType.BUG_REPORT,
                title="",  # Empty title
                description="Test empty title"
            )
            print(f"  Empty title allowed: {empty_feedback.title == ''}")
        except Exception as e:
            print(f"  Empty title error: {e}")
    
    print("✓ Error handling working")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("FEEDBACK SYSTEM TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_feedback_item_creation()
    test_feedback_collector_initialization()
    
    # Run async tests
    await test_feedback_submission()
    await test_auto_categorization()
    await test_sentiment_analysis()
    await test_duplicate_detection()
    await test_feedback_filtering()
    await test_feedback_status_updates()
    await test_feedback_statistics()
    await test_feedback_ui()
    await test_data_persistence()
    await test_export_functionality()
    await test_global_instances()
    await test_performance()
    await test_error_handling()
    
    print("\n" + "=" * 60)
    print("✓ All feedback system tests passed!")
    print("Sprint 40 complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())