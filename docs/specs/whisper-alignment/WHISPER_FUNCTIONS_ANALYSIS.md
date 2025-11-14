# Underlying Function Analysis

## Shared Module: `voice_mode.tools.services.whisper.models`

Both CLI and MCP tools import from the same shared module that provides core functionality:

### Core Functions in `models.py`:
- `get_model_directory()` - Returns path to model directory
- `get_current_model()` - Gets active model from config
- `set_current_model()` - Sets active model in config
- `is_model_installed()` - Checks if model file exists
- `get_installed_models()` - Lists all installed models
- `has_coreml_model()` - Checks for Core ML version
- `format_size()` - Formats file sizes
- `WHISPER_MODELS` - Dictionary of model metadata

## Function Mapping

| Function | CLI Implementation | MCP Implementation | Underlying Module |
|----------|-------------------|-------------------|-------------------|
| **List Models** |
| | `cli.py: whisper_models()` | `list_models_tool.py: whisper_list_models()` | Both use `models.py` functions |
| | Imports from `models.py` | Also has `list_models.py: list_whisper_models()` | Same: `get_installed_models()`, `get_current_model()` |
| **Active Model** |
| | `cli.py: whisper_model_active()` | ❌ Missing MCP tool | Uses `models.py: get/set_current_model()` |
| **Install Model** |
| | `cli.py: whisper_model_install()` | `download_model.py: download_model()` | Both use same download logic |
| | Calls `download_model.download_model()` | Direct implementation | Same underlying function |
| **Remove Model** |
| | `cli.py: whisper_model_remove()` | ❌ Missing MCP tool | Would use `models.py` functions |
| **Install Whisper** |
| | `cli.py: install()` | `install.py: whisper_install()` | Same implementation |
| **Uninstall Whisper** |
| | `cli.py: uninstall()` | `uninstall.py: whisper_uninstall()` | Same implementation |

## Key Findings

### 1. Shared Core Module
- Both CLI and MCP use `voice_mode.tools.services.whisper.models` for core functionality
- This ensures consistency between interfaces

### 2. Naming Inconsistency in MCP
- MCP has TWO list models functions:
  - `list_models_tool.py: whisper_list_models()` (returns string)
  - `list_models.py: list_whisper_models()` (returns dict)
- This duplication should be resolved

### 3. Missing MCP Functions
- `whisper_model_active()` - CLI has it, uses `models.py: set_current_model()`
- `whisper_model_remove()` - CLI has it, uses basic file operations

### 4. Function Naming Pattern
- CLI uses verb_noun: `whisper_model_install()`
- MCP uses noun_verb: `download_model()`
- Should standardize on CLI pattern for consistency

## Recommendations

### 1. Rename Core Functions for Consistency
To align with CLI command naming (`whisper model active`), consider renaming in `models.py`:
```python
# Current -> Recommended
get_current_model() -> get_active_model()
set_current_model() -> set_active_model()
# This makes the terminology consistent across all layers
```

### 2. Consolidate MCP List Functions
Remove duplication between `list_models_tool.py` and `list_models.py`:
```python
# Keep one implementation in list_models.py
async def whisper_models() -> str:  # Renamed to match CLI
    """List available Whisper models and their installation status."""
    # Use existing list_whisper_models() logic
```

### 2. Add Missing MCP Functions
```python
# In new file: active_model.py
async def whisper_model_active(model_name: str = None) -> str:
    """Show or set the active Whisper model."""
    from voice_mode.tools.services.whisper.models import (
        get_current_model, set_current_model
    )
    # Implementation using shared models.py functions

# In new file: remove_model.py  
async def whisper_model_remove(model_name: str) -> Dict[str, Any]:
    """Remove an installed Whisper model."""
    from voice_mode.tools.services.whisper.models import (
        is_model_installed, get_model_directory
    )
    # Implementation using shared models.py functions
```

### 4. Additional Core Function Alignments
Consider these additional renamings in `models.py` for better consistency:
```python
# Current -> Recommended  
is_model_installed() -> is_whisper_model_installed()  # More explicit
get_installed_models() -> get_installed_whisper_models()  # Clearer scope
has_coreml_model() -> has_whisper_coreml_model()  # Namespace clarity
WHISPER_MODELS -> WHISPER_MODEL_REGISTRY  # Better describes purpose
```

### 5. Add Missing Core Functions
Add these to `models.py` to support new features:
```python
def remove_whisper_model(model_name: str, remove_coreml: bool = True) -> bool:
    """Remove a whisper model and optionally its Core ML version."""
    # Core logic for model removal
    
def benchmark_whisper_model(model_name: str, sample_file: str = None) -> Dict:
    """Run performance benchmark on a model."""
    # Core benchmarking logic
```

### 6. Rename for Consistency
```python
# Current -> Recommended
download_model() -> whisper_model_install()
whisper_list_models() -> whisper_models()
```

This ensures both CLI and MCP:
- Use the same underlying functions from `models.py`
- Have consistent naming patterns
- Provide the same functionality to users