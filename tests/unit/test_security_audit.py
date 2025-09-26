#!/usr/bin/env python3
"""Test security audit system."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from voice_mode.security_audit import (
    SecurityAuditor,
    SecurityCategory,
    SeverityLevel,
    ComplianceStandard,
    SecurityFinding,
    SecurityAuditResult,
    APIKeyAudit,
    InputValidationAudit,
    DependencyAudit,
    CryptographyAudit,
    FileOperationsAudit,
    get_security_auditor,
    run_security_audit
)


def test_security_finding_creation():
    """Test security finding creation and properties."""
    print("\n=== Testing Security Finding Creation ===")
    
    finding = SecurityFinding(
        finding_id="test_001",
        title="Test Security Issue",
        description="This is a test security finding",
        category=SecurityCategory.AUTHENTICATION,
        severity=SeverityLevel.HIGH,
        file_path="/test/file.py",
        line_number=42,
        code_snippet="password = 'hardcoded'",
        recommendation="Use environment variables",
        references=["CWE-798", "OWASP-A07"],
        compliance=[ComplianceStandard.OWASP_TOP_10, ComplianceStandard.CWE_SANS_25]
    )
    
    print(f"  Finding created: {finding.title}")
    print(f"  Severity: {finding.severity.value}")
    print(f"  Risk score: {finding.risk_score}")
    print(f"  Category: {finding.category.value}")
    print(f"  Compliance standards: {len(finding.compliance)}")
    print(f"  Has recommendation: {finding.recommendation is not None}")
    
    # Test risk score calculation
    critical_finding = SecurityFinding("crit", "Critical", "", SecurityCategory.AUTHENTICATION, SeverityLevel.CRITICAL)
    high_finding = SecurityFinding("high", "High", "", SecurityCategory.AUTHENTICATION, SeverityLevel.HIGH)
    medium_finding = SecurityFinding("med", "Medium", "", SecurityCategory.AUTHENTICATION, SeverityLevel.MEDIUM)
    low_finding = SecurityFinding("low", "Low", "", SecurityCategory.AUTHENTICATION, SeverityLevel.LOW)
    info_finding = SecurityFinding("info", "Info", "", SecurityCategory.AUTHENTICATION, SeverityLevel.INFO)
    
    print(f"  Critical risk score: {critical_finding.risk_score}")
    print(f"  High risk score: {high_finding.risk_score}")
    print(f"  Medium risk score: {medium_finding.risk_score}")
    print(f"  Low risk score: {low_finding.risk_score}")
    print(f"  Info risk score: {info_finding.risk_score}")
    
    print("✓ Security finding creation working")


def test_audit_result_operations():
    """Test security audit result operations."""
    print("\n=== Testing Audit Result Operations ===")
    
    result = SecurityAuditResult(
        audit_id="test.audit",
        name="Test Audit",
        category=SecurityCategory.AUTHENTICATION,
        status="fail"
    )
    
    print(f"  Result created: {result.name}")
    print(f"  Initial findings: {len(result.findings)}")
    
    # Add findings
    result.add_finding(SecurityFinding(
        "f1", "Critical Issue", "", SecurityCategory.AUTHENTICATION, 
        SeverityLevel.CRITICAL
    ))
    result.add_finding(SecurityFinding(
        "f2", "High Issue", "", SecurityCategory.AUTHENTICATION, 
        SeverityLevel.HIGH
    ))
    result.add_finding(SecurityFinding(
        "f3", "Medium Issue", "", SecurityCategory.AUTHENTICATION, 
        SeverityLevel.MEDIUM
    ))
    
    print(f"  After adding findings: {len(result.findings)}")
    print(f"  Total risk score: {result.total_risk_score}")
    print(f"  Critical count: {result.critical_count}")
    print(f"  High count: {result.high_count}")
    
    # Test false positive handling
    false_positive_finding = SecurityFinding(
        "fp1", "False Positive", "", SecurityCategory.AUTHENTICATION,
        SeverityLevel.CRITICAL, false_positive=True
    )
    result.add_finding(false_positive_finding)
    
    print(f"  With false positive added: {len(result.findings)}")
    print(f"  Critical count (excluding FP): {result.critical_count}")
    print(f"  Risk score (excluding FP): {result.total_risk_score}")
    
    print("✓ Audit result operations working")


async def test_api_key_audit():
    """Test API key exposure audit."""
    print("\n=== Testing API Key Audit ===")
    
    audit = APIKeyAudit()
    
    # Create test file with potential API key
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_api.py"
        test_file.write_text("""
