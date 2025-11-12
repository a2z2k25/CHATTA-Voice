# Whisper Tools Alignment Implementation Specification

## Overview
This specification details the exact changes needed to align Whisper model management tools across CLI, MCP, and core layers for consistency and feature parity.

## File Structure
```
specs/whisper-alignment/
├── IMPLEMENTATION_SPEC.md           (this file - implementation guide)
├── WHISPER_ALIGNMENT.md            (complete alignment recommendations)
├── WHISPER_TOOLS_COMPARISON.md     (CLI vs MCP comparison table)
└── WHISPER_FUNCTIONS_ANALYSIS.md   (underlying function analysis)
```

## Implementation Tasks

### PHASE 1: Core Layer Changes
**Priority: HIGH - Must be done first as other layers depend on these**

#### Task 1.1: Rename Core Functions in `voice_mode/tools/services/whisper/models.py`

**File:** `voice_mode/tools/services/whisper/models.py`

**Changes:**
```python
# Line numbers are approximate - search for function names

# RENAME: get_current_model -> get_active_model
# Find: def get_current_model() -> str:
# Replace with: def get_active_model() -> str:

# RENAME: set_current_model -> set_active_model  
# Find: def set_current_model(model_name: str) -> None:
# Replace with: def set_active_model(model_name: str) -> None:

# ADD WHISPER PREFIX to functions for clarity:
# Find: def is_model_installed(model_name: str) -> bool:
# Replace with: def is_whisper_model_installed(model_name: str) -> bool:

# Find: def get_installed_models() -> List[str]:
# Replace with: def get_installed_whisper_models() -> List[str]:

# Find: def has_coreml_model(model_name: str) -> bool:
# Replace with: def has_whisper_coreml_model(model_name: str) -> bool:

# RENAME CONSTANT for clarity:
# Find: WHISPER_MODELS = {
# Replace with: WHISPER_MODEL_REGISTRY = {
```

#### Task 1.2: Add New Core Functions to `models.py`

**Add these new functions to `voice_mode/tools/services/whisper/models.py`:**

```python
def remove_whisper_model(model_name: str, remove_coreml: bool = True) -> Dict[str, Any]:
    """Remove a whisper model and optionally its Core ML version.
    
    Args:
        model_name: Name of the model to remove
        remove_coreml: Also remove Core ML version if it exists
        
    Returns:
        Dict with success status and space freed
    """
    model_dir = get_model_directory()
    model_file = model_dir / f"ggml-{model_name}.bin"
    
    if not model_file.exists():
        return {"success": False, "error": f"Model {model_name} not found"}
    
    space_freed = model_file.stat().st_size
    model_file.unlink()
    
    if remove_coreml and has_whisper_coreml_model(model_name):
        coreml_file = model_dir / f"ggml-{model_name}-encoder.mlmodel"
        if coreml_file.exists():
            space_freed += coreml_file.stat().st_size
            coreml_file.unlink()
    
    return {
        "success": True,
        "model": model_name,
        "space_freed": space_freed
    }

def benchmark_whisper_model(model_name: str, sample_file: str = None) -> Dict[str, Any]:
    """Run performance benchmark on a whisper model.
    
    Args:
        model_name: Name of the model to benchmark
        sample_file: Optional audio file to use (defaults to JFK sample)
        
    Returns:
        Dict with benchmark results
    """
    # Implementation would run whisper-cli with timing
    # This is a placeholder structure
    return {
        "model": model_name,
        "encode_time_ms": 0,
        "total_time_ms": 0,
        "real_time_factor": 0,
        "sample_duration": 11.0
    }
```

#### Task 1.3: Update All References to Renamed Functions

**Files to update:** Search entire codebase for old function names and update:
- `voice_mode/tools/services/whisper/list_models.py`
- `voice_mode/tools/services/whisper/list_models_tool.py`
- `voice_mode/cli.py`
- Any other files that import from `models.py`

**Search and Replace:**
- `get_current_model` → `get_active_model`
- `set_current_model` → `set_active_model`
- `is_model_installed` → `is_whisper_model_installed`
- `get_installed_models` → `get_installed_whisper_models`
- `has_coreml_model` → `has_whisper_coreml_model`
- `WHISPER_MODELS` → `WHISPER_MODEL_REGISTRY`

### PHASE 2: MCP Tool Changes
**Priority: HIGH - After Phase 1 is complete**

#### Task 2.1: Rename MCP Tool Files

