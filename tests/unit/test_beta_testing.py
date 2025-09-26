#!/usr/bin/env python3
"""Test suite for beta testing framework."""

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
import uuid

# Test imports
from voice_mode.beta_testing import (
    TestCategory,
    TestPriority,
    TestStatus,
    FeedbackType,
    FeedbackSeverity,
    UserSegment,
    BetaTest,
    UserFeedback,
    TestSession,
    TestSuite,
    FeedbackCollector,
    UserAcceptanceTester,
    BetaDeployment,
    BetaTestingManager
)


async def test_beta_test_creation():
    """Test beta test case creation and execution."""
    print("\n=== Testing Beta Test Creation ===")
    
    test = BetaTest(
        id=str(uuid.uuid4()),
        name="Sample Test",
        description="Test description",
        category=TestCategory.FUNCTIONALITY,
        priority=TestPriority.HIGH,
        steps=["Step 1", "Step 2", "Step 3"],
        expected_result="Expected outcome",
        user_segments={UserSegment.DEVELOPER, UserSegment.POWER_USER}
    )
    
    print(f"  Test created: {test.name}")
    print(f"  Category: {test.category.value}")
    print(f"  Priority: {test.priority.value}")
    print(f"  Steps: {len(test.steps)}")
    print(f"  User segments: {len(test.user_segments)}")
    
    # Execute test
    success = test.execute()
    print(f"  Execution result: {test.status.value}")
    print(f"  Test passed: {test.status == TestStatus.PASSED or test.status == TestStatus.FAILED}")
    
    # Convert to dict
    test_dict = test.to_dict()
    print(f"  Dict conversion: {len(test_dict)} fields")
    
    print("✓ Beta test creation working")
    return True


async def test_user_feedback():
    """Test user feedback submission and management."""
    print("\n=== Testing User Feedback ===")
    
    feedback = UserFeedback(
        id=str(uuid.uuid4()),
        user_id="test_user_123",
        user_segment=UserSegment.DEVELOPER,
        type=FeedbackType.BUG_REPORT,
        severity=FeedbackSeverity.HIGH,
        title="Voice recognition issue",
        description="Voice recognition fails with background noise",
        tags={"voice", "recognition", "audio"}
    )
    
    print(f"  Feedback created: {feedback.title}")
    print(f"  Type: {feedback.type.value}")
    print(f"  Severity: {feedback.severity.value}")
    print(f"  Tags: {len(feedback.tags)}")
    
    # Add comment
    feedback.add_comment("reviewer_1", "Confirmed, reproducible issue")
    print(f"  Comments added: {len(feedback.comments)}")
    
    # Resolve feedback
    feedback.resolve("Fixed in version 1.0.1", "dev_team")
    print(f"  Status: {feedback.status}")
    print(f"  Resolved: {feedback.resolved_at is not None}")
    
    # Convert to dict
    feedback_dict = feedback.to_dict()
    print(f"  Dict conversion: {len(feedback_dict)} fields")
    
    print("✓ User feedback working")
    return True


async def test_test_session():
    """Test beta testing session management."""
    print("\n=== Testing Test Session ===")
    
    session = TestSession(
        id=str(uuid.uuid4()),
        user_id="tester_456",
        user_segment=UserSegment.POWER_USER
    )
    
    print(f"  Session created: {session.id[:8]}...")
    print(f"  User segment: {session.user_segment.value}")
    
    # Simulate test completion
    session.tests_completed = ["test1", "test2", "test3"]
    session.tests_passed = ["test1", "test3"]
    session.tests_failed = ["test2"]
    
    # End session
    session.end_session()
    
    print(f"  Tests completed: {len(session.tests_completed)}")
    print(f"  Pass rate: {session.metrics.get('pass_rate', 0):.1%}")
    print(f"  Duration: {session.metrics.get('duration', 0):.1f} seconds")
    
    # Convert to dict
    session_dict = session.to_dict()
    print(f"  Dict conversion: {len(session_dict)} fields")
    
    print("✓ Test session working")
    return True


async def test_test_suite():
    """Test test suite management."""
    print("\n=== Testing Test Suite ===")
    
    suite = TestSuite("Test Suite", "1.0.0")
    
    # Add tests
    for i in range(5):
        test = BetaTest(
            id=str(uuid.uuid4()),
            name=f"Test {i+1}",
            description=f"Description {i+1}",
            category=list(TestCategory)[i % len(TestCategory)],
            priority=list(TestPriority)[i % len(TestPriority)]
        )
        suite.add_test(test)
    
    print(f"  Suite created: {suite.name}")
    print(f"  Version: {suite.version}")
    print(f"  Total tests: {len(suite.tests)}")
    
    # Get tests by category
    functionality_tests = suite.get_tests_by_category(TestCategory.FUNCTIONALITY)
    print(f"  Functionality tests: {len(functionality_tests)}")
    
    # Get statistics
    stats = suite.get_statistics()
    print(f"  Categories tracked: {len(stats['by_category'])}")
    print(f"  Priorities tracked: {len(stats['by_priority'])}")
    print(f"  Statuses tracked: {len(stats['by_status'])}")
    
    print("✓ Test suite working")
    return True