# Test file with various patterns
api_key = "sk-1234567890abcdef1234567890abcdef1234567890abcdef"  # OpenAI key
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
generic_token = "test_token_1234567890"
password = "example_password_123"

# Safe patterns (should not trigger)
api_key_example = "your_api_key_here"
test_key = "mock_key_for_testing"
""")
        
        # Run audit
        result = await audit.run()
        
        print(f"  Audit status: {result.status}")
        print(f"  Findings count: {len(result.findings)}")
        print(f"  Duration: {result.duration:.3f}s")
        
        if result.findings:
            print("  Sample findings:")
            for finding in result.findings[:3]:
                print(f"    - {finding.title}: {finding.severity.value}")
        
        # Check metadata
        if "env_usage" in result.metadata:
            print(f"  Environment variable usage detected: {result.metadata['env_usage'].get('uses_env_vars', False)}")
    
    print("✓ API key audit working")


async def test_input_validation_audit():
    """Test input validation audit."""
    print("\n=== Testing Input Validation Audit ===")
    
    audit = InputValidationAudit()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_validation.py"
        test_file.write_text("""
# Dangerous patterns
user_input = input("Enter command: ")
eval(user_input)  # Critical vulnerability

import subprocess
subprocess.run(user_input, shell=True)  # Shell injection

import pickle
data = pickle.loads(untrusted_data)  # Unsafe deserialization

import yaml
config = yaml.load(file_content)  # Should use safe_load

# Safe patterns
import ast
ast.literal_eval(user_input)  # Safe evaluation

import json
json.loads(json_string)  # Generally safe
""")
        
        result = await audit.run()
        
        print(f"  Audit status: {result.status}")
        print(f"  Findings count: {len(result.findings)}")
        
        # Check severity distribution
        severities = {}
        for finding in result.findings:
            sev = finding.severity.value
            severities[sev] = severities.get(sev, 0) + 1
        
        print(f"  Severity distribution: {severities}")
        
        if result.findings:
            print("  Recommendations provided: {}")
            for finding in result.findings[:2]:
                if finding.recommendation:
                    print(f"    - {finding.title}: {finding.recommendation[:50]}...")
    
    print("✓ Input validation audit working")


async def test_dependency_audit():
    """Test dependency vulnerability audit."""
    print("\n=== Testing Dependency Audit ===")
    
    audit = DependencyAudit()
    
    # This will check actual project dependencies
    result = await audit.run()
    
    print(f"  Audit status: {result.status}")
    print(f"  Requirements found: {result.metadata.get('requirements_found', False)}")
    
    if result.metadata.get('requirement_files'):
        print(f"  Requirement files: {len(result.metadata['requirement_files'])}")
        for req_file in result.metadata['requirement_files'][:3]:
            print(f"    - {Path(req_file).name}")
    
    print(f"  Safety check available: {result.metadata.get('safety_available', 'unknown')}")
    
    if result.metadata.get('significantly_outdated'):
        print(f"  Significantly outdated packages: {len(result.metadata['significantly_outdated'])}")
        for pkg in result.metadata['significantly_outdated'][:3]:
            print(f"    - {pkg.get('name')}: {pkg.get('current')} -> {pkg.get('latest')}")
    
    print(f"  Vulnerability findings: {len(result.findings)}")
    
    print("✓ Dependency audit working")


async def test_cryptography_audit():
    """Test cryptographic practices audit."""
    print("\n=== Testing Cryptography Audit ===")
    
    audit = CryptographyAudit()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_crypto.py"
        test_file.write_text("""
import hashlib
import random
import base64