**Rename files in `voice_mode/tools/services/whisper/`:**
- `download_model.py` → `model_install.py`
- `list_models_tool.py` → DELETE (duplicate functionality)
- `list_models.py` → `models_list.py`

#### Task 2.2: Update MCP Tool Functions

**File:** `voice_mode/tools/services/whisper/model_install.py` (renamed from download_model.py)
```python
# Change function name:
# From: async def download_model(
# To: async def whisper_model_install(
```

**File:** `voice_mode/tools/services/whisper/models_list.py` (renamed from list_models.py)
```python
# Change function name:
# From: async def list_whisper_models() -> Dict[str, Any]:
# To: async def whisper_models() -> Dict[str, Any]:
```

#### Task 2.3: Create New MCP Tool Files

**Create:** `voice_mode/tools/services/whisper/model_active.py`
```python
"""MCP tool for showing/setting active Whisper model."""

from typing import Optional, Dict, Any
from voice_mode.tools.services.whisper.models import (
    get_active_model,
    set_active_model,
    is_whisper_model_installed,
    WHISPER_MODEL_REGISTRY
)

async def whisper_model_active(model_name: Optional[str] = None) -> Dict[str, Any]:
    """Show or set the active Whisper model.
    
    Args:
        model_name: Model to set as active (None to just show current)
        
    Returns:
        Dict with current/new active model info
    """
    if model_name is None:
        # Just show current
        current = get_active_model()
        return {
            "active_model": current,
            "installed": is_whisper_model_installed(current)
        }
    
    # Set new active model
    if not is_whisper_model_installed(model_name):
        return {
            "success": False,
            "error": f"Model {model_name} is not installed"
        }
    
    set_active_model(model_name)
    return {
        "success": True,
        "active_model": model_name,
        "message": f"Active model set to {model_name}"
    }
```

**Create:** `voice_mode/tools/services/whisper/model_remove.py`
```python
"""MCP tool for removing Whisper models."""

from typing import Dict, Any
from voice_mode.tools.services.whisper.models import (
    remove_whisper_model,
    get_active_model
)

async def whisper_model_remove(model_name: str, remove_coreml: bool = True) -> Dict[str, Any]:
    """Remove an installed Whisper model.
    
    Args:
        model_name: Name of model to remove
        remove_coreml: Also remove Core ML version
        
    Returns:
        Dict with removal status
    """
    # Check if trying to remove active model
    if model_name == get_active_model():
        return {
            "success": False,
            "error": f"Cannot remove active model {model_name}. Set a different model as active first."
        }
    
    return remove_whisper_model(model_name, remove_coreml)
```

**Create:** `voice_mode/tools/services/whisper/model_benchmark.py`
```python
"""MCP tool for benchmarking Whisper models."""

from typing import Union, List, Dict, Any
from voice_mode.tools.services.whisper.models import (
    get_installed_whisper_models,
    benchmark_whisper_model
)

async def whisper_model_benchmark(
    models: Union[str, List[str]] = "installed",
    sample_file: str = None
) -> Dict[str, Any]:
    """Benchmark Whisper model performance.
    
    Args:
        models: 'installed', 'all', model name, or list of models
        sample_file: Optional audio file for testing
        
    Returns:
        Dict with benchmark results
    """
    if models == "installed":
        model_list = get_installed_whisper_models()
    elif models == "all":
        model_list = list(WHISPER_MODEL_REGISTRY.keys())
    elif isinstance(models, str):
        model_list = [models]
    else:
        model_list = models
    
    results = []
    for model in model_list:
        if is_whisper_model_installed(model):
            result = benchmark_whisper_model(model, sample_file)
            results.append(result)
    
    return {
        "benchmarks": results,
        "fastest": min(results, key=lambda x: x["total_time_ms"])["model"],
        "recommendation": "Use base or medium for balanced speed/accuracy"
    }
```

#### Task 2.4: Update MCP Server Registration

**File:** `voice_mode/server.py` or wherever MCP tools are registered

Update tool registrations to use new names:
```python
# Update imports
from voice_mode.tools.services.whisper.model_install import whisper_model_install
from voice_mode.tools.services.whisper.models_list import whisper_models
from voice_mode.tools.services.whisper.model_active import whisper_model_active
from voice_mode.tools.services.whisper.model_remove import whisper_model_remove
from voice_mode.tools.services.whisper.model_benchmark import whisper_model_benchmark

# Register tools with new names
# Old: download_model -> New: whisper_model_install
# Old: whisper_list_models -> New: whisper_models
# Add: whisper_model_active
# Add: whisper_model_remove
# Add: whisper_model_benchmark
```

