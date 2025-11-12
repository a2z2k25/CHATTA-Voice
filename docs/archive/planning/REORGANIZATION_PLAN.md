# CHATTA Project Reorganization Plan

## Current Issues
- Test files mixed with source code at root level
- Documentation scattered throughout
- Configuration files not centralized
- Demo/example files mixed with core code
- No clear separation of concerns

## New Directory Structure

```
CHATTA/
├── src/                      # Source code
│   └── voice_mode/          # Core voice mode package (unchanged)
├── tests/                   # All test files
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── performance/        # Performance tests
│   └── manual/             # Manual test scripts
├── examples/               # Demo and example scripts
│   ├── basic/             # Basic usage examples
│   └── advanced/          # Advanced usage examples
├── docs/                   # Documentation
│   ├── api/               # API documentation
│   ├── guides/            # User guides
│   ├── sprints/           # Sprint documentation
│   └── reports/           # Audit and achievement reports
├── config/                 # Configuration files
│   ├── development/       # Dev configs
│   ├── production/        # Prod configs
│   └── optimization/      # Optimization configs
├── scripts/               # Utility scripts
│   ├── setup/            # Setup and installation
│   ├── monitoring/       # Monitoring scripts
│   └── deployment/       # Deployment scripts
├── docker/                # Docker related files
├── .github/              # GitHub specific files
└── [root files]          # README, LICENSE, pyproject.toml, etc.
```

## File Mapping Plan

### Tests → tests/
- test_*.py → tests/unit/ or tests/integration/
- demo_*.py → examples/
- verify_*.py → tests/integration/
- simple_*.py → examples/basic/
- interactive_*.py → examples/advanced/

### Documentation → docs/
- *.md (documentation) → docs/guides/ or docs/reports/
- SPRINT_*.md → docs/sprints/
- *_REPORT.md → docs/reports/
- *_PLAN.md → docs/guides/

### Scripts → scripts/
- build_*.py → scripts/deployment/
- optimize_*.py → scripts/monitoring/
- comprehensive_system_audit.py → scripts/monitoring/
- performance_monitor.py → scripts/monitoring/

### Configuration → config/
- *.json configs → config/
- .env* files → config/development/
- docker-compose.yml → docker/

## Safety Measures
1. Create directories first
2. Copy (not move) files initially
3. Verify all imports still work
4. Run tests after reorganization
5. Only delete originals after verification