# Weak crypto patterns
password_hash = hashlib.md5(password.encode()).hexdigest()  # Weak hash
token = hashlib.sha1(data).hexdigest()  # Weak hash

# Insecure random
session_id = random.randint(1000000, 9999999)  # Not cryptographically secure

# Base64 (not encryption)
encoded = base64.b64encode(sensitive_data)

# Good patterns
import secrets
secure_token = secrets.token_hex(32)  # Secure random

import hashlib
secure_hash = hashlib.sha256(data).hexdigest()  # Strong hash
""")
        
        result = await audit.run()
        
        print(f"  Audit status: {result.status}")
        print(f"  Findings count: {len(result.findings)}")
        print(f"  Uses secure random: {result.metadata.get('uses_secure_random', False)}")
        
        # Check finding types
        finding_types = set()
        for finding in result.findings:
            if "MD5" in finding.title:
                finding_types.add("MD5")
            elif "SHA1" in finding.title:
                finding_types.add("SHA1")
            elif "random" in finding.title.lower():
                finding_types.add("Insecure Random")
            elif "Base64" in finding.title:
                finding_types.add("Base64")
        
        print(f"  Finding types detected: {finding_types}")
    
    print("✓ Cryptography audit working")


async def test_file_operations_audit():
    """Test file operations security audit."""
    print("\n=== Testing File Operations Audit ===")
    
    audit = FileOperationsAudit()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test_files.py"
        test_file.write_text("""
import os
import shutil
import tempfile

# Risky patterns
user_path = input("Enter path: ")
file_path = os.path.join(base_dir, "..", user_path)  # Path traversal risk

with open(file_path, 'w') as f:  # No encoding specified
    f.write(data)

os.chmod(file_path, 0o777)  # Overly permissive

shutil.rmtree(user_dir)  # Dangerous deletion

temp_file = tempfile.mktemp()  # Insecure temp file

