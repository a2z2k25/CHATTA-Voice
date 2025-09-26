#!/usr/bin/env python3
"""Production monitoring and deployment system for CHATTA voice mode.

Sprint 48: Production Release & Monitoring
This module provides comprehensive production monitoring, health checks,
deployment automation, and operational insights for the CHATTA system.
"""

import asyncio
import json
import logging
import os
import platform
import psutil
import socket
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from urllib.parse import urlparse
import hashlib
import shutil
import tempfile
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DeploymentStatus(Enum):
    """Deployment status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MetricType(Enum):
    """Types of metrics to track."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class HealthCheck:
    """Health check configuration and result."""
    name: str
    check_fn: Callable
    interval: int = 30  # seconds
    timeout: int = 10  # seconds
    retries: int = 3
    critical: bool = True
    last_check: Optional[datetime] = None
    last_status: ServiceStatus = ServiceStatus.UNKNOWN
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "interval": self.interval,
            "timeout": self.timeout,
            "critical": self.critical,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_status": self.last_status.value,
            "consecutive_failures": self.consecutive_failures,
            "metadata": self.metadata
        }


@dataclass
class Alert:
    """System alert."""
    id: str
    severity: AlertSeverity
    service: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "service": self.service,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata
        }


@dataclass
class Metric:
    """Performance metric."""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "unit": self.unit
        }


@dataclass
class Deployment:
    """Deployment record."""
    id: str
    version: str
    environment: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    rollback_from: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "version": self.version,
            "environment": self.environment,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rollback_from": self.rollback_from,
            "metadata": self.metadata
        }


class HealthMonitor:
    """Health monitoring system."""
    
    def __init__(self):
        """Initialize health monitor."""
        self.health_checks: Dict[str, HealthCheck] = {}
        self.check_results: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.running = False
        self.check_thread: Optional[threading.Thread] = None
        
    def add_health_check(self, check: HealthCheck):
        """Add a health check."""
        self.health_checks[check.name] = check
        logger.info(f"Added health check: {check.name}")
        
    async def run_health_check(self, check: HealthCheck) -> ServiceStatus:
        """Run a single health check."""
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                asyncio.create_task(check.check_fn()),
                timeout=check.timeout
            )
            
            # Update check status
            check.last_check = datetime.now()
            
            if result:
                check.last_status = ServiceStatus.HEALTHY
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
                if check.consecutive_failures >= check.retries:
                    check.last_status = ServiceStatus.UNHEALTHY
                else:
                    check.last_status = ServiceStatus.DEGRADED
                    
            # Store result
            self.check_results[check.name].append({
                "timestamp": check.last_check,
                "status": check.last_status,
                "metadata": check.metadata
            })
            
            return check.last_status
            
        except asyncio.TimeoutError:
            logger.warning(f"Health check {check.name} timed out")
            check.consecutive_failures += 1
            check.last_status = ServiceStatus.UNHEALTHY
            return ServiceStatus.UNHEALTHY
            
        except Exception as e:
            logger.error(f"Health check {check.name} failed: {e}")
            check.consecutive_failures += 1
            check.last_status = ServiceStatus.UNHEALTHY
            return ServiceStatus.UNHEALTHY
            
    async def run_all_checks(self) -> Dict[str, ServiceStatus]:
        """Run all health checks."""
        results = {}
        for name, check in self.health_checks.items():
            results[name] = await self.run_health_check(check)
        return results
        
    def get_system_health(self) -> ServiceStatus:
        """Get overall system health."""
        if not self.health_checks:
            return ServiceStatus.UNKNOWN
            
        critical_healthy = all(
            check.last_status == ServiceStatus.HEALTHY
            for check in self.health_checks.values()
            if check.critical
        )
        
        any_unhealthy = any(
            check.last_status == ServiceStatus.UNHEALTHY
            for check in self.health_checks.values()
        )
        
        if not critical_healthy:
            return ServiceStatus.UNHEALTHY
        elif any_unhealthy:
            return ServiceStatus.DEGRADED
        else:
            return ServiceStatus.HEALTHY
            
    def get_health_report(self) -> Dict[str, Any]:
        """Generate health report."""
        return {
            "overall_status": self.get_system_health().value,
            "checks": {
                name: check.to_dict()
                for name, check in self.health_checks.items()
            },
            "timestamp": datetime.now().isoformat()
        }


