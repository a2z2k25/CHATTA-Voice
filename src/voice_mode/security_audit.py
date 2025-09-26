#!/usr/bin/env python3
"""Security audit system for VoiceMode."""

import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import logging
import ast
import importlib.util

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityCategory(Enum):
    """Categories of security checks."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INPUT_VALIDATION = "input_validation"
    OUTPUT_ENCODING = "output_encoding"
    CRYPTOGRAPHY = "cryptography"
    SESSION_MANAGEMENT = "session_management"
    ERROR_HANDLING = "error_handling"
    LOGGING = "logging"
    DEPENDENCIES = "dependencies"
    CONFIGURATION = "configuration"
    FILE_OPERATIONS = "file_operations"
    NETWORK = "network"
    CODE_INJECTION = "code_injection"
    API_SECURITY = "api_security"


class SeverityLevel(Enum):
    """Security vulnerability severity levels."""
    CRITICAL = "critical"  # Immediate exploitation possible
    HIGH = "high"         # Significant risk
    MEDIUM = "medium"     # Moderate risk
    LOW = "low"          # Minor risk
    INFO = "info"        # Informational finding


class ComplianceStandard(Enum):
    """Security compliance standards."""
    OWASP_TOP_10 = "owasp_top_10"
    CWE_SANS_25 = "cwe_sans_25"
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO_27001 = "iso_27001"


@dataclass
class SecurityFinding:
    """Individual security finding."""
    finding_id: str
    title: str
    description: str
    category: SecurityCategory
    severity: SeverityLevel
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None
    references: List[str] = field(default_factory=list)
    compliance: List[ComplianceStandard] = field(default_factory=list)
    false_positive: bool = False
    remediation_effort: str = "medium"  # low, medium, high
    
    @property
    def risk_score(self) -> int:
        """Calculate risk score based on severity."""
        scores = {
            SeverityLevel.CRITICAL: 10,
            SeverityLevel.HIGH: 8,
            SeverityLevel.MEDIUM: 5,
            SeverityLevel.LOW: 2,
            SeverityLevel.INFO: 0
        }
        return scores.get(self.severity, 0)


@dataclass
class SecurityAuditResult:
    """Result of a security audit."""
    audit_id: str
    name: str
    category: SecurityCategory
    status: str  # pass, fail, error, skipped
    findings: List[SecurityFinding] = field(default_factory=list)
    duration: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_finding(self, finding: SecurityFinding) -> None:
        """Add a security finding."""
        self.findings.append(finding)
    
    @property
    def total_risk_score(self) -> int:
        """Calculate total risk score."""
        return sum(f.risk_score for f in self.findings if not f.false_positive)
    
    @property
    def critical_count(self) -> int:
        """Count critical findings."""
        return sum(1 for f in self.findings 
                  if f.severity == SeverityLevel.CRITICAL and not f.false_positive)
    
    @property
    def high_count(self) -> int:
        """Count high severity findings."""
        return sum(1 for f in self.findings 
                  if f.severity == SeverityLevel.HIGH and not f.false_positive)


class SecurityAudit(ABC):
    """Abstract base class for security audits."""
    
    def __init__(self, audit_id: str, name: str, category: SecurityCategory):
        self.audit_id = audit_id
        self.name = name
        self.category = category
    
    @abstractmethod
    async def run(self) -> SecurityAuditResult:
        """Run the security audit and return results."""
        pass
    
    def create_result(self, status: str = "pass") -> SecurityAuditResult:
        """Create an audit result."""
        return SecurityAuditResult(
            audit_id=self.audit_id,
            name=self.name,
            category=self.category,
            status=status
        )


class APIKeyAudit(SecurityAudit):
    """Audit for exposed API keys and credentials."""
    
    def __init__(self):
        super().__init__(
            "auth.api_keys",
            "API Key Exposure Check",
            SecurityCategory.AUTHENTICATION
        )
        
        # Common API key patterns
        self.key_patterns = [
            (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Generic API Key"),
            (r'sk-[a-zA-Z0-9]{48}', "OpenAI Secret Key"),
            (r'pk_[a-zA-Z0-9]{32,}', "Stripe Public Key"),
            (r'sk_[a-zA-Z0-9]{32,}', "Stripe Secret Key"),
            (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
            (r'[a-zA-Z0-9/+=]{40}', "AWS Secret Key (potential)"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
            (r'ghs_[a-zA-Z0-9]{36}', "GitHub Secret"),
            (r'["\']?token["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-\.]{20,}["\']', "Generic Token"),
            (r'["\']?secret["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-\.]{20,}["\']', "Generic Secret"),
            (r'["\']?password["\']?\s*[:=]\s*["\'][^"\']{8,}["\']', "Hardcoded Password"),
        ]
    
    async def run(self) -> SecurityAuditResult:
        """Scan for exposed API keys."""
        import time
        start_time = time.perf_counter()
        result = self.create_result("pass")
        
        try:
            # Scan Python files
            project_root = Path.cwd()
            python_files = list(project_root.rglob("*.py"))
            
            for file_path in python_files:
                # Skip test files and this file
                if "test" in file_path.name or file_path.name == "security_audit.py":
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.splitlines()
                    
                    for pattern, key_type in self.key_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            # Find line number
                            line_start = content[:match.start()].count('\n') + 1
                            
                            # Check if it's likely a false positive
                            matched_text = match.group(0)
                            if self._is_likely_false_positive(matched_text, file_path):
                                continue
                            
                            finding = SecurityFinding(
                                finding_id=f"api_key_{file_path.stem}_{line_start}",
                                title=f"Potential {key_type} Exposure",
                                description=f"Found potential {key_type} in source code",
                                category=self.category,
                                severity=SeverityLevel.CRITICAL if "secret" in key_type.lower() else SeverityLevel.HIGH,
                                file_path=str(file_path),
                                line_number=line_start,
                                code_snippet=matched_text[:50] + "..." if len(matched_text) > 50 else matched_text,
                                recommendation="Move credentials to environment variables or secure key management system",
                                references=["https://owasp.org/www-project-top-ten/", "CWE-798"],
                                compliance=[ComplianceStandard.OWASP_TOP_10, ComplianceStandard.CWE_SANS_25]
                            )
                            result.add_finding(finding)
                            result.status = "fail"
                
                except Exception as e:
                    logger.warning(f"Error scanning {file_path}: {e}")
            
            # Check environment usage
            env_usage = await self._check_env_usage()
            if env_usage:
                result.metadata["env_usage"] = env_usage
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        
        end_time = time.perf_counter()
        result.duration = end_time - start_time
        return result
    
    def _is_likely_false_positive(self, text: str, file_path: Path) -> bool:
        """Check if match is likely a false positive."""
        # Common false positive indicators
        false_positive_indicators = [
            "example", "test", "mock", "fake", "sample", "placeholder",
            "xxx", "your_", "my_", "<", ">", "{", "}"
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in false_positive_indicators)
    
    async def _check_env_usage(self) -> Dict[str, Any]:
        """Check for proper environment variable usage."""
        env_vars_found = []
        config_files = list(Path.cwd().rglob("config*.py"))
        
        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if "os.environ" in content or "os.getenv" in content:
                        env_vars_found.append(str(config_file))
            except:
                pass
        
        return {
            "uses_env_vars": len(env_vars_found) > 0,
            "config_files": env_vars_found
        }


class InputValidationAudit(SecurityAudit):
    """Audit for input validation vulnerabilities."""
    
    def __init__(self):
        super().__init__(
            "validation.input",
            "Input Validation Security Check",
            SecurityCategory.INPUT_VALIDATION
        )
    
    async def run(self) -> SecurityAuditResult:
        """Check for input validation issues."""
        import time
        start_time = time.perf_counter()
        result = self.create_result("pass")
        
        try:
            # Patterns that indicate potential input validation issues
            vulnerable_patterns = [
                (r'eval\s*\([^)]*\)', "Dangerous eval() usage", SeverityLevel.CRITICAL),
                (r'exec\s*\([^)]*\)', "Dangerous exec() usage", SeverityLevel.CRITICAL),
                (r'subprocess\.(call|run|Popen)\s*\([^,)]*shell\s*=\s*True', "Shell injection risk", SeverityLevel.HIGH),
                (r'os\.system\s*\([^)]*\)', "Command injection risk", SeverityLevel.HIGH),
                (r'pickle\.loads?\s*\([^)]*\)', "Unsafe deserialization", SeverityLevel.HIGH),
                (r'yaml\.load\s*\([^,)]*\)', "Unsafe YAML loading", SeverityLevel.MEDIUM),
                (r'json\.loads?\s*\([^)]*\)', "JSON parsing without validation", SeverityLevel.LOW),
                (r'open\s*\([^,)]*["\']w["\']', "File write without path validation", SeverityLevel.MEDIUM),
            ]
            
            project_root = Path.cwd()
            python_files = list(project_root.rglob("*.py"))
            
            for file_path in python_files:
                if "test" in file_path.name:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for pattern, description, severity in vulnerable_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            
                            finding = SecurityFinding(
                                finding_id=f"input_val_{file_path.stem}_{line_num}",
                                title=description,
                                description=f"Potential input validation vulnerability: {description}",
                                category=self.category,
                                severity=severity,
                                file_path=str(file_path),
                                line_number=line_num,
                                code_snippet=match.group(0),
                                recommendation=self._get_recommendation(description),
                                references=["CWE-20", "CWE-78", "CWE-502"],
                                compliance=[ComplianceStandard.OWASP_TOP_10, ComplianceStandard.CWE_SANS_25]
                            )
                            result.add_finding(finding)
                            result.status = "fail"
                
                except Exception as e:
                    logger.warning(f"Error scanning {file_path}: {e}")
        
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        
        end_time = time.perf_counter()
        result.duration = end_time - start_time
        return result
    
    def _get_recommendation(self, issue: str) -> str:
        """Get recommendation for specific issue."""
        recommendations = {
            "eval": "Avoid eval(). Use ast.literal_eval() for safe evaluation of literals",
            "exec": "Avoid exec(). Consider safer alternatives or sandboxing",
            "Shell injection": "Use shell=False and pass arguments as a list",
            "Command injection": "Use subprocess with shell=False instead of os.system",
            "Unsafe deserialization": "Use JSON or other safe formats. If pickle is required, validate source",
            "YAML": "Use yaml.safe_load() instead of yaml.load()",
            "File write": "Validate and sanitize file paths before writing"
        }
        
        for key, rec in recommendations.items():
            if key.lower() in issue.lower():
                return rec
        return "Implement proper input validation and sanitization"


class DependencyAudit(SecurityAudit):
    """Audit for dependency vulnerabilities."""
    
    def __init__(self):
        super().__init__(
            "deps.vulnerabilities",
            "Dependency Vulnerability Check",
            SecurityCategory.DEPENDENCIES
        )
    
    async def run(self) -> SecurityAuditResult:
        """Check for known vulnerabilities in dependencies."""
        import time
        start_time = time.perf_counter()
        result = self.create_result("pass")
        
        try:
            # Check for requirements files
            req_files = []
            for pattern in ["requirements*.txt", "pyproject.toml", "setup.py", "Pipfile", "poetry.lock"]:
                req_files.extend(Path.cwd().glob(pattern))
            
            if not req_files:
                result.metadata["requirements_found"] = False
                return result
            
            result.metadata["requirements_found"] = True
            result.metadata["requirement_files"] = [str(f) for f in req_files]
            
            # Try to run safety check if available
            try:
                safety_result = subprocess.run(
                    ["safety", "check", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if safety_result.returncode != 0 and safety_result.stdout:
                    vulnerabilities = json.loads(safety_result.stdout)
                    for vuln in vulnerabilities:
                        finding = SecurityFinding(
                            finding_id=f"dep_vuln_{vuln.get('package', 'unknown')}_{vuln.get('id', '')}",
                            title=f"Vulnerable dependency: {vuln.get('package', 'unknown')}",
                            description=vuln.get('description', 'Known vulnerability in dependency'),
                            category=self.category,
                            severity=self._map_cvss_to_severity(vuln.get('cvssv3_base_score', 0)),
                            recommendation=f"Update {vuln.get('package')} to {vuln.get('safe_version', 'latest safe version')}",
                            references=[vuln.get('cve', ''), vuln.get('advisory', '')],
                            compliance=[ComplianceStandard.OWASP_TOP_10]
                        )
                        result.add_finding(finding)
                        result.status = "fail"
                        
            except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
                # Safety not available or failed
                result.metadata["safety_available"] = False
            
            # Check for outdated packages
            await self._check_outdated_packages(result)
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        
        end_time = time.perf_counter()
        result.duration = end_time - start_time
        return result
    
    def _map_cvss_to_severity(self, cvss_score: float) -> SeverityLevel:
        """Map CVSS score to severity level."""
        if cvss_score >= 9.0:
            return SeverityLevel.CRITICAL
        elif cvss_score >= 7.0:
            return SeverityLevel.HIGH
        elif cvss_score >= 4.0:
            return SeverityLevel.MEDIUM
        elif cvss_score > 0:
            return SeverityLevel.LOW
        return SeverityLevel.INFO
    
    async def _check_outdated_packages(self, result: SecurityAuditResult) -> None:
        """Check for significantly outdated packages."""
        try:
            pip_list = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if pip_list.returncode == 0 and pip_list.stdout:
                outdated = json.loads(pip_list.stdout)
                significantly_outdated = []
                
                for pkg in outdated:
                    current = pkg.get('version', '0.0.0')
                    latest = pkg.get('latest_version', '0.0.0')
                    
                    # Check if major version is behind
                    if self._is_major_version_behind(current, latest):
                        significantly_outdated.append({
                            'name': pkg.get('name'),
                            'current': current,
                            'latest': latest
                        })
                
                result.metadata["significantly_outdated"] = significantly_outdated
                
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass
    
    def _is_major_version_behind(self, current: str, latest: str) -> bool:
        """Check if current version is major version behind latest."""
        try:
            current_major = int(current.split('.')[0])
            latest_major = int(latest.split('.')[0])
            return latest_major > current_major
        except:
            return False


class CryptographyAudit(SecurityAudit):
    """Audit for cryptographic issues."""
    
    def __init__(self):
        super().__init__(
            "crypto.practices",
            "Cryptographic Practices Check",
            SecurityCategory.CRYPTOGRAPHY
        )
    
    async def run(self) -> SecurityAuditResult:
        """Check for cryptographic vulnerabilities."""
        import time
        start_time = time.perf_counter()
        result = self.create_result("pass")
        
        try:
            weak_crypto_patterns = [
                (r'hashlib\.md5\s*\(', "Weak hash algorithm (MD5)", SeverityLevel.HIGH),
                (r'hashlib\.sha1\s*\(', "Weak hash algorithm (SHA1)", SeverityLevel.MEDIUM),
                (r'random\.random\s*\(', "Insecure random for cryptography", SeverityLevel.HIGH),
                (r'random\.randint\s*\(', "Insecure random for cryptography", SeverityLevel.HIGH),
                (r'DES\.new\s*\(', "Weak encryption algorithm (DES)", SeverityLevel.CRITICAL),
                (r'AES\.new\s*\([^)]*ECB', "Insecure cipher mode (ECB)", SeverityLevel.HIGH),
                (r'base64\.b64encode\s*\(', "Base64 is encoding, not encryption", SeverityLevel.INFO),
            ]
            
            project_root = Path.cwd()
            python_files = list(project_root.rglob("*.py"))
            
            for file_path in python_files:
                if "test" in file_path.name:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for pattern, description, severity in weak_crypto_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            
                            finding = SecurityFinding(
                                finding_id=f"crypto_{file_path.stem}_{line_num}",
                                title=description,
                                description=f"Potential cryptographic weakness: {description}",
                                category=self.category,
                                severity=severity,
                                file_path=str(file_path),
                                line_number=line_num,
                                code_snippet=match.group(0),
                                recommendation=self._get_crypto_recommendation(description),
                                references=["CWE-327", "CWE-326", "CWE-330"],
                                compliance=[ComplianceStandard.OWASP_TOP_10]
                            )
                            result.add_finding(finding)
                            if severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                                result.status = "fail"
                
                except Exception as e:
                    logger.warning(f"Error scanning {file_path}: {e}")
            
            # Check for proper use of secrets module
            await self._check_secure_random_usage(result)
            
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        
        end_time = time.perf_counter()
        result.duration = end_time - start_time
        return result
    
    def _get_crypto_recommendation(self, issue: str) -> str:
        """Get cryptography recommendation."""
        recommendations = {
            "MD5": "Use SHA-256 or SHA-3 for hashing",
            "SHA1": "Use SHA-256 or SHA-3 for hashing",
            "Insecure random": "Use secrets module for cryptographic randomness",
            "DES": "Use AES-256 for encryption",
            "ECB": "Use CBC, GCM, or other secure cipher modes",
            "Base64": "Base64 is not encryption. Use proper encryption if security is needed"
        }
        
        for key, rec in recommendations.items():
            if key.lower() in issue.lower():
                return rec
        return "Follow cryptographic best practices"
    
    async def _check_secure_random_usage(self, result: SecurityAuditResult) -> None:
        """Check if secrets module is properly used."""
        uses_secrets = False
        project_root = Path.cwd()
        
        for file_path in project_root.rglob("*.py"):
            try:
                with open(file_path, 'r') as f:
                    if "import secrets" in f.read():
                        uses_secrets = True
                        break
            except:
                pass
        
        result.metadata["uses_secure_random"] = uses_secrets


class FileOperationsAudit(SecurityAudit):
    """Audit for file operation security."""
    
    def __init__(self):
        super().__init__(
            "file.operations",
            "File Operations Security Check",
            SecurityCategory.FILE_OPERATIONS
        )
    
    async def run(self) -> SecurityAuditResult:
        """Check for file operation vulnerabilities."""
        import time
        start_time = time.perf_counter()
        result = self.create_result("pass")
        
        try:
            file_patterns = [
                (r'open\s*\([^)]*\)(?!.*encoding)', "File open without encoding specification", SeverityLevel.LOW),
                (r'os\.path\.join\s*\([^)]*\.\.[^)]*\)', "Path traversal risk", SeverityLevel.HIGH),
                (r'shutil\.rmtree\s*\([^)]*\)', "Dangerous directory deletion", SeverityLevel.MEDIUM),
                (r'os\.chmod\s*\([^,)]*,\s*0o?777', "Overly permissive file permissions", SeverityLevel.HIGH),
                (r'tempfile\.mktemp\s*\(', "Insecure temporary file creation", SeverityLevel.MEDIUM),
            ]
            
            project_root = Path.cwd()
            python_files = list(project_root.rglob("*.py"))
            
            for file_path in python_files:
                if "test" in file_path.name:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for pattern, description, severity in file_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            
                            # Check for false positives
                            if self._is_safe_file_operation(match.group(0), content, match.start()):
                                continue
                            
                            finding = SecurityFinding(
                                finding_id=f"file_op_{file_path.stem}_{line_num}",
                                title=description,
                                description=f"Potential file operation vulnerability: {description}",
                                category=self.category,
                                severity=severity,
                                file_path=str(file_path),
                                line_number=line_num,
                                code_snippet=match.group(0),
                                recommendation=self._get_file_recommendation(description),
                                references=["CWE-22", "CWE-732", "CWE-377"],
                                compliance=[ComplianceStandard.OWASP_TOP_10]
                            )
                            result.add_finding(finding)
                            if severity == SeverityLevel.HIGH:
                                result.status = "fail"
                
                except Exception as e:
                    logger.warning(f"Error scanning {file_path}: {e}")
        
        except Exception as e:
            result.status = "error"
            result.error = str(e)
        
        end_time = time.perf_counter()
        result.duration = end_time - start_time
        return result
    
    def _is_safe_file_operation(self, matched_text: str, content: str, position: int) -> bool:
        """Check if file operation is likely safe."""
        # Check if it's in a safe context (e.g., within try block, with validation)
        lines_before = content[:position].split('\n')[-5:]  # Check 5 lines before
        
        safe_indicators = ['try:', 'if os.path.exists', 'Path(', '.resolve()', 'safe_join']
        return any(indicator in line for line in lines_before for indicator in safe_indicators)
    
    def _get_file_recommendation(self, issue: str) -> str:
        """Get file operation recommendation."""
        recommendations = {
            "encoding": "Always specify encoding when opening text files (encoding='utf-8')",
            "traversal": "Validate and sanitize file paths. Use pathlib.Path.resolve()",
            "rmtree": "Validate directory path before deletion. Consider safer alternatives",
            "permissions": "Use restrictive file permissions (e.g., 0o600 or 0o644)",
            "mktemp": "Use tempfile.mkstemp() or NamedTemporaryFile() instead"
        }
        
        for key, rec in recommendations.items():
            if key.lower() in issue.lower():
                return rec
        return "Follow secure file handling practices"


class SecurityAuditor:
    """Main security auditor that runs all audits."""
    
    def __init__(self):
        self.audits: Dict[str, SecurityAudit] = {}
        self.results: List[SecurityAuditResult] = []
        self._register_audits()
    
    def _register_audits(self) -> None:
        """Register all security audits."""
        audits = [
            APIKeyAudit(),
            InputValidationAudit(),
            DependencyAudit(),
            CryptographyAudit(),
            FileOperationsAudit()
        ]
        
        for audit in audits:
            self.audits[audit.audit_id] = audit
    
    async def run_audit(self, audit_id: str) -> SecurityAuditResult:
        """Run a specific security audit."""
        if audit_id not in self.audits:
            raise ValueError(f"Audit '{audit_id}' not found")
        
        audit = self.audits[audit_id]
        logger.info(f"Running security audit: {audit.name}")
        
        try:
            result = await audit.run()
            self.results.append(result)
            return result
        except Exception as e:
            logger.error(f"Audit {audit_id} failed: {e}")
            error_result = audit.create_result("error")
            error_result.error = str(e)
            self.results.append(error_result)
            return error_result
    
    async def run_all_audits(
        self,
        categories: Optional[Set[SecurityCategory]] = None,
        severities: Optional[Set[SeverityLevel]] = None
    ) -> List[SecurityAuditResult]:
        """Run all security audits with optional filtering."""
        
        audits_to_run = []
        for audit_id, audit in self.audits.items():
            if categories and audit.category not in categories:
                continue
            audits_to_run.append(audit_id)
        
        logger.info(f"Running {len(audits_to_run)} security audits")
        
        results = []
        for audit_id in audits_to_run:
            result = await self.run_audit(audit_id)
            results.append(result)
        
        return results
    
    def generate_report(self, format: str = "text") -> Union[str, Dict[str, Any]]:
        """Generate security audit report."""
        if format == "json":
            return self._generate_json_report()
        else:
            return self._generate_text_report()
    
    def _generate_json_report(self) -> Dict[str, Any]:
        """Generate JSON format security report."""
        all_findings = []
        for result in self.results:
            for finding in result.findings:
                all_findings.append({
                    "id": finding.finding_id,
                    "title": finding.title,
                    "description": finding.description,
                    "category": finding.category.value,
                    "severity": finding.severity.value,
                    "file": finding.file_path,
                    "line": finding.line_number,
                    "recommendation": finding.recommendation,
                    "risk_score": finding.risk_score,
                    "false_positive": finding.false_positive
                })
        
        summary = self._calculate_summary()
        
        return {
            "summary": summary,
            "audits": [
                {
                    "id": r.audit_id,
                    "name": r.name,
                    "category": r.category.value,
                    "status": r.status,
                    "findings_count": len(r.findings),
                    "risk_score": r.total_risk_score,
                    "critical_count": r.critical_count,
                    "high_count": r.high_count
                }
                for r in self.results
            ],
            "findings": all_findings,
            "metadata": {
                "timestamp": time.time(),
                "platform": sys.platform,
                "python_version": sys.version
            }
        }
    
    def _generate_text_report(self) -> str:
        """Generate text format security report."""
        import time
        
        lines = [
            "=" * 70,
            "SECURITY AUDIT REPORT",
            "=" * 70,
            "",
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Platform: {sys.platform}",
            f"Python: {sys.version.split()[0]}",
            "",
            "EXECUTIVE SUMMARY:",
            "-" * 50
        ]
        
        summary = self._calculate_summary()
        lines.extend([
            f"  Total Audits: {summary['total_audits']}",
            f"  Passed: {summary['passed']}",
            f"  Failed: {summary['failed']}",
            f"  Total Findings: {summary['total_findings']}",
            f"  Critical: {summary['critical_findings']}",
            f"  High: {summary['high_findings']}",
            f"  Medium: {summary['medium_findings']}",
            f"  Low: {summary['low_findings']}",
            f"  Risk Score: {summary['total_risk_score']}",
            f"  Security Posture: {summary['security_posture']}",
            ""
        ])
        
        # Critical findings first
        if summary['critical_findings'] > 0:
            lines.append("CRITICAL FINDINGS:")
            lines.append("-" * 50)
            for result in self.results:
                for finding in result.findings:
                    if finding.severity == SeverityLevel.CRITICAL and not finding.false_positive:
                        lines.append(f"❌ {finding.title}")
                        lines.append(f"   File: {finding.file_path}")
                        lines.append(f"   Line: {finding.line_number}")
                        lines.append(f"   Risk Score: {finding.risk_score}")
                        lines.append(f"   Recommendation: {finding.recommendation}")
                        lines.append("")
        
        # Audit details
        lines.append("AUDIT DETAILS:")
        lines.append("-" * 50)
        
        for result in self.results:
            status_icon = "✅" if result.status == "pass" else "❌"
            lines.append(f"{status_icon} {result.name}")
            lines.append(f"   Category: {result.category.value}")
            lines.append(f"   Status: {result.status}")
            lines.append(f"   Findings: {len(result.findings)}")
            
            if result.findings:
                lines.append(f"   Risk Score: {result.total_risk_score}")
                lines.append(f"   Critical: {result.critical_count}, High: {result.high_count}")
            
            if result.error:
                lines.append(f"   Error: {result.error}")
            
            lines.append("")
        
        # Compliance summary
        compliance_mapping = self._get_compliance_summary()
        if compliance_mapping:
            lines.append("COMPLIANCE MAPPING:")
            lines.append("-" * 50)
            for standard, count in compliance_mapping.items():
                lines.append(f"  {standard}: {count} findings")
            lines.append("")
        
        return "\n".join(lines)
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate security audit summary."""
        total_audits = len(self.results)
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail")
        
        all_findings = []
        for result in self.results:
            all_findings.extend([f for f in result.findings if not f.false_positive])
        
        critical = sum(1 for f in all_findings if f.severity == SeverityLevel.CRITICAL)
        high = sum(1 for f in all_findings if f.severity == SeverityLevel.HIGH)
        medium = sum(1 for f in all_findings if f.severity == SeverityLevel.MEDIUM)
        low = sum(1 for f in all_findings if f.severity == SeverityLevel.LOW)
        
        total_risk = sum(f.risk_score for f in all_findings)
        
        # Determine security posture
        if critical > 0:
            posture = "CRITICAL - Immediate action required"
        elif high > 2:
            posture = "HIGH RISK - Significant vulnerabilities"
        elif high > 0 or medium > 5:
            posture = "MEDIUM RISK - Improvements needed"
        elif medium > 0 or low > 10:
            posture = "LOW RISK - Minor issues"
        else:
            posture = "SECURE - No significant issues"
        
        return {
            "total_audits": total_audits,
            "passed": passed,
            "failed": failed,
            "total_findings": len(all_findings),
            "critical_findings": critical,
            "high_findings": high,
            "medium_findings": medium,
            "low_findings": low,
            "total_risk_score": total_risk,
            "security_posture": posture
        }
    
    def _get_compliance_summary(self) -> Dict[str, int]:
        """Get compliance standard summary."""
        compliance_counts = {}
        
        for result in self.results:
            for finding in result.findings:
                if not finding.false_positive:
                    for standard in finding.compliance:
                        key = standard.value
                        compliance_counts[key] = compliance_counts.get(key, 0) + 1
        
        return compliance_counts


# Global auditor instance
_security_auditor = None


def get_security_auditor() -> SecurityAuditor:
    """Get the global security auditor."""
    global _security_auditor
    if _security_auditor is None:
        _security_auditor = SecurityAuditor()
    return _security_auditor


async def run_security_audit(
    categories: Optional[List[str]] = None,
    output_format: str = "text"
) -> Dict[str, Any]:
    """Run comprehensive security audit."""
    
    auditor = get_security_auditor()
    
    # Convert string categories to enums
    category_enums = None
    if categories:
        category_enums = {SecurityCategory(cat) for cat in categories 
                         if cat in [c.value for c in SecurityCategory]}
    
    # Run audits
    results = await auditor.run_all_audits(categories=category_enums)
    
    # Generate report
    report = auditor.generate_report(format=output_format)
    
    # Calculate success status
    summary = auditor._calculate_summary()
    success = (summary["critical_findings"] == 0 and 
              summary["security_posture"] != "CRITICAL")
    
    return {
        "success": success,
        "results": results,
        "report": report,
        "summary": summary
    }


if __name__ == "__main__":
    async def main():
        result = await run_security_audit()
        print(result["report"])
    
    asyncio.run(main())