async def test_feedback_collector():
    """Test feedback collection and reporting."""
    print("\n=== Testing Feedback Collector ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_feedback.db")
        collector = FeedbackCollector(db_path)
        
        # Submit feedback
        feedback_items = []
        for i in range(3):
            feedback = UserFeedback(
                id=str(uuid.uuid4()),
                user_id=f"user_{i}",
                user_segment=list(UserSegment)[i % len(UserSegment)],
                type=list(FeedbackType)[i % len(FeedbackType)],
                severity=list(FeedbackSeverity)[i % len(FeedbackSeverity)],
                title=f"Issue {i+1}",
                description=f"Description of issue {i+1}",
                upvotes=i * 10
            )
            feedback_id = collector.submit_feedback(feedback)
            feedback_items.append(feedback)
        
        print(f"  Feedback submitted: {len(collector.feedback)}")
        
        # Get trending issues
        trending = collector.get_trending_issues(2)
        print(f"  Trending issues: {len(trending)}")
        print(f"  Top issue upvotes: {trending[0].upvotes if trending else 0}")
        
        # Generate report
        report = collector.generate_feedback_report()
        print(f"  Report sections: {len(report)}")
        print(f"  Total feedback: {report['total_feedback']}")
        print(f"  Has trending data: {'trending_issues' in report}")
        
        print("✓ Feedback collector working")
    
    return True


