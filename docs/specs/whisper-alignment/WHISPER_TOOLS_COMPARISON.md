# Whisper Model Management Tools Comparison (Updated)

## Quick Comparison Table

| Function | CLI Command | MCP Tool | Recommendation |
|----------|------------|----------|----------------|
| **Service Management** |
| Start service | `whisper start` | `service("whisper", "start")` | Keep aligned ✅ |
| Stop service | `whisper stop` | `service("whisper", "stop")` | Keep aligned ✅ |
| Restart service | `whisper restart` | `service("whisper", "restart")` | Keep aligned ✅ |
| Service status | `whisper status` | `service("whisper", "status")` | Keep aligned ✅ |
| Enable at boot | `whisper enable` | `service("whisper", "enable")` | Keep aligned ✅ |
| Disable at boot | `whisper disable` | `service("whisper", "disable")` | Keep aligned ✅ |
| View logs | `whisper logs` | `service("whisper", "logs")` | Keep aligned ✅ |
| **Installation** |
| Install whisper.cpp | `whisper install` | `whisper_install()` | Keep aligned ✅ |
| Uninstall whisper.cpp | `whisper uninstall` | `whisper_uninstall()` | Keep aligned ✅ |
| **Model Management** |
| List models | `whisper models` | `whisper_list_models()` | Rename MCP to `whisper_models()` |
| Show/set active model | `whisper model active [NAME]` | ❌ Missing | Add `whisper_model_active()` |
| Install model | `whisper model install [NAME]` | `download_model()` | Rename MCP to `whisper_model_install()` |
| Remove model | `whisper model remove NAME` | ❌ Missing | Add `whisper_model_remove()` |
| Benchmark models | ❌ Missing | ❌ Missing | Add `whisper_model_benchmark()` to both |
| **Configuration** |
| Update config | N/A | `update_config()` | Keep for MCP only ✅ |

## Current MCP Tools (voice-mode MCP server)

### Model Management Tools
1. **`mcp__voice-mode__download_model`**
   - Downloads Whisper models
   - Parameters: model (name/list/"all"), force_download, skip_core_ml
   - Auto-converts to Core ML on Apple Silicon

2. **`mcp__voice-mode__whisper_list_models`**
   - Lists available models and installation status
   - Shows model sizes, language support, currently selected

3. **`mcp__voice-mode__whisper_install`**
   - Installs whisper.cpp with system detection
   - Parameters: install_dir, model, use_gpu, force_reinstall, auto_enable, version

4. **`mcp__voice-mode__whisper_uninstall`**
   - Uninstalls whisper.cpp
   - Parameters: remove_models, remove_all_data

5. **`mcp__voice-mode__update_config`**
   - Updates configuration values
   - Can set VOICEMODE_WHISPER_MODEL to change active model

6. **`mcp__voice-mode__service`**
   - Service management (start/stop/restart)
   - Required after changing active model

## Voice Mode CLI Tools (cli.py)

### Service Commands (`voicemode whisper`)
- `status` - Show Whisper service status
- `start` - Start Whisper service
- `stop` - Stop Whisper service
- `restart` - Restart Whisper service
- `enable` - Enable service at boot/login
- `disable` - Disable service from boot/login
- `logs` - View service logs (--lines/-n option)
- `update-service-files` - Update service files to latest
- `health` - Check Whisper health endpoint
- `install` - Install whisper.cpp
- `uninstall` - Uninstall whisper.cpp

### Model Commands (`voicemode whisper`)
- **`models`** - List available models and installation status
- **`model active [MODEL_NAME]`** - Show or set active model
- **`model install [MODEL]`** - Install model(s) with Core ML
- **`model remove MODEL`** - Remove installed model

## Comparison & Alignment

### Well-Aligned Tools
✅ Both have model listing functionality
✅ Both have model download/install
✅ Both have service management
✅ Both have uninstall capabilities

### Naming Inconsistencies

| MCP Tool | CLI Command | Recommended MCP Name |
|----------|-------------|---------------------|
| `download_model` | `whisper model install` | `whisper_model_install` |
| `whisper_list_models` | `whisper models` | `whisper_models` |
| `whisper_install` | `whisper install` | `whisper_install` (keep) |
| `whisper_uninstall` | `whisper uninstall` | `whisper_uninstall` (keep) |
| - | `whisper model active` | `whisper_model_active` (NEW) |
| - | `whisper model remove` | `whisper_model_remove` (NEW) |

### Gaps in MCP Tools

1. **No `whisper_model_active`** - CLI has it, MCP doesn't
   - Currently requires `update_config` + service restart
   - Should be a single convenient tool

2. **No `whisper_model_remove`** - CLI has it, MCP doesn't
   - Can't remove individual models via MCP

3. **No benchmark tool** - Neither CLI nor MCP has it
   - Would be valuable for performance optimization

## Recommended Changes

### 1. Rename Existing MCP Tools (Big-endian naming for grouping)
```python
# Current -> Recommended
download_model -> whisper_model_install
whisper_list_models -> whisper_models
```

### 2. Add Missing MCP Tools to Match CLI
```python
def whisper_model_active(model_name: str = None, restart_service: bool = True):
    """Show or set the active Whisper model.
    If model_name is None, shows current model.
    If provided, sets model and optionally restarts service."""
    
def whisper_model_remove(model_name: str, remove_coreml: bool = True):
    """Remove an installed Whisper model and its Core ML version."""
```

### 3. Add New Enhancement Tools
```python
def whisper_model_benchmark(
    models: Union[str, List[str]] = "installed",
    sample_file: str = None,
    runs: int = 3
):
    """Benchmark model performance.
    models: 'installed', 'all', specific model name, or list
    Returns speed metrics and recommendations."""
```

### 4. Enhanced Existing Tools
```python
def whisper_models():
    """Enhanced listing with:
    - Installed status with checkmarks
    - Core ML conversion status
    - Current active model indicator
    - Model characteristics (speed/accuracy)
    - Disk space used/required"""
```

## Implementation Priority

1. **Critical** - Add `whisper_model_active` 
   - Most common user need
   - CLI already has it

2. **High** - Rename tools to match CLI convention
   - `download_model` → `whisper_model_install`
   - `whisper_list_models` → `whisper_models`

3. **High** - Add `whisper_model_remove`
   - CLI already has it
   - Disk space management

4. **Medium** - Add `whisper_model_benchmark`
   - New functionality for both CLI and MCP
   - Helps users optimize

5. **Low** - Enhance `whisper_models` output
   - Quality of life improvement

## Summary

The CLI and MCP tools have similar functionality but different naming conventions. The CLI uses a hierarchical command structure (`whisper model active`) while MCP uses flat naming (`whisper_list_models`). 

Key recommendations:
- Adopt big-endian naming (`whisper_model_*`) for better grouping
- Add the two missing tools that CLI has (`active`, `remove`)
- Add benchmark functionality that neither currently has
- Maintain consistency between CLI and MCP interfaces