### PHASE 3: CLI Updates
**Priority: MEDIUM - After Phase 2**

#### Task 3.1: Add Benchmark Command to CLI

**File:** `voice_mode/cli.py`

Add new command under whisper_model group:
```python
@whisper_model.command("benchmark")
@click.option('--models', default='installed', help='Models to benchmark: installed, all, or comma-separated list')
@click.option('--sample', help='Audio file to use for benchmarking')
def whisper_model_benchmark_cmd(models, sample):
    """Benchmark Whisper model performance."""
    from voice_mode.tools.services.whisper.model_benchmark import whisper_model_benchmark
    
    if ',' in models:
        model_list = models.split(',')
    else:
        model_list = models
    
    result = asyncio.run(whisper_model_benchmark(model_list, sample))
    
    # Format output
    click.echo("Whisper Model Benchmark Results")
    click.echo("=" * 40)
    for bench in result['benchmarks']:
        click.echo(f"{bench['model']}:")
        click.echo(f"  Encode: {bench['encode_time_ms']}ms")
        click.echo(f"  Total: {bench['total_time_ms']}ms")
        click.echo(f"  Speed: {bench['real_time_factor']}x real-time")
    click.echo(f"\nFastest: {result['fastest']}")
    click.echo(f"Recommendation: {result['recommendation']}")
```

## Testing Checklist

After implementation, test these commands:

### CLI Tests
```bash
# Should all work consistently
voicemode whisper models
voicemode whisper model active
voicemode whisper model active base
voicemode whisper model install tiny
voicemode whisper model remove tiny
voicemode whisper model benchmark --models installed
```

### MCP Tests (via LLM)
```
# Should all work with new names
whisper_models()
whisper_model_active()
whisper_model_active("base")
whisper_model_install("tiny")
whisper_model_remove("tiny")
whisper_model_benchmark("installed")
```

## Success Criteria

1. ✅ All core functions use consistent "active" terminology
2. ✅ All core functions have "whisper" prefix for clarity
3. ✅ MCP tools match CLI command naming pattern
4. ✅ No duplicate MCP tool files
5. ✅ Feature parity between CLI and MCP
6. ✅ Benchmark functionality available in both interfaces
7. ✅ All tests pass without errors

### PHASE 4: Documentation Updates
**Priority: MEDIUM - After core implementation**

#### Task 4.1: Update AI Context Files

**File:** `.ai/README.md` or `.claude/README.md` (if exists)
Add section about Whisper model management:
```markdown
## Whisper Model Management

The voice-mode package provides consistent model management across CLI and MCP:

### Naming Convention
- CLI commands: `voicemode whisper model <action>`
- MCP tools: `whisper_model_<action>()`
- Core functions: Use "active" terminology, prefixed with `whisper_`

### Available Operations
- `whisper_models()` - List all models and status
- `whisper_model_active()` - Get/set active model
- `whisper_model_install()` - Download and install models
- `whisper_model_remove()` - Remove installed models
- `whisper_model_benchmark()` - Benchmark model performance
```

**File:** `CLAUDE.md` or similar AI instruction file
Add:
```markdown
## Whisper Model Tools

When working with Whisper models, use these standardized tools:
- List models: `whisper_models()` not `whisper_list_models()`
- Set active: `whisper_model_active("model-name")`
- Install: `whisper_model_install("model-name")`
- Remove: `whisper_model_remove("model-name")`
- Benchmark: `whisper_model_benchmark()`

Core functions in `models.py` use `get_active_model()` not `get_current_model()`.
```

#### Task 4.2: Update User Documentation

**File:** `docs/whisper.md` or `README.md` sections
Update all references to reflect new naming:

```markdown
## Whisper Model Management

### CLI Commands
```bash
# List available models
voicemode whisper models

# Show active model
voicemode whisper model active

# Set active model
voicemode whisper model active base

# Install a model
voicemode whisper model install tiny

# Remove a model
voicemode whisper model remove tiny

# Benchmark models
voicemode whisper model benchmark
```

### MCP Tools (for LLMs)
```python
# List models
whisper_models()

# Get/set active model
whisper_model_active()
whisper_model_active("base")

# Install model
whisper_model_install("tiny")

# Remove model
whisper_model_remove("tiny")

# Benchmark
whisper_model_benchmark()
```
```

### PHASE 5: Test Updates
**Priority: HIGH - Must be updated with code changes**

#### Task 5.1: Update Unit Tests

