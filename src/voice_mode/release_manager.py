#!/usr/bin/env python3
"""Release management system for VoiceMode."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import logging
import semver
import toml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReleaseType(str, Enum):
    """Types of releases."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    BUILD = "build"
    HOTFIX = "hotfix"
    ALPHA = "alpha"
    BETA = "beta"
    RELEASE_CANDIDATE = "rc"
    STABLE = "stable"


class PackageFormat(str, Enum):
    """Package format types."""
    WHEEL = "wheel"
    SDIST = "sdist"
    TAR_GZ = "tar.gz"
    ZIP = "zip"
    DEB = "deb"
    RPM = "rpm"
    DMG = "dmg"
    MSI = "msi"
    DOCKER = "docker"
    SNAP = "snap"


class DeploymentTarget(str, Enum):
    """Deployment target environments."""
    PYPI = "pypi"
    PYPI_TEST = "pypi-test"
    GITHUB = "github"
    DOCKER_HUB = "docker-hub"
    NPM = "npm"
    HOMEBREW = "homebrew"
    APT = "apt"
    YUM = "yum"
    LOCAL = "local"
    S3 = "s3"


@dataclass
class ReleaseArtifact:
    """Individual release artifact."""
    name: str
    version: str
    format: PackageFormat
    path: Path
    size: int
    checksum: str
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_checksum(self) -> str:
        """Calculate SHA256 checksum of artifact."""
        sha256 = hashlib.sha256()
        with open(self.path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def verify_checksum(self) -> bool:
        """Verify artifact checksum."""
        return self.calculate_checksum() == self.checksum


@dataclass
class ReleaseNotes:
    """Release notes information."""
    version: str
    date: str
    summary: str
    features: List[str] = field(default_factory=list)
    fixes: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    deprecations: List[str] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)
    contributors: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Convert release notes to markdown."""
        md_lines = [
            f"# Release Notes - v{self.version}",
            f"*Released: {self.date}*",
            "",
            f"## Summary",
            self.summary,
            ""
        ]
        
        if self.features:
            md_lines.extend([
                "## New Features",
                ""
            ])
            for feature in self.features:
                md_lines.append(f"- {feature}")
            md_lines.append("")
        
        if self.fixes:
            md_lines.extend([
                "## Bug Fixes",
                ""
            ])
            for fix in self.fixes:
                md_lines.append(f"- {fix}")
            md_lines.append("")
        
        if self.breaking_changes:
            md_lines.extend([
                "## ⚠️ Breaking Changes",
                ""
            ])
            for change in self.breaking_changes:
                md_lines.append(f"- {change}")
            md_lines.append("")
        
        if self.deprecations:
            md_lines.extend([
                "## Deprecations",
                ""
            ])
            for deprecation in self.deprecations:
                md_lines.append(f"- {deprecation}")
            md_lines.append("")
        
        if self.known_issues:
            md_lines.extend([
                "## Known Issues",
                ""
            ])
            for issue in self.known_issues:
                md_lines.append(f"- {issue}")
            md_lines.append("")
        
        if self.contributors:
            md_lines.extend([
                "## Contributors",
                ""
            ])
            for contributor in self.contributors:
                md_lines.append(f"- {contributor}")
            md_lines.append("")
        
        return "\n".join(md_lines)


@dataclass
class ReleaseManifest:
    """Complete release manifest."""
    version: str
    release_type: ReleaseType
    artifacts: List[ReleaseArtifact] = field(default_factory=list)
    notes: Optional[ReleaseNotes] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    checksums: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_json(self) -> str:
        """Convert manifest to JSON."""
        data = {
            "version": self.version,
            "release_type": self.release_type.value,
            "created_at": self.created_at,
            "artifacts": [
                {
                    "name": a.name,
                    "version": a.version,
                    "format": a.format.value,
                    "path": str(a.path),
                    "size": a.size,
                    "checksum": a.checksum,
                    "created_at": a.created_at,
                    "metadata": a.metadata
                }
                for a in self.artifacts
            ],
            "dependencies": self.dependencies,
            "checksums": self.checksums,
            "metadata": self.metadata
        }
        
        if self.notes:
            data["release_notes"] = {
                "version": self.notes.version,
                "date": self.notes.date,
                "summary": self.notes.summary,
                "features": self.notes.features,
                "fixes": self.notes.fixes,
                "breaking_changes": self.notes.breaking_changes,
                "deprecations": self.notes.deprecations,
                "known_issues": self.notes.known_issues,
                "contributors": self.notes.contributors
            }
        
        return json.dumps(data, indent=2)


class VersionManager:
    """Manage version numbers and bumping."""
    
    def __init__(self, project_file: Path):
        """Initialize version manager."""
        self.project_file = Path(project_file)
        self.current_version = self._read_current_version()
    
    def _read_current_version(self) -> str:
        """Read current version from project file."""
        if self.project_file.suffix == ".toml":
            with open(self.project_file, 'r') as f:
                data = toml.load(f)
                if "project" in data:
                    return data["project"].get("version", "0.0.0")
                elif "tool" in data and "poetry" in data["tool"]:
                    return data["tool"]["poetry"].get("version", "0.0.0")
        elif self.project_file.suffix == ".json":
            with open(self.project_file, 'r') as f:
                data = json.load(f)
                return data.get("version", "0.0.0")
        
        return "0.0.0"
    
    def bump_version(self, release_type: ReleaseType) -> str:
        """Bump version based on release type."""
        try:
            version = semver.VersionInfo.parse(self.current_version)
        except ValueError:
            # Handle non-semver versions
            version = semver.VersionInfo.parse("0.0.0")
        
        if release_type == ReleaseType.MAJOR:
            version = version.bump_major()
        elif release_type == ReleaseType.MINOR:
            version = version.bump_minor()
        elif release_type == ReleaseType.PATCH:
            version = version.bump_patch()
        elif release_type == ReleaseType.PRERELEASE:
            version = version.bump_prerelease()
        elif release_type == ReleaseType.BUILD:
            version = version.bump_build()
        
        new_version = str(version)
        self._update_version(new_version)
        return new_version
    
    def _update_version(self, new_version: str) -> None:
        """Update version in project file."""
        if self.project_file.suffix == ".toml":
            with open(self.project_file, 'r') as f:
                data = toml.load(f)
            
            if "project" in data:
                data["project"]["version"] = new_version
            elif "tool" in data and "poetry" in data["tool"]:
                data["tool"]["poetry"]["version"] = new_version
            
            with open(self.project_file, 'w') as f:
                toml.dump(data, f)
        
        elif self.project_file.suffix == ".json":
            with open(self.project_file, 'r') as f:
                data = json.load(f)
            
            data["version"] = new_version
            
            with open(self.project_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        self.current_version = new_version
        logger.info(f"Version updated to {new_version}")


class PackageBuilder:
    """Build release packages."""
    
    def __init__(self, project_dir: Path):
        """Initialize package builder."""
        self.project_dir = Path(project_dir)
        self.build_dir = self.project_dir / "build"
        self.dist_dir = self.project_dir / "dist"
    
    def build_wheel(self) -> ReleaseArtifact:
        """Build Python wheel package."""
        logger.info("Building wheel package")
        
        # Clean previous builds
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        
        # Build wheel
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Wheel build failed: {result.stderr}")
        
        # Find generated wheel
        wheel_files = list(self.dist_dir.glob("*.whl"))
        if not wheel_files:
            raise RuntimeError("No wheel file generated")
        
        wheel_file = wheel_files[0]
        
        # Create artifact
        artifact = ReleaseArtifact(
            name=wheel_file.name,
            version=self._extract_version_from_filename(wheel_file.name),
            format=PackageFormat.WHEEL,
            path=wheel_file,
            size=wheel_file.stat().st_size,
            checksum=""
        )
        artifact.checksum = artifact.calculate_checksum()
        
        return artifact
    
    def build_sdist(self) -> ReleaseArtifact:
        """Build source distribution."""
        logger.info("Building source distribution")
        
        # Build sdist
        result = subprocess.run(
            [sys.executable, "-m", "build", "--sdist"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Sdist build failed: {result.stderr}")
        
        # Find generated sdist
        sdist_files = list(self.dist_dir.glob("*.tar.gz"))
        if not sdist_files:
            raise RuntimeError("No sdist file generated")
        
        sdist_file = sdist_files[0]
        
        # Create artifact
        artifact = ReleaseArtifact(
            name=sdist_file.name,
            version=self._extract_version_from_filename(sdist_file.name),
            format=PackageFormat.SDIST,
            path=sdist_file,
            size=sdist_file.stat().st_size,
            checksum=""
        )
        artifact.checksum = artifact.calculate_checksum()
        
        return artifact
    
    def build_archive(self, format: PackageFormat = PackageFormat.TAR_GZ) -> ReleaseArtifact:
        """Build archive package."""
        logger.info(f"Building {format.value} archive")
        
        version = self._get_project_version()
        archive_name = f"voice-mode-{version}.{format.value}"
        archive_path = self.dist_dir / archive_name
        
        self.dist_dir.mkdir(exist_ok=True)
        
        if format == PackageFormat.TAR_GZ:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(self.project_dir, arcname=f"voice-mode-{version}")
        elif format == PackageFormat.ZIP:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.project_dir):
                    for file in files:
                        file_path = Path(root) / file
                        if not any(skip in str(file_path) for skip in [
                            "__pycache__", ".git", "dist", "build", ".egg-info"
                        ]):
                            arcname = str(file_path.relative_to(self.project_dir.parent))
                            zipf.write(file_path, arcname)
        
        # Create artifact
        artifact = ReleaseArtifact(
            name=archive_name,
            version=version,
            format=format,
            path=archive_path,
            size=archive_path.stat().st_size,
            checksum=""
        )
        artifact.checksum = artifact.calculate_checksum()
        
        return artifact
    
    def _extract_version_from_filename(self, filename: str) -> str:
        """Extract version from package filename."""
        # Pattern for wheel: name-version-py3-none-any.whl
        # Pattern for sdist: name-version.tar.gz
        match = re.search(r'-(\d+\.\d+\.\d+(?:\.\w+)?)', filename)
        if match:
            return match.group(1)
        return "unknown"
    
    def _get_project_version(self) -> str:
        """Get project version from pyproject.toml."""
        pyproject_file = self.project_dir / "pyproject.toml"
        if pyproject_file.exists():
            with open(pyproject_file, 'r') as f:
                data = toml.load(f)
                if "project" in data:
                    return data["project"].get("version", "0.0.0")
        return "0.0.0"


class DeploymentManager:
    """Manage deployment to various targets."""
    
    def __init__(self, artifacts_dir: Path):
        """Initialize deployment manager."""
        self.artifacts_dir = Path(artifacts_dir)
        self.deployed: List[Tuple[ReleaseArtifact, DeploymentTarget]] = []
    
    def deploy_to_pypi(self, artifact: ReleaseArtifact, test: bool = True) -> bool:
        """Deploy to PyPI."""
        target = DeploymentTarget.PYPI_TEST if test else DeploymentTarget.PYPI
        logger.info(f"Deploying {artifact.name} to {target.value}")
        
        # Use twine to upload
        repository_url = "https://test.pypi.org/legacy/" if test else "https://upload.pypi.org/legacy/"
        
        result = subprocess.run(
            [
                sys.executable, "-m", "twine", "upload",
                "--repository-url", repository_url,
                "--skip-existing",
                str(artifact.path)
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            self.deployed.append((artifact, target))
            logger.info(f"Successfully deployed to {target.value}")
            return True
        else:
            logger.error(f"Deployment failed: {result.stderr}")
            return False
    
    def deploy_to_github(self, artifact: ReleaseArtifact, tag: str) -> bool:
        """Deploy to GitHub releases."""
        logger.info(f"Deploying {artifact.name} to GitHub")
        
        # Use gh CLI to create/upload release
        result = subprocess.run(
            [
                "gh", "release", "upload", tag,
                str(artifact.path),
                "--clobber"
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            self.deployed.append((artifact, DeploymentTarget.GITHUB))
            logger.info("Successfully deployed to GitHub")
            return True
        else:
            logger.error(f"GitHub deployment failed: {result.stderr}")
            return False
    
    def deploy_local(self, artifact: ReleaseArtifact, destination: Path) -> bool:
        """Deploy to local directory."""
        logger.info(f"Deploying {artifact.name} locally to {destination}")
        
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        
        target_path = destination / artifact.name
        shutil.copy2(artifact.path, target_path)
        
        # Verify copy
        if target_path.exists():
            self.deployed.append((artifact, DeploymentTarget.LOCAL))
            logger.info(f"Successfully deployed to {target_path}")
            return True
        else:
            logger.error("Local deployment failed")
            return False
    
    def generate_deployment_report(self) -> str:
        """Generate deployment report."""
        report_lines = [
            "Deployment Report",
            "=" * 50,
            f"Total artifacts deployed: {len(self.deployed)}",
            ""
        ]
        
        # Group by target
        by_target = {}
        for artifact, target in self.deployed:
            if target not in by_target:
                by_target[target] = []
            by_target[target].append(artifact)
        
        for target, artifacts in by_target.items():
            report_lines.append(f"\n{target.value}:")
            for artifact in artifacts:
                report_lines.append(f"  - {artifact.name} ({artifact.size} bytes)")
        
        return "\n".join(report_lines)


class ReleaseValidator:
    """Validate release before deployment."""
    
    def __init__(self, project_dir: Path):
        """Initialize release validator."""
        self.project_dir = Path(project_dir)
        self.checks_passed: List[str] = []
        self.checks_failed: List[str] = []
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        logger.info("Running release validation")
        
        checks = [
            self.check_version,
            self.check_changelog,
            self.check_tests,
            self.check_documentation,
            self.check_dependencies,
            self.check_license,
            self.check_security
        ]
        
        for check in checks:
            try:
                if check():
                    self.checks_passed.append(check.__name__)
                else:
                    self.checks_failed.append(check.__name__)
            except Exception as e:
                logger.error(f"Check {check.__name__} failed: {e}")
                self.checks_failed.append(check.__name__)
        
        return len(self.checks_failed) == 0
    
    def check_version(self) -> bool:
        """Check version format and consistency."""
        logger.info("Checking version...")
        
        pyproject = self.project_dir / "pyproject.toml"
        if not pyproject.exists():
            return False
        
        with open(pyproject, 'r') as f:
            data = toml.load(f)
        
        version = data.get("project", {}).get("version")
        if not version:
            return False
        
        # Validate semver format
        try:
            semver.VersionInfo.parse(version)
            return True
        except ValueError:
            return False
    
    def check_changelog(self) -> bool:
        """Check for updated changelog."""
        logger.info("Checking changelog...")
        
        changelog_files = [
            "CHANGELOG.md",
            "CHANGELOG.rst",
            "HISTORY.md",
            "NEWS.md"
        ]
        
        for filename in changelog_files:
            changelog = self.project_dir / filename
            if changelog.exists():
                # Check if recently modified
                mtime = changelog.stat().st_mtime
                if time.time() - mtime < 86400:  # Modified in last 24 hours
                    return True
        
        return False
    
    def check_tests(self) -> bool:
        """Check if tests pass."""
        logger.info("Checking tests...")
        
        # Run pytest
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
    
    def check_documentation(self) -> bool:
        """Check documentation completeness."""
        logger.info("Checking documentation...")
        
        docs_dir = self.project_dir / "docs"
        readme = self.project_dir / "README.md"
        
        return docs_dir.exists() or readme.exists()
    
    def check_dependencies(self) -> bool:
        """Check for dependency issues."""
        logger.info("Checking dependencies...")
        
        # Check for security vulnerabilities
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
    
    def check_license(self) -> bool:
        """Check for license file."""
        logger.info("Checking license...")
        
        license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"]
        
        for filename in license_files:
            if (self.project_dir / filename).exists():
                return True
        
        return False
    
    def check_security(self) -> bool:
        """Check for security issues."""
        logger.info("Checking security...")
        
        # Basic security checks
        suspicious_patterns = [
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']'
        ]
        
        for py_file in self.project_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            with open(py_file, 'r') as f:
                content = f.read()
            
            for pattern in suspicious_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    logger.warning(f"Potential security issue in {py_file}")
                    return False
        
        return True
    
    def generate_validation_report(self) -> str:
        """Generate validation report."""
        report_lines = [
            "Release Validation Report",
            "=" * 50,
            f"Checks passed: {len(self.checks_passed)}",
            f"Checks failed: {len(self.checks_failed)}",
            ""
        ]
        
        if self.checks_passed:
            report_lines.append("✓ Passed Checks:")
            for check in self.checks_passed:
                report_lines.append(f"  - {check}")
        
        if self.checks_failed:
            report_lines.append("\n✗ Failed Checks:")
            for check in self.checks_failed:
                report_lines.append(f"  - {check}")
        
        return "\n".join(report_lines)


class ReleaseManager:
    """Main release manager coordinating all operations."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize release manager."""
        if not hasattr(self, 'initialized'):
            self.project_dir = Path.cwd()
            self.pyproject_file = self.project_dir / "pyproject.toml"
            self.version_manager = VersionManager(self.pyproject_file)
            self.package_builder = PackageBuilder(self.project_dir)
            self.deployment_manager = DeploymentManager(self.project_dir / "dist")
            self.validator = ReleaseValidator(self.project_dir)
            self.manifests: List[ReleaseManifest] = []
            self.initialized = True
    
    def create_release(
        self,
        release_type: ReleaseType,
        notes: Optional[ReleaseNotes] = None,
        validate: bool = True,
        build_formats: List[PackageFormat] = None
    ) -> ReleaseManifest:
        """Create a new release."""
        logger.info(f"Creating {release_type.value} release")
        
        # Validate first if requested
        if validate:
            if not self.validator.validate_all():
                logger.warning("Validation failed - review report")
                print(self.validator.generate_validation_report())
        
        # Bump version
        new_version = self.version_manager.bump_version(release_type)
        logger.info(f"Version bumped to {new_version}")
        
        # Build packages
        if build_formats is None:
            build_formats = [PackageFormat.WHEEL, PackageFormat.SDIST]
        
        artifacts = []
        for format in build_formats:
            if format == PackageFormat.WHEEL:
                artifact = self.package_builder.build_wheel()
            elif format == PackageFormat.SDIST:
                artifact = self.package_builder.build_sdist()
            else:
                artifact = self.package_builder.build_archive(format)
            
            artifacts.append(artifact)
            logger.info(f"Built {artifact.name}")
        
        # Create manifest
        manifest = ReleaseManifest(
            version=new_version,
            release_type=release_type,
            artifacts=artifacts,
            notes=notes
        )
        
        # Save manifest
        self.save_manifest(manifest)
        self.manifests.append(manifest)
        
        return manifest
    
    def deploy_release(
        self,
        manifest: ReleaseManifest,
        targets: List[DeploymentTarget]
    ) -> bool:
        """Deploy release to specified targets."""
        logger.info(f"Deploying release {manifest.version}")
        
        success = True
        for target in targets:
            for artifact in manifest.artifacts:
                if target == DeploymentTarget.PYPI_TEST:
                    if artifact.format in [PackageFormat.WHEEL, PackageFormat.SDIST]:
                        success &= self.deployment_manager.deploy_to_pypi(artifact, test=True)
                elif target == DeploymentTarget.PYPI:
                    if artifact.format in [PackageFormat.WHEEL, PackageFormat.SDIST]:
                        success &= self.deployment_manager.deploy_to_pypi(artifact, test=False)
                elif target == DeploymentTarget.GITHUB:
                    success &= self.deployment_manager.deploy_to_github(
                        artifact,
                        f"v{manifest.version}"
                    )
                elif target == DeploymentTarget.LOCAL:
                    success &= self.deployment_manager.deploy_local(
                        artifact,
                        self.project_dir / "releases" / manifest.version
                    )
        
        return success
    
    def save_manifest(self, manifest: ReleaseManifest) -> None:
        """Save release manifest."""
        manifests_dir = self.project_dir / "releases" / "manifests"
        manifests_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_file = manifests_dir / f"release-{manifest.version}.json"
        with open(manifest_file, 'w') as f:
            f.write(manifest.to_json())
        
        logger.info(f"Manifest saved to {manifest_file}")
    
    def load_manifest(self, version: str) -> Optional[ReleaseManifest]:
        """Load release manifest."""
        manifest_file = self.project_dir / "releases" / "manifests" / f"release-{version}.json"
        
        if not manifest_file.exists():
            return None
        
        with open(manifest_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct manifest
        manifest = ReleaseManifest(
            version=data["version"],
            release_type=ReleaseType(data["release_type"]),
            created_at=data["created_at"],
            dependencies=data.get("dependencies", {}),
            checksums=data.get("checksums", {}),
            metadata=data.get("metadata", {})
        )
        
        # Reconstruct artifacts
        for artifact_data in data.get("artifacts", []):
            artifact = ReleaseArtifact(
                name=artifact_data["name"],
                version=artifact_data["version"],
                format=PackageFormat(artifact_data["format"]),
                path=Path(artifact_data["path"]),
                size=artifact_data["size"],
                checksum=artifact_data["checksum"],
                created_at=artifact_data["created_at"],
                metadata=artifact_data.get("metadata", {})
            )
            manifest.artifacts.append(artifact)
        
        # Reconstruct release notes
        if "release_notes" in data:
            notes_data = data["release_notes"]
            manifest.notes = ReleaseNotes(
                version=notes_data["version"],
                date=notes_data["date"],
                summary=notes_data["summary"],
                features=notes_data.get("features", []),
                fixes=notes_data.get("fixes", []),
                breaking_changes=notes_data.get("breaking_changes", []),
                deprecations=notes_data.get("deprecations", []),
                known_issues=notes_data.get("known_issues", []),
                contributors=notes_data.get("contributors", [])
            )
        
        return manifest
    
    def generate_release_summary(self) -> str:
        """Generate release summary."""
        summary_lines = [
            "Release Manager Summary",
            "=" * 50,
            f"Current version: {self.version_manager.current_version}",
            f"Project directory: {self.project_dir}",
            f"Manifests created: {len(self.manifests)}",
            ""
        ]
        
        if self.manifests:
            summary_lines.append("Recent Releases:")
            for manifest in self.manifests[-5:]:
                summary_lines.append(f"  - v{manifest.version} ({manifest.release_type.value})")
                summary_lines.append(f"    Artifacts: {len(manifest.artifacts)}")
                summary_lines.append(f"    Created: {manifest.created_at}")
        
        # Add deployment summary
        if self.deployment_manager.deployed:
            summary_lines.append("\nDeployments:")
            summary_lines.append(self.deployment_manager.generate_deployment_report())
        
        return "\n".join(summary_lines)


# Singleton instance
_release_manager = None


def get_release_manager() -> ReleaseManager:
    """Get the singleton release manager instance."""
    global _release_manager
    if _release_manager is None:
        _release_manager = ReleaseManager()
    return _release_manager


if __name__ == "__main__":
    # Example usage
    manager = get_release_manager()
    
    # Create release notes
    notes = ReleaseNotes(
        version="1.0.0",
        date=time.strftime("%Y-%m-%d"),
        summary="Initial stable release of VoiceMode",
        features=[
            "Voice conversation support",
            "Multiple TTS/STT providers",
            "MCP protocol integration"
        ],
        fixes=[
            "Fixed audio feedback issues",
            "Improved silence detection"
        ]
    )
    
    # Create and deploy release
    manifest = manager.create_release(
        release_type=ReleaseType.STABLE,
        notes=notes,
        validate=True
    )
    
    print(manager.generate_release_summary())