#!/usr/bin/env python3
"""Beta testing and feedback collection framework."""

import asyncio
import json
import logging
import os
import platform
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from collections import defaultdict

# Set up logging
logger = logging.getLogger("voice_mode.beta_testing")


class TestCategory(Enum):
    """Categories for beta tests."""
    FUNCTIONALITY = "functionality"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    COMPATIBILITY = "compatibility"
    INTEGRATION = "integration"
    ACCESSIBILITY = "accessibility"
    LOCALIZATION = "localization"
    SECURITY = "security"
    RELIABILITY = "reliability"
    DOCUMENTATION = "documentation"


class TestPriority(Enum):
    """Priority levels for tests."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NICE_TO_HAVE = "nice_to_have"


class TestStatus(Enum):
    """Status of a test."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    DEFERRED = "deferred"


class FeedbackType(Enum):
    """Types of user feedback."""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    USABILITY_ISSUE = "usability_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    COMPATIBILITY_ISSUE = "compatibility_issue"
    DOCUMENTATION_ISSUE = "documentation_issue"
    SUGGESTION = "suggestion"
    COMPLIMENT = "compliment"
    QUESTION = "question"
    OTHER = "other"


class FeedbackSeverity(Enum):
    """Severity levels for feedback."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ENHANCEMENT = "enhancement"


class UserSegment(Enum):
    """User segments for testing."""
    DEVELOPER = "developer"
    POWER_USER = "power_user"
    CASUAL_USER = "casual_user"
    ENTERPRISE = "enterprise"
    STUDENT = "student"
    ACCESSIBILITY = "accessibility"
    INTERNATIONAL = "international"


@dataclass
class BetaTest:
    """Represents a beta test case."""
    id: str
    name: str
    description: str
    category: TestCategory
    priority: TestPriority
    status: TestStatus = TestStatus.PENDING
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    steps: List[str] = field(default_factory=list)
    expected_result: str = ""
    actual_result: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    user_segments: Set[UserSegment] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    
    def execute(self) -> bool:
        """Execute the test."""
        self.status = TestStatus.IN_PROGRESS
        self.updated_at = datetime.now()
        
        # Simulate test execution
        # In real implementation, this would run actual test logic
        logger.info(f"Executing test: {self.name}")
        
        # For demo, randomly pass/fail
        import random
        success = random.random() > 0.2
        
        if success:
            self.status = TestStatus.PASSED
            self.actual_result = self.expected_result
        else:
            self.status = TestStatus.FAILED
            self.actual_result = "Test failed - unexpected behavior"
        
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        
        return success
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['category'] = self.category.value
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['user_segments'] = [s.value for s in self.user_segments]
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


@dataclass
class UserFeedback:
    """Represents user feedback."""
    id: str
    user_id: str
    user_segment: UserSegment
    type: FeedbackType
    severity: FeedbackSeverity
    title: str
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: str = "open"
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    attachments: List[str] = field(default_factory=list)
    related_tests: Set[str] = field(default_factory=set)
    upvotes: int = 0
    comments: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_comment(self, user_id: str, comment: str):
        """Add a comment to the feedback."""
        self.comments.append({
            'user_id': user_id,
            'comment': comment,
            'timestamp': datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def resolve(self, resolution: str, assigned_to: str):
        """Resolve the feedback."""
        self.status = "resolved"
        self.resolution = resolution
        self.assigned_to = assigned_to
        self.resolved_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['user_segment'] = self.user_segment.value
        data['type'] = self.type.value
        data['severity'] = self.severity.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


@dataclass
class TestSession:
    """Represents a beta testing session."""
    id: str
    user_id: str
    user_segment: UserSegment
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    tests_completed: List[str] = field(default_factory=list)
    tests_passed: List[str] = field(default_factory=list)
    tests_failed: List[str] = field(default_factory=list)
    feedback_submitted: List[str] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def end_session(self):
        """End the testing session."""
        self.ended_at = datetime.now()
        
        # Calculate metrics
        total_tests = len(self.tests_completed)
        if total_tests > 0:
            self.metrics['pass_rate'] = len(self.tests_passed) / total_tests
            self.metrics['duration'] = (self.ended_at - self.started_at).total_seconds()
            self.metrics['tests_per_hour'] = total_tests / (self.metrics['duration'] / 3600)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['user_segment'] = self.user_segment.value
        data['started_at'] = self.started_at.isoformat()
        if self.ended_at:
            data['ended_at'] = self.ended_at.isoformat()
        return data


class TestSuite:
    """Manages a suite of beta tests."""
    
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.tests: Dict[str, BetaTest] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def add_test(self, test: BetaTest):
        """Add a test to the suite."""
        self.tests[test.id] = test
        self.updated_at = datetime.now()
        
    def remove_test(self, test_id: str):
        """Remove a test from the suite."""
        if test_id in self.tests:
            del self.tests[test_id]
            self.updated_at = datetime.now()
    
    def get_tests_by_category(self, category: TestCategory) -> List[BetaTest]:
        """Get tests by category."""
        return [t for t in self.tests.values() if t.category == category]
    
    def get_tests_by_priority(self, priority: TestPriority) -> List[BetaTest]:
        """Get tests by priority."""
        return [t for t in self.tests.values() if t.priority == priority]
    
    def get_tests_by_status(self, status: TestStatus) -> List[BetaTest]:
        """Get tests by status."""
        return [t for t in self.tests.values() if t.status == status]
    
    def get_tests_for_segment(self, segment: UserSegment) -> List[BetaTest]:
        """Get tests for a specific user segment."""
        return [t for t in self.tests.values() if segment in t.user_segments]
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests in the suite."""
        results = {
            'total': len(self.tests),
            'passed': 0,
            'failed': 0,
            'blocked': 0,
            'skipped': 0,
            'details': {}
        }
        
        for test_id, test in self.tests.items():
            if test.status == TestStatus.PENDING:
                success = test.execute()
                if success:
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                
                results['details'][test_id] = {
                    'name': test.name,
                    'status': test.status.value,
                    'result': test.actual_result
                }
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get test suite statistics."""
        stats = {
            'total_tests': len(self.tests),
            'by_status': defaultdict(int),
            'by_category': defaultdict(int),
            'by_priority': defaultdict(int),
            'completion_rate': 0.0
        }
        
        completed = 0
        for test in self.tests.values():
            stats['by_status'][test.status.value] += 1
            stats['by_category'][test.category.value] += 1
            stats['by_priority'][test.priority.value] += 1
            
            if test.status in [TestStatus.PASSED, TestStatus.FAILED]:
                completed += 1
        
        if stats['total_tests'] > 0:
            stats['completion_rate'] = completed / stats['total_tests']
        
        return stats


class FeedbackCollector:
    """Collects and manages user feedback."""
    
    def __init__(self, db_path: str = "beta_feedback.db"):
        self.db_path = db_path
        self.feedback: Dict[str, UserFeedback] = {}
        self._init_database()
    
    def _init_database(self):
        """Initialize the feedback database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_segment TEXT NOT NULL,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_to TEXT,
                resolution TEXT,
                resolved_at TEXT,
                tags TEXT,
                attachments TEXT,
                related_tests TEXT,
                upvotes INTEGER DEFAULT 0,
                comments TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def submit_feedback(self, feedback: UserFeedback) -> str:
        """Submit user feedback."""
        self.feedback[feedback.id] = feedback
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feedback (
                id, user_id, user_segment, type, severity,
                title, description, created_at, updated_at, status,
                assigned_to, resolution, resolved_at, tags, attachments,
                related_tests, upvotes, comments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback.id,
            feedback.user_id,
            feedback.user_segment.value,
            feedback.type.value,
            feedback.severity.value,
            feedback.title,
            feedback.description,
            feedback.created_at.isoformat(),
            feedback.updated_at.isoformat(),
            feedback.status,
            feedback.assigned_to,
            feedback.resolution,
            feedback.resolved_at.isoformat() if feedback.resolved_at else None,
            json.dumps(list(feedback.tags)),
            json.dumps(feedback.attachments),
            json.dumps(list(feedback.related_tests)),
            feedback.upvotes,
            json.dumps(feedback.comments)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Feedback submitted: {feedback.id}")
        return feedback.id
    
    def get_feedback_by_type(self, feedback_type: FeedbackType) -> List[UserFeedback]:
        """Get feedback by type."""
        return [f for f in self.feedback.values() if f.type == feedback_type]
    
    def get_feedback_by_severity(self, severity: FeedbackSeverity) -> List[UserFeedback]:
        """Get feedback by severity."""
        return [f for f in self.feedback.values() if f.severity == severity]
    
    def get_feedback_by_segment(self, segment: UserSegment) -> List[UserFeedback]:
        """Get feedback by user segment."""
        return [f for f in self.feedback.values() if f.user_segment == segment]
    
    def get_trending_issues(self, limit: int = 10) -> List[UserFeedback]:
        """Get trending issues based on upvotes."""
        sorted_feedback = sorted(
            self.feedback.values(),
            key=lambda f: f.upvotes,
            reverse=True
        )
        return sorted_feedback[:limit]
    
    def generate_feedback_report(self) -> Dict[str, Any]:
        """Generate a comprehensive feedback report."""
        report = {
            'total_feedback': len(self.feedback),
            'by_type': defaultdict(int),
            'by_severity': defaultdict(int),
            'by_segment': defaultdict(int),
            'by_status': defaultdict(int),
            'resolution_rate': 0.0,
            'average_resolution_time': None,
            'trending_issues': [],
            'common_tags': defaultdict(int)
        }
        
        resolved_count = 0
        resolution_times = []
        
        for feedback in self.feedback.values():
            report['by_type'][feedback.type.value] += 1
            report['by_severity'][feedback.severity.value] += 1
            report['by_segment'][feedback.user_segment.value] += 1
            report['by_status'][feedback.status] += 1
            
            if feedback.status == "resolved":
                resolved_count += 1
                if feedback.resolved_at and feedback.created_at:
                    resolution_time = (feedback.resolved_at - feedback.created_at).total_seconds()
                    resolution_times.append(resolution_time)
            
            for tag in feedback.tags:
                report['common_tags'][tag] += 1
        
        if report['total_feedback'] > 0:
            report['resolution_rate'] = resolved_count / report['total_feedback']
        
        if resolution_times:
            avg_time = sum(resolution_times) / len(resolution_times)
            report['average_resolution_time'] = avg_time / 3600  # Convert to hours
        
        # Get trending issues
        trending = self.get_trending_issues(5)
        report['trending_issues'] = [
            {
                'id': f.id,
                'title': f.title,
                'type': f.type.value,
                'severity': f.severity.value,
                'upvotes': f.upvotes
            }
            for f in trending
        ]
        
        return report


class UserAcceptanceTester:
    """Manages user acceptance testing."""
    
    def __init__(self):
        self.sessions: Dict[str, TestSession] = {}
        self.test_suite = TestSuite("CHATTA UAT", "1.0.0")
        self.feedback_collector = FeedbackCollector()
        self._create_default_tests()
    
    def _create_default_tests(self):
        """Create default UAT test cases."""
        # Functionality tests
        self.test_suite.add_test(BetaTest(
            id=str(uuid.uuid4()),
            name="Voice Conversation Basic",
            description="Test basic voice conversation functionality",
            category=TestCategory.FUNCTIONALITY,
            priority=TestPriority.CRITICAL,
            steps=[
                "Start voice mode",
                "Speak a simple question",
                "Verify response is received",
                "End conversation"
            ],
            expected_result="Voice conversation works smoothly",
            user_segments={UserSegment.CASUAL_USER, UserSegment.DEVELOPER}
        ))
        
        # Performance tests
        self.test_suite.add_test(BetaTest(
            id=str(uuid.uuid4()),
            name="Response Latency",
            description="Test response time for voice commands",
            category=TestCategory.PERFORMANCE,
            priority=TestPriority.HIGH,
            steps=[
                "Start voice mode",
                "Measure time from speech end to response start",
                "Repeat 10 times",
                "Calculate average latency"
            ],
            expected_result="Average latency < 2 seconds",
            user_segments={UserSegment.POWER_USER}
        ))
        
        # Usability tests
        self.test_suite.add_test(BetaTest(
            id=str(uuid.uuid4()),
            name="First-Time User Experience",
            description="Test ease of use for new users",
            category=TestCategory.USABILITY,
            priority=TestPriority.HIGH,
            steps=[
                "Install the application",
                "Start without reading documentation",
                "Try to have a voice conversation",
                "Rate difficulty on 1-10 scale"
            ],
            expected_result="Users can start using within 5 minutes",
            user_segments={UserSegment.CASUAL_USER, UserSegment.STUDENT}
        ))
        
        # Compatibility tests
        self.test_suite.add_test(BetaTest(
            id=str(uuid.uuid4()),
            name="Cross-Platform Compatibility",
            description="Test on different operating systems",
            category=TestCategory.COMPATIBILITY,
            priority=TestPriority.CRITICAL,
            steps=[
                "Test on Windows 10/11",
                "Test on macOS 12+",
                "Test on Ubuntu 20.04+",
                "Verify consistent behavior"
            ],
            expected_result="Works identically on all platforms",
            user_segments={UserSegment.DEVELOPER, UserSegment.ENTERPRISE}
        ))
        
        # Accessibility tests
        self.test_suite.add_test(BetaTest(
            id=str(uuid.uuid4()),
            name="Screen Reader Compatibility",
            description="Test with screen reader software",
            category=TestCategory.ACCESSIBILITY,
            priority=TestPriority.HIGH,
            steps=[
                "Enable screen reader",
                "Navigate interface",
                "Use voice commands",
                "Verify all features accessible"
            ],
            expected_result="Fully accessible with screen readers",
            user_segments={UserSegment.ACCESSIBILITY}
        ))
    
    def start_session(self, user_id: str, user_segment: UserSegment) -> str:
        """Start a new testing session."""
        session = TestSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_segment=user_segment,
            environment={
                'platform': platform.platform(),
                'python_version': sys.version,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        self.sessions[session.id] = session
        logger.info(f"Started testing session: {session.id}")
        return session.id
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a testing session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.end_session()
            
            return {
                'session_id': session_id,
                'duration': session.metrics.get('duration', 0),
                'tests_completed': len(session.tests_completed),
                'pass_rate': session.metrics.get('pass_rate', 0),
                'feedback_count': len(session.feedback_submitted)
            }
        
        return {}
    
    def run_test(self, session_id: str, test_id: str) -> Dict[str, Any]:
        """Run a specific test in a session."""
        if session_id not in self.sessions:
            return {'error': 'Invalid session'}
        
        if test_id not in self.test_suite.tests:
            return {'error': 'Invalid test'}
        
        session = self.sessions[session_id]
        test = self.test_suite.tests[test_id]
        
        # Execute test
        success = test.execute()
        
        # Update session
        session.tests_completed.append(test_id)
        if success:
            session.tests_passed.append(test_id)
        else:
            session.tests_failed.append(test_id)
        
        return {
            'test_id': test_id,
            'test_name': test.name,
            'success': success,
            'status': test.status.value,
            'result': test.actual_result
        }
    
    def submit_feedback(
        self,
        session_id: str,
        feedback_type: FeedbackType,
        severity: FeedbackSeverity,
        title: str,
        description: str,
        **kwargs
    ) -> str:
        """Submit feedback from a testing session."""
        if session_id not in self.sessions:
            return ""
        
        session = self.sessions[session_id]
        
        feedback = UserFeedback(
            id=str(uuid.uuid4()),
            user_id=session.user_id,
            user_segment=session.user_segment,
            type=feedback_type,
            severity=severity,
            title=title,
            description=description,
            tags=set(kwargs.get('tags', [])),
            attachments=kwargs.get('attachments', []),
            related_tests=set(kwargs.get('related_tests', []))
        )
        
        feedback_id = self.feedback_collector.submit_feedback(feedback)
        session.feedback_submitted.append(feedback_id)
        
        return feedback_id
    
    def generate_uat_report(self) -> Dict[str, Any]:
        """Generate comprehensive UAT report."""
        test_stats = self.test_suite.get_statistics()
        feedback_report = self.feedback_collector.generate_feedback_report()
        
        # Session statistics
        session_stats = {
            'total_sessions': len(self.sessions),
            'active_sessions': sum(1 for s in self.sessions.values() if s.ended_at is None),
            'completed_sessions': sum(1 for s in self.sessions.values() if s.ended_at is not None),
            'by_segment': defaultdict(int),
            'average_duration': None,
            'average_tests_per_session': None,
            'overall_pass_rate': None
        }
        
        total_duration = 0
        total_tests = 0
        total_passed = 0
        
        for session in self.sessions.values():
            session_stats['by_segment'][session.user_segment.value] += 1
            
            if session.ended_at:
                duration = (session.ended_at - session.started_at).total_seconds()
                total_duration += duration
                
                total_tests += len(session.tests_completed)
                total_passed += len(session.tests_passed)
        
        completed = session_stats['completed_sessions']
        if completed > 0:
            session_stats['average_duration'] = total_duration / completed / 3600  # Hours
            session_stats['average_tests_per_session'] = total_tests / completed
            
            if total_tests > 0:
                session_stats['overall_pass_rate'] = total_passed / total_tests
        
        return {
            'report_date': datetime.now().isoformat(),
            'test_statistics': test_stats,
            'session_statistics': session_stats,
            'feedback_report': feedback_report,
            'summary': {
                'total_tests': test_stats['total_tests'],
                'test_completion_rate': test_stats['completion_rate'],
                'total_feedback': feedback_report['total_feedback'],
                'feedback_resolution_rate': feedback_report['resolution_rate'],
                'total_sessions': session_stats['total_sessions'],
                'overall_pass_rate': session_stats['overall_pass_rate']
            }
        }


class BetaDeployment:
    """Manages beta deployment and distribution."""
    
    def __init__(self, version: str, channel: str = "beta"):
        self.version = version
        self.channel = channel
        self.deployed_at = None
        self.deployment_targets = []
        self.rollout_percentage = 0
        self.enabled_segments: Set[UserSegment] = set()
    
    def deploy(self, targets: List[str], rollout_percentage: int = 100):
        """Deploy beta version."""
        self.deployment_targets = targets
        self.rollout_percentage = rollout_percentage
        self.deployed_at = datetime.now()
        
        logger.info(f"Deployed version {self.version} to {targets} at {rollout_percentage}%")
        
        return {
            'version': self.version,
            'channel': self.channel,
            'targets': targets,
            'rollout_percentage': rollout_percentage,
            'deployed_at': self.deployed_at.isoformat()
        }
    
    def enable_for_segment(self, segment: UserSegment):
        """Enable beta for a specific user segment."""
        self.enabled_segments.add(segment)
        logger.info(f"Enabled beta for segment: {segment.value}")
    
    def disable_for_segment(self, segment: UserSegment):
        """Disable beta for a specific user segment."""
        self.enabled_segments.discard(segment)
        logger.info(f"Disabled beta for segment: {segment.value}")
    
    def adjust_rollout(self, new_percentage: int):
        """Adjust rollout percentage."""
        old_percentage = self.rollout_percentage
        self.rollout_percentage = new_percentage
        
        logger.info(f"Adjusted rollout from {old_percentage}% to {new_percentage}%")
        
        return {
            'previous': old_percentage,
            'current': new_percentage,
            'adjusted_at': datetime.now().isoformat()
        }
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        return {
            'version': self.version,
            'channel': self.channel,
            'deployed_at': self.deployed_at.isoformat() if self.deployed_at else None,
            'targets': self.deployment_targets,
            'rollout_percentage': self.rollout_percentage,
            'enabled_segments': [s.value for s in self.enabled_segments],
            'is_active': self.deployed_at is not None
        }


class BetaTestingManager:
    """Main manager for beta testing operations."""
    
    def __init__(self, project_name: str = "CHATTA", version: str = "1.0.0-beta"):
        self.project_name = project_name
        self.version = version
        self.uat_tester = UserAcceptanceTester()
        self.deployment = BetaDeployment(version)
        self.analytics = defaultdict(lambda: defaultdict(int))
        
    def launch_beta_program(self, segments: List[UserSegment], rollout: int = 10):
        """Launch the beta testing program."""
        logger.info(f"Launching beta program for {self.project_name} v{self.version}")
        
        # Deploy beta version
        deployment_result = self.deployment.deploy(
            targets=["staging", "beta-channel"],
            rollout_percentage=rollout
        )
        
        # Enable for specified segments
        for segment in segments:
            self.deployment.enable_for_segment(segment)
        
        # Track launch
        self.analytics['program']['launches'] += 1
        self.analytics['program']['launch_time'] = datetime.now().isoformat()
        
        return {
            'program': self.project_name,
            'version': self.version,
            'deployment': deployment_result,
            'enabled_segments': [s.value for s in segments],
            'status': 'launched'
        }
    
    def onboard_tester(self, user_id: str, segment: UserSegment) -> str:
        """Onboard a new beta tester."""
        session_id = self.uat_tester.start_session(user_id, segment)
        
        self.analytics['testers']['total'] += 1
        self.analytics['testers'][segment.value] += 1
        
        logger.info(f"Onboarded tester {user_id} in segment {segment.value}")
        
        return session_id
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive beta testing metrics."""
        uat_report = self.uat_tester.generate_uat_report()
        deployment_status = self.deployment.get_deployment_status()
        
        return {
            'program': self.project_name,
            'version': self.version,
            'deployment': deployment_status,
            'testing': uat_report,
            'analytics': dict(self.analytics),
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_beta_report(self) -> str:
        """Generate a comprehensive beta testing report."""
        metrics = self.collect_metrics()
        
        report = f"""
# Beta Testing Report
**Project:** {self.project_name}
**Version:** {self.version}
**Report Date:** {metrics['timestamp']}

## Deployment Status
- **Channel:** {metrics['deployment']['channel']}
- **Rollout:** {metrics['deployment']['rollout_percentage']}%
- **Targets:** {', '.join(metrics['deployment']['targets'])}
- **Enabled Segments:** {', '.join(metrics['deployment']['enabled_segments'])}

## Testing Summary
- **Total Tests:** {metrics['testing']['summary']['total_tests']}
- **Test Completion Rate:** {metrics['testing']['summary']['test_completion_rate']:.1%}
- **Overall Pass Rate:** {f"{metrics['testing']['summary']['overall_pass_rate']:.1%}" if metrics['testing']['summary'].get('overall_pass_rate') is not None else 'N/A'}
- **Total Sessions:** {metrics['testing']['summary']['total_sessions']}

## Feedback Summary
- **Total Feedback:** {metrics['testing']['summary']['total_feedback']}
- **Resolution Rate:** {metrics['testing']['summary']['feedback_resolution_rate']:.1%}

## Key Insights
- Most tested category: {max(metrics['testing']['test_statistics']['by_category'].items(), key=lambda x: x[1])[0] if metrics['testing']['test_statistics']['by_category'] else 'N/A'}
- Most common feedback type: {max(metrics['testing']['feedback_report']['by_type'].items(), key=lambda x: x[1])[0] if metrics['testing']['feedback_report']['by_type'] else 'N/A'}
- Most active segment: {max(metrics['testing']['session_statistics']['by_segment'].items(), key=lambda x: x[1])[0] if metrics['testing']['session_statistics']['by_segment'] else 'N/A'}

## Recommendations
1. Focus on resolving critical severity feedback
2. Improve test coverage for underrepresented segments
3. Consider expanding rollout if metrics are positive
4. Address trending issues before wider release
"""
        
        return report


def main():
    """Main entry point for beta testing."""
    manager = BetaTestingManager()
    
    # Launch beta program
    result = manager.launch_beta_program(
        segments=[UserSegment.DEVELOPER, UserSegment.POWER_USER],
        rollout=25
    )
    
    print(f"Beta program launched: {result}")
    
    # Generate report
    report = manager.generate_beta_report()
    print(report)


if __name__ == "__main__":
    main()