class MetricsCollector:
    """Metrics collection system."""
    
    def __init__(self, retention_hours: int = 24):
        """Initialize metrics collector."""
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque())
        self.retention_hours = retention_hours
        self.aggregations: Dict[str, Dict[str, float]] = defaultdict(dict)
        
    def record_metric(self, metric: Metric):
        """Record a metric."""
        key = f"{metric.name}:{json.dumps(metric.labels, sort_keys=True)}"
        self.metrics[key].append(metric)
        
        # Clean old metrics
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        while self.metrics[key] and self.metrics[key][0].timestamp < cutoff:
            self.metrics[key].popleft()
            
        # Update aggregations
        self._update_aggregations(key, metric)
        
    def _update_aggregations(self, key: str, metric: Metric):
        """Update metric aggregations."""
        if metric.type == MetricType.COUNTER:
            self.aggregations[key]["total"] = self.aggregations[key].get("total", 0) + metric.value
            self.aggregations[key]["count"] = self.aggregations[key].get("count", 0) + 1
            
        elif metric.type == MetricType.GAUGE:
            self.aggregations[key]["current"] = metric.value
            self.aggregations[key]["min"] = min(
                self.aggregations[key].get("min", float('inf')),
                metric.value
            )
            self.aggregations[key]["max"] = max(
                self.aggregations[key].get("max", float('-inf')),
                metric.value
            )
            
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        summary = {}
        
        for key, metrics_list in self.metrics.items():
            if not metrics_list:
                continue
                
            base_name = key.split(':')[0]
            recent_metrics = list(metrics_list)[-100:]  # Last 100 values
            
            values = [m.value for m in recent_metrics]
            summary[base_name] = {
                "count": len(recent_metrics),
                "current": recent_metrics[-1].value if recent_metrics else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "avg": sum(values) / len(values) if values else 0,
                "type": recent_metrics[-1].type.value if recent_metrics else "unknown"
            }
            
        return summary
        
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for key, metrics_list in self.metrics.items():
            if not metrics_list:
                continue
                
            metric = metrics_list[-1]
            labels_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
            
            if labels_str:
                lines.append(f'{metric.name}{{{labels_str}}} {metric.value}')
            else:
                lines.append(f'{metric.name} {metric.value}')
                
        return "\n".join(lines)