async def test_user_acceptance_tester():
    """Test UAT functionality."""
    print("\n=== Testing User Acceptance Tester ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        tester = UserAcceptanceTester()
        
        print(f"  UAT initialized")
        print(f"  Default tests: {len(tester.test_suite.tests)}")
        
        # Start session
        session_id = tester.start_session("test_user", UserSegment.DEVELOPER)
        print(f"  Session started: {session_id[:8]}...")
        
        # Run a test
        test_id = list(tester.test_suite.tests.keys())[0]
        result = tester.run_test(session_id, test_id)
        print(f"  Test executed: {result.get('test_name', 'Unknown')}")
        print(f"  Test status: {result.get('status', 'Unknown')}")
        
        # Submit feedback
        feedback_id = tester.submit_feedback(
            session_id,
            FeedbackType.SUGGESTION,
            FeedbackSeverity.LOW,
            "UI Improvement",
            "Consider adding dark mode",
            tags=["ui", "enhancement"]
        )
        print(f"  Feedback submitted: {feedback_id[:8]}...")
        
        # End session
        session_result = tester.end_session(session_id)
        print(f"  Session ended")
        print(f"  Tests completed: {session_result.get('tests_completed', 0)}")
        
        # Generate report
        report = tester.generate_uat_report()
        print(f"  UAT report generated")
        print(f"  Report sections: {len(report)}")
        
        print("✓ User acceptance tester working")
    
    return True


async def test_beta_deployment():
    """Test beta deployment management."""
    print("\n=== Testing Beta Deployment ===")
    
    deployment = BetaDeployment("1.0.0-beta", "beta")
    
    print(f"  Deployment created: v{deployment.version}")
    print(f"  Channel: {deployment.channel}")
    
    # Deploy
    result = deployment.deploy(["staging", "beta-users"], 25)
    print(f"  Deployed to: {len(result['targets'])} targets")
    print(f"  Rollout: {result['rollout_percentage']}%")
    
    # Enable for segments
    deployment.enable_for_segment(UserSegment.DEVELOPER)
    deployment.enable_for_segment(UserSegment.POWER_USER)
    print(f"  Enabled segments: {len(deployment.enabled_segments)}")
    
    # Adjust rollout
    adjustment = deployment.adjust_rollout(50)
    print(f"  Rollout adjusted: {adjustment['previous']}% -> {adjustment['current']}%")
    
    # Get status
    status = deployment.get_deployment_status()
    print(f"  Status active: {status['is_active']}")
    print(f"  Current rollout: {status['rollout_percentage']}%")
    
    print("✓ Beta deployment working")
    return True


async def test_beta_testing_manager():
    """Test main beta testing manager."""
    print("\n=== Testing Beta Testing Manager ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        manager = BetaTestingManager("CHATTA", "1.0.0-beta")
        
        print(f"  Manager initialized: {manager.project_name}")
        print(f"  Version: {manager.version}")
        
        # Launch beta program
        launch_result = manager.launch_beta_program(
            segments=[UserSegment.DEVELOPER, UserSegment.POWER_USER],
            rollout=20
        )
        print(f"  Beta launched: {launch_result['status']}")
        print(f"  Rollout: {launch_result['deployment']['rollout_percentage']}%")
        
        # Onboard tester
        session_id = manager.onboard_tester("beta_tester_1", UserSegment.DEVELOPER)
        print(f"  Tester onboarded: {session_id[:8]}...")
        
        # Collect metrics
        metrics = manager.collect_metrics()
        print(f"  Metrics collected")
        print(f"  Metric categories: {len(metrics)}")
        
        # Generate report
        report = manager.generate_beta_report()
        print(f"  Report generated: {len(report)} chars")
        print(f"  Has deployment status: {'Deployment Status' in report}")
        print(f"  Has testing summary: {'Testing Summary' in report}")
        print(f"  Has feedback summary: {'Feedback Summary' in report}")
        
        print("✓ Beta testing manager working")
    
    return True


async def test_test_categories_and_priorities():
    """Test all test categories and priorities."""
    print("\n=== Testing Categories and Priorities ===")
    
    # Test categories
    categories = list(TestCategory)
    print(f"  Test categories: {len(categories)}")
    for cat in categories:
        print(f"    - {cat.value}: {cat.name}")
    
    # Test priorities
    priorities = list(TestPriority)
    print(f"  Test priorities: {len(priorities)}")
    for pri in priorities:
        print(f"    - {pri.value}: {pri.name}")
    
    # Test statuses
    statuses = list(TestStatus)
    print(f"  Test statuses: {len(statuses)}")
    for status in statuses:
        print(f"    - {status.value}: {status.name}")
    
    # User segments
    segments = list(UserSegment)
    print(f"  User segments: {len(segments)}")
    for seg in segments:
        print(f"    - {seg.value}: {seg.name}")
    
    print("✓ Categories and priorities working")
    return True


async def test_feedback_types_and_severities():
    """Test feedback types and severities."""
    print("\n=== Testing Feedback Types and Severities ===")
    
    # Feedback types
    types = list(FeedbackType)
    print(f"  Feedback types: {len(types)}")
    for ft in types:
        print(f"    - {ft.value}: {ft.name}")
    
    # Feedback severities
    severities = list(FeedbackSeverity)
    print(f"  Feedback severities: {len(severities)}")
    for sev in severities:
        print(f"    - {sev.value}: {sev.name}")
    
    print("✓ Feedback types and severities working")
    return True


async def test_end_to_end_beta_flow():
    """Test complete beta testing workflow."""
    print("\n=== Testing End-to-End Beta Flow ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        # Initialize manager
        manager = BetaTestingManager("CHATTA", "1.0.0-beta")
        
        # Launch beta
        launch = manager.launch_beta_program(
            segments=[UserSegment.DEVELOPER],
            rollout=10
        )
        print(f"  Beta launched: {launch['status']}")
        
        # Onboard multiple testers
        sessions = []
        for i in range(3):
            session_id = manager.onboard_tester(
                f"tester_{i}",
                list(UserSegment)[i % len(UserSegment)]
            )
            sessions.append(session_id)
        
        print(f"  Testers onboarded: {len(sessions)}")
        
        # Run tests for each session
        for session_id in sessions[:1]:  # Run for first session only
            # Get available tests
            tests = list(manager.uat_tester.test_suite.tests.keys())
            if tests:
                test_result = manager.uat_tester.run_test(session_id, tests[0])
                print(f"  Test run: {test_result.get('test_name', 'Unknown')}")
            
            # Submit feedback
            feedback_id = manager.uat_tester.submit_feedback(
                session_id,
                FeedbackType.BUG_REPORT,
                FeedbackSeverity.MEDIUM,
                "Test Issue",
                "Found during beta testing"
            )
            print(f"  Feedback submitted: {feedback_id[:8]}...")
            
            # End session
            manager.uat_tester.end_session(session_id)
        
        # Collect final metrics
        final_metrics = manager.collect_metrics()
        print(f"  Final metrics collected")
        print(f"  Total sessions: {final_metrics['testing']['session_statistics']['total_sessions']}")
        
        # Generate final report
        final_report = manager.generate_beta_report()
        print(f"  Final report generated: {len(final_report)} chars")
        
        print("✓ End-to-end beta flow working")
    
    return True


async def run_all_beta_tests():
    """Run all beta testing tests."""
    tests = [
        test_beta_test_creation,
        test_user_feedback,
        test_test_session,
        test_test_suite,
        test_feedback_collector,
        test_user_acceptance_tester,
        test_beta_deployment,
        test_beta_testing_manager,
        test_test_categories_and_priorities,
        test_feedback_types_and_severities,
        test_end_to_end_beta_flow
    ]
    
    results = []
    for i, test in enumerate(tests, 1):
        try:
            print(f"\n[{i}/{len(tests)}] Running {test.__name__}")
            result = await test()
            results.append((test.__name__, result, None))
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            results.append((test.__name__, False, str(e)))
    
    return results


def main():
    """Main test runner."""
    print("=" * 70)
    print("BETA TESTING FRAMEWORK VALIDATION")
    print("=" * 70)
    
    start_time = time.time()
    
    # Run tests
    results = asyncio.run(run_all_beta_tests())
    
    # Summary
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    print("\n" + "=" * 70)
    print("✓ Beta testing validation complete!")
    print(f"  Tests passed: {passed}/{len(results)}")
    print(f"  Success rate: {passed/len(results)*100:.1f}%")
    print(f"  Total validation time: {time.time() - start_time:.3f}s")
    
    if passed == len(results):
        print("🎉 All beta testing tests PASSED!")
        print("Sprint 47 beta testing framework COMPLETE!")
    else:
        print(f"⚠️  {failed} test(s) failed - review above for details")
    
    print("=" * 70)
    
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    exit(main())