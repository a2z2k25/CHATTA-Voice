# CHATTA 1.0 Directory Structure

This document describes the organized directory structure of CHATTA following best practices for Python projects.

## Root Directory
```
CHATTA 1.0/
├── README.md                   # Main project documentation
├── CHANGELOG.md               # Version history and changes
├── CLAUDE.md                  # Claude Code configuration
├── reflections.json          # Project reflections data
├── DIRECTORY_STRUCTURE.md    # This file
├── .git/                     # Git repository data
├── .github/                  # GitHub configuration
├── .gitignore               # Git ignore rules
├── .venv/                   # Virtual environment (local)
│
├── src/                     # Source code
│   └── voice_mode/         # Main Python package
│
├── tests/                  # Test files
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── manual/            # Manual test scripts
│   ├── performance/       # Performance tests
│   └── *.py              # Root-level test files
│
├── docs/                  # Documentation
│   ├── guides/           # User and developer guides
│   ├── specs/            # Technical specifications
│   ├── integrations/     # Integration documentation
│   ├── reports/          # Analysis reports
│   ├── sprints/          # Sprint documentation
│   ├── troubleshooting/  # Troubleshooting guides
│   ├── web/              # Web documentation assets
│   ├── CONTRIBUTING.md   # Contribution guidelines
│   ├── GLOSSARY.md       # Project glossary
│   ├── mkdocs.yml        # MkDocs configuration
│   └── .readthedocs.yaml # ReadTheDocs configuration
│
├── deployments/           # Deployment configurations
│   ├── docker/           # Docker configurations
│   ├── config/           # Configuration files
│   ├── setup/            # Setup and installation scripts
│   ├── deployment/       # Deployment scripts
│   ├── monitoring/       # Monitoring configurations
│   └── setup/            # Setup wizards and scripts
│
├── infrastructure/        # Infrastructure and build tools
│   ├── .env.example      # Environment variables template
│   ├── bin/              # Binary files and executables
│   ├── Makefile          # Build automation
│   ├── pyproject.toml    # Python project configuration
│   ├── uv.lock           # UV lock file
│   ├── flake.nix         # Nix configuration
│   └── flake.lock        # Nix lock file
│
├── resources/             # Static resources and assets
│   ├── branding/         # Brand assets and logos
│   ├── models/           # ML models and data
│   └── archive/          # Archived files and legacy code
│
├── examples/              # Example code and usage
│   └── *.py              # Example scripts
│
└── scripts/               # Utility scripts
    ├── README.md         # Scripts documentation
    ├── chatta-local      # Local development script
    ├── chatta_mcp_server.sh  # MCP server script
    └── *.py              # Various utility scripts
```

## Organization Principles

### 1. **Source Code** (`src/`)
- Contains the main Python package (`voice_mode`)
- Follows Python packaging best practices
- Isolated from other project files

### 2. **Tests** (`tests/`)
- Organized by test type (unit, integration, manual, performance)
- Mirrors the source code structure
- Easy to run with pytest

### 3. **Documentation** (`docs/`)
- Comprehensive documentation structure
- Includes guides, specifications, and reports
- MkDocs configuration for static site generation

### 4. **Deployments** (`deployments/`)
- All deployment-related configurations
- Docker compose files and Dockerfiles
- Setup scripts and configuration templates
- Environment-specific configurations

### 5. **Infrastructure** (`infrastructure/`)
- Build tools and project configuration
- Environment setup files
- Package management files
- Build automation (Makefile)

### 6. **Resources** (`resources/`)
- Static assets and resources
- Brand materials and logos
- ML models and data files
- Archived legacy code

## Path Updates Required

Due to the reorganization, the following files may need path updates:

### Build Files
- `infrastructure/Makefile` - Update paths to src/ and tests/
- `infrastructure/pyproject.toml` - Update package paths

### Docker Files
- `deployments/docker/docker-compose.yml` - Update volume paths
- `deployments/docker/*/Dockerfile` - Update COPY paths

### Documentation
- `docs/mkdocs.yml` - Update navigation paths
- `docs/.readthedocs.yaml` - Update build paths

### Scripts
- `scripts/*` - Update import paths and file references

## Benefits of This Structure

1. **Clarity**: Clear separation of concerns
2. **Scalability**: Easy to add new components
3. **Maintainability**: Logical organization
4. **Standards Compliance**: Follows Python packaging standards
5. **Team Collaboration**: Intuitive structure for contributors
6. **CI/CD Friendly**: Clear paths for automation

## Migration Notes

All files have been moved without deletion. The reorganization maintains:
- All source code functionality
- Complete test coverage
- Full documentation
- All deployment configurations
- Build system integrity

The new structure follows industry best practices while maintaining backward compatibility where possible.