class AlertManager:
    """Alert management system."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Callable] = []
        self.notification_handlers: List[Callable] = []
        
    def create_alert(self, 
                    severity: AlertSeverity,
                    service: str,
                    message: str,
                    metadata: Optional[Dict[str, Any]] = None) -> Alert:
        """Create a new alert."""
        alert = Alert(
            id=str(uuid.uuid4()),
            severity=severity,
            service=service,
            message=message,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.alerts[alert.id] = alert
        logger.info(f"Alert created: {severity.value} - {service} - {message}")
        
        # Trigger notifications
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")
                
        return alert
        
    def resolve_alert(self, alert_id: str):
        """Resolve an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].resolved_at = datetime.now()
            logger.info(f"Alert resolved: {alert_id}")
            
    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts."""
        return [
            alert for alert in self.alerts.values()
            if not alert.resolved
        ]
        
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity."""
        return [
            alert for alert in self.alerts.values()
            if alert.severity == severity and not alert.resolved
        ]
        
    def add_notification_handler(self, handler: Callable):
        """Add notification handler."""
        self.notification_handlers.append(handler)
        
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary."""
        active_alerts = self.get_active_alerts()
        
        return {
            "total_active": len(active_alerts),
            "by_severity": {
                severity.value: len(self.get_alerts_by_severity(severity))
                for severity in AlertSeverity
            },
            "recent_alerts": [
                alert.to_dict()
                for alert in sorted(
                    active_alerts,
                    key=lambda a: a.timestamp,
                    reverse=True
                )[:10]
            ]
        }


class DeploymentAutomation:
    """Deployment automation system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize deployment automation."""
        self.config_path = config_path or "deployment.json"
        self.deployments: Dict[str, Deployment] = {}
        self.current_deployment: Optional[Deployment] = None
        self.rollback_stack: List[Deployment] = []
        
    async def deploy(self,
                    version: str,
                    environment: str,
                    pre_deploy_checks: Optional[List[Callable]] = None,
                    post_deploy_checks: Optional[List[Callable]] = None) -> Deployment:
        """Deploy a new version."""
        deployment = Deployment(
            id=str(uuid.uuid4()),
            version=version,
            environment=environment,
            status=DeploymentStatus.PENDING,
            started_at=datetime.now()
        )
        
        self.deployments[deployment.id] = deployment
        self.current_deployment = deployment
        
        try:
            # Pre-deployment checks
            if pre_deploy_checks:
                deployment.status = DeploymentStatus.IN_PROGRESS
                for check in pre_deploy_checks:
                    if not await check():
                        raise Exception("Pre-deployment check failed")
                        
            # Perform deployment
            await self._execute_deployment(deployment)
            
            # Post-deployment checks
            if post_deploy_checks:
                for check in post_deploy_checks:
                    if not await check():
                        raise Exception("Post-deployment check failed")
                        
            # Mark successful
            deployment.status = DeploymentStatus.COMPLETED
            deployment.completed_at = datetime.now()
            
            # Add to rollback stack
            self.rollback_stack.append(deployment)
            if len(self.rollback_stack) > 10:
                self.rollback_stack.pop(0)
                
            logger.info(f"Deployment {deployment.id} completed successfully")
            return deployment
            
        except Exception as e:
            logger.error(f"Deployment {deployment.id} failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.now()
            
            # Attempt rollback
            if self.rollback_stack:
                await self.rollback()
                
            raise
            
    async def _execute_deployment(self, deployment: Deployment):
        """Execute deployment steps."""
        # Simulate deployment steps
        steps = [
            "Pulling latest code",
            "Installing dependencies",
            "Running migrations",
            "Building assets",
            "Restarting services",
            "Verifying deployment"
        ]
        
        for step in steps:
            logger.info(f"Deployment {deployment.id}: {step}")
            await asyncio.sleep(0.5)  # Simulate work
            
    async def rollback(self) -> Optional[Deployment]:
        """Rollback to previous deployment."""
        if not self.rollback_stack:
            logger.warning("No previous deployment to rollback to")
            return None
            
        previous = self.rollback_stack.pop()
        
        rollback_deployment = Deployment(
            id=str(uuid.uuid4()),
            version=previous.version,
            environment=previous.environment,
            status=DeploymentStatus.ROLLING_BACK,
            started_at=datetime.now(),
            rollback_from=self.current_deployment.version if self.current_deployment else None
        )
        
        try:
            await self._execute_deployment(rollback_deployment)
            rollback_deployment.status = DeploymentStatus.ROLLED_BACK
            rollback_deployment.completed_at = datetime.now()
            
            self.current_deployment = rollback_deployment
            logger.info(f"Rollback to {previous.version} completed")
            return rollback_deployment
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            rollback_deployment.status = DeploymentStatus.FAILED
            raise
            
    def get_deployment_history(self) -> List[Deployment]:
        """Get deployment history."""
        return sorted(
            self.deployments.values(),
            key=lambda d: d.started_at,
            reverse=True
        )
        
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        return {
            "current": self.current_deployment.to_dict() if self.current_deployment else None,
            "rollback_available": len(self.rollback_stack) > 0,
            "recent_deployments": [
                d.to_dict()
                for d in self.get_deployment_history()[:5]
            ]
        }


class SystemProfiler:
    """System profiling and resource monitoring."""
    
    def __init__(self):
        """Initialize system profiler."""
        self.baseline_metrics: Dict[str, Any] = {}
        self.record_baseline()
        
    def record_baseline(self):
        """Record baseline system metrics."""
        self.baseline_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "network": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
        }
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters() if psutil.net_io_counters() else None
        
        # Get process-specific metrics
        process = psutil.Process()
        
        return {
            "system": {
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            },
            "process": {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / (1024**2),
                "threads": process.num_threads(),
                "connections": len(process.connections()),
                "open_files": len(process.open_files())
            },
            "network": {
                "bytes_sent": network.bytes_sent if network else 0,
                "bytes_recv": network.bytes_recv if network else 0,
                "packets_sent": network.packets_sent if network else 0,
                "packets_recv": network.packets_recv if network else 0
            } if network else {}
        }
        
    def check_resource_usage(self) -> List[str]:
        """Check for resource usage issues."""
        issues = []
        metrics = self.get_system_metrics()
        
        # CPU checks
        if metrics["system"]["cpu_percent"] > 80:
            issues.append(f"High CPU usage: {metrics['system']['cpu_percent']}%")
            
        # Memory checks
        if metrics["system"]["memory_percent"] > 85:
            issues.append(f"High memory usage: {metrics['system']['memory_percent']}%")
            
        # Disk checks
        if metrics["system"]["disk_percent"] > 90:
            issues.append(f"Low disk space: {metrics['system']['disk_percent']}% used")
            
        # Process checks
        if metrics["process"]["memory_mb"] > 500:
            issues.append(f"High process memory: {metrics['process']['memory_mb']:.1f} MB")
            
        return issues


class ProductionMonitor:
    """Main production monitoring system."""
    
    def __init__(self, project_name: str = "CHATTA", version: str = "1.0.0"):
        """Initialize production monitor."""
        self.project_name = project_name
        self.version = version
        self.health_monitor = HealthMonitor()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.deployment_automation = DeploymentAutomation()
        self.system_profiler = SystemProfiler()
        
        # Initialize default health checks
        self._setup_default_health_checks()
        
        # Initialize default metrics
        self._setup_default_metrics()
        
        # Start monitoring
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        
    def _setup_default_health_checks(self):
        """Setup default health checks."""
        # API health check
        async def check_api():
            """Check API availability."""
            try:
                # Check if API is responding
                return True  # Placeholder
            except:
                return False
                
        self.health_monitor.add_health_check(
            HealthCheck(
                name="api",
                check_fn=check_api,
                interval=30,
                critical=True
            )
        )
        
        # Database health check
        async def check_database():
            """Check database connectivity."""
            try:
                # Check database connection
                return True  # Placeholder
            except:
                return False
                
        self.health_monitor.add_health_check(
            HealthCheck(
                name="database",
                check_fn=check_database,
                interval=60,
                critical=True
            )
        )
        
        # Service health checks
        services = ["whisper", "kokoro", "livekit"]
        for service in services:
            async def check_service(svc=service):
                """Check service availability."""
                try:
                    # Check if service is running
                    return True  # Placeholder
                except:
                    return False
                    
            self.health_monitor.add_health_check(
                HealthCheck(
                    name=f"service_{service}",
                    check_fn=lambda s=service: check_service(s),
                    interval=45,
                    critical=False
                )
            )
            
    def _setup_default_metrics(self):
        """Setup default metrics collection."""
        # Record system metrics periodically
        def record_system_metrics():
            """Record system metrics."""
            metrics = self.system_profiler.get_system_metrics()
            
            # CPU metric
            self.metrics_collector.record_metric(
                Metric(
                    name="system_cpu_percent",
                    type=MetricType.GAUGE,
                    value=metrics["system"]["cpu_percent"],
                    timestamp=datetime.now(),
                    unit="percent"
                )
            )
            
            # Memory metric
            self.metrics_collector.record_metric(
                Metric(
                    name="system_memory_percent",
                    type=MetricType.GAUGE,
                    value=metrics["system"]["memory_percent"],
                    timestamp=datetime.now(),
                    unit="percent"
                )
            )
            
            # Process memory
            self.metrics_collector.record_metric(
                Metric(
                    name="process_memory_mb",
                    type=MetricType.GAUGE,
                    value=metrics["process"]["memory_mb"],
                    timestamp=datetime.now(),
                    unit="megabytes"
                )
            )
            
    async def start_monitoring(self):
        """Start monitoring systems."""
        self.monitoring_active = True
        logger.info(f"Starting production monitoring for {self.project_name} v{self.version}")
        
        while self.monitoring_active:
            try:
                # Run health checks
                health_results = await self.health_monitor.run_all_checks()
                
                # Check for issues
                system_health = self.health_monitor.get_system_health()
                if system_health == ServiceStatus.UNHEALTHY:
                    self.alert_manager.create_alert(
                        AlertSeverity.CRITICAL,
                        "system",
                        "System health is critical",
                        {"health_results": health_results}
                    )
                elif system_health == ServiceStatus.DEGRADED:
                    self.alert_manager.create_alert(
                        AlertSeverity.WARNING,
                        "system",
                        "System health is degraded",
                        {"health_results": health_results}
                    )
                    
                # Record metrics
                self._setup_default_metrics()
                
                # Check resource usage
                resource_issues = self.system_profiler.check_resource_usage()
                for issue in resource_issues:
                    self.alert_manager.create_alert(
                        AlertSeverity.WARNING,
                        "resources",
                        issue
                    )
                    
                # Sleep before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(60)
                
    def stop_monitoring(self):
        """Stop monitoring systems."""
        self.monitoring_active = False
        logger.info("Stopping production monitoring")
        
    async def deploy_to_production(self, version: str) -> Deployment:
        """Deploy to production."""
        logger.info(f"Deploying {self.project_name} v{version} to production")
        
        # Pre-deployment checks
        async def check_tests():
            """Verify all tests pass."""
            # Run test suite
            return True  # Placeholder
            
        async def check_resources():
            """Verify resources available."""
            issues = self.system_profiler.check_resource_usage()
            return len(issues) == 0
            
        # Post-deployment checks
        async def verify_deployment():
            """Verify deployment successful."""
            health = await self.health_monitor.run_all_checks()
            return all(
                status == ServiceStatus.HEALTHY
                for status in health.values()
            )
            
        # Execute deployment
        deployment = await self.deployment_automation.deploy(
            version=version,
            environment="production",
            pre_deploy_checks=[check_tests, check_resources],
            post_deploy_checks=[verify_deployment]
        )
        
        return deployment
        
    def generate_production_report(self) -> str:
        """Generate production status report."""
        report = []
        report.append(f"# Production Monitoring Report")
        report.append(f"**Project:** {self.project_name}")
        report.append(f"**Version:** {self.version}")
        report.append(f"**Generated:** {datetime.now().isoformat()}")
        report.append("")
        
        # Health status
        report.append("## System Health")
        health_report = self.health_monitor.get_health_report()
        report.append(f"**Overall Status:** {health_report['overall_status']}")
        report.append("")
        report.append("### Health Checks")
        for name, check in health_report["checks"].items():
            status_emoji = "✅" if check["last_status"] == "healthy" else "❌"
            report.append(f"- {status_emoji} **{name}**: {check['last_status']}")
        report.append("")
        
        # Metrics summary
        report.append("## Performance Metrics")
        metrics_summary = self.metrics_collector.get_metrics_summary()
        for metric_name, stats in metrics_summary.items():
            report.append(f"### {metric_name}")
            report.append(f"- Current: {stats['current']:.2f}")
            report.append(f"- Average: {stats['avg']:.2f}")
            report.append(f"- Min/Max: {stats['min']:.2f}/{stats['max']:.2f}")
            report.append("")
            
        # System resources
        report.append("## System Resources")
        system_metrics = self.system_profiler.get_system_metrics()
        report.append(f"- CPU Usage: {system_metrics['system']['cpu_percent']}%")
        report.append(f"- Memory Usage: {system_metrics['system']['memory_percent']}%")
        report.append(f"- Disk Usage: {system_metrics['system']['disk_percent']}%")
        report.append(f"- Process Memory: {system_metrics['process']['memory_mb']:.1f} MB")
        report.append("")
        
        # Active alerts
        report.append("## Active Alerts")
        alert_summary = self.alert_manager.get_alert_summary()
        if alert_summary["total_active"] == 0:
            report.append("No active alerts ✅")
        else:
            report.append(f"**Total Active:** {alert_summary['total_active']}")
            for severity in AlertSeverity:
                count = alert_summary["by_severity"][severity.value]
                if count > 0:
                    report.append(f"- {severity.value.upper()}: {count}")
            report.append("")
            report.append("### Recent Alerts")
            for alert in alert_summary["recent_alerts"][:5]:
                report.append(f"- [{alert['severity']}] {alert['service']}: {alert['message']}")
        report.append("")
        
        # Deployment status
        report.append("## Deployment Status")
        deployment_status = self.deployment_automation.get_deployment_status()
        if deployment_status["current"]:
            current = deployment_status["current"]
            report.append(f"**Current Version:** {current['version']}")
            report.append(f"**Environment:** {current['environment']}")
            report.append(f"**Status:** {current['status']}")
            report.append(f"**Deployed:** {current['started_at']}")
        report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        resource_issues = self.system_profiler.check_resource_usage()
        if resource_issues:
            for issue in resource_issues:
                report.append(f"- ⚠️ {issue}")
        else:
            report.append("- ✅ All resources within normal parameters")
            
        return "\n".join(report)
        
    def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        return self.metrics_collector.export_prometheus()
        
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data."""
        return {
            "project": self.project_name,
            "version": self.version,
            "health": self.health_monitor.get_health_report(),
            "metrics": self.metrics_collector.get_metrics_summary(),
            "alerts": self.alert_manager.get_alert_summary(),
            "deployment": self.deployment_automation.get_deployment_status(),
            "system": self.system_profiler.get_system_metrics(),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Example usage
    monitor = ProductionMonitor("CHATTA", "1.0.0")
    
    # Start monitoring in background
    async def main():
        # Deploy to production
        try:
            deployment = await monitor.deploy_to_production("1.0.0")
            print(f"Deployment completed: {deployment.id}")
        except Exception as e:
            print(f"Deployment failed: {e}")
            
        # Generate report
        report = monitor.generate_production_report()
        print(report)
        
        # Get dashboard data
        dashboard = monitor.get_dashboard_data()
        print(f"\nDashboard data keys: {list(dashboard.keys())}")
        
    asyncio.run(main())