**Files to update:**
- `tests/test_whisper_models.py`
- `tests/test_whisper_tools.py`
- `tests/test_cli.py`

**Changes needed:**
```python
# Update all test imports
# Old:
from voice_mode.tools.services.whisper.models import get_current_model
# New:
from voice_mode.tools.services.whisper.models import get_active_model

# Update test function names
# Old:
def test_get_current_model():
# New:
def test_get_active_model():

# Update assertions
# Old:
assert get_current_model() == "large-v3-turbo"
# New:
assert get_active_model() == "large-v3-turbo"
```

#### Task 5.2: Add New Tests

**Create:** `tests/test_whisper_model_benchmark.py`
```python
import pytest
from voice_mode.tools.services.whisper.model_benchmark import whisper_model_benchmark

@pytest.mark.asyncio
async def test_benchmark_installed_models():
    result = await whisper_model_benchmark("installed")
    assert "benchmarks" in result
    assert "fastest" in result
    assert isinstance(result["benchmarks"], list)

@pytest.mark.asyncio
async def test_benchmark_single_model():
    result = await whisper_model_benchmark("tiny")
    assert len(result["benchmarks"]) == 1
    assert result["benchmarks"][0]["model"] == "tiny"
```

**Create:** `tests/test_whisper_model_active.py`
```python
import pytest
from voice_mode.tools.services.whisper.model_active import whisper_model_active

@pytest.mark.asyncio
async def test_get_active_model():
    result = await whisper_model_active()
    assert "active_model" in result
    assert "installed" in result

@pytest.mark.asyncio
async def test_set_active_model():
    result = await whisper_model_active("base")
    assert result["success"] == True
    assert result["active_model"] == "base"
```

### PHASE 6: Shell Completion Updates
**Priority: LOW - Nice to have**

#### Task 6.1: Update Bash Completion

**File:** `completions/voicemode.bash` or similar
```bash
# Add new commands to completion
_voicemode_whisper_model() {
    local commands="active install remove benchmark"
    COMPREPLY=($(compgen -W "${commands}" -- "${COMP_WORDS[COMP_CWORD]}"))
}

# Add model name completion
_voicemode_whisper_model_active() {
    local models="tiny base small medium large-v3-turbo"
    COMPREPLY=($(compgen -W "${models}" -- "${COMP_WORDS[COMP_CWORD]}"))
}
```

#### Task 6.2: Update Zsh Completion

**File:** `completions/_voicemode` or similar
```zsh
# Add whisper model subcommands
_voicemode_whisper_model_commands() {
    local -a commands
    commands=(
        'active:Show or set active model'
        'install:Install a model'
        'remove:Remove a model'
        'benchmark:Benchmark model performance'
    )
    _describe 'command' commands
}

# Add model name completion
_whisper_models() {
    local -a models
    models=(tiny base small medium large-v3-turbo)
    _describe 'model' models
}
```

### PHASE 7: Migration & Backwards Compatibility
**Priority: MEDIUM - For smooth transition**

#### Task 7.1: Add Deprecation Warnings

**File:** `voice_mode/tools/services/whisper/models.py`
```python
import warnings

def get_current_model() -> str:
    """DEPRECATED: Use get_active_model() instead."""
    warnings.warn(
        "get_current_model() is deprecated. Use get_active_model() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return get_active_model()

def set_current_model(model_name: str) -> None:
    """DEPRECATED: Use set_active_model() instead."""
    warnings.warn(
        "set_current_model() is deprecated. Use set_active_model() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return set_active_model(model_name)
```

#### Task 7.2: Add Aliases for MCP Tools

**File:** MCP server registration
```python
# Register both old and new names temporarily
tools = {
    # New names (primary)
    "whisper_models": whisper_models,
    "whisper_model_active": whisper_model_active,
    "whisper_model_install": whisper_model_install,
    
    # Old names (deprecated aliases)
    "whisper_list_models": whisper_models,  # Alias
    "download_model": whisper_model_install,  # Alias
}
```

## Notes for Implementing LLM

1. Start with Phase 1 (core changes) as everything depends on it
2. Use search/replace for function renames to catch all references
3. Run tests after each phase to ensure nothing breaks
4. The benchmark implementation can be basic initially and enhanced later
5. Preserve all existing functionality while adding new features

## Related Documentation

- See `WHISPER_ALIGNMENT.md` for rationale behind changes
- See `WHISPER_TOOLS_COMPARISON.md` for CLI vs MCP comparison
- See `WHISPER_FUNCTIONS_ANALYSIS.md` for function relationships