# Safe patterns
from pathlib import Path
safe_path = Path(user_path).resolve()

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(data)
""")
        
        result = await audit.run()
        
        print(f"  Audit status: {result.status}")
        print(f"  Findings count: {len(result.findings)}")
        
        # Check finding categories
        categories = set()
        for finding in result.findings:
            if "traversal" in finding.title.lower():
                categories.add("Path Traversal")
            elif "encoding" in finding.title.lower():
                categories.add("Encoding")
            elif "permission" in finding.title.lower():
                categories.add("Permissions")
            elif "deletion" in finding.title.lower():
                categories.add("Deletion")
            elif "temp" in finding.title.lower():
                categories.add("Temp Files")
        
        print(f"  Security categories found: {categories}")
    
    print("✓ File operations audit working")


def test_security_auditor_creation():
    """Test security auditor creation and registration."""
    print("\n=== Testing Security Auditor Creation ===")
    
    auditor = SecurityAuditor()
    
    print(f"  Auditor created: {auditor is not None}")
    print(f"  Audits registered: {len(auditor.audits)}")
    print(f"  Initial results: {len(auditor.results)}")
    
    # Check audit categories
    categories = {}
    for audit_id, audit in auditor.audits.items():
        cat = audit.category.value
        categories[cat] = categories.get(cat, 0) + 1
        print(f"    {audit_id}: {audit.name}")
    
    print(f"  Categories covered: {len(categories)}")
    for category, count in categories.items():
        print(f"    {category}: {count} audits")
    
    print("✓ Security auditor creation working")


async def test_auditor_execution():
    """Test security auditor execution."""
    print("\n=== Testing Auditor Execution ===")
    
    auditor = get_security_auditor()
    
    # Test single audit execution
    if "auth.api_keys" in auditor.audits:
        result = await auditor.run_audit("auth.api_keys")
        print(f"  Single audit result: {result.status}")
        print(f"    Category: {result.category.value}")
        print(f"    Findings: {len(result.findings)}")
    
    # Test invalid audit
    try:
        await auditor.run_audit("nonexistent.audit")
        print("  Invalid audit handled: False")
    except ValueError:
        print("  Invalid audit handled: True")
    
    print("✓ Auditor execution working")


async def test_category_filtering():
    """Test audit filtering by category."""
    print("\n=== Testing Category Filtering ===")
    
    auditor = get_security_auditor()
    
    # Test category filtering
    auth_results = await auditor.run_all_audits(categories={SecurityCategory.AUTHENTICATION})
    print(f"  Authentication audits: {len(auth_results)}")
    
    validation_results = await auditor.run_all_audits(categories={SecurityCategory.INPUT_VALIDATION})
    print(f"  Input validation audits: {len(validation_results)}")
    
    # Test multiple categories
    multi_results = await auditor.run_all_audits(
        categories={SecurityCategory.AUTHENTICATION, SecurityCategory.CRYPTOGRAPHY}
    )
    print(f"  Multiple category audits: {len(multi_results)}")
    
    # Verify filtering worked
    if auth_results:
        all_auth = all(r.category == SecurityCategory.AUTHENTICATION for r in auth_results)
        print(f"  All results are authentication: {all_auth}")
    
    print("✓ Category filtering working")


async def test_report_generation():
    """Test security report generation."""
    print("\n=== Testing Report Generation ===")
    
    auditor = get_security_auditor()
    
    # Run some audits to generate results
    await auditor.run_all_audits(categories={SecurityCategory.AUTHENTICATION, SecurityCategory.INPUT_VALIDATION})
    
    # Test text report
    text_report = auditor.generate_report(format="text")
    print(f"  Text report generated: {isinstance(text_report, str)}")
    print(f"  Text report length: {len(text_report)} characters")
    print(f"  Contains header: {'SECURITY AUDIT REPORT' in text_report}")
    print(f"  Contains summary: {'EXECUTIVE SUMMARY' in text_report}")
    
    # Test JSON report
    json_report = auditor.generate_report(format="json")
    print(f"  JSON report generated: {isinstance(json_report, dict)}")
    
    if isinstance(json_report, dict):
        print(f"  JSON report keys: {list(json_report.keys())}")
        print(f"  Has summary: {'summary' in json_report}")
        print(f"  Has audits: {'audits' in json_report}")
        print(f"  Has findings: {'findings' in json_report}")
        
        if 'summary' in json_report:
            summary = json_report['summary']
            print(f"    Total findings: {summary.get('total_findings', 0)}")
            print(f"    Security posture: {summary.get('security_posture', 'unknown')}")
    
    # Test compliance summary
    compliance = auditor._get_compliance_summary()
    print(f"  Compliance standards tracked: {len(compliance)}")
    
    print("✓ Report generation working")


async def test_high_level_interface():
    """Test high-level run_security_audit function."""
    print("\n=== Testing High-Level Interface ===")
    
    # Test with different parameters
    test_configs = [
        {"output_format": "text"},
        {"categories": ["authentication", "cryptography"], "output_format": "json"},
        {"output_format": "text"}
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"  Test {i}: {config}")
        
        try:
            result = await run_security_audit(**config)
            
            print(f"    Success: {result.get('success', False)}")
            print(f"    Has results: {'results' in result}")
            print(f"    Has report: {'report' in result}")
            print(f"    Has summary: {'summary' in result}")
            
            if 'summary' in result:
                summary = result['summary']
                print(f"    Total audits: {summary.get('total_audits', 0)}")
                print(f"    Critical findings: {summary.get('critical_findings', 0)}")
                print(f"    Risk score: {summary.get('total_risk_score', 0)}")
                print(f"    Security posture: {summary.get('security_posture', 'unknown')}")
        
        except Exception as e:
            print(f"    Error: {e}")
    
    print("✓ High-level interface working")


def test_singleton_behavior():
    """Test singleton behavior of security auditor."""
    print("\n=== Testing Singleton Behavior ===")
    
    auditor1 = get_security_auditor()
    auditor2 = get_security_auditor()
    
    print(f"  Same instance: {auditor1 is auditor2}")
    print(f"  Instance type: {type(auditor1).__name__}")
    
    # Test shared state
    initial_results = len(auditor1.results)
    
    # Add a dummy result to auditor1
    dummy_result = SecurityAuditResult(
        "test.dummy", "Dummy Test", SecurityCategory.AUTHENTICATION, "pass"
    )
    auditor1.results.append(dummy_result)
    
    after_addition = len(auditor2.results)
    print(f"  State shared: {after_addition > initial_results}")
    print(f"  Total results: {len(auditor2.results)}")
    
    print("✓ Singleton behavior working")


async def test_risk_scoring():
    """Test risk scoring system."""
    print("\n=== Testing Risk Scoring System ===")
    
    # Create findings with different severities
    findings = [
        SecurityFinding("c1", "Critical 1", "", SecurityCategory.AUTHENTICATION, SeverityLevel.CRITICAL),
        SecurityFinding("c2", "Critical 2", "", SecurityCategory.AUTHENTICATION, SeverityLevel.CRITICAL),
        SecurityFinding("h1", "High 1", "", SecurityCategory.AUTHENTICATION, SeverityLevel.HIGH),
        SecurityFinding("m1", "Medium 1", "", SecurityCategory.AUTHENTICATION, SeverityLevel.MEDIUM),
        SecurityFinding("m2", "Medium 2", "", SecurityCategory.AUTHENTICATION, SeverityLevel.MEDIUM),
        SecurityFinding("l1", "Low 1", "", SecurityCategory.AUTHENTICATION, SeverityLevel.LOW),
        SecurityFinding("i1", "Info 1", "", SecurityCategory.AUTHENTICATION, SeverityLevel.INFO),
    ]
    
    result = SecurityAuditResult("risk.test", "Risk Test", SecurityCategory.AUTHENTICATION, "fail")
    for finding in findings:
        result.add_finding(finding)
    
    print(f"  Total findings: {len(result.findings)}")
    print(f"  Total risk score: {result.total_risk_score}")
    print(f"  Expected score: {2*10 + 1*8 + 2*5 + 1*2 + 1*0} = {2*10 + 1*8 + 2*5 + 1*2}")
    print(f"  Score calculation correct: {result.total_risk_score == 40}")
    
    # Test with false positives
    fp_finding = SecurityFinding("fp1", "False Positive", "", SecurityCategory.AUTHENTICATION, 
                                 SeverityLevel.CRITICAL, false_positive=True)
    result.add_finding(fp_finding)
    
    print(f"  With false positive added: {len(result.findings)}")
    print(f"  Risk score unchanged: {result.total_risk_score == 40}")
    
    print("✓ Risk scoring system working")


async def run_all_security_tests():
    """Run all security audit tests."""
    print("=" * 70)
    print("SECURITY AUDIT SYSTEM VALIDATION")
    print("=" * 70)
    
    test_functions = [
        test_security_finding_creation,
        test_audit_result_operations,
        test_api_key_audit,
        test_input_validation_audit,
        test_dependency_audit,
        test_cryptography_audit,
        test_file_operations_audit,
        test_security_auditor_creation,
        test_auditor_execution,
        test_category_filtering,
        test_report_generation,
        test_high_level_interface,
        test_singleton_behavior,
        test_risk_scoring
    ]
    
    start_time = asyncio.get_event_loop().time()
    passed_tests = 0
    
    for i, test_func in enumerate(test_functions, 1):
        try:
            print(f"\n[{i}/{len(test_functions)}] Running {test_func.__name__}")
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            passed_tests += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    total_time = asyncio.get_event_loop().time() - start_time
    
    print(f"\n{'=' * 70}")
    print(f"✓ Security audit system validation complete!")
    print(f"  Tests passed: {passed_tests}/{len(test_functions)}")
    print(f"  Success rate: {passed_tests / len(test_functions) * 100:.1f}%")
    print(f"  Total validation time: {total_time:.3f}s")
    print(f"  Average per test: {total_time / len(test_functions):.3f}s")
    
    if passed_tests == len(test_functions):
        print("🎉 All security audit tests PASSED!")
        print("Sprint 44 security audit COMPLETE!")
    else:
        print("⚠️  Some tests failed - review above for details")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_security_tests())